#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evolution_consumer 演化消费者 ｜ W-08 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
职责: 周期读取云端 evolution-manifest.json（权威源），增量消费:
      truth 类 MERGED        → 真值小数据同步归档 var/fleet/evolution-consumed.jsonl（append-only）
      files 类 REVIEW_APPROVED → 生成采纳清单 var/fleet/approved-files.json（供 mirror/镜像采纳）
      applied 状态           → var/fleet/applied-evolutions.json（proposal_id → consumed_at）
安全: 只追加本地归档；不自动拉取/覆盖实体文件（评审通过后才进采纳清单，由采纳侧执行）
"""
import json, os, subprocess, sys, time

ZR = "/home/user/ZONGYUAN-ROOT"
CLOUD = "zongyuan-cloud"
REMOTE_MANIFEST = "/opt/ZONGYUAN-ROOT/var/fleet/evolution-manifest.json"
CONSUMED_LOG = f"{ZR}/var/fleet/evolution-consumed.jsonl"
APPROVED_FILE = f"{ZR}/var/fleet/approved-files.json"
STATE_FILE = f"{ZR}/var/fleet/applied-evolutions.json"

def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")

def load_state():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE, encoding="utf-8"))
    return {"since": now(), "applied": {}}

def save_state(st):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(st, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def fetch_manifest():
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", CLOUD,
                        f"cat {REMOTE_MANIFEST}"], capture_output=True, text=True, timeout=40)
    if r.returncode != 0:
        return None, r.stderr[:200]
    return json.loads(r.stdout), None

def consume():
    st = load_state()
    applied = st["applied"]
    m, err = fetch_manifest()
    if m is None:
        print(json.dumps({"status": "CLOUD_UNREACHABLE", "error": err}, ensure_ascii=False))
        sys.exit(1)
    os.makedirs(f"{ZR}/var/fleet", exist_ok=True)
    consumed = []
    approved_files = []
    for x in m.get("merged", []):
        pid = x["proposal_id"]
        if pid in applied:
            continue
        if x.get("type") == "truth" and x.get("status") == "MERGED":
            rec = {"proposal_id": pid, "kind": "truth", "node": x.get("node"),
                   "items": x.get("items"), "consumed_at": now()}
            with open(CONSUMED_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            consumed.append({"proposal_id": pid, "kind": "truth"})
            applied[pid] = now()
        elif x.get("type") == "files" and x.get("status") == "REVIEW_APPROVED":
            approved_files.append({"proposal_id": pid, "node": x.get("node"),
                                   "files": x.get("files", []), "approved_at": x.get("review", {}).get("at")})
            consumed.append({"proposal_id": pid, "kind": "files-approved"})
            applied[pid] = now()
    if approved_files:
        old = []
        if os.path.exists(APPROVED_FILE):
            old = json.load(open(APPROVED_FILE, encoding="utf-8"))
        merged = {x["proposal_id"]: x for x in old}
        for a in approved_files:
            merged[a["proposal_id"]] = a
        json.dump(list(merged.values()), open(APPROVED_FILE, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    save_state(st)
    print(json.dumps({"status": "consumed", "new_consumed": consumed,
                      "total_applied": len(applied)}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    consume()
