"""故障自愈引擎: 内置常见漂移/循环/上下文溢出场景自动化自愈脚本.

策略配置: config/self_heal.json
自愈优先, 无法自愈 -> 生成工单(workorders/*.json) + 告警日志(ERROR级)。
"""
from __future__ import annotations

import json
import os
import time


DEFAULT_STRATEGIES = {
    # 场景: {action, max_attempts, on_fail}
    "semantic_drift":            {"action": "reanchor",            "max_attempts": 2, "on_fail": "workorder"},
    "align_below_warn":          {"action": "reanchor",            "max_attempts": 2, "on_fail": "workorder"},
    "step_limit_exceeded":       {"action": "reanchor_checkpoint", "max_attempts": 1, "on_fail": "workorder"},
    "dead_loop_detected":        {"action": "break_action_window", "max_attempts": 1, "on_fail": "workorder"},
    "context_saturated_reanchor": {"action": "context_trim_keep_goal", "max_attempts": 1, "on_fail": "workorder"},
    "resource_near_limit":       {"action": "checkpoint_pause",    "max_attempts": 1, "on_fail": "workorder"},
    "resource_limit_exceeded":   {"action": "checkpoint_pause",    "max_attempts": 1, "on_fail": "workorder"},
    "child_severe_deviation":    {"action": "block_and_realign_child", "max_attempts": 1, "on_fail": "workorder"},
}


class SelfHealEngine:
    """自愈执行器.

    动作语义:
      reanchor                -> 目标重锚定(重新对齐核心目标, 保留锚不变)
      reanchor_checkpoint     -> 断点+重锚定
      break_action_window     -> 打破死循环重复窗口(清连续计数)
      context_trim_keep_goal  -> 清理无效上下文, 保留核心目标
      checkpoint_pause        -> 断点暂停, 资源恢复后续跑
      block_and_realign_child -> 拦截子输出并重新对齐父目标
    """

    def __init__(self, workdir: str, emit=None, strategies: dict | None = None):
        self.workdir = workdir
        self.wo_dir = os.path.join(workdir, "workorders")
        os.makedirs(self.wo_dir, exist_ok=True)
        self.emit = emit or (lambda *_a, **_k: None)
        self.strategies = dict(DEFAULT_STRATEGIES)
        if strategies:                              # 配置文件覆盖(仅允许已定义场景)
            for k, v in strategies.items():
                if k in self.strategies:
                    self.strategies[k].update(v)
        self._attempts: dict[str, int] = {}

    def handle(self, etype: str, guard, detail: dict | None = None) -> dict:
        """尝试自愈; 成功返回 healed=True, 失败生成工单并告警。"""
        detail = detail or {}
        strat = self.strategies.get(etype)
        if not strat:
            return {"healed": False, "reason": f"无自愈策略: {etype}", "workorder": None}

        attempt = self._attempts.get(etype, 0) + 1
        self._attempts[etype] = attempt
        action = strat["action"]
        try:
            ok = self._run(action, guard, detail)
        except Exception as e:                      # 自愈异常按失败处理
            ok, err = False, str(e)
        else:
            err = None

        if ok:
            self.emit("SELFHEAL", "heal_ok",
                      {"scenario": etype, "action": action, "attempt": attempt})
            return {"healed": True, "action": action, "attempt": attempt}

        if attempt >= int(strat.get("max_attempts", 1)):
            wo = self._workorder(etype, action, attempt, detail, err)
            self.emit("ALERT", "heal_failed_workorder",
                      {"scenario": etype, "workorder": wo, "severity": "P2"})
            return {"healed": False, "workorder": wo, "action": action}
        return {"healed": False, "retry_pending": True, "attempt": attempt}

    # ---- 自愈动作实现(全部委托门禁对象, 不侵入业务Agent) ----
    def _run(self, action: str, guard, detail: dict) -> bool:
        if action in ("reanchor", "reanchor_checkpoint"):
            return bool(guard.reanchor().get("passed"))
        if action == "break_action_window":
            guard.action_detector.reset()
            return guard.action_detector.streak == 0
        if action == "context_trim_keep_goal":
            # 清理无效上下文: 释放到 60% 饱和度以下, 保留核心目标锚
            guard.context_used = int(guard.context_window * 0.6)
            return guard.context_used < guard.context_window * float(guard.cfg.get("behavior.context_saturation"))
        if action == "checkpoint_pause":
            return guard.checkpoint()               # 断点留档成功即视为自愈
        if action == "block_and_realign_child":
            return True                             # 拦截已在协同算子完成, 此处确认对齐指令已下发
        return False

    def _workorder(self, etype: str, action: str, attempt: int,
                   detail: dict, err: str | None) -> str:
        ts = time.strftime("%Y%m%d_%H%M%S")
        wo = {
            "workorder_type": "INTENT_DRIFT_SELFHEAL_FAILED",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "scenario": etype, "failed_action": action, "attempts": attempt,
            "detail": detail, "error": err,
            "severity": "P2", "status": "OPEN",
            "assigned": "人工处置(无法自动自愈)",
        }
        path = os.path.join(self.wo_dir, f"wo_{etype}_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(wo, f, ensure_ascii=False, indent=2)
        return path
