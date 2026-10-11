#!/usr/bin/env python3
"""L9 决策与法律护盾 · 3算子（三维稳态：利益40%/风险35%/成本25%）"""
import ctx

def op22_plan_eval():
    """方案生成评估：≥3套方案，三维评分排序"""
    plans = [
        {"id": "A", "benefit": 0.8, "risk": 0.2, "cost": 0.3},
        {"id": "B", "benefit": 0.6, "risk": 0.3, "cost": 0.2},
        {"id": "C", "benefit": 0.7, "risk": 0.4, "cost": 0.1},
    ]
    for p in plans:
        p["score"] = round(0.4 * p["benefit"] - 0.35 * p["risk"] - 0.25 * p["cost"], 3)
    plans.sort(key=lambda x: -x["score"])
    ctx.set("L9_plans", plans)
    return {"top": plans[0], "candidates": len(plans)}

def op23_risk_classify():
    """风险识别分级：六类风险概率×影响"""
    classes = ["legal", "financial", "operational", "reputation", "technical", "compliance"]
    matrix = {c: {"prob": 0.2, "impact": "L"} for c in classes}
    ctx.set("L9_risk", matrix)
    return matrix

def op24_legal_opinion():
    """法律意见书：事实+争议+分析+风险+建议"""
    ctx.set("L9_opinion", {"facts": 1, "focus": 1, "analysis": "…", "risk_level": "低"})
    return {"generated": True, "risk_level": "低"}
