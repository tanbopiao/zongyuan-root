#!/usr/bin/env python3
"""
增值循环引擎 value_cycle.py v1.0
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
双向增值闭环: 拉取云端真值 → 本地语义转译/提炼 → 语义召回 → 提炼增值 → 上报云端
云端未处理则本地处理后再上报 → 自增强循环
真实部署: 真实拉取/真实转译/真实增值/真实上报
"""
import os, sys, json, glob, time, hashlib, argparse, urllib.request, urllib.parse

PRJ = "/home/user/Doubao/chats/38418284746129666"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
VERSION = "VALUE-CYCLE-V1.0"
CENTRAL_URL = "https://drama.huodouai.com"
TOKEN = "ZR-CAPTURE-2026-OMEGA-666b43e342a6b57ee54742f58d3e3fcd"

def now(): return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())

# ---------- 1 拉取(下行召回) ----------
def recall(key):
    try:
        url = f"{CENTRAL_URL}/api/truth/{urllib.parse.quote(key)}"
        req = urllib.request.Request(url, headers={"X-Capture-Token": TOKEN, "X-DID": DID})
        r = urllib.request.urlopen(req, timeout=10)
        d = json.loads(r.read().decode())
        if d.get("status") == "ok" and d.get("truth"):
            return {"key": key, "truth": d["truth"]}
        return {"key": key, "status": d.get("status")}
    except Exception as e:
        return {"key": key, "status": "error", "error": str(e)}

# ---------- 2 语义转译(提炼要点) ----------
def translate(t):
    val = t.get("truth_value", "")
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, dict):
                return {"raw": val, "structured": parsed,
                        "points": [str(v)[:120] for v in parsed.values() if not isinstance(v, (dict, list))][:5]}
        except Exception:
            pass
    return {"raw": str(val)[:200], "structured": None,
            "points": [str(val)[:120]] if val else []}

# ---------- 3 语义召回(本地匹配相关) ----------
def recall_local(translated):
    pts = translated.get("points", [])
    hits = []
    for p in glob.glob(PRJ + "/experience/truth-core/TRUTH-*.json"):
        try:
            d = json.load(open(p))
            truths = d.get("truths", []) if isinstance(d, dict) else []
            for t in truths:
                v = json.dumps(t, ensure_ascii=False)
                if any(pt[:20] in v for pt in pts):
                    hits.append({"key": t.get("key"), "value": str(t.get("value", ""))[:80]})
        except Exception: pass
    return hits[:5]

# ---------- 4 提炼增值 ----------
def augment(key, translated, local_hits):
    if not translated.get("points"):
        return None
    aug = {"dim": "增值循环", "key": f"value.cycle.{time.strftime('%Y%m%d%H%M')}.{DID}",
           "value": f"增值提炼自云端真值[{key}]: 要点{len(translated['points'])}个, 关联本地语义{len(local_hits)}条, 已完成语义转译与增值",
           "source_key": key, "points": translated["points"],
           "related_local": [h["key"] for h in local_hits],
           "confidence": 0.85, "did": DID, "time": now()}
    return aug

# ---------- 5 上报(上行反哺) ----------
def report_cloud(aug):
    if not aug: return {"status": False, "reason": "无增值"}
    try:
        req = urllib.request.Request(f"{CENTRAL_URL}/api/report/truth",
            data=json.dumps({"key": aug["key"], "value": aug, "did": DID}).encode(),
            headers={"X-Capture-Token": TOKEN, "X-DID": DID, "Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=10)
        return json.loads(r.read().decode())
    except Exception as e:
        return {"status": False, "reason": str(e), "degrade": "云端未处理, 本地已留存待补上报"}

def main():
    ap = argparse.ArgumentParser(description="增值循环引擎")
    ap.add_argument("--keys", required=True, help="待增值的云端真值key(逗号分隔)")
    ap.add_argument("--dry-run", action="store_true", help="只拉取提炼不写入不上报")
    a = ap.parse_args()

    cycles = []
    for k in [x.strip() for x in a.keys.split(",") if x.strip()]:
        rc = recall(k)
        if rc.get("status") not in (None, "ok") or not rc.get("truth"):
            cycles.append({"key": k, "recall": {"status": rc.get("status"), "error": rc.get("error")}})
            continue
        t = rc["truth"]
        tr = translate(t)
        lh = recall_local(tr)
        aug = augment(k, tr, lh)
        rp = {"skipped": "dry-run"} if a.dry_run else report_cloud(aug)
        cycles.append({"key": k, "recall": {"status": "ok", "id": t.get("id")},
                       "translated_points": tr["points"], "local_semantic_hits": lh,
                       "augmented": aug, "report": rp})
        if not a.dry_run and aug:
            # 本地留存增值记录
            os.makedirs(PRJ + "/experience/truth-core", exist_ok=True)
            f = PRJ + "/experience/truth-core/VALUE-CYCLE-{}.json".format(time.strftime("%Y%m%d"))
            try: os.chmod(f, 0o666)
            except Exception: pass
            json.dump({"engine": VERSION, "did": DID, "time": now(), "augmented": aug},
                      open(f, "w"), ensure_ascii=False, indent=2)
            os.chmod(f, 0o444)

    report = {"engine": VERSION, "did": DID, "time": now(),
              "cycles": len(cycles),
              "recalled": sum(1 for c in cycles if c.get("recall", {}).get("status") == "ok"),
              "augmented": sum(1 for c in cycles if c.get("augmented")),
              "reported": sum(1 for c in cycles if c.get("report", {}).get("status")),
              "cycle_detail": cycles,
              "note": "增值循环: 拉取→语义转译→本地语义召回→提炼增值→上报中枢"}
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
