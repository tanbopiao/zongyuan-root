#!/usr/bin/env python3
# 自动从记忆网关提炼种子
import sqlite3, json, time
from pathlib import Path

SEED_FILE = "/root/zongyuan-yuanji/persist/seed_truth/text/seed_text.jsonl"

def auto_extract():
    con = sqlite3.connect("/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db")
    # 找L0相关真值
    rows = con.execute("SELECT key, value FROM truth WHERE key LIKE \"%L0%\" OR key LIKE \"%meta%\" ORDER BY seq DESC LIMIT 5").fetchall()
    
    existing = set()
    if Path(SEED_FILE).exists():
        for line in open(SEED_FILE):
            existing.add(json.loads(line)["seed_id"])
    
    new_seeds = []
    for key, value in rows:
        seed_id = key[:20]
        if seed_id in existing:
            continue
        try:
            v = json.loads(value) if isinstance(value, str) else value
            new_seeds.append({
                "seed_id": seed_id,
                "level": "L0",
                "system_prompt": "你是元内核微脑，按元法则输出",
                "user_prompt": key,
                "response": str(v)[:200],
                "weight_version": "v6",
                "gen_params": {"seed": 42, "temp": 0.0},
                "timestamp": time.strftime("%Y-%m-%d")
            })
        except:
            pass
    
    with open(SEED_FILE, "a") as f:
        for s in new_seeds:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    
    print(f"自动提炼了{len(new_seeds)}条种子")

if __name__ == "__main__":
    auto_extract()
