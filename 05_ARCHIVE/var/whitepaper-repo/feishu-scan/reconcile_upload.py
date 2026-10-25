#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconcile extracted candidate keys against cloud gateway; upload missing."""
import json, os, urllib.request, urllib.error, time, re

BASE = "/opt/ZONGYUAN-ROOT/ZONGYUAN-ROOT/feishu-scan"
GATEWAY = "https://www.huodouai.com"
DID, TRACE = "DID-BR-000002", "Ω₀⊂⊙∞⊂Ω"

def http_json(method, path, body=None, timeout=15):
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(f"{GATEWAY}{path}", data=data,
                                 headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode())
        except Exception: return e.code, {}
    except Exception:
        return 599, {}

def truth_type_of(key):
    if key.startswith("asset:"): return "asset"
    if key.startswith("LOCK"): return "lock"
    if key.startswith(("META-RULES", "ACHIEVEMENT")): return "meta"
    if key.startswith(("KD-EP", "KF-M", "Ω-")): return "ip_asset"
    if key.startswith("SNAP-"): return "lock"
    return "asset"

def main():
    # 1. merge per-item
    key_meta = {}   # key -> {"summary","shard","source","type"}
    for n in (1,2,3):
        d = json.load(open(os.path.join(BASE, f"shard_{n}_extract.json")))
        for it in d["_per_item"]:
            for k in it["keys"]:
                if k not in key_meta:
                    key_meta[k] = {"summary": it["summary"], "shard": n,
                                   "source": it["parent"], "name": it["name"]}
    candidates = sorted(key_meta.keys())

    # 2. cloud fast set
    cloud_set = set(json.load(open(os.path.join(BASE, "cloud-keys.json"))).get("truths", []))

    # 3. fast filter
    matched = [k for k in candidates if k in cloud_set]
    to_check = [k for k in candidates if k not in cloud_set]

    # 4. GET confirm
    confirmed_missing = []
    for k in to_check:
        code, _ = http_json("GET", f"/api/truth/{urllib.parse.quote(k)}", timeout=10)
        if code == 200:
            matched.append(k)
        elif code == 404:
            confirmed_missing.append(k)
        else:
            # network/other: treat as unknown -> still attempt upload (idempotent upsert)
            confirmed_missing.append(k)
        time.sleep(0.1)

    # 5. upload missing
    uploaded, failed = [], []
    for k in confirmed_missing:
        meta = key_meta[k]
        value = f"{meta['summary']}｜确权DID={DID}｜溯源={TRACE}"
        body = {"truth_key": k, "truth_value": value,
                "source_node": "local-feishu-extract", "confidence": 0.95,
                "truth_type": truth_type_of(k)}
        code, ack = http_json("POST", "/api/report/truth", body=body, timeout=15)
        action = ack.get("action") if isinstance(ack, dict) else None
        if code in (200, 201) and action in ("inserted", "updated"):
            uploaded.append({"truth_key": k, "truth_type": body["truth_type"], "http": code, "action": action})
        else:
            failed.append({"key": k, "code": code, "err": str(ack)[:80]})
        time.sleep(0.1)

    result = {"scanned_assets": 692, "readable": 482, "nontext_meta": 210,
              "candidate_keys": len(candidates),
              "cloud_matched": len(matched),
              "confirmed_missing": len(confirmed_missing),
              "uploaded": uploaded, "upload_failed": failed,
              "uploaded_keys": [u["truth_key"] for u in uploaded]}
    out = os.path.join(BASE, "reconcile_result.json")
    json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"candidates={len(candidates)} matched={len(matched)} "
          f"missing={len(confirmed_missing)} uploaded={len(uploaded)} failed={len(failed)}")
    print("UPLOADED:", [u['truth_key'] for u in uploaded])

if __name__ == "__main__":
    import urllib.parse
    main()
