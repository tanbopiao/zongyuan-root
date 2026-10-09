#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT · AxiomGate 裁决器 + 配额稳态保护
==========================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 协议: NTFY-CONNECT-001 | 火斗云智AIOS
版本: V1.0 (2026-10-08)
定位: 自治内核基底的安全/资源算子层 — 派发前裁决 + 配额稳态三模式

能力:
  1. 风险三优先评分: 风险最小 > 成本最小 > 收益最大 (元法则 P1>P2>P3)
  2. 四维真值校验:  空间/时间/属性/因果 四维完整性校验
  3. 配额稳态三模式: 正常 → 预警 → 只读空转 (META-RULE-012)
  4. 权限准入裁决:  节点/任务 准入判定 (AxiomGate 裁决器)

集成: 被 zr_cloud_ctl.py 的 dispatch_one 调用, 派发前过裁决
"""
import json, os, time

# ---------- 元法则常量 ----------
RISK_PRIORITY = "风险最小 > 成本最小 > 收益最大"   # P1>P2>P3
QUOTA_MODES = ["normal", "pre_warn", "read_only_idle"]  # 配额三模式

# 配额阈值 (可被环境变量覆盖)
QUOTA_THRESHOLD_PRE = float(os.environ.get("QUOTA_THRESHOLD_PRE", "0.30"))   # 余量<30% 预警
QUOTA_THRESHOLD_IDLE = float(os.environ.get("QUOTA_THRESHOLD_IDLE", "0.10")) # 余量<10% 只读

# ---------- 配额稳态 ----------
class QuotaSteady:
    """配额稳态保护 META-RULE-012: 正常→预警→只读空转"""
    def __init__(self):
        self.mode = "normal"
        self.last_check = 0

    def check(self, quota_left=None, quota_total=None):
        """返回当前稳态模式; 可传实际配额, 缺省走 last_check 刷新"""
        now = time.time()
        if now - self.last_check < 15:  # 15s 缓存
            return self.mode
        self.last_check = now
        if quota_total and quota_total > 0:
            ratio = (quota_left or 0) / quota_total
            if ratio <= QUOTA_THRESHOLD_IDLE:
                self.mode = "read_only_idle"
            elif ratio <= QUOTA_THRESHOLD_PRE:
                self.mode = "pre_warn"
            else:
                self.mode = "normal"
        return self.mode

    def allow_generative(self):
        """是否允许消耗型(生成/推理)任务"""
        return self.check() in ("normal", "pre_warn")

    def status(self):
        return {"mode": self.mode, "thresholds": {
            "pre_warn": QUOTA_THRESHOLD_PRE, "idle": QUOTA_THRESHOLD_IDLE}}

# ---------- 风险三优先评分 ----------
def risk_three_priority(task, node=None, node_rep=None):
    """按风险三优先元法则对任务评分: 返回 (allow, risk_level, score, reasons)
    P1 风险最小: 不可逆/高危/越权 → 拦截
    P2 成本最小: 消耗型任务 → 降级或仅在高收益时放行
    P3 收益最大: 常规任务放行
    """
    cmd = (task.get("cmd") or "")[:120]
    reasons = []
    risk_level = "low"

    # P1 风险拦截 (硬约束)
    cmd_low = cmd.lower()
    high_risk_kw = ["rm -rf", "mkfs", "dd if=", ":(){", "shutdown", "reboot",
                    "drop database", "truncate table", "git push --force"]
    for kw in high_risk_kw:
        if kw in cmd_low:
            return False, "high", 0.0, [f"高危命令拦截: {kw}"]
    if not node:
        return False, "high", 0.0, ["节点缺失, 无法派发"]

    # 节点信誉风险: 低信誉(<40) 拦截
    rep = node_rep if node_rep is not None else 100
    if rep < 40:
        return False, "high", rep / 100.0, [f"低信誉节点({rep:.0f})拦截"]

    # P2 成本评估
    generative = any(k in cmd_low for k in ["train", "infer", "render", "generate",
                                            "generate_image", "convert"])
    cost_score = 0.6 if generative else 0.2

    # P3 收益评估
    benefit = 0.7 if cmd_low else 0.3

    # 综合: 风险低 + 信誉正常 → 放行
    allow = True
    risk_level = "low" if rep >= 80 else "medium"
    score = (rep / 100.0) * 0.5 + (1.0 - cost_score) * 0.3 + benefit * 0.2
    reasons = [f"信誉{rep:.0f}", f"成本{'高' if generative else '低'}",
               RISK_PRIORITY]
    return allow, risk_level, round(score, 3), reasons

# ---------- 四维真值校验 ----------
def four_dim_check(task):
    """四维本体校验: 空间/时间/属性/因果 完整性"""
    dims = {
        "空间(存在)": bool(task.get("cmd")),                       # 任务命令=空间存在
        "时间(时序)": bool(task.get("created_ts") or task.get("ts")),  # 时间戳=时序
        "属性(规则)": bool(task.get("capability")),                # 能力标签=属性
        "因果(闭环)": bool(task.get("task_id")),                   # 任务ID=因果锚
    }
    missing = [k for k, v in dims.items() if not v]
    return (not missing), missing

# ---------- AxiomGate 裁决器 ----------
class AxiomGate:
    """派发前裁决器: 四维校验 + 风险评分 + 配额稳态, 三重裁决"""
    def __init__(self):
        self.quota = QuotaSteady()
        self.gate_id = "AXIOM-GATE-001"

    def authorize(self, task, node=None, node_rep=None):
        """裁决待派发任务; 返回 (allow, verdict, detail)
        verdict 含 四维/风险/配额 三层结论
        """
        # L1 四维真值校验
        ok4, missing4 = four_dim_check(task)
        # L2 风险三优先评分
        okr, risk, score, reasons = risk_three_priority(task, node, node_rep)
        # L3 配额稳态 (只读空转禁派发)
        qmode = self.quota.check()
        okq = qmode in ("normal", "pre_warn")
        # 若任务消耗型且配额预警, 拦截(降级)
        cmd_low = (task.get("cmd") or "").lower()
        generative = any(k in cmd_low for k in ["train", "infer", "render"])
        if generative and qmode == "pre_warn":
            okq = False
            qmode = "pre_warn(降级拦截消耗型)"

        allow = ok4 and okr and okq
        verdict = {
            "allow": allow,
            "four_dim": {"pass": ok4, "missing": missing4},
            "risk": {"level": risk, "score": score, "reasons": reasons},
            "quota": {"mode": qmode, "allow": okq},
            "priority_law": RISK_PRIORITY,
            "gate": self.gate_id,
        }
        return allow, verdict

# 便捷: 全局裁决器
axiom_gate = AxiomGate()

def authorize(task, node=None, node_rep=None):
    """模块级便捷函数"""
    return axiom_gate.authorize(task, node, node_rep)
