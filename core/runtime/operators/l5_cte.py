#!/usr/bin/env python3
"""L5 CTE三位一体适配器流转 · 3算子（C→T→E→C闭环）"""
import ctx

def op13_causal_to_truth():
    """因果链→真值条目：奇点概率→置信度"""
    prob = ctx.get("L4_singularity", {}).get("prob", 0)
    conf = round(max(0.1, 1 - prob / 100), 2)
    ctx.set("L5_ct_score", conf)
    return {"confidence": conf}

def op14_truth_to_evolution():
    """真值→进化：纯度→适应度Φ，漂移→进化压力"""
    purity = ctx.get("L1_distill", {}).get("purity", 0)
    fitness = round(min(1, purity / 100), 2)
    pressure = ctx.get("L2_drift", 0)
    ctx.set("L5_fitness", fitness)
    return {"fitness_phi": fitness, "evolution_pressure": pressure}

def op15_evolution_to_causal():
    """进化→因果：策略变更→干预变量，预激活待进化域"""
    fitness = ctx.get("L5_fitness", 0)
    preactive = "进化域已预激活" if fitness < 0.8 else "稳态域保持"
    ctx.set("L5_preactive", preactive)
    return {"preactive": preactive}
