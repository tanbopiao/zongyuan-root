#!/usr/bin/env python3
"""真值轻量索引入库 | truths_mirror（append-only, INSERT OR IGNORE）| DID-BR-000002
用法: truth_import.py <inc.jsonl> <mirror.db>  → 输出 条数|last=id
字段: id, truth_key, category, node_id, created_at, version, truth_value_preview, truth_hash
"""
import sqlite3, json, sys
src, db = sys.argv[1], sys.argv[2]
conn = sqlite3.connect(db)
conn.execute("CREATE TABLE IF NOT EXISTS truths_mirror (id INTEGER PRIMARY KEY, truth_key TEXT, category TEXT, node_id TEXT, created_at REAL, version INTEGER, truth_value_preview TEXT, truth_hash TEXT)")
rows, last_id = [], 0
with open(src, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if "__meta__" in d:
            last_id = d["__meta__"]["last_id"]
            continue
        rows.append((d["id"], d["truth_key"], d.get("category",""), d.get("node_id",""),
                     d.get("created_at",0), d.get("version",1), d.get("truth_value_preview",""), d.get("truth_hash","")))
conn.executemany("INSERT OR IGNORE INTO truths_mirror VALUES (?,?,?,?,?,?,?,?)", rows)
conn.commit()
n = conn.execute("SELECT COUNT(*) FROM truths_mirror").fetchone()[0]
print(f"{n} | last={last_id}", flush=True)
