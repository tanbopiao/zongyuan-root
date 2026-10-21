#!/usr/bin/env python3
import json, subprocess, os, sys, re

BASE = "WBQNbr4tca2neIs23X8coL4jnch"
TABLES = [
    ("tblCAOoZWlXJaES2", "快照注册表"),
    ("tblupyiEi8wxJJzv", "昆仑洞天IP资产库"),
    ("tblzSekdjIBEtSKY", "飞书资源索引"),
    ("tblwjUrcuuHg3LP9", "ZONGYUAN-ROOT元规则库"),
    ("tblzUfFmQ3uZ9fUl", "ZONGYUAN-ROOT元法则库"),
    ("tbl6JcYtRJx21aBs", "子域隔离注册表"),
    ("tblj6UtrvvNYbLpi", "架构断点清单"),
    ("tblOx2talJkurh5m", "数据表"),
]

def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    try:
        return json.loads(p.stdout)
    except Exception:
        return {"ok": False, "_err": p.stderr[-300:], "_raw": p.stdout[-300:]}

def load_fields(tid):
    d = json.load(open(f"reg1_fields/{tid}.json"))
    fs = d.get("data", {}).get("fields", d.get("data", {}).get("items", []))
    names = [f.get("field_name") or f.get("name") for f in fs]
    return names

result = {"base_token": BASE, "tables": []}
for tid, tname in TABLES:
    names = load_fields(tid)
    rows = []
    offset = 0
    while True:
        d = run(["lark-cli","base","+record-list","--base-token",BASE,"--table-id",tid,
                 "--as","user","--format","json","--limit","200","--offset",str(offset)])
        data = d.get("data", {})
        batch = data.get("data", [])
        rows.extend(batch)
        if not data.get("has_more") or not batch:
            break
        offset += len(batch)
    # map rows to dicts
    recs = []
    for r in rows:
        recs.append({names[i]: (r[i] if i < len(r) else None) for i in range(len(names))})
    result["tables"].append({"table_id": tid, "name": tname, "fields": names, "record_count": len(recs), "records": recs})
    print(f"{tname} ({tid}): {len(recs)} records, fields={names}")

json.dump(result, open("reg1_all_records.json","w"), ensure_ascii=False, indent=1)
print("saved reg1_all_records.json")
