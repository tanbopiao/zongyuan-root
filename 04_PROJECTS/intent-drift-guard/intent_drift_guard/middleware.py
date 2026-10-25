"""低侵入中间件: IntentDriftGuard —— 对外唯一门面.

挂载方式(不改业务代码):
    guard = IntentDriftGuard(task_id, natural_goal, workdir=".")
    gate = guard.before_thought(text)      # 每轮推理前
    if gate.allow: ...                     # allow=False 时按 gate.action 处理
    gate = guard.before_tool("name", params)  # 每次工具调用前
    ...
    guard.mount(agent) / guard.unmount()   # 一键挂载/卸载
    guard.enable() / guard.disable()       # 独立启停

执行次序(全局执行准则1, 不可逆不跳过):
    锚定目标 -> 校验推理 -> 执行动作 -> 复核闭环
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

from .anchor import AnchorStore, GoalAnchor
from .behavior import ActionSequenceDetector, ResourceMonitor
from .circuit_breaker import CircuitBreaker, CircuitState
from .collab import CollabGuard
from .config import ThresholdConfig
from .observability import EventLogger, MetricsRegistry, TrajectoryLogger
from .quota import QuotaGuard
from .self_heal import SelfHealEngine
from .semantic import SemanticMonitor, make_embedder


@dataclass
class Gate:
    """门禁结果: allow=是否放行; level=事件级别; action=处置指令; reason=原因。"""
    allow: bool
    level: str = "OK"
    action: str = "continue"
    reason: str = "ok"
    events: list = field(default_factory=list)
    detail: dict = field(default_factory=dict)


# 这些类型是熔断器/自愈器自身的留痕事件, 不回灌状态机(防递归)
_INTERNAL = {"fuse_level1", "fuse_level2", "fuse_level3", "l2_recovered",
             "l3_repaired", "reanchor_passed", "tool_param_violation",
             "tool_result_out_of_range", "heal_ok", "heal_failed_workorder"}


def _load_heal_strategies(pkg_root: str) -> dict | None:
    """加载 config/self_heal.json 的 strategies 段(白名单外场景由引擎拒绝)。"""
    path = os.path.join(pkg_root, "config", "self_heal.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("strategies") or None
    except Exception:
        return None


class IntentDriftGuard:
    def __init__(self, task_id: str, natural_goal: str,
                 workdir: str = ".", config_path: str | None = None,
                 embedder=None):
        self.task_id = task_id
        self.workdir = workdir
        os.makedirs(workdir, exist_ok=True)
        pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if config_path is None:                      # 默认加载 config/thresholds.json
            cand = os.path.join(pkg_root, "config", "thresholds.json")
            config_path = cand if os.path.exists(cand) else None
        self.cfg = ThresholdConfig(config_path)
        rt = self.cfg.section("runtime")
        self.log_dir = os.path.join(workdir, rt.get("log_dir", "logs"))
        self.report_dir = os.path.join(workdir, rt.get("report_dir", "reports"))
        os.makedirs(self.report_dir, exist_ok=True)

        # 可观测
        self.logger = EventLogger(self.log_dir)
        self.traj = TrajectoryLogger(self.log_dir)
        self.metrics = MetricsRegistry()

        # 事件总线: 落日志 + 计数 + (非内部事件)回灌熔断状态机
        self._breaker: CircuitBreaker | None = None

        # 算子1 锚定 (只读锁档)
        self.anchor_doc = GoalAnchor.parse(natural_goal)
        self.store = AnchorStore(os.path.join(workdir, rt.get("anchor_dir", "anchor_store")))
        self.store.save(task_id, self.anchor_doc)

        emb = embedder or make_embedder(self.cfg)
        if getattr(emb, "degraded", False):         # 后端降级如实留痕(可观测)
            self._log_only("ALERT", "embedding_backend_degraded",
                           {"configured": self.cfg.get("semantic.embedding_backend"),
                            "active": emb.name,
                            "calibration": getattr(emb, "calibration", 1.0),
                            "note": "BGE-m3不可用已降级lexical, 分数经标定系数对齐0.75阈值标尺"})
        # 熔断器(其 emit 只留痕, 不回灌)
        self.breaker = CircuitBreaker(
            self.cfg, self.report_dir,
            emit=lambda lv, tp, d=None: self._log_only(lv, tp, d),
            get_context=self._fault_context)
        self._breaker = self.breaker

        # 算子2 语义漂移 (每轮推理前强制对齐)
        self.semantic = SemanticMonitor(self.anchor_doc, self.cfg,
                                        emit=self._emit, embedder=emb)
        # 算子3 行为风控
        self.action_detector = ActionSequenceDetector(self.cfg, emit=self._emit)
        self.resource = ResourceMonitor(self.cfg, emit=self._emit)
        # 算子4 跨Agent协同
        self.collab = CollabGuard(self.cfg, emb, emit=self._emit)
        # 自愈 (策略配置: config/self_heal.json, 白名单校验)
        self.heal = SelfHealEngine(workdir, emit=self._log_only,
                                   strategies=_load_heal_strategies(pkg_root))
        # 扩展算子: 平台积分/额度熔断 (台账 config/platform_quota.json)
        self.quota = QuotaGuard(self.cfg, pkg_root,
                                emit=self._log_only, metrics=self.metrics)

        # 上下文状态(供90%饱和判定与自愈裁剪)
        self.context_window = 0
        self.context_used = 0
        self.enabled = True
        self._mounted: dict = {}
        self._auto_heal = True

    # ---------------- 事件管道 ----------------
    def _log_only(self, level: str, etype: str, detail: dict | None = None) -> None:
        self.logger.write(level, etype, detail)
        self.metrics.incr(f"event.{etype}")

    def _emit(self, level: str, etype: str, detail: dict | None = None) -> None:
        """算子事件: 留痕 + 计数 + 回灌熔断状态机(内部事件除外)。"""
        self._log_only(level, etype, detail)
        if etype in _INTERNAL:
            return
        res = self.breaker.handle(level, etype, detail or {})
        self.metrics.incr(f"fuse.{res.get('derived_level', level)}")
        # 一级事件 -> 自动触发自愈(漂移/循环/溢出场景)
        if self._auto_heal and res.get("action") in ("reanchor", "limit") \
                and etype not in _INTERNAL:
            self.heal.handle(etype, self, detail or {})

    # ---------------- 门禁钩子 ----------------
    def before_thought(self, text: str) -> Gate:
        """每轮推理前: 锚定对齐校验 + 漂移判定 + 步数/资源管控。"""
        if not self.enabled:
            return Gate(True, action="continue", reason="guard_disabled")
        if self.breaker.terminated:
            return Gate(False, level="L3", action="terminate",
                        reason="三级熔断已终止, 需人工排查修复后重启")
        rec = self.semantic.check(text)
        self.traj.write(rec.__dict__)
        if not rec.events:                          # 稳定步: 解除"连续一级"计数
            self.breaker.mark_clean_step()
        self.metrics.gauge("semantic.last_similarity", rec.similarity)
        self.metrics.gauge("semantic.step", rec.step)
        events = list(rec.events)
        action = "continue"
        if self.breaker.state is CircuitState.L1:
            action = "reanchor"                    # 预警级: 推送重锚定指令
        return Gate(
            allow=self.breaker.can_execute(),
            level="L2" if self.breaker.readonly else ("L1" if events else "OK"),
            action=action,
            reason=";".join(events) if events else "ok",
            events=events,
            detail={"step": rec.step, "similarity": rec.similarity,
                    "distance": rec.distance},
        )

    def before_tool(self, name: str, params: dict) -> Gate:
        """每次工具调用前: 锁定判定 + 入参强校验。"""
        if not self.enabled:
            return Gate(True, action="continue", reason="guard_disabled")
        if self.breaker.tools_locked:
            return Gate(False, level="L2", action="tools_locked",
                        reason=f"工具调用权限已锁定({self.breaker.state.value})")
        ok, reason = self.semantic.validate_tool_params(params or {})
        if not ok:
            self._log_only("BLOCK", "tool_param_violation",
                           {"tool": name, "reason": reason})
            return Gate(False, level="BLOCK", action="intercept", reason=reason)
        self.resource.add_api_call(1)
        return Gate(True, action="continue", reason=f"tool={name} ok")

    def after_tool(self, result: str, tokens: int = 0) -> Gate:
        """工具执行后: 出参校验 + 资源入账 + 饱和度评估。"""
        if not self.enabled:
            return Gate(True)
        if tokens:
            self.resource.add_tokens(tokens)
        ok, reason = self.semantic.validate_tool_result(result)
        if not ok:
            self._log_only("BLOCK", "tool_result_out_of_range", {"reason": reason})
            return Gate(False, level="BLOCK", action="intercept", reason=reason)
        evs = self.resource.evaluate(self.context_used, self.context_window)
        return Gate(not self.breaker.tools_locked,
                    level="L1" if evs else "OK",
                    action="reanchor" if evs else "continue",
                    reason="resource_evaluated", events=[e["type"] for e in evs])

    def on_action(self, action) -> Gate:
        """行为动作登记: 死循环检测(连续3次->二级熔断)。"""
        entry = self.action_detector.record(action)
        if entry["dead_loop"]:
            return Gate(False, level="L2", action="limit",
                        reason="连续3次重复动作, 判定无效循环, 触发二级熔断")
        return Gate(True, action="continue",
                    reason=f"streak={entry['streak']}",
                    detail=entry)

    def on_context(self, used: int, window: int) -> Gate:
        """上下文占用更新: >=90% 强制重锚定(清理无效上下文, 保留核心目标)。"""
        self.context_used, self.context_window = int(used), int(window)
        evs = self.resource.evaluate(self.context_used, self.context_window)
        saturated = any(e["type"] == "context_saturated_reanchor" for e in evs)
        if saturated and self._auto_heal:
            self.heal.handle("context_saturated_reanchor", self, {"used": used})
        return Gate(True, level="L1" if saturated else "OK",
                    action="force_reanchor" if saturated else "continue",
                    reason=f"util={self.context_used}/{self.context_window}",
                    events=[e["type"] for e in evs])

    def report_tokens(self, n: int) -> None:
        self.resource.add_tokens(n)

    def on_quota(self, platform: str, used: int, budget: int | None = None) -> Gate:
        """平台积分/额度上报(扩展算子): >=80%一级预警, >=95%二级只读+锁工具.

        边沿触发: 仅跨越档位时进熔断状态机, 持续同档不重复计数;
        额度回填 -> 一级自动解除(二级仍须人工确认/备用流程)。
        """
        if not self.enabled:
            return Gate(True, action="continue", reason="guard_disabled")
        res = self.quota.report(platform, used, budget)
        ev, level, detail = res.get("event"), res.get("level"), res.get("detail") or {}
        if ev == "quota_refilled":                # 不进状态机(防被误判为一级事件)
            self._log_only("OPS", "quota_refilled", detail)
            self.breaker.quota_refilled(platform)
        elif ev:                                  # L1/L2 进熔断+自愈管道
            self._emit(level, ev, detail)
        locked = self.breaker.tools_locked
        if level == "REFILL":                     # 回填档不算告警级别
            level = "OK"
        return Gate(
            allow=not locked,
            level="L2" if locked else (level if ev else "OK"),
            action="limit" if locked else ("warn" if ev else "continue"),
            reason=f"{platform} ratio={detail.get('ratio', 'n/a')}",
            events=[ev] if ev else [],
            detail=detail,
        )

    def on_child_dispatch(self, child_payload: dict, child_id: str = "child-1") -> Gate:
        """父->子下发: 完整携带结构化目标+全部约束, 否则拦截。"""
        ok, reason = self.collab.dispatch(self.anchor_doc, child_payload, child_id=child_id)
        return Gate(ok, level="L2" if not ok else "OK",
                    action="block" if not ok else "continue", reason=reason)

    def on_child_submit(self, child_output: str, child_id: str = "child-1") -> Gate:
        """子->父提交: 相似度<0.6 拦截输出+告警; 自愈=重新对齐。"""
        ok, reason, dev = self.collab.validate_submit(self.anchor_doc, child_output, child_id)
        if not ok and self._auto_heal:
            self.heal.handle("child_severe_deviation", self,
                             {"child": child_id, "deviation": dev})
        return Gate(ok, level="L2" if not ok else "OK",
                    action="block" if not ok else "continue",
                    reason=reason, detail={"deviation": dev})

    def report_malicious(self, reason: str) -> Gate:
        """恶意无效执行直报 -> 三级熔断。"""
        self._emit("L3", "malicious_invalid_execution", {"reason": reason})
        return Gate(False, level="L3", action="terminate", reason=reason)

    # ---------------- 熔断恢复入口 ----------------
    def reanchor(self) -> dict:
        """一级恢复: 重锚定校验通过 -> 自动接续(锚本身不可改)。"""
        try:
            locked = self.store.get(self.task_id)           # 哈希复核
        except Exception as e:
            return {"passed": False, "reason": f"锚校验失败: {e}"}
        same = locked.text() == self.anchor_doc.text()
        if same:
            self.breaker.reanchor_passed(self.task_id)
            return {"passed": True, "action": "auto_resume", "no_breakpoint": True}
        return {"passed": False, "reason": "锚内容与在用目标不一致"}

    def manual_confirm(self, note: str = "人工确认目标") -> dict:
        return self.breaker.manual_confirm(note)

    def backup_flow(self, name: str = "default") -> dict:
        return self.breaker.backup_flow(name)

    def repair_completed(self, note: str = "人工排查修复完成") -> dict:
        return self.breaker.repair_completed(note)

    def checkpoint(self) -> dict:
        """断点留档(自愈动作之一): 状态快照落盘。"""
        path = os.path.join(self.report_dir,
                            f"checkpoint_{time.strftime('%Y%m%d_%H%M%S')}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.stats(), f, ensure_ascii=False, indent=2)
        return {"path": path}

    # ---------------- 低侵入挂载 ----------------
    def mount(self, agent) -> None:
        """一键挂载: 在业务Agent上挂 guard 与钩子引用, 不改其源码。"""
        self._mounted = {
            "agent": agent, "prev_guard": getattr(agent, "intent_drift_guard", None),
        }
        agent.intent_drift_guard = self
        self._log_only("OPS", "mounted", {"agent": type(agent).__name__})

    def unmount(self) -> None:
        """一键卸载: 还原现场。"""
        agent = self._mounted.get("agent")
        if agent is not None:
            prev = self._mounted.get("prev_guard")
            if prev is None:
                if hasattr(agent, "intent_drift_guard"):
                    delattr(agent, "intent_drift_guard")
            else:
                agent.intent_drift_guard = prev
        self._mounted = {}
        self._log_only("OPS", "unmounted", {})

    def enable(self) -> None:
        self.enabled = True
        self._log_only("OPS", "enabled", {})

    def disable(self) -> None:
        self.enabled = False
        self._log_only("OPS", "disabled", {})

    # ---------------- 面板/自测数据 ----------------
    def _fault_context(self) -> dict:
        return {"trajectory": self.semantic.trajectory(),
                "abnormal_nodes": [h for h in self.breaker.history()
                                   if h.get("derived_level") in ("L2", "L3")],
                "resource_usage": self.resource.stats()}

    def stats(self) -> dict:
        snap = self.breaker.snapshot()
        self.metrics.gauge("fuse.L1_total", snap["totals"]["L1"])
        self.metrics.gauge("fuse.L2_total", snap["totals"]["L2"])
        self.metrics.gauge("fuse.L3_total", snap["totals"]["L3"])
        return {"task_id": self.task_id,
                "anchor": self.anchor_doc.to_dict(),
                "semantic": self.semantic.stats(),
                "resources": self.resource.stats(),
                "context": {"used": self.context_used, "window": self.context_window},
                "circuit": snap,
                "collab_chain": self.collab.trace(),
                "per_level_deviations": self.collab.per_level_deviations(),
                "quota": self.quota.snapshot(),
                "metrics": self.metrics.snapshot()}

    def export_report(self, name: str = "guard_stats") -> str:
        path = os.path.join(self.report_dir, f"{name}_{time.strftime('%Y%m%d_%H%M%S')}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.stats(), f, ensure_ascii=False, indent=2)
        return path
