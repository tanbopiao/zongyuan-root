#!/usr/bin/env python3
"""
手脚驱动层 - 幂等控制与补偿事务

解决:
  - 网络抖动导致重复请求 → 幂等键去重
  - 部分成功部分失败 → Saga补偿事务
  - 进程崩溃后状态不一致 → 补偿回放

核心概念:
  IdempotencyStore: 幂等键存储，重复请求直接返回首次结果
  CompensatingTransaction: 补偿事务，记录每一步的回滚动作
  SagaOrchestrator: Saga编排器，按步骤执行，失败时反向补偿
"""

import hashlib
import json
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


class IdempotencyStore:
    """
    幂等键存储

    相同幂等键的请求只执行一次，后续请求直接返回首次结果。
    持久化到磁盘，进程重启后仍然有效。
    """

    def __init__(self, store_file: str = None):
        self.store_file = Path(store_file) if store_file else Path(__file__).parent.parent / 'executor' / 'idempotency.json'
        self.store_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._records: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.store_file.exists():
            try:
                with open(self.store_file) as f:
                    self._records = json.load(f)
            except Exception:
                self._records = {}

    def _save(self):
        try:
            with open(self.store_file, 'w') as f:
                json.dump(self._records, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    @staticmethod
    def generate_key(action_name: str, params: dict, salt: str = "") -> str:
        """生成幂等键"""
        def _serialize_bytes(obj):
            if isinstance(obj, bytes):
                return obj.hex()
            if isinstance(obj, dict):
                return {k: _serialize_bytes(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_serialize_bytes(x) for x in obj]
            return obj
        content = json.dumps({'action': action_name, 'params': _serialize_bytes(params), 'salt': salt},
                             sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def check(self, key: str) -> Optional[dict]:
        """
        检查幂等键是否已执行

        Returns:
            已执行 → 返回首次结果dict
            未执行 → 返回None
        """
        with self._lock:
            record = self._records.get(key)
            if record:
                # 返回副本，防止外部修改
                return dict(record)
            return None

    def record(self, key: str, result: dict, action_name: str = ""):
        """记录幂等执行结果"""
        with self._lock:
            self._records[key] = {
                'action': action_name,
                'result': result,
                'executed_at': datetime.now(timezone.utc).isoformat(),
            }
            self._save()

    def execute_with_idempotency(self, key: str, action_name: str,
                                  func: Callable[[], dict]) -> Tuple[dict, bool]:
        """
        带幂等控制的执行

        Returns:
            (result, was_cached)
        """
        cached = self.check(key)
        if cached is not None:
            return cached['result'], True

        result = func()
        self.record(key, result, action_name)
        return result, False

    def cleanup(self, max_age_days: int = 30):
        """清理过期幂等记录"""
        cutoff = time.time() - max_age_days * 86400
        with self._lock:
            to_remove = []
            for k, v in self._records.items():
                try:
                    ts = datetime.fromisoformat(v['executed_at']).timestamp()
                    if ts < cutoff:
                        to_remove.append(k)
                except Exception:
                    continue
            for k in to_remove:
                del self._records[k]
            self._save()

    def stats(self) -> dict:
        return {'total_keys': len(self._records)}


class CompensatingAction:
    """补偿动作：记录一个正向操作和对应的回滚操作"""

    def __init__(self, name: str,
                 forward: Callable[[], Any],
                 backward: Callable[[], bool],
                 description: str = ""):
        self.name = name
        self.forward = forward
        self.backward = backward
        self.description = description
        self.executed = False
        self.result: Any = None
        self.compensated = False

    def run(self) -> Any:
        self.result = self.forward()
        self.executed = True
        return self.result

    def compensate(self) -> bool:
        if not self.executed or self.compensated:
            return True
        try:
            self.compensated = self.backward()
        except Exception:
            self.compensated = False
        return self.compensated


class SagaOrchestrator:
    """
    Saga补偿事务编排器

    按顺序执行一系列补偿动作；任何一步失败，反向执行已执行步骤的回滚。

    用法:
        saga = SagaOrchestrator("vector_sync_pipeline")
        saga.add_step("backup", do_backup, undo_backup)
        saga.add_step("cas_write", do_cas_write, undo_cas_write)
        saga.add_step("vector_push", do_vector_push, undo_vector_push)
        result = saga.execute()
        if not result['success']:
            print("compensated:", result['compensated'])
    """

    def __init__(self, name: str, idempotency_store: IdempotencyStore = None):
        self.name = name
        self.steps: List[CompensatingAction] = []
        self.idempotency = idempotency_store or IdempotencyStore()
        self._lock = threading.Lock()
        self.execution_log: List[dict] = []

    def add_step(self, name: str,
                 forward: Callable[[], Any],
                 backward: Callable[[], bool],
                 description: str = "") -> 'SagaOrchestrator':
        """添加步骤"""
        self.steps.append(CompensatingAction(name, forward, backward, description))
        return self

    def execute(self) -> dict:
        """
        执行Saga事务

        Returns:
            {
                'success': bool,
                'steps_executed': int,
                'compensated': bool,
                'failed_step': str,
                'error': str,
                'results': dict
            }
        """
        with self._lock:
            results = {}
            saga_id = hashlib.sha256(f"{self.name}_{time.time()}".encode()).hexdigest()[:12]

            # 幂等检查
            idem_key = IdempotencyStore.generate_key(
                f"saga_{self.name}",
                {'steps': [s.name for s in self.steps]}
            )
            cached = self.idempotency.check(idem_key)
            if cached:
                return {**cached, 'was_cached': True}

            start_time = time.time()
            executed_count = 0

            try:
                for step in self.steps:
                    self._log(saga_id, step.name, 'start')
                    step.run()
                    results[step.name] = step.result
                    executed_count += 1
                    self._log(saga_id, step.name, 'success')

                # 全部成功
                result = {
                    'success': True,
                    'saga_id': saga_id,
                    'steps_executed': executed_count,
                    'compensated': False,
                    'results': results,
                    'duration_ms': round((time.time() - start_time) * 1000, 2),
                }
                self.idempotency.record(idem_key, result, f"saga_{self.name}")
                return result

            except Exception as e:
                # 失败：反向补偿
                self._log(saga_id, self.steps[executed_count].name if executed_count < len(self.steps) else 'unknown', 'failed', str(e))
                compensated = self._compensate(executed_count - 1)
                result = {
                    'success': False,
                    'saga_id': saga_id,
                    'steps_executed': executed_count,
                    'compensated': compensated,
                    'failed_step': self.steps[executed_count].name if executed_count < len(self.steps) else 'unknown',
                    'error': str(e),
                    'results': results,
                    'duration_ms': round((time.time() - start_time) * 1000, 2),
                }
                return result

    def _compensate(self, from_index: int) -> bool:
        """反向执行补偿"""
        all_ok = True
        for i in range(from_index, -1, -1):
            step = self.steps[i]
            self._log('', step.name, 'compensating')
            ok = step.compensate()
            if not ok:
                all_ok = False
                self._log('', step.name, 'compensation_failed')
            else:
                self._log('', step.name, 'compensated')
        return all_ok

    def _log(self, saga_id: str, step: str, event: str, detail: str = ""):
        self.execution_log.append({
            'saga_id': saga_id,
            'step': step,
            'event': event,
            'detail': detail,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })

    def get_log(self) -> List[dict]:
        return list(self.execution_log)


# 全局单例
_global_idem_store: Optional[IdempotencyStore] = None

def get_global_idem_store() -> IdempotencyStore:
    global _global_idem_store
    if _global_idem_store is None:
        _global_idem_store = IdempotencyStore()
    return _global_idem_store
