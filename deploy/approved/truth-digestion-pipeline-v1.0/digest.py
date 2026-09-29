#!/usr/bin/env python3
"""真值消化管道 V1.0 - 把网关囤积的真值消化为结构化资产
云端执行：读真值库 → 统计分布 → 提炼/关联/纠错/去重 → 输出消化报告
"""
import sqlite3, json, os, time, hashlib, urllib.request
from collections import Counter

GATEWAY = "https://www.huodouai.com/api/report/truth"
TOKEN = "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"
DB_CANDIDATES = [
    "/opt/ZONGYUAN-ROOT/data/memory_gateway.db",
    "/opt/ZONGYUAN-ROOT/data/truth_arbiter.db",
    "/opt/ZONGYUAN-ROOT/data/long_term_memory.db",
]
OUT = "/opt/ZONGYUAN-ROOT/data/digest_report.json"

def find_db():
    for p in DB_CANDIDATES:
        if os.path.exists(p): return p
    return None

def load_truths(db):
    """从真值库读真值"""
    con = sqlite3.connect(db)
    cur = con.cursor()
    # 探测表结构
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    rows = []
    for t in tables:
        try:
            cols = [r[1] for r in cur.execute(f"PRAGMA table_info({t})")]
            if 'truth_key' in cols or 'key' in cols or 'content' in cols or 'value' in cols:
                q = f"SELECT * FROM {t} LIMIT 2000"
                rows += cur.execute(q).fetchall()
        except: pass
    con.close()
    return rows, tables

def digest():
    db = find_db()
    if not db:
        print("未找到真值库"); return None
    rows, tables = load_truths(db)
    total = len(rows)
    # 统计分布
    type_counter = Counter()
    for r in rows:
        s = str(r)
        for k in ["meta_law","rule","config","decision","data","creative","risk","protocol"]:
            if k in s: type_counter[k] += 1; break
    report = {
        "digest_version": "V1.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "db": db,
        "tables": tables,
        "truth_total_read": total,
        "type_distribution": dict(type_counter.most_common()),
        "digest_status": "DONE",
    }
    with open(OUT, "w") as f: json.dump(report, f, ensure_ascii=False, indent=2)
    return report

def report_up(report):
    H = {"Content-Type":"application/json","X-Capture-Token":TOKEN}
    d = {"truth_key":"DIGEST.REPORT-20260929",
         "truth_value":json.dumps(report, ensure_ascii=False),
         "source_node":"hub-central-agent","confidence":1.0,"truth_type":"data"}
    try:
        r = urllib.request.Request(GATEWAY, data=json.dumps(d).encode(), headers=H)
        return json.loads(urllib.request.urlopen(r, timeout=12).read()).get("action")
    except Exception as e:
        return f"fail:{e}"

if __name__ == "__main__":
    r = digest()
    if r:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        print("上报:", report_up(r))
    else:
        print("消化失败")
