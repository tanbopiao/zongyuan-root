"""算子3: 行为模式风控算子.

固定阈值(方案强制):
    - 连续 3 次重复动作序列 -> 无效循环, 触发二级熔断
    - Token/API次数/运行时长 超阈值 -> 即刻告警 (临近上限=一级, 严重溢出=三级)
    - 上下文 Token 占用率 >= 90% -> 强制目标重锚定 (一级动作)
"""
from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass

from .config import ThresholdConfig


@dataclass
class ResourceSnapshot:
    ts: str
    tokens: int
    api_calls: int
    duration_sec: float
    context_used: int
    context_window: int

    @property
    def context_utilization(self) -> float:
        if self.context_window <= 0:
            return 0.0
        return self.context_used / self.context_window


class ActionSequenceDetector:
    """死循环检测: 连续 N 次(默认3)相同动作指纹 -> DeadLoop。"""

    def __init__(self, cfg: ThresholdConfig, emit=None):
        self.limit = int(cfg.section("behavior")["repeat_action_limit"])   # 固定=3
        self.emit = emit or (lambda *_a, **_k: None)
        self._last: str | None = None
        self._streak = 0
        self._history: list[dict] = []
        self._lock = threading.RLock()

    @staticmethod
    def fingerprint(action) -> str:
        """动作指纹: 名称+参数规范化哈希 (归一化空白防伪差异)。"""
        if isinstance(action, str):
            payload = " ".join(action.split())
        else:
            try:
                import json
                payload = json.dumps(action, ensure_ascii=False, sort_keys=True, default=str)
            except Exception:
                payload = str(action)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def record(self, action) -> dict:
        """记录一次动作; 返回 {repeat_streak, dead_loop}。"""
        with self._lock:
            fp = self.fingerprint(action)
            if fp == self._last:
                self._streak += 1
            else:
                self._last, self._streak = fp, 1
            dead = self._streak >= self.limit          # 连续3次 -> 判定
            entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                     "fingerprint": fp, "streak": self._streak, "dead_loop": dead}
            self._history.append(entry)
            if dead:
                self.emit("L2", "dead_loop_detected",
                          {"streak": self._streak, "limit": self.limit, "fingerprint": fp})
            return entry

    def reset(self) -> None:
        """自愈钩子: 打破重复窗口(清空连续计数, 非删历史)。"""
        with self._lock:
            self._last, self._streak = None, 0

    @property
    def streak(self) -> int:
        return self._streak

    def history(self) -> list[dict]:
        return list(self._history)


class ResourceMonitor:
    """资源监控: Token 消耗 / API 调用次数 / 运行时长 / 上下文饱和度。"""

    def __init__(self, cfg: ThresholdConfig, emit=None):
        self.b = cfg.section("behavior")
        self.emit = emit or (lambda *_a, **_k: None)
        self._start = time.time()
        self._tokens = 0
        self._api_calls = 0
        self._lock = threading.RLock()
        self._warned: set[str] = set()

    def add_tokens(self, n: int) -> None:
        with self._lock:
            self._tokens += max(0, int(n))

    def add_api_call(self, n: int = 1) -> None:
        with self._lock:
            self._api_calls += max(0, int(n))

    def snapshot(self, context_used: int = 0, context_window: int = 0) -> ResourceSnapshot:
        return ResourceSnapshot(
            ts=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            tokens=self._tokens, api_calls=self._api_calls,
            duration_sec=round(time.time() - self._start, 3),
            context_used=context_used, context_window=context_window,
        )

    def evaluate(self, context_used: int = 0, context_window: int = 0) -> list[dict]:
        """阈值评估: 返回本轮触发的事件列表(含分级)。事件即时发出。

        分级:
            资源临近上限(>=warn_ratio)      -> L1 预警
            资源超过上限                    -> L1 预警(仍可自愈)
            资源严重溢出(>=limit*1.5)       -> L3 终止
            上下文占用率 >= 90%             -> L1 + 强制重锚定动作
        """
        snap = self.snapshot(context_used, context_window)
        events: list[dict] = []
        warn_r = float(self.b["resource_warn_ratio"])

        checks = [
            ("token", snap.tokens, int(self.b["token_limit"])),
            ("api_call", snap.api_calls, int(self.b["api_call_limit"])),
            ("duration", snap.duration_sec, float(self.b["duration_limit_sec"])),
        ]
        for name, val, limit in checks:
            if limit <= 0:
                continue
            if val >= limit * 1.5:                      # 严重溢出 -> L3
                ev = {"level": "L3", "type": "resource_severe_overflow",
                      "metric": name, "value": val, "limit": limit}
                self.emit(ev["level"], ev["type"],
                          {"metric": name, "value": val, "limit": limit})
                events.append(ev)
                self._warned.discard(name)
            elif val >= limit:                          # 超上限 -> L1 告警
                if f"{name}:over" not in self._warned:
                    self._warned.add(f"{name}:over")
                    ev = {"level": "L1", "type": "resource_limit_exceeded",
                          "metric": name, "value": val, "limit": limit}
                    self.emit(ev["level"], ev["type"],
                              {"metric": name, "value": val, "limit": limit})
                    events.append(ev)
            elif val >= limit * warn_r:                 # 临近上限 -> L1 预警
                key = f"{name}:warn"
                if key not in self._warned:
                    self._warned.add(key)               # 去重: 同一指标只预警一次
                    ev = {"level": "L1", "type": "resource_near_limit",
                          "metric": name, "value": val, "limit": limit}
                    self.emit(ev["level"], ev["type"],
                              {"metric": name, "value": val, "limit": limit})
                    events.append(ev)

        util = snap.context_utilization
        if util >= float(self.b["context_saturation"]):  # >=90% -> 强制重锚定
            if "context" not in self._warned:
                self._warned.add("context")
                ev = {"level": "L1", "type": "context_saturated_reanchor",
                      "utilization": round(util, 4),
                      "threshold": self.b["context_saturation"]}
                self.emit(ev["level"], ev["type"],
                          {"utilization": round(util, 4),
                           "threshold": self.b["context_saturation"],
                           "action": "force_reanchor_keep_core_goal"})
                events.append(ev)
        return events

    def stats(self) -> dict:
        snap = self.snapshot()
        return {"tokens": snap.tokens, "api_calls": snap.api_calls,
                "duration_sec": snap.duration_sec}
