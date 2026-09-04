#!/usr/bin/env python3
"""
手脚驱动层深度加固 - 全链路集成测试

覆盖:
  T1 执行哈希链 (追加/验证/篡改检测)
  T2 两阶段提交 (prepare/commit/rollback)
  T3 RBAC权限矩阵 (角色拦截/二次确认/权限变更)
  T4 执行指标采集 (Counter/Histogram/Prometheus/告警)
  T5 流水线执行引擎 (完整七层+向量同步)
"""

import json
import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'omega_brain'))
sys.path.insert(0, str(ROOT))

from execution_hash_chain import ExecutionHashChain
from two_phase_action import TPCSnapshotAction, TPCCasWriteAction, TPCState
from action_rbac import ActionRBAC, Role, SensitivityLevel
from execution_metrics import ExecutionMetrics
from pipeline_executor import PipelineExecutor, PipelineStage


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def record(self, name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        self.results.append({'test': name, 'status': status, 'detail': detail})
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        print(f"  [{status}] {name} {detail}")

    def summary(self):
        return {
            'total': self.passed + self.failed,
            'passed': self.passed,
            'failed': self.failed,
            'pass_rate': round(self.passed / (self.passed + self.failed) * 100, 1) if (self.passed + self.failed) > 0 else 0,
            'results': self.results,
        }


def test_t1_execution_hash_chain(tr):
    """T1: 执行哈希链"""
    print("\n=== T1: 执行哈希链 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        chain = ExecutionHashChain(chain_file=os.path.join(tmpdir, 'exec_chain.json'))

        # 追加记录
        e1 = chain.append("task-001", "cas_write", "success", result={'cid': 'abc'}, operator="test")
        e2 = chain.append("task-002", "snapshot", "success", result={'root': 'def'}, operator="test")
        e3 = chain.append("task-003", "api_call", "failed", error="timeout", operator="test")

        tr.record("追加执行记录", len(chain._chain) == 3, f"count={len(chain._chain)}")

        # 验证链完整性
        verify = chain.verify_chain()
        tr.record("哈希链完整性验证", verify['valid'], f"valid={verify['valid']}, total={verify['total']}")

        # 验证prev_hash链接
        tr.record("prev_hash链接正确", e2['prev_hash'] == e1['hash'] and e3['prev_hash'] == e2['hash'],
                  f"e2.prev={e2['prev_hash'][:8]}==e1.hash={e1['hash'][:8]}")

        # 篡改检测：修改一条记录的result_hash
        chain._chain[1]['result_hash'] = 'tampered_hash_value'
        verify2 = chain.verify_chain()
        tr.record("篡改检测", not verify2['valid'], f"broken_at={verify2.get('broken_at')}")

        # 持久化验证
        chain2 = ExecutionHashChain(chain_file=os.path.join(tmpdir, 'exec_chain.json'))
        tr.record("执行链持久化", len(chain2._chain) == 3, f"loaded={len(chain2._chain)}")

        # 统计
        stats = chain.stats()
        tr.record("统计信息完整", 'total_records' in stats and 'status_distribution' in stats,
                  f"total={stats['total_records']}")


def test_t2_two_phase_commit(tr):
    """T2: 两阶段提交"""
    print("\n=== T2: 两阶段提交 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        # TPC CAS写入
        action = TPCCasWriteAction(params={'data': b'tpc test data', 'ref_name': 'tpc_test'})

        # prepare阶段
        prep = action.prepare()
        tr.record("TPC prepare成功", prep.status.value == 'success' and action.tpc_state == TPCState.PREPARED,
                  f"state={action.tpc_state.value}")

        # commit阶段
        commit = action.commit()
        tr.record("TPC commit成功", commit.status.value == 'success' and action.tpc_state == TPCState.COMMITTED,
                  f"state={action.tpc_state.value}, cid={commit.data.get('result',{}).get('content_id','N/A') if commit.data else 'N/A'}")

        # 状态校验：不能在非PREPARED状态commit
        action2 = TPCCasWriteAction(params={'data': b'test2'})
        commit2 = action2.commit()
        tr.record("非PREPARED状态commit被拒", commit2.status.value == 'failed',
                  f"error={commit2.error[:50] if commit2.error else 'N/A'}")

        # TPC快照
        snap_action = TPCSnapshotAction(params={'snapshot_id': 'TPC-TEST-001', 'save_dir': tmpdir, 'root_dir': tmpdir})
        result = snap_action.run()  # prepare + commit一键执行
        tr.record("TPC快照一键执行", result.status.value == 'success',
                  f"status={result.status.value}")

        # 回滚测试
        action3 = TPCCasWriteAction(params={'data': b'rollback test', 'ref_name': 'rb_test'})
        action3.prepare()
        action3.commit()
        rb = action3.rollback()
        tr.record("TPC rollback成功", rb.status.value == 'success' and action3.tpc_state == TPCState.ROLLED_BACK,
                  f"state={action3.tpc_state.value}")


def test_t3_rbac(tr):
    """T3: RBAC权限矩阵"""
    print("\n=== T3: RBAC权限矩阵 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        rbac = ActionRBAC(
            matrix_file=os.path.join(tmpdir, 'rbac.json'),
            audit_file=os.path.join(tmpdir, 'rbac_audit.jsonl'),
        )

        # observer角色不能执行修改类动作
        r1 = rbac.check("cas_write", "observer_user", Role.OBSERVER)
        tr.record("OBSERVER被拦截修改类动作", not r1['allowed'],
                  f"reason={r1['reason'][:50]}")

        # operator可以执行常规修改
        r2 = rbac.check("cas_write", "op_user", Role.OPERATOR)
        tr.record("OPERATOR允许常规修改", r2['allowed'], f"sensitivity={r2['sensitivity']}")

        # operator不能执行敏感操作
        r3 = rbac.check("evolution_cycle", "op_user", Role.OPERATOR)
        tr.record("OPERATOR被拦截敏感操作", not r3['allowed'],
                  f"reason={r3['reason'][:50]}")

        # admin执行敏感操作需要二次确认
        r4 = rbac.check("evolution_cycle", "admin_user", Role.ADMIN)
        tr.record("ADMIN敏感操作需二次确认", not r4['allowed'] and r4['need_confirmation'],
                  f"need_confirm={r4['need_confirmation']}")

        # 生成确认token并确认
        token = rbac.generate_confirmation_token("evolution_cycle", "admin_user")
        r5 = rbac.check("evolution_cycle", "admin_user", Role.ADMIN, confirmation_token=token)
        tr.record("二次确认后放行", r5['allowed'], f"allowed={r5['allowed']}")

        # 无效token被拒
        r6 = rbac.check("evolution_cycle", "admin_user", Role.ADMIN, confirmation_token="invalid_token")
        tr.record("无效确认token被拒", not r6['allowed'], f"reason={r6['reason'][:40]}")

        # 权限授予/撤销
        rbac.grant_permission("evolution_cycle", Role.OPERATOR, granted_by="admin")
        r7 = rbac.check("evolution_cycle", "op_user", Role.OPERATOR)
        tr.record("权限授予后OPERATOR可执行（仍需确认）", r7['need_confirmation'],
                  f"need_confirm={r7['need_confirmation']}")

        rbac.revoke_permission("evolution_cycle", Role.OPERATOR, revoked_by="admin")
        r8 = rbac.check("evolution_cycle", "op_user", Role.OPERATOR)
        tr.record("权限撤销后OPERATOR被拒", not r8['allowed'], f"allowed={r8['allowed']}")

        # 审计日志
        audit = rbac.get_audit_log()
        tr.record("权限审计日志记录", len(audit) >= 6, f"entries={len(audit)}")


def test_t4_execution_metrics(tr):
    """T4: 执行指标采集"""
    print("\n=== T4: 执行指标采集 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        metrics = ExecutionMetrics(metrics_file=os.path.join(tmpdir, 'metrics.json'))

        # 记录执行
        for i in range(10):
            metrics.record_execution("cas_write", success=True, duration_ms=50 + i * 10)
        for i in range(2):
            metrics.record_execution("snapshot", success=False, duration_ms=5000, error="timeout")
        metrics.record_execution("api_call", success=True, duration_ms=100, rolled_back=True)
        metrics.record_execution("vector_sync", success=False, duration_ms=0, blocked=True)

        summary = metrics.get_summary()
        tr.record("执行总数统计", summary['total_executions'] == 14,
                  f"total={summary['total_executions']}")
        tr.record("成功数统计", summary['success_count'] == 11,
                  f"success={summary['success_count']}")
        tr.record("失败数统计", summary['failure_count'] == 2,
                  f"failure={summary['failure_count']}")
        tr.record("拦截数统计", summary['blocked_count'] == 1,
                  f"blocked={summary['blocked_count']}")
        tr.record("回滚数统计", summary['rollback_count'] == 1,
                  f"rollback={summary['rollback_count']}")

        # 百分位数
        tr.record("P50耗时计算", summary['duration_p50_ms'] > 0,
                  f"p50={summary['duration_p50_ms']}ms")
        tr.record("P95耗时计算", summary['duration_p95_ms'] > 0,
                  f"p95={summary['duration_p95_ms']}ms")
        tr.record("P99耗时计算", summary['duration_p99_ms'] > 0,
                  f"p99={summary['duration_p99_ms']}ms")

        # 成功率
        tr.record("成功率计算", 70 < summary['success_rate_pct'] < 90,
                  f"rate={summary['success_rate_pct']}%")

        # 按Action分组
        tr.record("按Action分组统计", len(summary['per_action']) == 4,
                  f"actions={list(summary['per_action'].keys())}")

        # Prometheus导出
        prom = metrics.to_prometheus()
        tr.record("Prometheus格式导出", 'limb_driver_executions_total' in prom and 'limb_driver_duration_p99_ms' in prom,
                  f"lines={len(prom.split(chr(10)))}")

        # 告警检测
        metrics.set_gauge(circuit_state='open', drift_level='P1')
        alerts = metrics.check_alerts()
        alert_types = [a['type'] for a in alerts]
        tr.record("熔断器open告警", 'circuit_breaker_open' in alert_types,
                  f"alerts={alert_types}")
        tr.record("P1漂移告警", 'system_drift' in alert_types,
                  f"alerts={alert_types}")

        # 持久化
        metrics2 = ExecutionMetrics(metrics_file=os.path.join(tmpdir, 'metrics.json'))
        tr.record("指标持久化", metrics2.total_executions == 14,
                  f"loaded={metrics2.total_executions}")


def test_t5_pipeline_executor(tr):
    """T5: 流水线执行引擎"""
    print("\n=== T5: 流水线执行引擎 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        engine = PipelineExecutor(work_dir=tmpdir, operator="test_runner", operator_role=Role.SYSTEM)

        # 运行完整流水线
        result = engine.run_pipeline(run_id="TEST-PIPELINE-001")

        tr.record("流水线执行完成", result['total_stages'] == 8,
                  f"stages={result['total_stages']}")
        tr.record("流水线Merkle根生成", bool(result['pipeline_merkle_root']),
                  f"root={result['pipeline_merkle_root'][:16]}...")
        tr.record("执行哈希链有效", result['execution_chain_valid'],
                  f"valid={result['execution_chain_valid']}")
        tr.record("执行哈希链记录数", result['execution_chain_total'] >= 8,
                  f"total={result['execution_chain_total']}")

        # 检查各阶段结果
        stages = result['stages']
        success_count = sum(1 for s in stages if s['status'] == 'success')
        tr.record("阶段执行有结果", len(stages) == 8,
                  f"executed={len(stages)}, success={success_count}")

        # 检查L1 CAS阶段
        l1 = next((s for s in stages if s['stage_id'] == 'L1_cas'), None)
        tr.record("L1 CAS阶段执行", l1 is not None and l1['status'] in ('success', 'failed', 'blocked'),
                  f"L1 status={l1['status'] if l1 else 'N/A'}")

        # 检查L2 Merkle阶段
        l2 = next((s for s in stages if s['stage_id'] == 'L2_merkle'), None)
        tr.record("L2 Merkle阶段执行", l2 is not None,
                  f"L2 status={l2['status'] if l2 else 'N/A'}")

        # 指标采集
        metrics_summary = result['metrics_summary']
        tr.record("流水线指标采集", metrics_summary['total_executions'] >= 8,
                  f"executions={metrics_summary['total_executions']}")

        # 引擎状态
        status = engine.get_status()
        tr.record("引擎状态完整", all(k in status for k in ['version', 'breaker', 'exec_chain', 'metrics']),
                  f"version={status['version']}")


def main():
    print("=" * 60)
    print("手脚驱动层深度加固 - 全链路集成测试")
    print("=" * 60)

    tr = TestResult()

    try:
        test_t1_execution_hash_chain(tr)
    except Exception as e:
        tr.record("T1异常", False, str(e)[:200])
        import traceback
        traceback.print_exc()

    try:
        test_t2_two_phase_commit(tr)
    except Exception as e:
        tr.record("T2异常", False, str(e)[:200])
        import traceback
        traceback.print_exc()

    try:
        test_t3_rbac(tr)
    except Exception as e:
        tr.record("T3异常", False, str(e)[:200])
        import traceback
        traceback.print_exc()

    try:
        test_t4_execution_metrics(tr)
    except Exception as e:
        tr.record("T4异常", False, str(e)[:200])
        import traceback
        traceback.print_exc()

    try:
        test_t5_pipeline_executor(tr)
    except Exception as e:
        tr.record("T5异常", False, str(e)[:200])
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    summary = tr.summary()
    print(f"测试结果: {summary['passed']}/{summary['total']} 通过, 通过率 {summary['pass_rate']}%")
    print("=" * 60)

    report_path = ROOT / 'tests' / 'limb_driver_hardening_report.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n报告已保存: {report_path}")

    return summary


if __name__ == '__main__':
    main()
