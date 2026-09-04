#!/usr/bin/env python3
"""
手脚驱动层 - Action抽象基类

每一个外部操作封装为独立Action单元:
  - pre_check():  前置校验（漂移检测、权限、状态）
  - execute():    执行本体（真实IO/API/文件操作）
  - post_check(): 后置校验（结果完整性、哈希比对）
  - rollback():   失败回滚/补偿
  - audit():      审计留痕

所有修改类动作必须经过前置校验，失败必须可回滚，全程留痕。
"""

import hashlib
import json
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class ActionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"
    BLOCKED = "blocked"  # 被熔断拦截


class ActionResult:
    """Action执行结果"""

    def __init__(self, status: ActionStatus, data: Any = None,
                 error: str = None, rollback_performed: bool = False):
        self.status = status
        self.data = data
        self.error = error
        self.rollback_performed = rollback_performed
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            'status': self.status.value,
            'data': self._serialize(self.data),
            'error': self.error,
            'rollback_performed': self.rollback_performed,
            'timestamp': self.timestamp,
        }

    @staticmethod
    def _serialize(obj):
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, (list, tuple)):
            return [ActionResult._serialize(x) for x in obj]
        if isinstance(obj, dict):
            return {k: ActionResult._serialize(v) for k, v in obj.items()}
        if hasattr(obj, '__dict__'):
            return str(obj)
        return str(obj)


class BaseAction(ABC):
    """
    Action抽象基类

    子类必须实现:
      - name: 动作名称
      - execute(): 执行本体
    可选重写:
      - pre_check(), post_check(), rollback()
    """

    # 子类必须定义
    name: str = "base_action"
    description: str = ""
    # 是否为修改类动作（修改类动作需要前置漂移校验+回滚能力）
    is_mutation: bool = True
    # 最大重试次数
    max_retries: int = 3
    # 超时秒数
    timeout: int = 60
    # 幂等键生成方式: "input_hash" | "custom"
    idempotency_mode: str = "input_hash"

    def __init__(self, params: dict = None, context: dict = None):
        self.params = params or {}
        self.context = context or {}
        self.result: Optional[ActionResult] = None
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.attempts = 0
        self._rollback_registered = False
        self._snapshot_before: Optional[dict] = None

    # ===== 核心生命周期 =====

    def run(self) -> ActionResult:
        """
        完整执行生命周期:
        pre_check → execute → post_check → (rollback on failure)
        """
        self.start_time = time.time()
        self.attempts = 0

        # 1. 前置校验
        try:
            check_result = self.pre_check()
            if check_result is not None and not check_result[0]:
                self.result = ActionResult(
                    ActionStatus.BLOCKED,
                    error=f"pre_check failed: {check_result[1]}"
                )
                self._audit()
                return self.result
        except Exception as e:
            self.result = ActionResult(ActionStatus.FAILED, error=f"pre_check exception: {e}")
            self._audit()
            return self.result

        # 2. 执行（带重试）
        last_error = None
        for attempt in range(self.max_retries):
            self.attempts = attempt + 1
            try:
                # 执行前快照（用于回滚）
                if self.is_mutation:
                    self._snapshot_before = self._take_snapshot()

                exec_result = self.execute()
                if isinstance(exec_result, ActionResult):
                    self.result = exec_result
                else:
                    self.result = ActionResult(ActionStatus.SUCCESS, data=exec_result)
                break
            except Exception as e:
                last_error = e
                self.result = ActionResult(
                    ActionStatus.FAILED,
                    error=f"attempt {attempt+1}/{self.max_retries}: {e}\n{traceback.format_exc()[-500:]}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(min(2 ** attempt, 10))  # 指数退避
                    continue

        # 3. 后置校验
        if self.result and self.result.status == ActionStatus.SUCCESS:
            try:
                post_ok = self.post_check(self.result)
                if post_ok is not None and not post_ok[0]:
                    self.result = ActionResult(
                        ActionStatus.FAILED,
                        data=self.result.data,
                        error=f"post_check failed: {post_ok[1]}"
                    )
            except Exception as e:
                self.result = ActionResult(
                    ActionStatus.FAILED,
                    data=self.result.data if self.result else None,
                    error=f"post_check exception: {e}"
                )

        # 4. 失败回滚
        if self.result and self.result.status == ActionStatus.FAILED and self.is_mutation:
            try:
                rb_result = self.rollback()
                if rb_result:
                    self.result.rollback_performed = True
            except Exception as e:
                self.result.error += f" | rollback failed: {e}"

        self.end_time = time.time()
        self._audit()
        return self.result

    # ===== 子类实现接口 =====

    @abstractmethod
    def execute(self) -> Any:
        """执行本体，返回数据或ActionResult"""
        raise NotImplementedError

    def pre_check(self) -> Optional[Tuple[bool, str]]:
        """
        前置校验
        返回 (True, "") 表示通过；(False, reason) 表示拦截
        返回None表示跳过校验
        """
        return (True, "")

    def post_check(self, result: ActionResult) -> Optional[Tuple[bool, str]]:
        """后置校验，验证执行结果完整性"""
        return (True, "")

    def rollback(self) -> bool:
        """
        回滚/补偿
        返回True表示回滚成功
        默认实现: 基于执行前快照恢复
        """
        if self._snapshot_before:
            return self._restore_snapshot(self._snapshot_before)
        return False

    # ===== 工具方法 =====

    def generate_idempotency_key(self) -> str:
        """生成幂等键"""
        if self.idempotency_mode == "input_hash":
            def _serialize_bytes(obj):
                if isinstance(obj, bytes):
                    return obj.hex()
                if isinstance(obj, dict):
                    return {k: _serialize_bytes(v) for k, v in obj.items()}
                if isinstance(obj, (list, tuple)):
                    return [_serialize_bytes(x) for x in obj]
                return obj
            content = json.dumps({
                'name': self.name,
                'params': _serialize_bytes(self.params),
            }, sort_keys=True, ensure_ascii=False)
            return hashlib.sha256(content.encode()).hexdigest()[:16]
        return self.params.get('idempotency_key', f"{self.name}_{int(time.time())}")

    def _take_snapshot(self) -> Optional[dict]:
        """执行前快照（子类可重写，默认空）"""
        return None

    def _restore_snapshot(self, snapshot: dict) -> bool:
        """从快照恢复（子类可重写）"""
        return False

    def _audit(self):
        """审计留痕"""
        try:
            from audit_log import AuditLog
            audit = AuditLog(chain_id='action_execution')
            entry = audit.append(
                op_type=f'ACTION_{self.name.upper()}',
                operator=self.context.get('operator', 'executor'),
                data_hash=self.generate_idempotency_key(),
                details={
                    'status': self.result.status.value if self.result else 'unknown',
                    'attempts': self.attempts,
                    'duration_ms': round((self.end_time or time.time()) - (self.start_time or time.time()), 2) * 1000,
                    'error': self.result.error if self.result else None,
                    'params_hash': hashlib.sha256(json.dumps(self.params, sort_keys=True).encode()).hexdigest()[:16],
                }
            )
            return entry
        except Exception:
            pass  # 审计失败不影响主流程

    def get_execution_summary(self) -> dict:
        return {
            'name': self.name,
            'status': self.result.status.value if self.result else 'not_run',
            'attempts': self.attempts,
            'duration_ms': round((self.end_time or 0) - (self.start_time or 0), 3) * 1000 if self.start_time else 0,
            'idempotency_key': self.generate_idempotency_key(),
            'is_mutation': self.is_mutation,
        }
