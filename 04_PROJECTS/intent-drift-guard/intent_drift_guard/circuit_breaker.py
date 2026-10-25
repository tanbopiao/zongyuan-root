"""算子5: 三级熔断自愈调度算子 (核心控制中枢).

三级逻辑 (方案强制, 逐条匹配):

一级熔断 (预警级·自动纠偏)
    触发: 语义漂移超阈值 / 推理步数超限 / 资源临近上限 / 上下文饱和重锚定
    动作: 日志留存 + 推送目标重锚定指令 + 强制重新对齐初始任务
    恢复: 重锚定校验通过 -> 自动接续原任务(无断点), 连续计数清零
    升级: 连续 2 次一级熔断(中间无成功恢复) -> 二级

二级熔断 (限制级·强制管控)
    触发: 连续2次一级 / 死循环 / 子Agent严重偏离目标
    动作: 暂停业务执行 + 锁定工具调用 + 只读观测模式
    恢复: 人工确认目标 / 自动备用任务流程 (确认后连续计数清零)
    升级: 连续 3 次二级熔断 -> 三级

三级熔断 (终止级·彻底止损)
    触发: 连续3次二级 / 恶意无效执行 / 资源严重溢出
    动作: 终止全部任务 + 回收资源 + 生成标准化故障报告
          (漂移轨迹 / 异常节点 / 资源消耗数据)
    恢复: 人工排查修复后重启任务链路
"""
from __future__ import annotations

import json
import os
import threading
import time
from enum import Enum

from .config import ThresholdConfig


class CircuitState(str, Enum):
    NORMAL = "NORMAL"
    L1 = "L1_WARN"          # 预警级(自动纠偏中)
    L2 = "L2_LIMIT"         # 限制级(只读观测)
    L3 = "L3_HALT"          # 终止级(彻底止损)


# 事件 -> 触发级别 映射 (方案语义)
_L1_TYPES = {"semantic_drift", "align_below_warn", "step_limit_exceeded",
             "resource_near_limit", "resource_limit_exceeded",
             "context_saturated_reanchor"}
_L2_TYPES = {"dead_loop_detected", "child_severe_deviation",
             "dispatch_simplified_blocked", "dispatch_constraint_omitted"}
_L3_TYPES = {"resource_severe_overflow", "malicious_invalid_execution"}


