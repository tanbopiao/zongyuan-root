#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Retry previously rate-limited (429) uploads with backoff."""
import json, os, urllib.request, urllib.error, time, urllib.parse

BASE = "/opt/ZONGYUAN-ROOT/ZONGYUAN-ROOT/feishu-scan"
GATEWAY = "https://www.huodouai.com"
DID, TRACE = "DID-BR-000002", "Ω₀⊂⊙∞⊂Ω"

def http_json(method, path, body=None, timeout=20):
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
    r = json.load(open(os.path.join(BASE, "reconcile_result.json")))
    # rebuild key->summary from shard extracts
    key_meta = {}
    for n in (1,2,3):
        d = json.load(open(os.path.join(BASE, f"shard_{n}_extract.json")))
        for it in d["_per_item"]:
            for k in it["keys"]:
                key_meta.setdefault(k, it["summary"])
    failed_keys = [f["key"] for f in r["upload_failed"]]
    newly_ok, still_failed = [], []
    for k in failed_keys:
        summary = key_meta.get(k, f"飞书资产 {k}")
        body = {"truth_key": k,
                "truth_value": f"{summary}｜确权DID={DID}｜溯源={TRACE}",
                "source_node": "local-feishu-extract", "confidence": 0.95,
                "truth_type": truth_type_of(k)}
        # retry up to 4 times with backoff on 429
        for attempt in range(4):
            code, ack = http_json("POST", "/api/report/truth", body=body)
            action = ack.get("action") if isinstance(ack, dict) else None
            if code in (200,201) and action in ("inserted","updated"):
                newly_ok.append({"truth_key": k, "truth_type": body["truth_type"], "http": code})
                break
            if code == 429:
                time.sleep(2.0 * (attempt+1))
                continue
            time.sleep(1.0)
        else:
            still_failed.append({"key": k, "code": code, "err": str(ack)[:80]})
        time.sleep(1.2)  # gentle spacing between keys
    r["uploaded"].extend(newly_ok)
    r["uploaded_keys"] = [u["truth_key"] for u in r["uploaded"]]
    r["upload_failed"] = still_failed
    json.dump(r, open(os.path.join(BASE, "reconcile_result.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"recovered={len(newly_ok)} still_failed={len(still_failed)} total_uploaded={len(r['uploaded'])}")

if __name__ == "__main__":
    main()
