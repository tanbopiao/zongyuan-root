#!/usr/bin/env python3
# 从真值库提炼种子
import sqlite3, json
from pathlib import Path

con = sqlite3.connect("/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db")
rows = con.execute("SELECT key, value FROM truth WHERE key LIKE \"%EVOLUTION%\" OR key LIKE \"%DELIVERY%\" ORDER BY seq DESC LIMIT 10").fetchall()

seeds = []
for key, value in rows:
    try:
        v = json.loads(value)
        seeds.append({
            "seed_id": key[:20],
            "level": "L2",
            "system_prompt": "你是元内核微脑，按元法则输出",
            "user_prompt": key,
            "response": str(v)[:200]
        })
    except:
        pass

with open("/root/zongyuan-yuanji/persist/seed_truth/text/seed_text.jsonl", "a") as f:
    for s in seeds:
        f.write(json.dumps(s, ensure_ascii=False) + "\n")

print(f"提炼了{len(seeds)}条种子")
