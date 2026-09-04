#!/usr/bin/env python3
"""
手脚驱动层 - 漂移熔断器 (Circuit Breaker)

三层防护:
  L1 系统健康检查: 哈希链完整性、CAS一致性、快照有效性
  L2 动作级熔断: 连续失败自动熔断，半开探测恢复
  L3 全局急停: 检测到P0级漂移时，禁止所有修改类动作

状态机: closed → open → half_open → closed
"""

import json
import time
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Tuple


class BreakerState(Enum):
    CLOSED = "closed"        # 正常放行
    OPEN = "open"            # 熔断，拒绝所有请求
    HALF_OPEN = "half_open"  # 半开，允许探测请求


class DriftLevel(Enum):
    NONE = "none"
    P3 = "P3"  # 轻微：观测偏差，不阻断
    P2 = "P2"  # 中等：警告，降低并发
    P1 = "P1"  # 严重：阻断修改类动作
    P0 = "P0"  # 致命：全局急停


class CircuitBreaker:
    """
    增强版熔断器

    用法:
        breaker = CircuitBreaker()
        if breaker.allow(action_name="cas_write", is_mutation=True):
            result = do_action()
            breaker.record_success()
        else:
            breaker.record_failure()
    """

    def __init__(self,
                 failure_threshold: int = 3,
                 recovery_timeout: int = 60,
                 half_open_max_requests: int = 1,
                 state_file: str = None):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests
        self.state_file = Path(state_file) if state_file else Path(__file__).parent.parent / 'executor' / 'breaker_state.json'
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.state = BreakerState.CLOSED
        self.half_open_requests = 0
        self.drift_level = DriftLevel.NONE
        self.drift_reason = ""

        # 健康检查函数注册表
        self._health_checks: list = []
        self._register_default_health_checks()
        self._load_state()

    def _register_default_health_checks(self):
        """注册默认健康检查"""
        self._health_checks.append(self._check_hash_chain)
        self._health_checks.append(self._check_cas_integrity)

    def _check_hash_chain(self) -> Tuple[bool, str]:
        """检查哈希链完整性"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from hash_chain import HashChain
            chain = HashChain()
            result = chain.verify_chain()
            if not result['valid']:
                return (False, f"hash chain broken at seq {result.get('broken_at')}")
            return (True, "")
        except Exception as e:
            return (True, f"hash chain check skipped: {e}")  # 组件不可用时不阻断

    def _check_cas_integrity(self) -> Tuple[bool, str]:
        """检查CAS存储完整性"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from cas_store import CASStore
            store = CASStore()
            # 抽样验证：检查引用是否指向存在的对象
            refs = store.list_refs()
            for ref_name, cid in list(refs.items())[:10]:
                if not store.exists(cid):
                    return (False, f"CAS ref '{ref_name}' points to missing object {cid}")
            return (True, "")
        except Exception as e:
            return (True, f"CAS check skipped: {e}")

    def register_health_check(self, func: Callable[[], Tuple[bool, str]]):
        """注册自定义健康检查"""
        self._health_checks.append(func)

    def run_health_checks(self) -> Tuple[DriftLevel, str]:
        """运行全部健康检查，返回漂移等级"""
        for check in self._health_checks:
            try:
                ok, reason = check()
                if not ok:
                    return (DriftLevel.P1, reason)
            except Exception as e:
                continue
        return (DriftLevel.NONE, "")

    def allow(self, action_name: str = "", is_mutation: bool = False) -> bool:
        """
        判断是否允许执行

        Args:
            action_name: 动作名称
            is_mutation: 是否为修改类动作
        """
        with self._lock:
            # P0全局急停
            if self.drift_level == DriftLevel.P0:
                return False

            # P1只允许只读动作
            if self.drift_level == DriftLevel.P1 and is_mutation:
                return False

            # 状态机判断
            if self.state == BreakerState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = BreakerState.HALF_OPEN
                    self.half_open_requests = 0
                    return True
                return False

            if self.state == BreakerState.HALF_OPEN:
                if self.half_open_requests < self.half_open_max_requests:
                    self.half_open_requests += 1
                    return True
                return False

            return True

    def record_success(self):
        """记录成功"""
        with self._lock:
            self.failure_count = 0
            self.success_count += 1
            if self.state == BreakerState.HALF_OPEN:
                self.state = BreakerState.CLOSED
                self.half_open_requests = 0
            self._save_state()

    def record_failure(self, reason: str = ""):
        """记录失败"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = BreakerState.OPEN
            self._save_state()

    def set_drift_level(self, level: DriftLevel, reason: str = ""):
        """手动设置漂移等级（由漂移监测模块调用）"""
        with self._lock:
            self.drift_level = level
            self.drift_reason = reason
            self._save_state()

    def reset(self):
        """重置熔断器"""
        with self._lock:
            self.failure_count = 0
            self.success_count = 0
            self.state = BreakerState.CLOSED
            self.drift_level = DriftLevel.NONE
            self.drift_reason = ""
            self._save_state()

    def get_status(self) -> dict:
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'drift_level': self.drift_level.value,
            'drift_reason': self.drift_reason,
            'last_failure_age_s': round(time.time() - self.last_failure_time, 1) if self.last_failure_time else None,
            'recovery_timeout_s': self.recovery_timeout,
            'health_checks_count': len(self._health_checks),
        }

    def _save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump({
                    'state': self.state.value,
                    'failure_count': self.failure_count,
                    'success_count': self.success_count,
                    'last_failure_time': self.last_failure_time,
                    'drift_level': self.drift_level.value,
                    'drift_reason': self.drift_reason,
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                }, f, indent=2)
        except Exception:
            pass

    def _load_state(self):
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    d = json.load(f)
                    self.state = BreakerState(d.get('state', 'closed'))
                    self.failure_count = d.get('failure_count', 0)
                    self.success_count = d.get('success_count', 0)
                    self.last_failure_time = d.get('last_failure_time', 0)
                    self.drift_level = DriftLevel(d.get('drift_level', 'none'))
                    self.drift_reason = d.get('drift_reason', '')
        except Exception:
            pass


# 全局单例
_global_breaker: Optional[CircuitBreaker] = None

def get_global_breaker() -> CircuitBreaker:
    global _global_breaker
    if _global_breaker is None:
        _global_breaker = CircuitBreaker()
    return _global_breaker
