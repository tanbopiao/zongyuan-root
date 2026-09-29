#!/usr/bin/env python3
"""
真值内生引擎 truth_generator.py v1.0
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
内核级进化·阶段2: 内核从自身运行经验内生真值(非仅外部注入)
流程: 读取版本链+账本+自省报告 → 聚类重复模式 → 提炼稳定真值 → 增量入真值库 → 反哺中枢
真实部署: 真实读取运行轨迹, 真实提炼写入, 真实上报中枢
"""
import os, sys, json, glob, time, hashlib, argparse, csv, urllib.request
from collections import Counter

PRJ = "/home/user/Doubao/chats/38418284746129666"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
VERSION = "TRUTH-GENERATOR-V1.0"

def now(): return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())

# ---------- 1 读取运行轨迹 ----------
def load_evolution_chain():
    p = PRJ + "/experience/evolution-versions/EVOLUTION-VERSIONS.json"
    if not os.path.exists(p): return []
    try: return json.load(open(p))
    except Exception: return []

def load_ledger():
    p = PRJ + "/HASH-LEDGER.csv"
    rows = []
    if not os.path.exists(p): return rows
    try:
        with open(p) as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2: rows.append(parts[1].strip())  # 事件ID在第2列
    except Exception: pass
    return [r for r in rows if r]

def load_meta_reports():
    out = []
    for p in glob.glob(PRJ + "/experience/meta-cognition/*.json"):
        try: out.append(json.load(open(p)))
        except Exception: pass
    return out

# ---------- 2 聚类提炼 ----------
def extract_truths(chain, ledger, reports):
    truths = []
    # A. 决策真值: 版本链gate分布
    gates = Counter(r.get("decision", "N/A") for r in chain if isinstance(r, dict))
    for gate, cnt in gates.most_common(5):
        if cnt >= 2:
            truths.append({"dim": "决策", "key": f"truth.decision.{gate.lower()}",
                           "value": f"进化决策gate='{gate}'出现{cnt}次, 为稳定决策模式",
                           "confidence": min(1.0, cnt / 5.0), "source": "EVOLUTION-VERSIONS"})
    # B. 运行真值: 账本事件高频
    ev = Counter(ledger)
    for ev_id, cnt in ev.most_common(6):
        if cnt >= 2:
            truths.append({"dim": "运行", "key": f"truth.ledger.{ev_id[:20]}",
                           "value": f"运行事件'{ev_id}'发生{cnt}次, 高频运行轨迹",
                           "confidence": min(1.0, cnt / 5.0), "source": "HASH-LEDGER"})
    # C. 规则真值: 自省报告维度覆盖
    for rep in reports:
        gap = rep.get("gap", {})
        if gap.get("covered"):
            truths.append({"dim": "规则", "key": "truth.rule.coverage",
                           "value": f"规则库自省覆盖{len(gap['covered'])}维度: {gap['covered']}",
                           "confidence": 0.9, "source": "META-COGNITION"})
    # 去重: 按key保留
    seen, unique = set(), []
    for t in truths:
        if t["key"] not in seen:
            seen.add(t["key"]); unique.append(t)
    return unique

# ---------- 3 增量入真值库 ----------
def persist(truths):
    if not truths: return {"added": 0, "note": "无新真值"}
    os.makedirs(PRJ + "/experience/truth-core", exist_ok=True)
    # 累积历史真值文件
    existing = {}
    for p in glob.glob(PRJ + "/experience/truth-core/TRUTH-GENERATED-*.json"):
        try:
            d = json.load(open(p))
            if isinstance(d.get("truths"), list):
                for t in d["truths"]: existing[t["key"]] = t
        except Exception: pass
    added = 0
    for t in truths:
        if t["key"] not in existing:
            existing[t["key"]] = t; added += 1
    out = {"version": VERSION, "did": DID, "time": now(),
           "truths": list(existing.values()), "total_truths": len(existing)}
    ofile = PRJ + "/experience/truth-core/TRUTH-GENERATED-{}.json".format(time.strftime("%Y%m%d"))
    try: os.chmod(ofile, 0o666)
    except Exception: pass
    json.dump(out, open(ofile, "w"), ensure_ascii=False, indent=2)
    os.chmod(ofile, 0o444)
    return {"added": added, "total_truths": len(existing), "file": ofile}

# ---------- 4 反哺中枢 ----------
def feedback(truths):
    if not truths: return {"status": False, "reason": "无真值可反哺"}
    CENTRAL_URL = "https://drama.huodouai.com/api/report/truth"
    TOKEN = "ZR-CAPTURE-2026-OMEGA-666b43e342a6b57ee54742f58d3e3fcd"
    key = f"truth.generated.{time.strftime('%Y%m%d%H%M')}.{DID}"
    value = {"engine": VERSION, "truth_count": len(truths), "truths": truths[:8], "did": DID, "time": now()}
    try:
        req = urllib.request.Request(CENTRAL_URL, data=json.dumps({"key": key, "value": value, "did": DID}).encode(),
            headers={"X-Capture-Token": TOKEN, "X-DID": DID, "Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=10)
        resp = json.loads(r.read().decode())
        return {"status": resp.get("success"), "action": resp.get("action"),
                "truth_count": resp.get("truth_count"), "key": key}
    except Exception as e:
        return {"status": False, "reason": str(e), "degrade": "中枢离线, 记录待补"}

def main():
    ap = argparse.ArgumentParser(description="真值内生引擎")
    ap.add_argument("--dry-run", action="store_true", help="只提炼不写入不反哺")
    a = ap.parse_args()
    chain = load_evolution_chain()
    ledger = load_ledger()
    reports = load_meta_reports()
    truths = extract_truths(chain, ledger, reports)
    pers = {"skipped": "dry-run"} if a.dry_run else persist(truths)
    fb = {"skipped": "dry-run"} if a.dry_run else feedback(truths)
    report = {"engine": VERSION, "did": DID, "time": now(),
              "inputs": {"evolution_chain": len(chain), "ledger_events": len(ledger), "meta_reports": len(reports)},
              "extracted_truths": len(truths), "truths_sample": truths[:6],
              "persist": pers, "feedback": fb}
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
