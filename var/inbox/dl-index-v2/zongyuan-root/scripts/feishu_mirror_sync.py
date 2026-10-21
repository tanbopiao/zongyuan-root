#!/usr/bin/env python3
"""飞书台账全量镜像同步 | DID-BR-000002 | append-only 快照式 | 逐表分页"""
import subprocess, json, os, time, sys

BASE = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
OUT = "/home/user/ZONGYUAN-ROOT/var/feishu-mirror"
TS = time.strftime("%Y%m%d-%H%M%S")
os.makedirs(OUT, exist_ok=True)
ts_dir = os.path.join(OUT, TS)
os.makedirs(ts_dir, exist_ok=True)

def cli(*args):
    r = subprocess.run(["lark-cli", "base"] + list(args) + ["--base-token", BASE, "--as", "user"],
                       capture_output=True, text=True, timeout=60)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"error": r.stdout[:300]}

tables = cli("+table-list")
tlist = tables.get("data", {}).get("tables", [])
if not tlist:
    print("获取表列表失败:", tables.get("error", "unknown"))
    sys.exit(1)

table_meta, total = {}, 0
for t in tlist:
    tid, tname = t["id"], t["name"]
    recs, offset = [], 0
    while True:
        d = cli("+record-list", "--table-id", tid, "--format", "json", "--limit", "200", "--offset", str(offset))
        if "error" in d:
            recs.append({"sync_error": d["error"]})
            break
        data = d.get("data", {})
        fields = data.get("fields", [])
        rows = data.get("data", [])
        for row in rows:
            if isinstance(row, dict):
                recs.append(row)
            else:
                recs.append({fields[j]: (row[j] if j < len(row) else None) for j in range(len(fields))})
        offset += len(rows)
        if not data.get("has_more") or len(rows) == 0:
            break
    safe = tname.replace("/", "_").replace(" ", "_")
    with open(os.path.join(ts_dir, f"{safe}.json"), "w", encoding="utf-8") as f:
        json.dump({"table_id": tid, "table_name": tname, "record_count": len(recs), "records": recs}, f, ensure_ascii=False)
    table_meta[tname] = len(recs)
    total += len(recs)
    print(f"  {tname}: {len(recs)} 条")

manifest = {"sync_ts": TS, "base_token": BASE, "table_count": len(table_meta), "total_records": total, "tables": table_meta}
with open(os.path.join(ts_dir, "MANIFEST.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)
print(f"✅ 完成: {len(table_meta)} 表 / {total} 记录 → {ts_dir}")
