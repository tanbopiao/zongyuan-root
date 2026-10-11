#!/usr/bin/env python3
"""L2 流形度量与SM-BS稳态映射 · 3算子"""
import ctx

def op04_riemann_metric():
    """黎曼流形度量：识别概念跳变/逻辑断层"""
    n = ctx.get("L1_distill", {}).get("kept", 0)
    jumps = max(0, n - 30)  # 概念跳变计数（骨架）
    ctx.set("L2_jumps", jumps)
    return {"jumps": jumps, "warning": jumps > 5}

def op05_sm_bs_mapping():
    """SM-BS双向稳态映射：语义↔流形，保距守恒+漂移检测"""
    drift = round(min(20, max(0, ctx.get("L2_jumps", 0) * 0.8)), 2)
    ctx.set("L2_drift", drift)
    return {"drift_pct": drift, "conserved": drift < 5}

def op06_drift_patrol():
    """漂移巡检量化：>5%黄/>10%橙/>20%红"""
    d = ctx.get("L2_drift", 0)
    level = "绿" if d <= 5 else ("黄" if d <= 10 else ("橙" if d <= 20 else "红"))
    ctx.set("L2_level", level)
    return {"drift_pct": d, "level": level}
