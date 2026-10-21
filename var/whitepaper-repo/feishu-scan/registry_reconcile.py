#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract registry identifiers, reconcile to cloud, upload missing. Rate-limit gentle."""
import json, os, glob, urllib.request, urllib.error, time

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

# identifier field priority per table file
def record_key(rec, fname):
    for fld in ("快照ID","基因ID","进化ID","记录ID","ID","名称","标题","规则ID","法则ID","资产ID"):
        v = rec.get(fld)
        if isinstance(v, str) and v.strip():
            return v.strip()
    # fallback: first string field that looks like an ID
    for k, v in rec.items():
        if isinstance(v, str) and any(ch in v for ch in ("-","_")) and len(v) >= 6 and k not in ("record_id",):
            return v
    return None

def truth_type_of(k):
    if k.startswith(("SNAP","EVO","EFUSE")): return "lock"
    if k.startswith(("LOCK","META-RULES","ACHIEVEMENT")): return "meta"
    if k.startswith(("KD-EP","KF-M","Ω-")): return "ip_asset"
    return "meta"

def summarize(rec):
    bits = []
    for k in ("层级","状态","资产数","最优适应度","漂移分数","盲测分数","基因哈希","eFuse熔断ID","归档节点","执行时间","父链","备注"):
        if k in rec and rec[k] not in (None,"","N/A"):
            v = str(rec[k])[:40]
            bits.append(f"{k}={v}")
    return "；".join(bits)[:180]

def main():
    cloud_set = set(json.load(open(os.path.join(BASE,"cloud-keys.json"))).get("truths", []))
    candidates = {}  # key -> (value, table)
    for fp in sorted(glob.glob(os.path.join(BASE,"registry_ndjson","*.ndjson"))):
        table = os.path.basename(fp).replace(".ndjson","")
        for line in open(fp, encoding="utf-8"):
            line = line.strip()
            if not line: continue
            rec = json.loads(line)
            k = record_key(rec, table)
            if not k: continue
            if k not in candidates:
                candidates[k] = (f"注册表[{table}] {summarize(rec)}｜确权DID={DID}｜溯源={TRACE}", table)
    keys = sorted(candidates)
    matched = [k for k in keys if k in cloud_set]
    todo = [k for k in keys if k not in cloud_set]
    uploaded, failed = [], []
    for k in todo:
        value, table = candidates[k]
        body = {"truth_key": k, "truth_value": value, "source_node": "local-feishu-extract",
                "confidence": 0.95, "truth_type": truth_type_of(k)}
        for attempt in range(4):
            code, ack = http_json("POST", "/api/report/truth", body=body)
            action = ack.get("action") if isinstance(ack, dict) else None
            if code in (200,201) and action in ("inserted","updated"):
                uploaded.append(k); break
            if code == 429:
                time.sleep(2.0*(attempt+1)); continue
            time.sleep(1.0)
        else:
            failed.append({"key": k, "code": code, "err": str(ack)[:60]})
        time.sleep(1.3)
    result = {"registry_tables": len(glob.glob(os.path.join(BASE,"registry_ndjson","*.ndjson"))),
              "registry_records_keys": len(keys), "cloud_matched": len(matched),
              "to_upload": len(todo), "uploaded": uploaded, "upload_failed": failed}
    json.dump(result, open(os.path.join(BASE,"registry_reconcile.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"registry keys={len(keys)} matched={len(matched)} uploaded={len(uploaded)} failed={len(failed)}")

if __name__ == "__main__":
    main()
