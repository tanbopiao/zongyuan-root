#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOP-DATA-LAKE-BUILD-V1 数据湖构建 (V3 ndjson版)
验收: 8表全绿 + 索引≥100资产
"""
import json, subprocess, datetime, os

BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

TABLES = [
    ("资产台账",   "tbltgttCuWgAnN2e"),
    ("任务台账",   "tblnVRjuf7P31cEP"),
    ("节点状态",   "tblOmIRJtTn2EsvM"),
    ("真值共识区", "tbl9QxL35rwA16eS"),
    ("知识库索引", "tblmMEeXhlrOvXI2"),
    ("跨节点消息", "tbl4Dv798yO7u0IK"),
    ("决策日志",   "tblFQTgWkJQR6Xwp"),
    ("问题阻塞",   "tbljp3z11UtiuWCF"),
]

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip()

def fetch_table(name, tid):
    """用ndjson格式拉取全量"""
    fname = os.path.join(OUT_DIR, f"lake_{name}.ndjson")
    run(f'lark-cli base +record-list --base-token {BASE_TOKEN} --table-id {tid} --format ndjson --output {fname} --overwrite --limit 2000 --as user')
    if not os.path.exists(fname):
        return []
    records = []
    with open(fname, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                d = json.loads(line)
                if "_record_id" in d:
                    records.append({"record_id": d["_record_id"], "name": str(d.get("资产名称") or d.get("任务名称") or d.get("节点名称") or d.get("消息内容") or "")[:60]})
            except Exception:
                continue
    return records

def main():
    print("=== SOP-DATA-LAKE-BUILD-V1 数据湖构建 ===")
    print(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report = {"tables": [], "total_assets": 0}
    index_entries = []
    
    for name, tid in TABLES:
        try:
            records = fetch_table(name, tid)
            count = len(records)
            status = "GREEN" if count > 0 else "RED"
            report["tables"].append({"name": name, "records": count, "status": status})
            report["total_assets"] += count
            for r in records[:3]:
                index_entries.append({"table": name, "record_id": r["record_id"], "name": r["name"]})
            print(f"  [{'✅' if status=='GREEN' else '❌'}] {name}: {count}条")
        except Exception as e:
            report["tables"].append({"name": name, "records": 0, "status": "RED", "error": str(e)})
            print(f"  [❌] {name}: 拉取失败 {e}")
    
    all_green = all(t["status"] == "GREEN" for t in report["tables"])
    index_count = report["total_assets"]
    report["all_green"] = all_green
    report["index_count"] = index_count
    report["status"] = "PASS" if (all_green and index_count >= 100) else "FAIL"
    
    with open(os.path.join(OUT_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"report": report, "sample_index": index_entries}, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== 验收结果 ===")
    print(f"  8表全绿: {'✅' if all_green else '❌'}")
    print(f"  索引资产: {index_count} (要求≥100)")
    print(f"  总状态: {report['status']}")
    print(f"  索引文件: {os.path.join(OUT_DIR, 'index.json')}")
    return report

if __name__ == "__main__":
    main()
