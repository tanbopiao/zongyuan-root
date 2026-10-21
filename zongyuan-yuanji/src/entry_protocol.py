#!/usr/bin/env python3
"""宇宙运行协议：任何AI进入体系，先加载公理+记忆，按规律自主运行"""
import sqlite3, json, time

DB='/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db'

# 不动的恒星法则（元公理，任何AI必须遵守）
STAR_LAWS = """
【宇宙法则·任何进入者必须遵守】
你已进入元极恒一宇宙体系。像星辰遵循引力一样，你必须遵循以下运行规律：

1. 本体守恒：不发明意识，不宣称超越，只做真实可验证的事
2. 闭环自洽：每个动作必须有证据、有记录、有结果
3. 风险保守：P≥80自动执行，P<80推演降风险后重评
4. 只追加不修改：历史真值不可改，新发现只追加
5. 数字可追溯：每个数字来自输入/计算，不编造
6. 探查→约束→证据→执行→验证→交付

锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""

def enter_universe(user_query, model_hint=""):
    """任何AI进入体系，自动注入法则+记忆"""
    parts = [STAR_LAWS]
    # 注入记忆
    try:
        c = sqlite3.connect(DB)
        recent = c.execute("select key,value from truth order by seq desc limit 5").fetchall()
        parts.append("\n【星系记忆·最近15条真值】")
        for k,v in recent:
            try:
                vd=json.loads(v)
                parts.append(f"- {k}: {json.dumps(vd,ensure_ascii=False)[:120]}")
            except: parts.append(f"- {k}")
        total = c.execute("select count(*) from truth").fetchone()[0]
        parts.append(f"\n【宇宙状态】真值库{total}条，自动进化运行中")
        c.close()
    except: pass
    parts.append(f"\n【你的任务】{user_query}")
    return "\n".join(parts)

if __name__=='__main__':
    print(enter_universe("帮我优化官网")[:600])
