#!/usr/bin/env python3
"""
手脚驱动层 - 持久化任务调度器

核心能力:
  - 持久化任务队列 (JSONL, 崩溃可恢复)
  - 断点续跑 (进程重启后从断点继续)
  - 超时控制 + 重试
  - 任务依赖 (DAG)
  - 与熔断层集成 (漂移检测拦截)
  - 执行审计

这是Ω-Brainμ的"脊髓"：大脑下发任务意图，调度器安全可靠地驱动手脚执行。
"""

import hashlib
import json
import os
import signal
import sys
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from action_base import BaseAction, ActionResult, ActionStatus
from actions import create_action, ACTION_REGISTRY


class TaskState:
    """任务状态常量"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"  # 被熔断拦截


class Task:
    """任务单元"""

    def __init__(self, task_id: str, action_name: str, params: dict = None,
                 dependencies: List[str] = None, priority: int = 0,
                 timeout: int = 60, max_retries: int = 3):
        self.task_id = task_id
        self.action_name = action_name
        self.params = params or {}
        self.dependencies = dependencies or []
        self.priority = priority
        self.timeout = timeout
        self.max_retries = max_retries
        self.state = TaskState.PENDING
        self.result: Optional[dict] = None
        self.error: Optional[str] = None
        self.attempts = 0
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'task_id': self.task_id,
            'action_name': self.action_name,
            'params': self.params,
            'dependencies': self.dependencies,
            'priority': self.priority,
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'state': self.state,
            'result': self.result,
            'error': self.error,
            'attempts': self.attempts,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'Task':
        t = cls(
            task_id=d['task_id'],
            action_name=d['action_name'],
            params=d.get('params', {}),
            dependencies=d.get('dependencies', []),
            priority=d.get('priority', 0),
            timeout=d.get('timeout', 60),
            max_retries=d.get('max_retries', 3),
        )
        t.state = d.get('state', TaskState.PENDING)
        t.result = d.get('result')
        t.error = d.get('error')
        t.attempts = d.get('attempts', 0)
        t.created_at = d.get('created_at', t.created_at)
        t.started_at = d.get('started_at')
        t.completed_at = d.get('completed_at')
        return t


class PersistentTaskQueue:
    """持久化任务队列 (JSONL文件)"""

    def __init__(self, queue_file: str = None):
        self.queue_file = Path(queue_file) if queue_file else Path(__file__).parent.parent / 'executor' / 'task_queue.jsonl'
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._tasks: Dict[str, Task] = {}
        self._load()

    def _load(self):
        """从磁盘加载任务队列"""
        if not self.queue_file.exists():
            return
        with open(self.queue_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        d = json.loads(line)
                        t = Task.from_dict(d)
                        self._tasks[t.task_id] = t
                    except Exception:
                        continue

    def _persist(self, task: Task):
        """持久化单个任务（追加写入）"""
        with self._lock:
            # 读取全部，更新对应行，重写
            all_tasks = []
            if self.queue_file.exists():
                with open(self.queue_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                d = json.loads(line)
                                if d['task_id'] != task.task_id:
                                    all_tasks.append(line)
                            except Exception:
                                continue
            all_tasks.append(json.dumps(task.to_dict(), ensure_ascii=False))
            with open(self.queue_file, 'w') as f:
                f.write('\n'.join(all_tasks) + '\n')

    def add(self, task: Task) -> str:
        """添加任务"""
        with self._lock:
            self._tasks[task.task_id] = task
        self._persist(task)
        return task.task_id

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def get_pending(self) -> List[Task]:
        """获取所有待执行任务（按优先级排序）"""
        pending = [t for t in self._tasks.values() if t.state == TaskState.PENDING]
        return sorted(pending, key=lambda t: (-t.priority, t.created_at))

    def get_running(self) -> List[Task]:
        """获取运行中任务（用于崩溃恢复）"""
        return [t for t in self._tasks.values() if t.state == TaskState.RUNNING]

    def update(self, task: Task):
        """更新任务状态"""
        with self._lock:
            self._tasks[task.task_id] = task
        self._persist(task)

    def get_all(self) -> List[Task]:
        return list(self._tasks.values())

    def clear_completed(self):
        """清理已完成任务（保留最近100条）"""
        completed = [t for t in self._tasks.values() if t.state in (TaskState.SUCCESS, TaskState.FAILED, TaskState.SKIPPED)]
        if len(completed) > 100:
            to_remove = sorted(completed, key=lambda t: t.completed_at or '')[:-100]
            for t in to_remove:
                del self._tasks[t.task_id]
            # 重写文件
            with open(self.queue_file, 'w') as f:
                for t in self._tasks.values():
                    f.write(json.dumps(t.to_dict(), ensure_ascii=False) + '\n')

    def stats(self) -> dict:
        states = {}
        for t in self._tasks.values():
            states[t.state] = states.get(t.state, 0) + 1
        return {'total': len(self._tasks), **states}


class CircuitBreaker:
    """熔断器：漂移检测拦截"""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed/open/half_open
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        """是否允许执行"""
        with self._lock:
            if self.state == "open":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "half_open"
                    return True
                return False
            return True

    def record_success(self):
        with self._lock:
            self.failure_count = 0
            self.state = "closed"

    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"

    def check_system_health(self) -> tuple:
        """
        执行系统健康检查（漂移检测）
        返回 (healthy: bool, reason: str)
        """
        try:
            from hash_chain import HashChain
            chain = HashChain()
            result = chain.verify_chain()
            if not result['valid']:
                return (False, f"hash chain broken at seq {result.get('broken_at')}")
        except Exception as e:
            # 健康检查组件不可用时不阻断
            pass
        return (True, "")

    def reset(self):
        with self._lock:
            self.failure_count = 0
            self.state = "closed"


class TaskExecutor:
    """
    任务执行器 - 手脚驱动层核心

    用法:
        executor = TaskExecutor()
        executor.submit("cas_write", {"data": b"test", "ref_name": "test"})
        executor.submit("snapshot", {"snapshot_id": "test-snap"})
        results = executor.run_all()
    """

    def __init__(self, queue_file: str = None, enable_circuit_breaker: bool = True):
        self.queue = PersistentTaskQueue(queue_file)
        self.circuit_breaker = CircuitBreaker() if enable_circuit_breaker else None
        self._running = False
        self._stop_event = threading.Event()
        self.results: Dict[str, dict] = {}

    def submit(self, action_name: str, params: dict = None,
               dependencies: List[str] = None, priority: int = 0,
               timeout: int = 60, max_retries: int = 3,
               task_id: str = None) -> str:
        """
        提交任务

        Args:
            action_name: Action名称 (必须在ACTION_REGISTRY中)
            params: Action参数
            dependencies: 依赖的task_id列表
            priority: 优先级 (数字越大越优先)
            timeout: 超时秒数
            max_retries: 最大重试次数
            task_id: 自定义任务ID (默认自动生成)

        Returns:
            task_id
        """
        if action_name not in ACTION_REGISTRY:
            raise ValueError(f"unknown action: {action_name}. available: {list(ACTION_REGISTRY.keys())}")

        if not task_id:
            content = json.dumps({'action': action_name, 'params': params, 'ts': time.time()}, sort_keys=True)
            task_id = hashlib.sha256(content.encode()).hexdigest()[:12]

        task = Task(
            task_id=task_id,
            action_name=action_name,
            params=params,
            dependencies=dependencies or [],
            priority=priority,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.queue.add(task)
        return task_id

    def _execute_task(self, task: Task) -> ActionResult:
        """执行单个任务"""
        # 熔断检查
        if self.circuit_breaker and not self.circuit_breaker.allow_request():
            task.state = TaskState.BLOCKED
            task.error = "circuit breaker open"
            self.queue.update(task)
            return ActionResult(ActionStatus.BLOCKED, error="circuit breaker open")

        # 系统健康检查（修改类动作）
        action_cls = ACTION_REGISTRY[task.action_name]
        if action_cls.is_mutation and self.circuit_breaker:
            healthy, reason = self.circuit_breaker.check_system_health()
            if not healthy:
                task.state = TaskState.BLOCKED
                task.error = f"system unhealthy: {reason}"
                self.queue.update(task)
                self.circuit_breaker.record_failure()
                return ActionResult(ActionStatus.BLOCKED, error=reason)

        # 创建Action并执行
        action = create_action(task.action_name, params=task.params,
                               context={'task_id': task.task_id, 'executor': 'task_executor'})
        action.timeout = task.timeout
        action.max_retries = task.max_retries

        task.state = TaskState.RUNNING
        task.started_at = datetime.now(timezone.utc).isoformat()
        task.attempts = action.attempts
        self.queue.update(task)

        result = action.run()

        task.state = result.status.value
        task.result = result.data if isinstance(result.data, (dict, list, str, int, float, bool)) else str(result.data)
        task.error = result.error
        task.completed_at = datetime.now(timezone.utc).isoformat()
        self.queue.update(task)

        # 熔断记录
        if self.circuit_breaker:
            if result.status == ActionStatus.SUCCESS:
                self.circuit_breaker.record_success()
            elif result.status in (ActionStatus.FAILED, ActionStatus.BLOCKED):
                self.circuit_breaker.record_failure()

        return result

    def _dependencies_met(self, task: Task) -> bool:
        """检查依赖是否全部完成"""
        for dep_id in task.dependencies:
            dep = self.queue.get(dep_id)
            if not dep or dep.state != TaskState.SUCCESS:
                return False
        return True

    def run_all(self, block: bool = True) -> Dict[str, dict]:
        """
        执行所有待处理任务

        Args:
            block: 是否阻塞等待全部完成

        Returns:
            {task_id: result_dict}
        """
        self._running = True
        self._stop_event.clear()

        # 崩溃恢复：将RUNNING状态的任务重置为PENDING
        for t in self.queue.get_running():
            t.state = TaskState.PENDING
            self.queue.update(t)

        while not self._stop_event.is_set():
            pending = self.queue.get_pending()
            if not pending:
                break

            executed_any = False
            for task in pending:
                if self._stop_event.is_set():
                    break
                if not self._dependencies_met(task):
                    continue

                result = self._execute_task(task)
                self.results[task.task_id] = {
                    'status': result.status.value,
                    'data': result.data,
                    'error': result.error,
                }
                executed_any = True

            if not executed_any:
                # 没有可执行任务（可能都在等依赖）
                # 检查是否有死锁
                pending_ids = {t.task_id for t in self.queue.get_pending()}
                blocked = [t for t in self.queue.get_pending()
                           if any(d in pending_ids for d in t.dependencies)]
                if len(blocked) == len(pending) and pending:
                    # 死锁，标记失败
                    for t in blocked:
                        t.state = TaskState.FAILED
                        t.error = "dependency deadlock"
                        self.queue.update(t)
                else:
                    time.sleep(0.1)

        self._running = False
        self.queue.clear_completed()
        return self.results

    def run_single(self, task_id: str) -> Optional[dict]:
        """执行单个任务"""
        task = self.queue.get(task_id)
        if not task:
            return None
        result = self._execute_task(task)
        return {'status': result.status.value, 'data': result.data, 'error': result.error}

    def stop(self):
        """优雅停止"""
        self._stop_event.set()

    def get_status(self) -> dict:
        """获取执行器状态"""
        return {
            'running': self._running,
            'queue_stats': self.queue.stats(),
            'circuit_breaker': {
                'state': self.circuit_breaker.state if self.circuit_breaker else 'disabled',
                'failure_count': self.circuit_breaker.failure_count if self.circuit_breaker else 0,
            } if self.circuit_breaker else 'disabled',
            'results_count': len(self.results),
        }


def main():
    """CLI入口"""
    import argparse
    parser = argparse.ArgumentParser(description='Task Executor - 手脚驱动层调度器')
    sub = parser.add_subparsers(dest='command')

    # submit
    s_p = sub.add_parser('submit', help='Submit a task')
    s_p.add_argument('--action', required=True, help='Action name')
    s_p.add_argument('--params', default='{}', help='Params JSON')
    s_p.add_argument('--priority', type=int, default=0)

    # run
    sub.add_parser('run', help='Run all pending tasks')

    # status
    sub.add_parser('status', help='Executor status')

    # list
    sub.add_parser('list', help='List all tasks')

    args = parser.parse_args()
    executor = TaskExecutor()

    if args.command == 'submit':
        params = json.loads(args.params)
        tid = executor.submit(args.action, params, priority=args.priority)
        print(json.dumps({'task_id': tid, 'action': args.action}, indent=2))
    elif args.command == 'run':
        results = executor.run_all()
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    elif args.command == 'status':
        print(json.dumps(executor.get_status(), indent=2))
    elif args.command == 'list':
        tasks = executor.queue.get_all()
        print(json.dumps([t.to_dict() for t in tasks], indent=2, ensure_ascii=False, default=str))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
