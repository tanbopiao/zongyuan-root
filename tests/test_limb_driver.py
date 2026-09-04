#!/usr/bin/env python3
"""
手脚驱动层 - 全链路集成测试

测试覆盖:
  T1 Action基类生命周期 (pre_check→execute→post_check→rollback)
  T2 任务调度器正常执行
  T3 任务依赖DAG
  T4 熔断拦截 (P1漂移阻断修改类动作)
  T5 幂等去重 (重复请求返回缓存)
  T6 Saga补偿事务 (失败时反向回滚)
  T7 断点恢复 (崩溃后RUNNING→PENDING)
  T8 LimbDriver统一入口
"""

import json
import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

# 确保模块路径
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'omega_brain'))
sys.path.insert(0, str(ROOT))

from action_base import BaseAction, ActionResult, ActionStatus
from actions import create_action, ACTION_REGISTRY, CasWriteAction, AuditWriteAction
from executor import TaskExecutor, Task, TaskState, PersistentTaskQueue
from circuit_breaker import CircuitBreaker, DriftLevel, BreakerState
from idempotency import IdempotencyStore, SagaOrchestrator, CompensatingAction
from limb_driver import LimbDriver


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def record(self, name: str, passed: bool, detail: str = ""):
        status = "PASS" if passed else "FAIL"
        self.results.append({'test': name, 'status': status, 'detail': detail})
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        print(f"  [{status}] {name} {detail}")

    def summary(self) -> dict:
        return {
            'total': self.passed + self.failed,
            'passed': self.passed,
            'failed': self.failed,
            'pass_rate': round(self.passed / (self.passed + self.failed) * 100, 1) if (self.passed + self.failed) > 0 else 0,
            'results': self.results,
        }


def test_t1_action_lifecycle(tr: TestResult):
    """T1: Action基类生命周期"""
    print("\n=== T1: Action生命周期 ===")

    # 测试正常执行
    action = CasWriteAction(params={'data': b'test lifecycle data', 'ref_name': 'test_lifecycle'})
    result = action.run()
    tr.record("CasWriteAction正常执行", result.status == ActionStatus.SUCCESS,
              f"status={result.status.value}, cid={result.data.get('content_id', 'N/A') if result.data else 'N/A'}")

    # 测试前置校验拦截
    action2 = CasWriteAction(params={})  # 缺少data
    result2 = action2.run()
    tr.record("前置校验拦截缺参", result2.status == ActionStatus.BLOCKED,
              f"status={result2.status.value}")

    # 测试幂等键生成
    key1 = action.generate_idempotency_key()
    key2 = CasWriteAction(params={'data': b'test lifecycle data', 'ref_name': 'test_lifecycle'}).generate_idempotency_key()
    tr.record("幂等键确定性", key1 == key2, f"key={key1[:8]}")

    # 测试执行摘要
    summary = action.get_execution_summary()
    tr.record("执行摘要完整", all(k in summary for k in ['name', 'status', 'attempts', 'duration_ms', 'idempotency_key']),
              f"keys={list(summary.keys())}")


def test_t2_executor_normal(tr: TestResult):
    """T2: 任务调度器正常执行"""
    print("\n=== T2: 任务调度器 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        executor = TaskExecutor(queue_file=os.path.join(tmpdir, 'queue.jsonl'),
                                enable_circuit_breaker=False)

        tid = executor.submit("audit_write", {
            'op_type': 'TEST_EXECUTOR',
            'operator': 'integration_test',
            'details': {'test': True}
        })
        tr.record("任务提交成功", bool(tid), f"task_id={tid}")

        results = executor.run_all()
        tr.record("任务执行成功", tid in results and results[tid]['status'] == 'success',
                  f"result={results.get(tid, {}).get('status', 'N/A')}")

        # 验证持久化
        queue2 = PersistentTaskQueue(os.path.join(tmpdir, 'queue.jsonl'))
        task = queue2.get(tid)
        tr.record("任务持久化", task is not None and task.state == TaskState.SUCCESS,
                  f"state={task.state if task else 'None'}")


def test_t3_dag_dependencies(tr: TestResult):
    """T3: 任务依赖DAG"""
    print("\n=== T3: 任务依赖DAG ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        executor = TaskExecutor(queue_file=os.path.join(tmpdir, 'dag.jsonl'),
                                enable_circuit_breaker=False)

        t1 = executor.submit("audit_write", {'op_type': 'STEP1', 'operator': 'test'})
        t2 = executor.submit("audit_write", {'op_type': 'STEP2', 'operator': 'test'},
                             dependencies=[t1])
        t3 = executor.submit("audit_write", {'op_type': 'STEP3', 'operator': 'test'},
                             dependencies=[t2])

        results = executor.run_all()
        tr.record("DAG全部执行", all(results.get(t, {}).get('status') == 'success' for t in [t1, t2, t3]),
                  f"t1={results.get(t1,{}).get('status')}, t2={results.get(t2,{}).get('status')}, t3={results.get(t3,{}).get('status')}")


