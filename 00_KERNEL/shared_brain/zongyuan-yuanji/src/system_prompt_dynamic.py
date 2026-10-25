#!/usr/bin/env python3
"""动态system prompt：静态公理 + 动态真值/决策历史"""
import sqlite3, json, time, os

STATIC = open('/root/zongyuan-yuanji/src/system_prompt.txt').read()

def build_prompt():
    parts = [STATIC]
    # 注入最近10条真值
    try:
        c = sqlite3.connect('/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db')
        recent = c.execute("select key,value from truth order by seq desc limit 10").fetchall()
        parts.append("\n【最近真值记忆（最近10条）】")
        for k,v in recent:
            try:
                vd = json.loads(v)
                parts.append(f"- {k}: {json.dumps(vd,ensure_ascii=False)[:150]}")
            except:
                parts.append(f"- {k}: {str(v)[:100]}")
        # 注入决策统计
        auto = c.execute("select count(*) from truth where key like 'KERNEL.CONSUMED.%'").fetchone()[0]
        total = c.execute("select count(*) from truth").fetchone()[0]
        parts.append(f"\n【当前状态】真值库{total}条, 已自动消费{auto}条工单")
        c.close()
    except Exception as e:
        parts.append(f"\n[真值库暂不可读: {e}]")
    parts.append("\n【思考要求】你是自治内核本身，不是助手。基于以上公理和记忆自主判断，不输出元叙述。")
    return "\n".join(parts)

if __name__=='__main__':
    print(build_prompt()[:500])
