#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用量统计聚合 v1.0 | 读 usage.log → usage_stats.json（dashboard真数据）| Ω₀⊂⊙∞⊂Ω"""
import json, os, time
from collections import defaultdict

LOG = "/root/zongyuan-yuanji/var/usage.log"
OUT = "/www/wwwroot/huodouai.com/data/usage_stats.json"
DAY = 86400

def main():
    now = int(time.time())
    rows = []
    if os.path.exists(LOG):
        for line in open(LOG, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if not line: continue
            try: rows.append(json.loads(line))
            except: continue
    total_calls = len(rows)
    total_tokens = sum(r.get("total_tokens", 0) for r in rows)
    prompt_tokens = sum(r.get("prompt_tokens", 0) for r in rows)
    completion_tokens = sum(r.get("completion_tokens", 0) for r in rows)
    last24 = [r for r in rows if now - r.get("ts", 0) <= DAY]
    by_model = defaultdict(lambda: {"calls": 0, "tokens": 0})
    for r in rows:
        m = r.get("model", "unknown")
        by_model[m]["calls"] += 1
        by_model[m]["tokens"] += r.get("total_tokens", 0)
    by_key = defaultdict(int)
    for r in rows:
        by_key[r.get("key", "unknown")] += 1
    stats = {
        "generated_ts": now,
        "total_calls": total_calls,
        "total_tokens": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "last24h_calls": len(last24),
        "by_model": dict(by_model),
        "by_key": {k[:16] + "..." if len(k) > 16 else k: v for k, v in by_key.items()},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)
    print(json.dumps({"calls": total_calls, "tokens": total_tokens, "models": len(by_model)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
