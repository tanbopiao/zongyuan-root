#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN 联邦融合进化 · 中枢仲裁合并器 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
落地: /opt/ZONGYUAN-ROOT/scripts/fleet_merge.py
职责: 扫描 var/fleet/proposals/ 演化提案 → 校验(DID/签名) → 合并:
      type=truth : 真值 items 幂等写入中枢真值库(INSERT OR IGNORE)
      type=files : 仅登记哈希清单至 manifest(pending_review, 不覆盖中枢文件=风险闸门)
      → 更新 var/fleet/evolution-manifest.json
用法: python3 fleet_merge.py merge | python3 fleet_merge.py broadcast
安全: 校验失败拒绝; 只追加 manifest; 永不覆盖/删除中枢既有真值与文件
"""
import json, os, sqlite3, time, sys, glob, hashlib

ROOT = "/opt/ZONGYUAN-ROOT"
PROP_DIR = f"{ROOT}/var/fleet/proposals"
MANIFEST = f"{ROOT}/var/fleet/evolution-manifest.json"
DB = f"{ROOT}/data/gateway_9120_only/memory_gateway.db"
DID = "DID-BR-000002"
ONT = "Ω₀⊂⊙∞⊂Ω"

def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")

def load_manifest():
    if os.path.exists(MANIFEST):
        return json.load(open(MANIFEST, encoding="utf-8"))
    return {"did": DID, "since": now(), "merged": [], "broadcast": []}

def save_manifest(m):
    json.dump(m, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    os.chmod(MANIFEST, 0o444)

def write_truth(key, value, node_id, ts):
    c = sqlite3.connect(DB)
    c.execute("INSERT OR IGNORE INTO truths(truth_key, truth_value, truth_hash, category, node_id, created_at, version) VALUES (?,?,?,?,?,?,?)",
              (key, json.dumps(value, ensure_ascii=False), "fusion-evol", "evolution", node_id, int(ts), 1))
    c.commit()
    cur = c.execute("SELECT changes()").fetchone()[0]
    c.close()
    return cur

def validate(p):
    errs = []
    if p.get("did") != DID: errs.append("DID 不符")
    if p.get("ontology_signature") != ONT: errs.append("本体签名不符")
    if p.get("type") not in ("truth", "files"): errs.append("type 非法")
    if not p.get("proposal_id"): errs.append("缺少 proposal_id")
    if not isinstance(p.get("items", []), list) or not p["items"]: errs.append("items 为空")
    return errs

def merge():
    m = load_manifest()
    merged_ids = {x["proposal_id"] for x in m["merged"]}
    os.makedirs(PROP_DIR, exist_ok=True)
    files = sorted(glob.glob(f"{PROP_DIR}/*.json"))
    result = []
    for fp in files:
        try:
            p = json.load(open(fp, encoding="utf-8"))
        except Exception as e:
            result.append({"proposal_id": os.path.basename(fp), "status": "INVALID_JSON", "reason": str(e)})
            continue
        pid = p["proposal_id"]
        if pid in merged_ids:
            continue
        errs = validate(p)
        if errs:
            result.append({"proposal_id": pid, "status": "REJECTED", "reasons": errs})
            continue
        node = p.get("node", "unknown")
        p_ts = p.get("ts", int(time.time()))
        if p["type"] == "truth":
            ok_n = 0
            for it in p["items"]:
                k, v = it.get("key"), it.get("value")
                if not k:
                    continue
                ok_n += write_truth(k, v, node, p_ts)
            st = {"proposal_id": pid, "type": "truth", "node": node, "ts": now(),
                  "items": len(p["items"]), "inserted": ok_n, "status": "MERGED"}
        else:  # files: 仅登记哈希清单，pending_review（风险闸门：不覆盖中枢文件）
            st = {"proposal_id": pid, "type": "files", "node": node, "ts": now(),
                  "files": p["items"], "status": "PENDING_REVIEW",
                  "note": "文件级演化仅登记哈希，需人工复核后由中枢侧采纳"}
        m["merged"].append(st)
        result.append(st)
    save_manifest(m)
    return result

def broadcast():
    m = load_manifest()
    todo = [x for x in m["merged"] if x.get("status") in ("MERGED", "PENDING_REVIEW")
            and x["proposal_id"] not in {b.get("proposal_id") for b in m["broadcast"]}]
    out = []
    for item in todo:
        key = f"INSTRUCTION.EVOLUTION.{item['proposal_id']}"
        value = {"cmd": "evolution-broadcast", "proposal_id": item["proposal_id"],
                 "type": item["type"], "node": item["node"], "status": item["status"],
                 "ts": int(time.time())}
        ok = False
        try:
            import urllib.request
            payload = json.dumps({"key": key, "value": value}).encode()
            req = urllib.request.Request("https://www.huodouai.com/api/report/truth",
                data=payload, headers={"Content-Type": "application/json", "X-DID": DID})
            r = json.load(urllib.request.urlopen(req, timeout=20))
            ok = "真值写入成功" in r.get("message", "")
        except Exception:
            ok = False
        item["broadcast"] = {"key": key, "ts": now(), "gateway_ok": ok}
        m["broadcast"].append({"proposal_id": item["proposal_id"], "key": key, "ts": now(), "gateway_ok": ok})
        out.append(item)
    save_manifest(m)
    return out

if __name__ == "__main__":
    act = sys.argv[1] if len(sys.argv) > 1 else "merge"
    if act == "merge":
        for r in merge():
            print(f"  {r['status']:>14}  {r['proposal_id']}")
    elif act == "broadcast":
        rs = broadcast()
        if not rs:
            print("  无待广播批次")
        for r in rs:
            print(f"  已广播 {r['proposal_id']}  type={r['type']}  gateway={r.get('broadcast',{}).get('gateway_ok')}")
    else:
        print("用法: fleet_merge.py merge|broadcast")
        sys.exit(2)
