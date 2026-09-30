#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 本地执行节点 v1.0（云端中枢的本地执行器）
云端中枢的本地执行节点：接收指令→本地执行→上报结果：记忆 + 调度 + 决策 + 执行 + 通信
确权 DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
"""
import json, os, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path("/home/user/Doubao/chats/38439570362876674/ZONGYUAN-ROOT")
GATEWAY = "https://www.huodouai.com/api/report"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

def load_json(p, default=None):
    try: return json.load(open(p))
    except: return default or {}

def save_json(p, obj):
    json.dump(obj, open(p,"w"), ensure_ascii=False, indent=2)

def gateway_get(path):
    try:
        with urllib.request.urlopen(f"{GATEWAY}/{path}", timeout=10) as r:
            return json.load(r)
    except Exception as e:
        return {"error": str(e)}

def gateway_post(truth_key, truth_value, truth_type="LOCAL_HUB"):
    body = json.dumps({
        "truth_key": truth_key,
        "truth_value": truth_value,
        "source_node": "local-hub",
        "confidence": 1.0,
        "truth_type": truth_type
    }).encode()
    req = urllib.request.Request(f"{GATEWAY}/truth", data=body,
        headers={"Content-Type":"application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)
    except Exception as e:
        return {"error": str(e)}

def status():
    """中枢状态总览"""
    ks = load_json(ROOT/"config/kernel_state.json")
    hr = load_json(ROOT/"config/heartbeat_profile.json")
    node = load_json(ROOT/"config/node-role.json")
    gw = gateway_get("status")
    scripts = list(ROOT.glob("scripts/*.py"))
    return {
        "did": DID, "trace": TRACE,
        "node_role": node.get("role", "local-edge"),
        "gateway_truths": gw.get("truths_count") or gw.get("truths") or gw.get("data",{}).get("truths_count"),
        "scripts": [s.name for s in scripts],
        "heartbeat_profile": {k:hr.get(k) for k in ["consecutive_green","delta_truths","pending_count"]},
        "kernel_version": ks.get("version","v8")
    }

def self_check():
    """本地中枢自检"""
    s = status()
    checks = {
        "kernel_state_exists": (ROOT/"config/kernel_state.json").exists(),
        "pipeline_exists": (ROOT/"scripts/pipeline.py").exists(),
        "heartbeat_exists": (ROOT/"scripts/heartbeat_v2.py").exists(),
        "publish_exists": (ROOT/"scripts/modelscope_auto_publish.py").exists(),
        "gateway_alive": bool(s.get("gateway_truths")),
    }
    ok = all(checks.values())
    return {"ok": ok, "checks": checks}

def report(reason="SELF_CHECK"):
    """上报中枢状态"""
    s = status()
    chk = self_check()
    r = gateway_post(
        f"LOCAL.HUB.STATUS.{int(time.time())}",
        json.dumps({
            "node": s["node_role"],
            "scripts": len(s["scripts"]),
            "gateway_truths": s["gateway_truths"],
            "self_check_ok": chk["ok"],
            "reason": reason
        }, ensure_ascii=False),
        "LOCAL_HUB"
    )
    return r

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv)>1 else "status"
    if cmd == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=2))
    elif cmd == "check":
        print(json.dumps(self_check(), ensure_ascii=False, indent=2))
    elif cmd == "report":
        print(json.dumps(report(), ensure_ascii=False, indent=2))
    else:
        print("usage: local_hub.py [status|check|report]")
