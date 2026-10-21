#!/usr/bin/env python3
import json

reg1 = json.load(open("reg1_all_records.json"))
reg2 = json.load(open("reg2_all_records.json"))
pre = json.load(open("recon_pre.json"))
up = json.load(open("upload_result.json"))

# group keys by table
keys_by_table = {}
for e in pre["extracted"]:
    keys_by_table.setdefault(e["table"], []).append(e["key"])

def build_register(reg, name):
    tables = []
    for t in reg["tables"]:
        tables.append({
            "table_id": t["table_id"],
            "name": t["name"],
            "fields": t["fields"],
            "record_count": t["record_count"],
            "keys_extracted": keys_by_table.get(t["name"], [])
        })
    return {"name": name, "base_token": reg["base_token"], "tables": tables}

result = {
    "registers": [
        build_register(reg1, "ZONGYUAN-ROOT 全域快照注册表"),
        build_register(reg2, "ZONGYUAN-ROOT进化抗漂移谱系注册表"),
    ],
    "cloud_matched": pre["matched_keys"],
    "confirmed_missing": [e["key"] for e in json.load(open("confirmed.json"))["confirmed_missing"]],
    "uploaded": up["uploaded"],
    "upload_failed": up["failed"],
    "meta": {
        "did": "DID-BR-000002",
        "trace_mark": "Ω₀⊂⊙∞⊂Ω",
        "source_node": "local-feishu-extract",
        "confidence": 0.95,
        "generated_at": "2026-09-19T21:00:00+08:00"
    }
}

json.dump(result, open("registry_result.json","w"), ensure_ascii=False, indent=1)

# summary
total_records = sum(t["record_count"] for r in result["registers"] for t in r["tables"])
total_keys = sum(len(t["keys_extracted"]) for r in result["registers"] for t in r["tables"])
print("registers:", len(result["registers"]))
for r in result["registers"]:
    print(f"  {r['name']}: {len(r['tables'])} tables, {sum(t['record_count'] for t in r['tables'])} records, {sum(len(t['keys_extracted']) for t in r['tables'])} keys")
print("total records:", total_records, "total keys:", total_keys)
print("cloud_matched:", len(result["cloud_matched"]))
print("confirmed_missing:", len(result["confirmed_missing"]))
print("uploaded:", len(result["uploaded"]), "failed:", len(result["upload_failed"]))
