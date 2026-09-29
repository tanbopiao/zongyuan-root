#!/usr/bin/env python3
"""
手脚驱动层 - 统一入口 (Limb Driver)

Ω-Brainμ的"脊髓+神经+四肢"：
  大脑(决策层) → LimbDriver(调度) → Action(手脚) → 外部世界

核心能力:
  - 一键提交任务并执行
  - 任务依赖DAG
  - 熔断防护
  - 幂等去重
  - Saga补偿事务
  - 断点续跑
  - 全链路审计

用法:
    from limb_driver import LimbDriver

    driver = LimbDriver()
    driver.submit("cas_write", {"data": b"hello", "ref_name": "test"})
    driver.submit("snapshot", {"snapshot_id": "test-001"},
                  dependencies=["cas_write_task_id"])
    results = driver.run_all()
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from action_base import BaseAction, ActionResult, ActionStatus
from actions import create_action, ACTION_REGISTRY
from executor import TaskExecutor, Task, TaskState, PersistentTaskQueue
from circuit_breaker import CircuitBreaker, DriftLevel, get_global_breaker
from idempotency import IdempotencyStore, SagaOrchestrator, get_global_idem_store


class LimbDriver:
    """
    手脚驱动层统一入口

    整合: TaskExecutor + CircuitBreaker + IdempotencyStore + SagaOrchestrator
    """

    VERSION = "1.0.0"
    BUILD_DATE = "20260831"

    def __init__(self, work_dir: str = None, enable_circuit_breaker: bool = True):
        self.work_dir = Path(work_dir) if work_dir else Path(__file__).parent.parent / 'executor'
        self.work_dir.mkdir(parents=True, exist_ok=True)

        self.executor = TaskExecutor(
            queue_file=str(self.work_dir / 'task_queue.jsonl'),
            enable_circuit_breaker=enable_circuit_breaker
        )
        # 使用独立的熔断器和幂等存储（基于work_dir），避免全局单例跨实例污染
        self.breaker = CircuitBreaker(state_file=str(self.work_dir / 'breaker_state.json'))
        self.idem_store = IdempotencyStore(store_file=str(self.work_dir / 'idempotency.json'))
        self._sagas: Dict[str, SagaOrchestrator] = {}

    # ===== 任务提交与执行 =====

    def submit(self, action_name: str, params: dict = None,
               dependencies: List[str] = None, priority: int = 0,
               timeout: int = 60, max_retries: int = 3,
               idempotent: bool = True) -> str:
        """
        提交任务

        Args:
            action_name: Action名称
            params: Action参数
            dependencies: 依赖task_id列表
            priority: 优先级
            timeout: 超时秒数
            max_retries: 最大重试
            idempotent: 是否启用幂等

        Returns:
            task_id
        """
        if action_name not in ACTION_REGISTRY:
            raise ValueError(f"unknown action: {action_name}. available: {list(ACTION_REGISTRY.keys())}")

        # 幂等检查
        if idempotent:
            idem_key = IdempotencyStore.generate_key(action_name, params or {})
            cached = self.idem_store.check(idem_key)
            if cached is not None:
                # 已执行过，直接返回缓存的task_id（创建一个已完成的占位任务）
                task_id = f"cached_{idem_key[:8]}"
                task = Task(task_id=task_id, action_name=action_name, params=params or {})
                task.state = TaskState.SUCCESS
                task.result = cached['result']
                self.executor.queue.add(task)
                return task_id

        return self.executor.submit(
            action_name=action_name,
            params=params,
            dependencies=dependencies,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries,
        )

    def run_all(self) -> Dict[str, dict]:
        """执行所有待处理任务"""
        results = self.executor.run_all()

        # 记录幂等
        for task_id, result in results.items():
            task = self.executor.queue.get(task_id)
            if task and task.state == TaskState.SUCCESS:
                idem_key = IdempotencyStore.generate_key(task.action_name, task.params)
                self.idem_store.record(idem_key, result, task.action_name)

        return results

    def run_single(self, task_id: str) -> Optional[dict]:
        """执行单个任务"""
        return self.executor.run_single(task_id)

    # ===== Saga补偿事务 =====

    def create_saga(self, name: str) -> SagaOrchestrator:
        """创建Saga补偿事务"""
        saga = SagaOrchestrator(name, idempotency_store=self.idem_store)
        self._sagas[name] = saga
        return saga

    def execute_saga(self, name: str) -> dict:
        """执行已创建的Saga"""
        saga = self._sagas.get(name)
        if not saga:
            raise ValueError(f"saga not found: {name}")
        return saga.execute()

    # ===== 熔断控制 =====

    def check_breaker(self, action_name: str = "", is_mutation: bool = False) -> bool:
        """检查熔断器是否放行"""
        return self.breaker.allow(action_name, is_mutation)

    def set_drift_level(self, level: str, reason: str = ""):
        """设置漂移等级（由漂移监测模块调用）"""
        self.breaker.set_drift_level(DriftLevel(level), reason)

    def reset_breaker(self):
        """重置熔断器"""
        self.breaker.reset()

    # ===== 健康检查 =====

    def health_check(self) -> dict:
        """执行系统健康检查"""
        drift_level, reason = self.breaker.run_health_checks()
        return {
            'drift_level': drift_level.value,
            'reason': reason,
            'breaker_state': self.breaker.get_status(),
        }

    # ===== 状态查询 =====

    def get_status(self) -> dict:
        """获取手脚驱动层完整状态"""
        return {
            'version': self.VERSION,
            'build_date': self.BUILD_DATE,
            'executor': self.executor.get_status(),
            'breaker': self.breaker.get_status(),
            'idempotency': self.idem_store.stats(),
            'sagas': {name: {'steps': len(s.steps), 'log_entries': len(s.execution_log)}
                      for name, s in self._sagas.items()},
            'available_actions': list(ACTION_REGISTRY.keys()),
            'work_dir': str(self.work_dir),
        }

    def list_tasks(self, state: str = None) -> List[dict]:
        """列出任务"""
        tasks = self.executor.queue.get_all()
        if state:
            tasks = [t for t in tasks if t.state == state]
        return [t.to_dict() for t in tasks]

    # ===== 断点恢复 =====

    def recover_from_crash(self) -> dict:
        """
        崩溃恢复：将RUNNING状态的任务重置为PENDING，重新执行

        Returns:
            恢复报告
        """
        running = self.executor.queue.get_running()
        recovered = []
        for t in running:
            t.state = TaskState.PENDING
            t.error = f"recovered from crash (was running)"
            self.executor.queue.update(t)
            recovered.append(t.task_id)

        return {
            'recovered_count': len(recovered),
            'recovered_tasks': recovered,
            'message': f"{len(recovered)} tasks recovered from crash and re-queued",
        }


def main():
    """CLI入口"""
    import argparse
    parser = argparse.ArgumentParser(description='LimbDriver - 手脚驱动层统一入口')
    sub = parser.add_subparsers(dest='command')

    # status
    sub.add_parser('status', help='Show driver status')

    # submit
    s_p = sub.add_parser('submit', help='Submit a task')
    s_p.add_argument('--action', required=True)
    s_p.add_argument('--params', default='{}')
    s_p.add_argument('--priority', type=int, default=0)

    # run
    sub.add_parser('run', help='Run all pending tasks')

    # list
    l_p = sub.add_parser('list', help='List tasks')
    l_p.add_argument('--state', default=None)

    # recover
    sub.add_parser('recover', help='Recover from crash')

    # health
    sub.add_parser('health', help='Run health check')

    args = parser.parse_args()
    driver = LimbDriver()

    if args.command == 'status':
        print(json.dumps(driver.get_status(), indent=2, ensure_ascii=False))
    elif args.command == 'submit':
        params = json.loads(args.params)
        tid = driver.submit(args.action, params, priority=args.priority)
        print(json.dumps({'task_id': tid}, indent=2))
    elif args.command == 'run':
        results = driver.run_all()
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    elif args.command == 'list':
        tasks = driver.list_tasks(args.state)
        print(json.dumps(tasks, indent=2, ensure_ascii=False, default=str))
    elif args.command == 'recover':
        print(json.dumps(driver.recover_from_crash(), indent=2))
    elif args.command == 'health':
        print(json.dumps(driver.health_check(), indent=2))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
