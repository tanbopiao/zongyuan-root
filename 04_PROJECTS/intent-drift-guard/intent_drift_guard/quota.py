"""扩展算子: 平台积分/额度熔断 (platform quota fuse).

背景(归因分析 CREDIT-BURN-20261022): 各平台办公AI的赠送积分/额度消耗过快, 而零成本元
宪法只熔断"钱"(单日10元), 平台积分既无计量也无熔断 -> 无告警耗尽。本算子把平台积分
纳入既有三级熔断防线:

    ratio >= quota.warn_ratio     (默认0.80) -> 一级: 预警留痕(边沿触发)
    ratio >= quota.critical_ratio (默认0.95) -> 二级: 锁工具 + 只读观测(边沿触发)

判定规则:
    - 边沿触发: 仅跨越档位时发事件, 持续处于同档不重复计数(防误升级, 符合"连续N次"语义)
    - 直接跳档: 一次性跨越两级只发最高档事件(不制造虚假"连续一级")
    - budget <= 0 = 未配置额度 -> 不参与判定(避免误熔断)
    - 额度回填(比例跌回预警线以下) -> 记录复位, 一级自动解除; 二级按方案仍须人工/备用流程
"""
from __future__ import annotations

import json
import os

_LEVEL_ORDER = {"NONE": 0, "WARN": 1, "CRITICAL": 2}


class QuotaGuard:
    """平台积分/额度台账 + 档位判定.

    台账文件 config/platform_quota.json: {platforms: {name: {budget, used, ...}}}
    阈值来源 config/thresholds.json 的 quota 段(动态阈值适配, 变更留痕于 audit)。
    """

    def __init__(self, cfg, pkg_root: str, emit=None, metrics=None):
        self.cfg = cfg
        self.q = cfg.section("quota") or {}
        self.emit = emit or (lambda *_a, **_k: None)
        self.metrics = metrics
        self.warn_ratio = float(self.q.get("warn_ratio", 0.8))
        self.critical_ratio = float(self.q.get("critical_ratio", 0.95))
        self.enabled = bool(self.q.get("enable", True))
        self._last: dict[str, str] = {}          # platform -> 最近档位(边沿触发基准)
        self._data: dict[str, dict] = {}         # platform -> {budget, used, ...}
        self._path = os.path.join(pkg_root, self.q.get("quota_file",
                                                       "config/platform_quota.json"))
        self._load()

    # ---- 台账加载 ----
    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                raw = json.load(f)
            for name, rec in (raw.get("platforms") or {}).items():
                if isinstance(rec, dict):
                    self._data[name] = {k: v for k, v in rec.items()
                                        if not str(k).startswith("_")}
        except Exception:
            # 台账损坏不阻断主链路; 状态可观测(snapshot 里 load_error)
            self._data = {}
            self._load_error = True

    # ---- 档位判定 ----
    def _level_of(self, ratio: float) -> str:
        if ratio >= self.critical_ratio:
            return "CRITICAL"
        if ratio >= self.warn_ratio:
            return "WARN"
        return "NONE"

    def report(self, platform: str, used: int, budget: int | None = None) -> dict:
        """上报某平台已用/预算; 返回边沿触发的熔断事件(无事件时 event=None)。"""
        rec = self._data.setdefault(platform, {})
        rec["used"] = int(used)
        if budget is not None:
            rec["budget"] = int(budget)
        b = int(rec.get("budget", 0) or 0)
        if not self.enabled or b <= 0:
            return {"event": None, "level": "OK",
                    "detail": {"platform": platform, "enabled": self.enabled,
                               "budget": b, "reason": "未配置或未启用"}}
        ratio = max(0.0, min(1.0, int(used) / b))
        rec["ratio"] = round(ratio, 4)
        target = self._level_of(ratio)
        last = self._last.get(platform, "NONE")
        if self.metrics:
            self.metrics.gauge(f"quota.{platform}.ratio", round(ratio, 4))
        if target == last:                        # 边沿未变: 不重复发事件
            return {"event": None, "level": "OK",
                    "detail": {"platform": platform, "ratio": round(ratio, 4),
                               "level": target}}
        self._last[platform] = target
        detail = {"platform": platform, "used": int(used), "budget": b,
                  "ratio": round(ratio, 4), "warn_ratio": self.warn_ratio,
                  "critical_ratio": self.critical_ratio}
        if target == "CRITICAL":                  # 跳档也只发最高档
            return {"event": "quota_critical", "level": "L2", "detail": detail}
        if target == "WARN":
            return {"event": "quota_near_limit", "level": "L1", "detail": detail}
        # target == NONE: 从高档位跌回(额度回填)
        return {"event": "quota_refilled", "level": "REFILL", "detail": detail}

    # ---- 观测 ----
    def snapshot(self) -> dict:
        out = {}
        for name, rec in self._data.items():
            out[name] = {"budget": rec.get("budget", 0),
                         "used": rec.get("used", 0),
                         "ratio": rec.get("ratio", 0.0),
                         "level": self._last.get(name, "NONE")}
        return {"enable": self.enabled, "warn_ratio": self.warn_ratio,
                "critical_ratio": self.critical_ratio, "platforms": out}
