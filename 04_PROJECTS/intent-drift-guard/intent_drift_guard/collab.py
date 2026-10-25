"""算子4: 跨Agent协同校验算子.

固定规则(方案强制):
    - 父Agent下发子任务必须完整携带 结构化目标JSON + 全部约束规则(禁简化省略)
    - 子Agent输出对齐父目标: 相似度 < 0.6 -> 拦截输出 + 告警(二级: 严重偏离)
    - 多Agent任务溯源链路: 记录每一级传递偏差值
"""
from __future__ import annotations

import threading
import time

from .anchor import GOAL_FIELDS, GoalAnchor
from .config import ThresholdConfig
from .semantic import similarity


class CollabGuard:
    def __init__(self, cfg: ThresholdConfig, embedder, emit=None):
        self.min_sim = float(cfg.section("collab")["parent_child_similarity_min"])  # 0.6
        self.embed = embedder
        self.emit = emit or (lambda *_a, **_k: None)
        self._chain: list[dict] = []          # 多Agent任务溯源链路
        self._lock = threading.RLock()

    # ---- 下发: 完整携带校验 ----
    def validate_dispatch(self, child_payload: dict) -> tuple[bool, str]:
        """父->子下发强校验: 结构化目标四字段 + 约束规则必须齐备, 禁简化省略。"""
        if not isinstance(child_payload, dict):
            return False, "下发载荷非结构化目标JSON, 拦截"
        missing = [f for f in GOAL_FIELDS if f not in child_payload]
        if missing:
            self.emit("L2", "dispatch_simplified_blocked",
                      {"missing_fields": missing})
            return False, f"下发禁止简化省略, 缺失字段: {missing}"
        constraints = child_payload.get("constraint_conditions")
        if not isinstance(constraints, list):
            return False, "约束规则必须为完整列表(非字符串摘要), 拦截"
        # 约束完整性: 父锚约束必须全部透传
        return True, "ok"

    def dispatch(self, parent_goal: GoalAnchor, child_payload: dict,
                 parent_goal_full: GoalAnchor | None = None,
                 child_id: str = "child-1") -> tuple[bool, str]:
        """下发完整校验 + 父约束透传核验 + 链路登记。"""
        ok, reason = self.validate_dispatch(child_payload)
        if not ok:
            with self._lock:
                self._chain.append({"ts": _now(), "event": "dispatch_blocked",
                                    "child": child_id, "reason": reason})
            return False, reason
        # 父约束逐条透传核验 (禁省略)
        src = set(parent_goal.constraint_conditions)
        got = set(child_payload.get("constraint_conditions") or [])
        omitted = sorted(src - got)
        if omitted:
            self.emit("L2", "dispatch_constraint_omitted",
                      {"child": child_id, "omitted": omitted})
            with self._lock:
                self._chain.append({"ts": _now(), "event": "dispatch_blocked",
                                    "child": child_id, "reason": f"约束省略:{omitted}"})
            return False, f"父约束未完整透传, 省略: {omitted}"
        with self._lock:
            self._chain.append({"ts": _now(), "event": "dispatch_ok",
                                "child": child_id, "deviation": 0.0})
        return True, "ok"

    # ---- 提交: 父子目标一致性校验 ----
    def validate_submit(self, parent_goal: GoalAnchor, child_output: str,
                        child_id: str = "child-1") -> tuple[bool, str, float]:
        """子输出 vs 父目标语义相似度; <0.6 -> 拦截输出 + 二级告警。"""
        sim = similarity(self.embed, parent_goal.text(),
                         self.embed.embed(parent_goal.text()), str(child_output or ""))
        deviation = round(1.0 - sim, 4)
        allowed = sim >= self.min_sim
        with self._lock:
            self._chain.append({"ts": _now(), "event": "submit",
                                "child": child_id, "similarity": round(sim, 4),
                                "deviation": deviation, "allowed": allowed})
        if not allowed:
            self.emit("L2", "child_severe_deviation",
                      {"child": child_id, "similarity": round(sim, 4),
                       "threshold": self.min_sim, "action": "block_output"})
            return False, (f"父子目标语义相似度{sim:.3f}<0.6, 拦截输出并告警"), deviation
        return True, "ok", deviation

    # ---- 溯源链路 ----
    def trace(self) -> list[dict]:
        with self._lock:
            return list(self._chain)

    def per_level_deviations(self) -> dict:
        """每级任务传递偏差值汇总 (第N级 = 连续提交偏差)。"""
        with self._lock:
            subs = [c for c in self._chain if c["event"] == "submit"]
            return {f"L{i+1}": s["deviation"] for i, s in enumerate(subs)}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")
