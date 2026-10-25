#!/usr/bin/env python3
"""指令过滤入库 | 去重后 append-only 追加 inbox | DID-BR-000002
用法: instruction_filter.py <raw.jsonl> <inbox.jsonl> <seen-ids> <ts>
"""
import json, sys, os
raw, inbox, seen_file, ts = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
seen = set()
if os.path.exists(seen_file):
    seen = set(x.strip() for x in open(seen_file) if x.strip())
new_n = 0
with open(raw, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line: continue
        d = json.loads(line)
        if "__meta__" in d: continue
        i = str(d["id"])
        if i in seen: continue
        rec = {"pulled_at": int(ts), "id": d["id"], "truth_key": d["truth_key"],
               "category": d.get("category",""), "node_id": d.get("node_id",""),
               "created_at": d.get("created_at",0), "truth_value_preview": (d.get("truth_value") or "")[:200],
               "truth_hash": d.get("truth_hash",""), "instruction": (d.get("truth_value") or "")[:200]}
        with open(inbox, "a", encoding="utf-8") as w:
            w.write(json.dumps(rec, ensure_ascii=False) + "\n")
        seen.add(i)
        new_n += 1
with open(seen_file, "a", encoding="utf-8") as w:
    for i in sorted(seen):
        w.write(i + "\n")
total = sum(1 for _ in open(inbox, encoding="utf-8")) if os.path.exists(inbox) else 0
print(f"新增{new_n}条 | inbox累计{total}条", flush=True)
