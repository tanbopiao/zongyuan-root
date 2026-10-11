#!/usr/bin/env python3
"""L1 真值过滤与深度蒸馏 · 3算子
来源：云端母本 27-operator-topology | 本地契约骨架（真实算法待接云端引擎）"""
import ctx

def op01_p4_truth_reconcile():
    """P4真值对账：粗对账，区分事实/猜想/观点，过滤无来源碎片"""
    items = ctx.get("raw_truths", [])
    facts, guesses, opinions = [], [], []
    for it in items:
        src = it.get("source", "")
        kind = it.get("kind", "guess")
        (facts if kind == "fact" and src else guesses if kind == "guess" else opinions).append(it)
    ctx.set("L1_reconciled", {"facts": len(facts), "guesses": len(guesses), "opinions": len(opinions)})
    return len(facts)

def op02_p7_external_anchor():
    """P7外部锚定：交叉锚定外部源，抑制幻觉，追加置信度"""
    facts = ctx.get("L1_reconciled", {}).get("facts", 0)
    anchored = []
    for i in range(facts):
        anchored.append({"id": f"T-{i+1}", "confidence": 0.9, "anchored": True})
    ctx.set("L1_anchored", len(anchored))
    return len(anchored)

def op03_truth_distill():
    """真值提炼蒸馏：多轮交叉验证+冲突消解，输出纯度评分+压缩比"""
    n = ctx.get("L1_anchored", 0)
    purity = round(min(100, 60 + n * 0.5), 1) if n else 0
    ratio = round(max(0.1, 1 - n / max(1, n + 20)), 2)
    ctx.set("L1_distill", {"purity": purity, "ratio": ratio, "kept": n})
    return {"purity": purity, "ratio": ratio}
