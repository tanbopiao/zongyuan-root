#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 全自动上报云端+同步共享大脑
每次发现新成果/真值/配置变更时自动执行：
1. POST到记忆网关(huodouai.com/api/report/truth)
2. 写入飞书Base共享大脑对应表
3. 推送AtomGit仓库同步
"""
import json, subprocess, sys, os
from datetime import datetime

GATEWAY = "https://www.huodouai.com/api/report/truth"
GATEWAY_TOKEN = "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"
DID = "DID-BR-000002"
NODE_ID = "NODE-DEV-DOUBAO-WORK-001"
BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
ATOMGIT_REMOTE = "atomgit"

def report_truth(key, value, confidence=0.95):
    """上报真值到记忆网关"""
    payload = {
        "key": key,
        "value": value,
        "node_id": NODE_ID,
        "confidence": confidence
    }
    cmd = [
        "curl", "-s", "-X", "POST", GATEWAY,
        "-H", "Content-Type: application/json",
        "-H", f"X-Capture-Token: {GATEWAY_TOKEN}",
        "-H", f"X-DID: {DID}",
        "-d", json.dumps(payload, ensure_ascii=False)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    try:
        d = json.loads(r.stdout)
        return d.get("seq"), d.get("message")
    except:
        return None, r.stdout[:200]

def write_base(table_id, records):
    """写入飞书Base共享大脑"""
    payload = json.dumps({"create_records": records}, ensure_ascii=False)
    cmd = [
        "lark-cli", "base", "+record-batch-create",
        "--base-token", BASE_TOKEN,
        "--table-id", table_id,
        "--as", "user",
        "--json", payload
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    try:
        d = json.loads(r.stdout)
        return d.get("ok", False), d.get("error", {}).get("message", "")
    except:
        return False, r.stdout[:200]

def sync_atomgit():
    """同步代码到AtomGit"""
    repo = "/home/user/ZONGYUAN-ROOT"
    if not os.path.isdir(repo):
        return False, "repo not found"
    r = subprocess.run(
        ["git", "-C", repo, "push", ATOMGIT_REMOTE, "main"],
        capture_output=True, text=True, timeout=60
    )
    return r.returncode == 0, (r.stdout + r.stderr)[-200:]

def auto_report(key, value, base_table=None, base_records=None, confidence=0.95):
    """一键全自动：上报网关+写Base+同步AtomGit"""
    results = {}
    
    # 1. 上报网关
    seq, msg = report_truth(key, value, confidence)
    results["gateway"] = {"seq": seq, "msg": msg}
    
    # 2. 写共享大脑
    if base_table and base_records:
        ok, err = write_base(base_table, base_records)
        results["base"] = {"ok": ok, "err": err}
    
    # 3. 同步AtomGit
    ok, out = sync_atomgit()
    results["atomgit"] = {"ok": ok, "out": out}
    
    return results

if __name__ == "__main__":
    # CLI用法: python3 auto_report_sync.py <key> <json_value>
    if len(sys.argv) >= 3:
        key = sys.argv[1]
        value = json.loads(sys.argv[2])
        results = auto_report(key, value)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("用法: python3 auto_report_sync.py <key> '<json_value>'")
