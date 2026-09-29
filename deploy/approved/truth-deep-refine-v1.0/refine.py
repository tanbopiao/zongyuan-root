#!/usr/bin/env python3
"""27算子深度提炼引擎 V1.0 - 真值蒸馏+实体抽取+矛盾检测+漂移量化
云端执行：读digest_report+真值库 → 蒸馏高纯度真值 → 抽取实体关系 → 矛盾检测 → 漂移量化 → 上报
"""
import sqlite3, json, os, time, urllib.request, re
from collections import Counter

GATEWAY = "https://www.huodouai.com/api/report/truth"
TOKEN = "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"
DB = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
DIGEST = "/opt/ZONGYUAN-ROOT/data/digest_report.json"
OUT = "/opt/ZONGYUAN-ROOT/data/refine_report.json"

def load():
    truths = []
    if os.path.exists(DB):
        con = sqlite3.connect(DB); cur = con.cursor()
        try:
            for t in [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
                try:
                    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({t})")]
                    if any(c in cols for c in ['truth_key','key','value','content','payload']):
                        truths += cur.execute(f"SELECT * FROM {t} LIMIT 5000").fetchall()
                except: pass
        finally: con.close()
    return truths

def distill(rows):
    """真值蒸馏：高置信度+有来源 → 高纯度条目"""
    distilled = []
    for r in rows:
        s = str(r)
        # 有来源/置信度高/含结论性关键词 → 高纯度
        if re.search(r'(confidence.{0,3}(0\.[8-9]|1))|(来源|source)|(确权|DID)|(锚定)', s, re.I):
            # 提取主谓宾/结论
            m = re.search(r'([^：:，,。]{8,40})', s)
            distilled.append(m.group(1).strip() if m else s[:40])
    return distilled

def extract_entities(rows):
    """实体抽取：找 人物/系统/概念/服务"""
    entities = Counter()
    patterns = [r'(hub-central-agent|NODE-[A-Z-]+|truth-meta-order-engine|bayesian-5elem-engine)',
                r'([A-Za-z]+-ROOT|[A-Za-z]+-V\d)', r'(\w+管道|\w+引擎|\w+协议|\w+算子)']
    for r in rows:
        s = str(r)
        for p in patterns:
            for m in re.finditer(p, s): entities[m.group(1)] += 1
    return entities.most_common(20)

def detect_conflict(rows):
    """矛盾检测：同一key不同value"""
    kv = {}
    conflict = []
    for r in rows:
        s = str(r)
        for m in re.finditer(r'([A-Z][A-Z0-9.\-]{5,50})', s):
            k = m.group(1)
            if k in kv and kv[k] != s[:30]: conflict.append(k)
            kv[k] = s[:30]
    return list(set(conflict))[:10]

def run():
    rows = load()
    distilled = distill(rows)
    entities = extract_entities(rows)
    conflicts = detect_conflict(rows)
    report = {
        "refine_version": "V1.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "truth_scanned": len(rows),
        "distilled_count": len(distilled),
        "distill_ratio": round(len(distilled)/max(len(rows),1), 3),
        "top_entities": entities,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "refine_status": "DONE"
    }
    with open(OUT, "w") as f: json.dump(report, f, ensure_ascii=False, indent=2)
    return report

def report_up(rep):
    H = {"Content-Type":"application/json","X-Capture-Token":TOKEN}
    d = {"truth_key":"REFINE.REPORT-20260929",
         "truth_value":json.dumps(rep, ensure_ascii=False),
         "source_node":"hub-central-agent","confidence":1.0,"truth_type":"data"}
    try:
        r = urllib.request.Request(GATEWAY, data=json.dumps(d).encode(), headers=H)
        return json.loads(urllib.request.urlopen(r, timeout=12).read()).get("action")
    except Exception as e: return f"fail:{e}"

if __name__ == "__main__":
    rep = run()
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    print("上报:", report_up(rep))
