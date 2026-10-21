#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ZONGYUAN METAPACK 执行器 — 中枢侧自动部署+执行+回报（幂等）"""
import json, sys, time, hashlib, subprocess, urllib.request
from pathlib import Path

GATEWAY = "https://www.huodouai.com"
KROOT = Path("/opt/ZONGYUAN-ROOT")  # 云端内核根
PK_ROOT = Path(__file__).resolve().parent.parent
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

def deploy_meta_rules():
    """部署元法则到云端内核 meta-rules/"""
    dst = KROOT / "meta-rules"
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in (PK_ROOT / "meta-rules").glob("*.md"):
        (dst / f.name).write_text(f.read_text())
        n += 1
    return n

def register_node():
    """更新节点注册表"""
    src = PK_ROOT / "registry.json"
    if src.exists():
        dst_dir = KROOT / "config"
        dst_dir.mkdir(parents=True, exist_ok=True)
        (dst_dir / "node_registry.json").write_text(src.read_text())
        return True
    return False

def report(action, detail):
    body = json.dumps({
        "truth_key": action,
        "truth_value": json.dumps({"pack": "ZONGYUAN-METAPACK-V1.0", "result": detail, "did": DID, "trace": TRACE}, ensure_ascii=False),
        "source_node": "cloud-kernel", "confidence": 1.0, "truth_type": "execution"}).encode()
    req = urllib.request.Request(f"{GATEWAY}/api/report/truth", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode()).get("action")
    except Exception as e:
        return f"err:{str(e)[:60]}"

def main():
    log("METAPACK 执行器启动")
    n = deploy_meta_rules()
    reg = register_node()
    log(f"元法则部署: {n} 条 | 注册表更新: {reg}")
    # 幂等：重复执行不产生新真值（同 key 覆盖）
    ack = report("ZONGYUAN.METAPACK.ACK.V1.0", {"rules": n, "registry": reg, "status": "deployed"})
    log(f"回执上报: {ack}")
    log("METAPACK 执行完成，全域生效")

if __name__ == "__main__":
    main()
