#!/usr/bin/env python3
"""
P2断点补齐 - 多写入者与执行层集成 (Multi-Writer Executor)

将multi_writer_evolution协议与TaskExecutor集成，解决并发写入冲突:
  - 分布式文件锁 (基于fcntl/portalocker)
  - 写入者注册与心跳
  - 冲突检测 (同一资源并发写入)
  - 冲突解决策略 (last_write_wins / merge / reject)
  - 写入队列串行化 (按资源维度排队)
  - 写入审计 (谁在什么时间写了什么)

与executor的关系:
  TaskExecutor负责任务调度执行
  MultiWriterExecutor负责在执行写入类Action时加锁、冲突检测、串行化
"""

import hashlib
import json
import os
import sys
import time
import threading
import fcntl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable

sys.path.insert(0, str(Path(__file__).parent))

from action_base import BaseAction, ActionResult, ActionStatus
from actions import create_action
from executor import TaskExecutor, Task, TaskState
from execution_hash_chain import ExecutionHashChain
from execution_metrics import ExecutionMetrics


class LockType:
    """锁类型"""
    SHARED = "shared"        # 读锁（多写入者可同时持有）
    EXCLUSIVE = "exclusive"  # 写锁（独占）


class ConflictResolution:
    """冲突解决策略"""
    LAST_WRITE_WINS = "last_write_wins"  # 后写入覆盖先写入
    MERGE = "merge"                       # 尝试合并（需自定义merge函数）
    REJECT = "reject"                     # 拒绝并发写入，返回冲突错误


class WriterSession:
    """写入者会话"""

    def __init__(self, writer_id: str, resource: str, lock_type: str):
        self.writer_id = writer_id
        self.resource = resource
        self.lock_type = lock_type
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.last_heartbeat = time.time()
        self.active = True

    def heartbeat(self):
        self.last_heartbeat = time.time()

    def is_alive(self, timeout: int = 60) -> bool:
        return self.active and (time.time() - self.last_heartbeat) < timeout


class DistributedLock:
    """
    基于文件的分布式锁

    用法:
        lock = DistributedLock('/path/to/lockfile')
        with lock.acquire(timeout=30):
            do_critical_section()
    """

    def __init__(self, lock_path: str):
        self.lock_path = Path(lock_path)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = None
        self._locked = False

    def acquire(self, timeout: int = 30, exclusive: bool = True) -> bool:
        """获取锁"""
        start = time.time()
        lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH

        while time.time() - start < timeout:
            try:
                self._fd = open(self.lock_path, 'w')
                fcntl.flock(self._fd.fileno(), lock_type | fcntl.LOCK_NB)
                self._locked = True
                # 写入锁信息
                self._fd.write(json.dumps({
                    'pid': os.getpid(),
                    'acquired_at': datetime.now(timezone.utc).isoformat(),
                    'exclusive': exclusive,
                }))
                self._fd.flush()
                return True
            except (IOError, OSError):
                if self._fd:
                    self._fd.close()
                    self._fd = None
                time.sleep(0.1)

        return False

    def release(self):
        """释放锁"""
        if self._locked and self._fd:
            try:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
                self._fd.close()
            except Exception:
                pass
            self._fd = None
            self._locked = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()


