#!/usr/bin/env python3
"""
中枢真值召回引擎 truth_recall.py v1.0
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
双向同步·下行: 从中枢召回真值 → 本地比对吸收
流程: 提取本地已上报key → 调用/api/truth/{key}真实拉回 → 与本地比对 → 吸收差异 → 写本地真值库
真实部署: 真实调用中枢下行接口, 真实拉回, 真实比对写入
"""
import os, sys, json, glob, time, hashlib, argparse, urllib.request

PRJ = "/home/user/Doubao/chats/38418284746129666"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
VERSION = "TRUTH-RECALL-V1.0"
CENTRAL_URL = "https://drama.huodouai.com"
TOKEN = "ZR-CAPTURE-2026-OMEGA-666b43e342a6b57ee54742f58d3e3fcd"

def now(): return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())

# ---------- 1 提取本地已上报key ----------
def local_keys():
    keys = set()
    # 从真值内生库提取key
    for p in glob.glob(PRJ + "/experience/truth-core/TRUTH-GENERATED-*.json"):
        try:
            d = json.load(open(p))
            for t in d.get("truths", []):
                if t.get("key"): keys.add(t["key"])
        except Exception: pass
    # 已知上报过的闭环反哺key
    base = "evolve.cloop.20260929.gen{}.DID-BR-000002"
    for g in range(1, 12): keys.add(base.format(g))
    keys.add(f"truth.generated.{now()[:8]}.{DID}")
    return list(keys)

# ---------- 2 调用中枢单条召回 ----------
def recall(key):
    url = f"{CENTRAL_URL}/api/truth/{urllib.parse.quote(key)}"
    try:
        req = urllib.request.Request(url, headers={"X-Capture-Token": TOKEN, "X-DID": DID})
        r = urllib.request.urlopen(req, timeout=10)
        return json.loads(r.read().decode())
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ---------- 3 本地真值集 ----------
def local_truths():
    existing = {}
    for p in glob.glob(PRJ + "/experience/truth-core/TRUTH-*.json"):
        try:
            d = json.load(open(p))
            if isinstance(d.get("truths"), list):
                for t in d["truths"]:
                    k = t.get("key") or t.get("truth_key")
                    if k: existing[k] = t
            elif isinstance(d.get("truth"), dict):
                k = d["truth"].get("truth_key")
                if k: existing[k] = d["truth"]
        except Exception: pass
    return existing

def main():
    ap = argparse.ArgumentParser(description="中枢真值召回引擎")
    ap.add_argument("--keys", default="", help="指定key(逗号分隔), 默认从本地提取已上报key")
    ap.add_argument("--dry-run", action="store_true", help="只召回比对不写入")
    a = ap.parse_args()
    import urllib.parse
    keys = [k.strip() for k in a.keys.split(",") if k.strip()] if a.keys else local_keys()
    local = local_truths()

    recalled = []
    for key in keys:
        resp = recall(key)
        if resp.get("status") == "ok" and resp.get("truth"):
            t = resp["truth"]
            recalled.append({"key": key, "truth_key": t.get("truth_key"), "id": t.get("id"),
                             "value": t.get("truth_value", "")[:200], "category": t.get("category"),
                             "node_id": t.get("node_id"), "in_local": key in local})
        elif resp.get("status") == "not_found":
            recalled.append({"key": key, "status": "not_found"})
        else:
            recalled.append({"key": key, "status": resp.get("status"), "error": resp.get("error")})

    ok = [r for r in recalled if r.get("truth_key")]
    not_found = [r for r in recalled if r.get("status") == "not_found"]
    verified = [r for r in ok if r.get("in_local")]
    # 吸收: 云端有而本地无的新真值
    new_from_cloud = [r for r in ok if not r.get("in_local")]

    persist = {"skipped": "dry-run"}
    if not a.dry_run:
        os.makedirs(PRJ + "/experience/truth-core", exist_ok=True)
        ofile = PRJ + "/experience/truth-core/TRUTH-RECALLED-{}.json".format(time.strftime("%Y%m%d"))
        out = {"version": VERSION, "did": DID, "time": now(),
               "recalled": recalled, "new_from_cloud": new_from_cloud}
        try: os.chmod(ofile, 0o666)
        except Exception: pass
        json.dump(out, open(ofile, "w"), ensure_ascii=False, indent=2)
        os.chmod(ofile, 0o444)
        persist = {"recall_record": ofile, "recalled_count": len(ok), "new_from_cloud": len(new_from_cloud)}

    report = {"engine": VERSION, "did": DID, "time": now(),
              "keys_queried": len(keys),
              "recalled_ok": len(ok), "not_found": len(not_found),
              "cloud_verified_in_local": len(verified),
              "new_from_cloud": len(new_from_cloud),
              "persist": persist,
              "recall_detail": recalled[:10],
              "downlink_note": "下行链路: /api/truth/{key}单条召回可用; /api/truths列表当前返回脏数据不可靠"}
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
