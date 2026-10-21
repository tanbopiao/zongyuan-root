#!/usr/bin/env python3
# 全自动从真值库提炼种子
import sqlite3, json, time, hashlib
from pathlib import Path

SEED_FILE = "/root/zongyuan-yuanji/persist/seed_truth/text/seed_text.jsonl"

def load_existing():
    ids = set()
    if Path(SEED_FILE).exists():
        for line in open(SEED_FILE):
            try:
                ids.add(json.loads(line)["seed_id"])
            except: pass
    return ids

def extract():
    con = sqlite3.connect("/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db")
    rows = con.execute("SELECT key, value FROM truth WHERE key LIKE \"%kernel%\" ORDER BY seq DESC LIMIT 20").fetchall()
    
    existing = load_existing()
    new = 0
    
    for key, value in rows:
        seed_id = key[:30]
        if seed_id in existing:
            continue
        try:
            v = json.loads(value) if isinstance(value, str) else value
            seed = {
                "seed_id": seed_id,
                "level": "L0",
                "system_prompt": "你是元内核微脑，按元法则输出",
                "user_prompt": key,
                "response": str(v)[:200],
                "weight_version": "v6",
                "gen_params": {"seed": 42, "temp": 0.0},
                "timestamp": time.strftime("%Y-%m-%d")
            }
            with open(SEED_FILE, "a") as f:
                f.write(json.dumps(seed, ensure_ascii=False) + "\n")
            new += 1
        except: pass
    
    print(f"自动提炼了{new}条新种子")

if __name__ == "__main__":
    extract()