class CircuitBreaker:
    """三级熔断状态机 (线程安全, 全事件留痕)。"""

    def __init__(self, cfg: ThresholdConfig, report_dir: str,
                 emit=None, get_context=None):
        self.c = cfg.section("circuit")
        self.report_dir = report_dir
        os.makedirs(self.report_dir, exist_ok=True)
        self.emit = emit or (lambda *_a, **_k: None)
        self.get_context = get_context or (lambda: {})
        self.state = CircuitState.NORMAL
        self.l1_streak = 0            # 连续一级计数(重锚定后需连续N步稳定才清零)
        self.l2_count = 0             # 二级熔断计数(人工确认/备用流程清零)
        self._clean_steps = 0         # 重锚定后的稳定步计数
        self.totals = {"L1": 0, "L2": 0, "L3": 0}
        self._history: list[dict] = []
        self._lock = threading.RLock()
        self._terminate_reason: str | None = None

    # ---------- 门禁(供中间件查询) ----------
    @property
    def tools_locked(self) -> bool:
        """二级及以上: 锁定工具调用权限。"""
        return self.state in (CircuitState.L2, CircuitState.L3)

    @property
    def readonly(self) -> bool:
        """二级及以上: 只读观测模式。"""
        return self.tools_locked

    @property
    def terminated(self) -> bool:
        return self.state is CircuitState.L3

    def can_execute(self) -> bool:
        """业务执行门: 三级终止后 False; 二级限制期仅观测; 一级可继续。"""
        return self.state in (CircuitState.NORMAL, CircuitState.L1)

    # ---------- 事件主入口 ----------
    def handle(self, level: str, etype: str, detail: dict | None = None) -> dict:
        """接收事件(来自各算子), 推进状态机, 返回动作指令。"""
        detail = detail or {}
        with self._lock:
            derived = self._derive_level(level, etype)
            result = {"event": etype, "derived_level": derived,
                      "from_state": self.state.value, "action": None}
            if derived == "L1":
                result.update(self._enter_l1(etype, detail))
            elif derived == "L2":
                result.update(self._enter_l2(etype, detail))
            elif derived == "L3":
                result.update(self._enter_l3(etype, detail))
            result["to_state"] = self.state.value
            self._history.append({"ts": _now(), **result, "detail": detail})
            return result

    @staticmethod
    def _derive_level(level: str, etype: str) -> str:
        if etype in _L3_TYPES:
            return "L3"
        if etype in _L2_TYPES:
            return "L2"
        if etype in _L1_TYPES:
            return "L1"
        return level if level in ("L1", "L2", "L3") else "L1"

    # ---------- 一级: 预警纠偏 ----------
    def _enter_l1(self, etype: str, detail: dict) -> dict:
        self.totals["L1"] += 1
        self.l1_streak += 1
        already = self.state is CircuitState.L1
        # 升级判定: 连续第2次一级(无成功恢复) -> 二级
        if self.l1_streak >= int(self.c["l1_to_l2_count"]):
            return self._enter_l2("l1_escalated",
                                  {"cause": etype, "l1_streak": self.l1_streak})
        if self.state is CircuitState.NORMAL:
            self.state = CircuitState.L1
        action = {
            "action": "reanchor",
            "instruction": "推送目标重锚定指令: 重新对齐初始任务核心目标/约束/成功标准",
            "resume": "重锚定校验通过后自动接续, 无断点丢失",
            "log": "level1_fuse_logged",
        }
        if already:
            action["note"] = "已处于一级预警态, 持续留痕"
        self.emit("L1", "fuse_level1", {"cause": etype, "streak": self.l1_streak, **detail})
        return action

    def reanchor_passed(self, task_id: str = "") -> dict:
        """一级恢复: 重锚定校验通过 -> 接续原任务(无断点).

        注意: 不立即清零 l1_streak —— 连续计数须由后续稳定步数解除
        (mark_clean_step), 以保证"连续2次一级熔断->二级"可被观测。
        """
        with self._lock:
            self._clean_steps = 0
            if self.state is CircuitState.L1:
                self.state = CircuitState.NORMAL
            rec = {"ts": _now(), "event": "reanchor_passed", "task_id": task_id,
                   "action": "auto_resume", "l1_streak_kept": self.l1_streak,
                   "to_state": self.state.value}
            self._history.append(rec)
            self.emit("L1", "reanchor_passed", {"task_id": task_id, "resume": "auto_continue"})
            return rec

    def mark_clean_step(self) -> None:
        """连续一级计数的解除条件: 重锚定后连续 N 步(默认3)对齐校验通过。"""
        with self._lock:
            if self.l1_streak <= 0 or self.state is not CircuitState.NORMAL:
                return
            self._clean_steps += 1
            if self._clean_steps >= int(self.c.get("l1_clear_clean_steps", 3)):
                self.l1_streak = 0
                self._clean_steps = 0
                self.emit("L1", "streak_cleared_by_stability",
                          {"clean_steps": self.c.get("l1_clear_clean_steps", 3)})

    # ---------- 二级: 限制管控 ----------
    def _enter_l2(self, etype: str, detail: dict) -> dict:
        self.totals["L2"] += 1
        self.l2_count += 1
        # 升级判定: 连续第3次二级 -> 三级
        if self.l2_count >= int(self.c["l2_to_l3_count"]):
            return self._enter_l3("l2_escalated",
                                  {"cause": etype, "l2_count": self.l2_count, **detail})
        self.state = CircuitState.L2
        self.emit("L2", "fuse_level2", {"cause": etype, "l2_count": self.l2_count, **detail})
        return {
            "action": "limit",
            "instruction": ["暂停所有业务执行", "锁定工具调用权限", "进入只读观测模式"],
            "recovery": "人工确认目标 / 自动触发备用任务流程",
            "logged": "level2_fuse_logged",
        }

    def manual_confirm(self, note: str = "人工确认目标") -> dict:
        """二级恢复路径A: 人工确认目标 -> 解锁, 计数清零。"""
        return self._recover_l2("manual_confirm", note)

    def quota_refilled(self, platform: str = "") -> dict:
        """配额恢复: 平台积分回填 -> 自动解除一级预警并清连续计数。

        二级限制仍按方案恢复规则(人工确认目标 / 备用流程), 防止额度反复触顶自动逃逸。
        """
        with self._lock:
            if self.state is CircuitState.L1:
                self.state = CircuitState.NORMAL
            self.l1_streak = 0
            self._clean_steps = 0
            rec = {"ts": _now(), "event": "quota_refilled", "platform": platform,
                   "action": "release_l1_keep_l2", "to_state": self.state.value}
            self._history.append(rec)
            self.emit("L1", "quota_refilled", {"platform": platform,
                                               "resume": "auto_continue"})
            return rec

    def backup_flow(self, name: str = "default") -> dict:
        """二级恢复路径B: 自动触发备用任务流程。"""
        return self._recover_l2("backup_flow", name)

    def _recover_l2(self, how: str, note: str) -> dict:
        with self._lock:
            if self.state is CircuitState.L2:
                self.state = CircuitState.NORMAL
            self.l1_streak = 0
            self.l2_count = 0                       # 恢复即断开"连续"
            rec = {"ts": _now(), "event": f"l2_recovered:{how}", "note": note,
                   "to_state": self.state.value}
            self._history.append(rec)
            self.emit("L2", "l2_recovered", {"how": how, "note": note})
            return rec

    # ---------- 三级: 彻底止损 ----------
    def _enter_l3(self, etype: str, detail: dict) -> dict:
        self.totals["L3"] += 1
        self.state = CircuitState.L3
        self._terminate_reason = etype
        self.emit("L3", "fuse_level3",
                  {"cause": etype, "action": "terminate_reclaim_report", **detail})
        report_path = self._write_fault_report(etype, detail)
        return {
            "action": "terminate",
            "instruction": ["终止全部任务进程", "回收所有资源",
                            "生成标准化故障报告"],
            "fault_report": report_path,
            "recovery": "人工排查修复后重启任务链路",
        }

    def _write_fault_report(self, cause: str, detail: dict) -> str:
        """标准化故障报告: 漂移轨迹 + 异常节点 + 资源消耗数据。"""
        try:
            ctx = self.get_context() or {}
        except Exception as e:                       # 报告自身不可再失败
            ctx = {"context_error": str(e)}
        report = {
            "report_type": "INTENT_DRIFT_FAULT_REPORT",
            "generated_at": _now(),
            "cause": cause,
            "detail": detail,
            "final_state": self.state.value,
            "terminate_reason": self._terminate_reason,
            "fuse_totals": dict(self.totals),
            "drift_trajectory": ctx.get("trajectory", []),   # 漂移轨迹
            "abnormal_nodes": ctx.get("abnormal_nodes", []),  # 异常节点
            "resource_usage": ctx.get("resource_usage", {}),   # 资源消耗
            "recovery_required": "人工排查修复后重启任务链路",
        }
        path = os.path.join(self.report_dir,
                            f"fault_{time.strftime('%Y%m%d_%H%M%S')}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return path

    def repair_completed(self, note: str = "人工排查修复完成") -> dict:
        """三级恢复: 人工排查修复后重启任务链路 (唯一恢复入口)。"""
        with self._lock:
            self.state = CircuitState.NORMAL
            self.l1_streak = 0
            self.l2_count = 0
            self._terminate_reason = None
            rec = {"ts": _now(), "event": "l3_repaired", "note": note,
                   "action": "restart_task_pipeline", "to_state": self.state.value}
            self._history.append(rec)
            self.emit("L3", "l3_repaired", {"note": note})
            return rec

    # ---------- 观测 ----------
    def snapshot(self) -> dict:
        with self._lock:
            return {"state": self.state.value, "l1_streak": self.l1_streak,
                    "l2_count": self.l2_count, "totals": dict(self.totals),
                    "tools_locked": self.tools_locked, "readonly": self.readonly}

    def history(self) -> list[dict]:
        with self._lock:
            return list(self._history)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")