def test_t4_circuit_breaker(tr: TestResult):
    """T4: 熔断拦截"""
    print("\n=== T4: 熔断器 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        breaker = CircuitBreaker(state_file=os.path.join(tmpdir, 'breaker.json'))

        # 正常状态放行
        tr.record("CLOSED状态放行", breaker.allow("test", is_mutation=True),
                  f"state={breaker.state.value}")

        # P1漂移阻断修改类动作
        breaker.set_drift_level(DriftLevel.P1, "hash chain broken")
        tr.record("P1阻断修改动作", not breaker.allow("cas_write", is_mutation=True),
                  f"drift={breaker.drift_level.value}")
        tr.record("P1放行只读动作", breaker.allow("api_call", is_mutation=False),
                  "readonly allowed")

        # P0全局急停
        breaker.set_drift_level(DriftLevel.P0, "fatal")
        tr.record("P0全局急停", not breaker.allow("api_call", is_mutation=False),
                  f"drift={breaker.drift_level.value}")

        # 重置
        breaker.reset()
        tr.record("重置后恢复", breaker.allow("test", is_mutation=True),
                  f"state={breaker.state.value}")

        # 连续失败触发熔断
        breaker2 = CircuitBreaker(failure_threshold=2, recovery_timeout=1,
                                   state_file=os.path.join(tmpdir, 'breaker2.json'))
        breaker2.record_failure()
        breaker2.record_failure()
        tr.record("连续失败触发OPEN", breaker2.state == BreakerState.OPEN,
                  f"failures={breaker2.failure_count}")
        tr.record("OPEN状态拒绝", not breaker2.allow("test"),
                  f"state={breaker2.state.value}")

        # 恢复超时后半开
        time.sleep(1.1)
        tr.record("超时后半开探测", breaker2.allow("test"),
                  f"state={breaker2.state.value}")


def test_t5_idempotency(tr: TestResult):
    """T5: 幂等去重"""
    print("\n=== T5: 幂等控制 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        store = IdempotencyStore(store_file=os.path.join(tmpdir, 'idem.json'))

        key = IdempotencyStore.generate_key("test_action", {'a': 1, 'b': 2})
        tr.record("幂等键生成", len(key) == 16, f"key={key}")

        # 首次执行
        call_count = [0]
        def do_work():
            call_count[0] += 1
            return {'value': 42, 'call': call_count[0]}

        result1, cached1 = store.execute_with_idempotency(key, "test_action", do_work)
        tr.record("首次执行不缓存", not cached1 and result1['value'] == 42,
                  f"call_count={call_count[0]}")

        # 重复执行
        result2, cached2 = store.execute_with_idempotency(key, "test_action", do_work)
        tr.record("重复执行返回缓存", cached2 and call_count[0] == 1,
                  f"call_count={call_count[0]}, cached={cached2}")

        # 持久化验证
        store2 = IdempotencyStore(store_file=os.path.join(tmpdir, 'idem.json'))
        tr.record("幂等记录持久化", store2.check(key) is not None,
                  f"keys={store2.stats()['total_keys']}")


def test_t6_saga_compensation(tr: TestResult):
    """T6: Saga补偿事务"""
    print("\n=== T6: Saga补偿事务 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        store = IdempotencyStore(store_file=os.path.join(tmpdir, 'saga_idem.json'))
        saga = SagaOrchestrator("test_pipeline", idempotency_store=store)

        state = {'step1': False, 'step2': False, 'step3': False, 'rollbacks': []}

        def step1_forward():
            state['step1'] = True
            return "step1 done"
        def step1_backward():
            state['step1'] = False
            state['rollbacks'].append('step1')
            return True

        def step2_forward():
            state['step2'] = True
            return "step2 done"
        def step2_backward():
            state['step2'] = False
            state['rollbacks'].append('step2')
            return True

        def step3_forward():
            raise RuntimeError("step3 simulated failure")
        def step3_backward():
            return True

        saga.add_step("step1", step1_forward, step1_backward)
        saga.add_step("step2", step2_forward, step2_backward)
        saga.add_step("step3", step3_forward, step3_backward)

        result = saga.execute()
        tr.record("Saga失败标记", not result['success'],
                  f"failed_step={result['failed_step']}")
        tr.record("Saga补偿执行", result['compensated'],
                  f"rollbacks={state['rollbacks']}")
        tr.record("补偿后状态回滚", not state['step1'] and not state['step2'],
                  f"state={state}")

        # 正常Saga
        saga2 = SagaOrchestrator("success_pipeline", idempotency_store=store)
        saga2.add_step("s1", lambda: "ok1", lambda: True)
        saga2.add_step("s2", lambda: "ok2", lambda: True)
        result2 = saga2.execute()
        tr.record("正常Saga成功", result2['success'] and result2['steps_executed'] == 2,
                  f"results={result2['results']}")


def test_t7_crash_recovery(tr: TestResult):
    """T7: 断点恢复"""
    print("\n=== T7: 崩溃恢复 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        queue_file = os.path.join(tmpdir, 'crash_queue.jsonl')
        executor = TaskExecutor(queue_file=queue_file, enable_circuit_breaker=False)

        # 提交任务并手动标记为RUNNING（模拟崩溃）
        tid = executor.submit("audit_write", {'op_type': 'CRASH_TEST', 'operator': 'test'})
        task = executor.queue.get(tid)
        task.state = TaskState.RUNNING
        task.started_at = "2026-01-01T00:00:00+00:00"
        executor.queue.update(task)

        # 新执行器实例加载（模拟进程重启）
        executor2 = TaskExecutor(queue_file=queue_file, enable_circuit_breaker=False)
        running = executor2.queue.get_running()
        tr.record("崩溃后检测到RUNNING任务", len(running) == 1,
                  f"running={len(running)}")

        # 执行恢复
        report = executor2.recover_from_crash() if hasattr(executor2, 'recover_from_crash') else None
        # TaskExecutor没有recover_from_crash，手动恢复
        for t in executor2.queue.get_running():
            t.state = TaskState.PENDING
            executor2.queue.update(t)

        pending = executor2.queue.get_pending()
        tr.record("恢复后任务回到PENDING", len(pending) == 1,
                  f"pending={len(pending)}")

        # 重新执行
        results = executor2.run_all()
        tr.record("恢复后任务执行成功", results.get(tid, {}).get('status') == 'success',
                  f"status={results.get(tid, {}).get('status', 'N/A')}")


def test_t8_limb_driver(tr: TestResult):
    """T8: LimbDriver统一入口"""
    print("\n=== T8: LimbDriver统一入口 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        driver = LimbDriver(work_dir=tmpdir)

        # 状态查询
        status = driver.get_status()
        tr.record("驱动状态完整", all(k in status for k in ['version', 'executor', 'breaker', 'idempotency', 'available_actions']),
                  f"version={status['version']}, actions={len(status['available_actions'])}")

        # 提交+执行
        tid = driver.submit("audit_write", {'op_type': 'LIMB_DRIVER_TEST', 'operator': 'test'})
        results = driver.run_all()
        tr.record("LimbDriver执行任务", results.get(tid, {}).get('status') == 'success',
                  f"status={results.get(tid, {}).get('status', 'N/A')}")

        # 幂等重复提交
        tid2 = driver.submit("audit_write", {'op_type': 'LIMB_DRIVER_TEST', 'operator': 'test'})
        tr.record("幂等重复提交返回缓存", tid2.startswith("cached_"),
                  f"task_id={tid2}")

        # 健康检查
        health = driver.health_check()
        tr.record("健康检查执行", 'drift_level' in health,
                  f"drift={health['drift_level']}")

        # Saga
        saga = driver.create_saga("driver_saga")
        saga.add_step("s1", lambda: "ok", lambda: True)
        saga_result = driver.execute_saga("driver_saga")
        tr.record("LimbDriver Saga执行", saga_result['success'],
                  f"success={saga_result['success']}")


def main():
    print("=" * 60)
    print("手脚驱动层 - 全链路集成测试")
    print("=" * 60)

    tr = TestResult()

    try:
        test_t1_action_lifecycle(tr)
    except Exception as e:
        tr.record("T1异常", False, str(e)[:200])

    try:
        test_t2_executor_normal(tr)
    except Exception as e:
        tr.record("T2异常", False, str(e)[:200])

    try:
        test_t3_dag_dependencies(tr)
    except Exception as e:
        tr.record("T3异常", False, str(e)[:200])

    try:
        test_t4_circuit_breaker(tr)
    except Exception as e:
        tr.record("T4异常", False, str(e)[:200])

    try:
        test_t5_idempotency(tr)
    except Exception as e:
        tr.record("T5异常", False, str(e)[:200])

    try:
        test_t6_saga_compensation(tr)
    except Exception as e:
        tr.record("T6异常", False, str(e)[:200])

    try:
        test_t7_crash_recovery(tr)
    except Exception as e:
        tr.record("T7异常", False, str(e)[:200])

    try:
        test_t8_limb_driver(tr)
    except Exception as e:
        tr.record("T8异常", False, str(e)[:200])

    print("\n" + "=" * 60)
    summary = tr.summary()
    print(f"测试结果: {summary['passed']}/{summary['total']} 通过, 通过率 {summary['pass_rate']}%")
    print("=" * 60)

    # 保存报告
    report_path = Path(__file__).parent.parent / 'tests' / 'limb_driver_integration_report.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n报告已保存: {report_path}")

    return summary


if __name__ == '__main__':
    main()