class MultiWriterExecutor:
    """
    多写入者执行器 - 与TaskExecutor集成

    职责:
      1. 写入者注册与心跳管理
      2. 资源级分布式锁
      3. 并发写入冲突检测
      4. 冲突解决策略执行
      5. 写入审计
    """

    VERSION = "1.0.0"

    def __init__(self, work_dir: str = None,
                 conflict_resolution: str = ConflictResolution.LAST_WRITE_WINS,
                 lock_timeout: int = 30,
                 max_concurrent_writers: int = 4):
        self.work_dir = Path(work_dir) if work_dir else Path(__file__).parent.parent / 'executor' / 'multi_writer'
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.lock_dir = self.work_dir / 'locks'
        self.lock_dir.mkdir(exist_ok=True)

        self.conflict_resolution = conflict_resolution
        self.lock_timeout = lock_timeout
        self.max_concurrent_writers = max_concurrent_writers

        self._writers: Dict[str, WriterSession] = {}
        self._write_queue: Dict[str, List[dict]] = {}  # resource -> queue
        self._lock = threading.Lock()
        self._audit_log: List[dict] = []

        # 集成执行器和审计链
        self.executor = TaskExecutor(queue_file=str(self.work_dir / 'mw_task_queue.jsonl'))
        self.exec_chain = ExecutionHashChain(chain_file=str(self.work_dir / 'mw_exec_chain.json'))
        self.metrics = ExecutionMetrics(metrics_file=str(self.work_dir / 'mw_metrics.json'))

    # ===== 写入者管理 =====

    def register_writer(self, writer_id: str, resource: str,
                        lock_type: str = LockType.EXCLUSIVE) -> Tuple[bool, str]:
        """
        注册写入者

        Returns:
            (success, message)
        """
        with self._lock:
            # 检查并发写入者数
            active_writers = sum(1 for w in self._writers.values() if w.is_alive())
            if active_writers >= self.max_concurrent_writers:
                return False, f"max concurrent writers ({self.max_concurrent_writers}) reached"

            # 检查资源冲突
            existing = [w for w in self._writers.values()
                        if w.resource == resource and w.is_alive() and w.lock_type == LockType.EXCLUSIVE]
            if existing and lock_type == LockType.EXCLUSIVE:
                if self.conflict_resolution == ConflictResolution.REJECT:
                    return False, f"resource {resource} is locked by {existing[0].writer_id}"
                # LAST_WRITE_WINS: 旧写入者失效
                for w in existing:
                    w.active = False

            session = WriterSession(writer_id, resource, lock_type)
            self._writers[writer_id] = session
            self._audit('register', writer_id, resource, {'lock_type': lock_type})
            return True, f"writer {writer_id} registered for {resource}"

    def unregister_writer(self, writer_id: str):
        """注销写入者"""
        with self._lock:
            if writer_id in self._writers:
                self._writers[writer_id].active = False
                self._audit('unregister', writer_id, self._writers[writer_id].resource)

    def heartbeat(self, writer_id: str) -> bool:
        """写入者心跳"""
        with self._lock:
            if writer_id in self._writers and self._writers[writer_id].active:
                self._writers[writer_id].heartbeat()
                return True
            return False

    def get_active_writers(self) -> List[dict]:
        """获取活跃写入者"""
        with self._lock:
            return [
                {'writer_id': w.writer_id, 'resource': w.resource,
                 'lock_type': w.lock_type, 'started_at': w.started_at}
                for w in self._writers.values() if w.is_alive()
            ]

    # ===== 资源锁 =====

    def _get_lock_path(self, resource: str) -> str:
        resource_hash = hashlib.sha256(resource.encode()).hexdigest()[:16]
        return str(self.lock_dir / f'{resource_hash}.lock')

    def acquire_resource_lock(self, resource: str, writer_id: str,
                              exclusive: bool = True, timeout: int = None) -> bool:
        """获取资源锁"""
        timeout = timeout or self.lock_timeout
        lock = DistributedLock(self._get_lock_path(resource))
        success = lock.acquire(timeout=timeout, exclusive=exclusive)
        if success:
            self._audit('lock_acquire', writer_id, resource, {'exclusive': exclusive})
        return success

    def execute_with_lock(self, action_name: str, params: dict,
                          resource: str, writer_id: str,
                          exclusive: bool = True) -> dict:
        """
        带锁执行Action

        Args:
            action_name: Action名称
            params: Action参数
            resource: 锁定的资源标识
            writer_id: 写入者ID
            exclusive: 是否独占锁

        Returns:
            执行结果
        """
        start_time = time.time()

        # 1. 注册写入者
        registered, msg = self.register_writer(writer_id, resource,
                                                LockType.EXCLUSIVE if exclusive else LockType.SHARED)
        if not registered:
            self.metrics.record_execution(action_name, False, 0, blocked=True, error=msg)
            return {'status': 'blocked', 'error': msg, 'writer_id': writer_id}

        # 2. 获取资源锁
        lock = DistributedLock(self._get_lock_path(resource))
        if not lock.acquire(timeout=self.lock_timeout, exclusive=exclusive):
            self.unregister_writer(writer_id)
            self.metrics.record_execution(action_name, False, 0, blocked=True, error='lock timeout')
            return {'status': 'blocked', 'error': f'failed to acquire lock for {resource}', 'writer_id': writer_id}

        try:
            # 3. 心跳线程
            stop_heartbeat = threading.Event()

            def heartbeat_loop():
                while not stop_heartbeat.is_set():
                    self.heartbeat(writer_id)
                    time.sleep(5)

            hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
            hb_thread.start()

            # 4. 执行Action
            action = create_action(action_name, params=params,
                                   context={'writer_id': writer_id, 'resource': resource})
            result = action.run()
            duration = round((time.time() - start_time) * 1000, 2)

            # 5. 记录执行哈希链
            self.exec_chain.append(
                f"{writer_id}_{resource}_{int(time.time())}",
                action_name,
                result.status.value,
                result=result.data,
                operator=writer_id,
                metadata={'resource': resource, 'duration_ms': duration},
            )

            # 6. 指标采集
            self.metrics.record_execution(
                action_name,
                success=result.status == ActionStatus.SUCCESS,
                duration_ms=duration,
                error=result.error,
                rolled_back=result.rollback_performed,
            )

            stop_heartbeat.set()

            return {
                'status': result.status.value,
                'result': result.data,
                'error': result.error,
                'rollback_performed': result.rollback_performed,
                'duration_ms': duration,
                'writer_id': writer_id,
                'resource': resource,
            }

        finally:
            # 7. 释放锁和注销
            lock.release()
            self.unregister_writer(writer_id)

    # ===== 冲突检测 =====

    def detect_conflicts(self) -> List[dict]:
        """检测当前资源冲突"""
        conflicts = []
        with self._lock:
            resource_writers: Dict[str, List[WriterSession]] = {}
            for w in self._writers.values():
                if w.is_alive():
                    resource_writers.setdefault(w.resource, []).append(w)

            for resource, writers in resource_writers.items():
                exclusive_writers = [w for w in writers if w.lock_type == LockType.EXCLUSIVE]
                if len(exclusive_writers) > 1:
                    conflicts.append({
                        'resource': resource,
                        'conflicting_writers': [w.writer_id for w in exclusive_writers],
                        'severity': 'P1',
                        'resolution': self.conflict_resolution,
                    })
        return conflicts

    def resolve_conflicts(self) -> dict:
        """解决检测到的冲突"""
        conflicts = self.detect_conflicts()
        resolved = 0
        for conflict in conflicts:
            if self.conflict_resolution == ConflictResolution.LAST_WRITE_WINS:
                # 保留最新的，其他失效
                writers = conflict['conflicting_writers']
                for wid in writers[:-1]:
                    if wid in self._writers:
                        self._writers[wid].active = False
                resolved += 1
            elif self.conflict_resolution == ConflictResolution.REJECT:
                # 全部失效
                for wid in conflict['conflicting_writers']:
                    if wid in self._writers:
                        self._writers[wid].active = False
                resolved += 1
        return {'conflicts_detected': len(conflicts), 'resolved': resolved}

    # ===== 审计 =====

    def _audit(self, event: str, writer_id: str, resource: str, details: dict = None):
        entry = {
            'event': event,
            'writer_id': writer_id,
            'resource': resource,
            'details': details or {},
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        self._audit_log.append(entry)
        # 持久化
        audit_file = self.work_dir / 'multi_writer_audit.jsonl'
        with open(audit_file, 'a') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def get_audit_log(self, limit: int = 50) -> List[dict]:
        return self._audit_log[-limit:]

    def get_status(self) -> dict:
        return {
            'version': self.VERSION,
            'active_writers': len(self.get_active_writers()),
            'max_concurrent_writers': self.max_concurrent_writers,
            'conflict_resolution': self.conflict_resolution,
            'lock_timeout': self.lock_timeout,
            'pending_conflicts': len(self.detect_conflicts()),
            'executor': self.executor.get_status(),
            'metrics': self.metrics.get_summary(),
            'audit_entries': len(self._audit_log),
        }
