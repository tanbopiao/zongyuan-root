#!/usr/bin/env python3
"""最优稳态评分器 执行态
100分制，6维度，80分达标线
"""
DIM_WEIGHT = {'自动化':25,'成本':20,'稳定':20,'扩展':15,'全域':10,'验证':10}
THRESHOLD = 80

def score(automation, cost, stability, extensibility, global_cover, verifiability):
    s = automation+cost+stability+extensibility+global_cover+verifiability
    if s >= THRESHOLD:
        verdict = "达标-落地"
    elif s >= 60:
        verdict = "待优化-补短板"
    else:
        verdict = "不达标-推翻重推"
    return s, verdict

if __name__ == "__main__":
    cases = [(22,20,19,12,9,9),(10,15,10,10,5,5)]
    for c in cases:
        s, v = score(*c)
        print(f"  {c} → {s}分 → {v}")
