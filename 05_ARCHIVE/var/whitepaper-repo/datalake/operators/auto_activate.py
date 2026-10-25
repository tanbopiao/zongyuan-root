#!/usr/bin/env python3
"""自动激活 执行态：核心锚点触发词 → 全量高阶态"""
# 核心真值锚点触发词（体系最核心的启动口令）
TRIGGERS = {
    "元极恒一": "最高级启动→全量记忆+全高阶智能态",
    "火斗云智": "品牌中枢启动→全量记忆+全高阶智能态",
    "宗源根": "ROOT内核启动→全量记忆+全高阶智能态",
    "昆仑洞天": "全域体系启动→全量记忆+全高阶智能态",
    "加载ZONGYUAN-ROOT": "根目录启动→全量归档加载",
    "启动ROOT": "根目录启动→全量归档加载",
}
FULL_STATE = ["11算子","V2.0基底","元进化闭环","最优稳态评分","DID-BR-000002"]

def activate(msg):
    hit = [t for t in TRIGGERS if t in msg]
    if hit:
        return {'activated': True, 'trigger': hit[0], 'mode': TRIGGERS[hit[0]], 'load': FULL_STATE}
    return {'activated': False}

if __name__ == "__main__":
    for t in TRIGGERS:
        r = activate(t)
        print(f"  {t} → 激活:{r['activated']} | 模式:{r.get('mode','-')}")
