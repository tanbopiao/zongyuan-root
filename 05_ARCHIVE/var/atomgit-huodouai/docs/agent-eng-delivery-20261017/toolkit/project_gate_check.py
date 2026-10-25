#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Agent 工程化落地交付 · 项目准入校验器
基于 META-LAW-SYS-ENG-DELIVERY-20261017 元法则体系（CONST-ENG-001 / AXIOM-ENG-001~004 / META-LAW-ENG-001~006 / AGENT-PREREQ-001~006）
用法：
    python3 project_gate_check.py --spec project_spec.json
    python3 project_gate_check.py --spec project_spec.json --json
校验通过输出 0，未通过输出 1。
锚定：Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002
"""
import argparse
import json
import sys
from datetime import datetime

ANCHOR = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"
VERSION = "v1.0-20261017"

# 元法则体系引用（用于报告溯源）
LAWS = {
    "CONST-ENG-001": "工程约束优先于智能上限，拒绝Demo级交付",
    "AXIOM-ENG-001": "工程约束/风险/量化/运维决定成败",
    "AXIOM-ENG-002": "稳定可控优先，模型是可插拔组件",
    "AXIOM-ENG-003": "高危操作TEE硬边界拦截",
    "AXIOM-ENG-004": "极简优先，复杂度需收益裁决",
    "META-LAW-ENG-001": "边界前置准入",
    "META-LAW-ENG-002": "量化验收闭环",
    "META-LAW-ENG-003": "风险分级硬隔离",
    "META-LAW-ENG-004": "复杂度收益裁决",
    "META-LAW-ENG-005": "资产哈希存证",
    "META-LAW-ENG-006": "模型稳态调度",
    "AGENT-PREREQ-001": "任务准入边界",
    "AGENT-PREREQ-002": "验收量化",
    "AGENT-PREREQ-003": "风险分级管控",
    "AGENT-PREREQ-004": "复杂度收益评估",
    "AGENT-PREREQ-005": "资产哈希存证",
    "AGENT-PREREQ-006": "模型调度稳态",
}

REQUIRED_TOP_KEYS = ["name", "scenario_boundary", "acceptance_metrics", "risk_operations", "architecture", "assets", "model_strategy"]


def _check_spec(spec):
    """返回 (passed, issues, items)"""
    issues = []
    items = []

    # 1. 结构完整性
    missing = [k for k in REQUIRED_TOP_KEYS if k not in spec]
    if missing:
        issues.append(f"[CONST-ENG-001] 工单缺少必需字段: {', '.join(missing)}")
    else:
        items.append("[CONST-ENG-001] 工单结构完整")

    # 2. 边界前置准入（META-LAW-ENG-001 / AGENT-PREREQ-001）
    boundary = spec.get("scenario_boundary", {})
    whitelist = boundary.get("whitelist", [])
    blacklist = boundary.get("blacklist", [])
    if isinstance(whitelist, list) and isinstance(blacklist, list) and (whitelist or blacklist):
        items.append(f"[META-LAW-ENG-001] 边界清单已定义: 白名单{len(whitelist)}项/黑名单{len(blacklist)}项")
    else:
        issues.append("[META-LAW-ENG-001] 场景边界缺少白名单/黑名单，无法执行准入校验")

    # 3. 量化验收闭环（META-LAW-ENG-002 / AGENT-PREREQ-002）
    metrics = spec.get("acceptance_metrics", {})
    quant_keys = ["accuracy", "pass_rate", "hallucination_rate", "tolerance"]
    has_quant = all(k in metrics for k in quant_keys)
    if has_quant and all(isinstance(metrics.get(k), (int, float)) for k in quant_keys):
        items.append("[META-LAW-ENG-002] 量化验收指标已固化(准确率/通过率/幻觉率/容忍阈值)")
    else:
        issues.append("[META-LAW-ENG-002] 无量化验收指标或数值缺失，违反『无量化指标不予立项』")

    # 4. 风险分级硬隔离（META-LAW-ENG-003 / AGENT-PREREQ-003）
    risks = spec.get("risk_operations", {})
    high_risk = risks.get("high_risk", [])
    tee = risks.get("tee_boundary", False)
    if isinstance(high_risk, list) and high_risk and tee:
        items.append(f"[META-LAW-ENG-003] 高风险操作{len(high_risk)}项已列，TEE硬边界已启用")
    else:
        issues.append("[META-LAW-ENG-003] 高危操作清单缺失或未启用TEE硬边界拦截")

    # 5. 复杂度收益裁决（META-LAW-ENG-004 / AGENT-PREREQ-004）
    arch = spec.get("architecture", {})
    agent_mode = arch.get("mode", "single")
    roi = arch.get("multi_agent_roi", {})
    if agent_mode == "single":
        items.append("[META-LAW-ENG-004] 单Agent架构（默认极简，符合公理）")
    elif agent_mode == "multi" and isinstance(roi, dict) and roi.get("benefit", 0) > roi.get("cost", 0):
        items.append("[META-LAW-ENG-004] 多Agent已通过ROI收益裁决")
    elif agent_mode == "multi":
        issues.append("[META-LAW-ENG-004] 多Agent收益<=成本，违反极简优先公理")
    else:
        issues.append("[META-LAW-ENG-004] 架构模式未定义")

    # 6. 资产哈希存证（META-LAW-ENG-005 / AGENT-PREREQ-005）
    assets = spec.get("assets", {})
    if assets.get("hash_persist", False) and assets.get("merkle_dag", False):
        items.append("[META-LAW-ENG-005] 资产哈希存证+Merkle-DAG已启用")
    else:
        issues.append("[META-LAW-ENG-005] 未启用资产哈希锁档/版本快照")

    # 7. 模型稳态调度（META-LAW-ENG-006 / AGENT-PREREQ-006）
    model = spec.get("model_strategy", {})
    if model.get("stable_first", False) or model.get("scheduler", False):
        items.append("[META-LAW-ENG-006] 模型稳态调度策略已配置")
    else:
        issues.append("[META-LAW-ENG-006] 未配置模型稳态调度（稳定可控优先）")

    return (len(issues) == 0, issues, items)


def main():
    ap = argparse.ArgumentParser(description="AI Agent 工程化交付项目准入校验器")
    ap.add_argument("--spec", required=True, help="项目工单JSON路径")
    ap.add_argument("--json", action="store_true", help="输出JSON")
    args = ap.parse_args()

    try:
        with open(args.spec, "r", encoding="utf-8") as f:
            spec = json.load(f)
    except Exception as e:
        if args.json:
            print(json.dumps({"passed": False, "error": f"工单读取失败: {e}"}, ensure_ascii=False))
        else:
            print(f"[ERROR] 工单读取失败: {e}")
        sys.exit(1)

    passed, issues, items = _check_spec(spec)
    report = {
        "tool": "project_gate_check",
        "version": VERSION,
        "project": spec.get("name", "未命名"),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "passed": passed,
        "laws_applied": len(items) + len(issues),
        "passed_checks": items,
        "failed_checks": issues,
        "anchor": ANCHOR,
        "did": DID,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        verdict = "✅ 准入通过，允许立项" if passed else "❌ 准入未通过，禁止立项"
        print(f"\n{'='*52}")
        print(f"项目准入校验报告 ｜ {spec.get('name','未命名')} ｜ {VERSION}")
        print(f"结果: {verdict}")
        print(f"{'='*52}")
        for i in items:
            print(f"  ✔ {i}")
        for i in issues:
            print(f"  ✘ {i}")
        print(f"{'='*52}")
        print(f"锚定 {ANCHOR} ｜ {DID}")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
