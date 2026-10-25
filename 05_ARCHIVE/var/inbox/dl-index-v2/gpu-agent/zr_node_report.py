#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZR-NODE-REPORT 同源节点自主上报脚本 V1.0
用途: 实例本地读取节点token, 直接上报云端中枢(不经本地桥接)
位置: /mnt/workspace/zr_node_report.py (持久层)
协议: NTFY-CONNECT-001 V1.4 | 云端 V2.2
用法:
  python3 zr_node_report.py                      # 上报默认节点状态
  python3 zr_node_report.py --key <KEY> --val <VALUE>
  python3 zr_node_report.py --heartbeat          # 心跳上报
"""
import json, os, socket, sys, time, urllib.request

TOKEN_FILE = "/mnt/workspace/.zr/node_token.env"
CLOUD_URL = "https://www.huodouai.com/api/report/truth"
DID = "DID-BR-000002"
NODE = "ZR-NODE-MODEL-dsw-223619"

def load_token():
    for line in open(TOKEN_FILE):
        line = line.strip()
        if line.startswith("ZR_NODE_TOKEN="):
            return line.split("=", 1)[1]
    raise RuntimeError(f"token not found in {TOKEN_FILE}")

def report(key, value, ttype="rule", conf=0.98):
    body = json.dumps({
        "truth_key": key,
        "truth_value": value,
        "source_node": NODE,
        "confidence": conf,
        "truth_type": ttype,
    }, ensure_ascii=False).encode()
    req = urllib.request.Request(CLOUD_URL, data=body, headers={
        "X-Capture-Token": load_token(),
        "X-DID": DID,
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read().decode())
    print(json.dumps(resp, ensure_ascii=False))
    return resp

def default_state():
    ts = int(time.time())
    return json.dumps({
        "node": NODE, "hostname": socket.gethostname(),
        "gpu": "CPU", "worker": "V1.4-strict", "ts": ts,
        "direct_cloud": True,
    }, ensure_ascii=False)

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--key" in args and "--val" in args:
        k = args[args.index("--key")+1]
        v = args[args.index("--val")+1]
        report(k, v)
    elif "--heartbeat" in args:
        report(f"NODE.CPU.HEARTBEAT.{time.strftime('%Y%m%d')}", default_state())
    else:
        report(f"NODE.CPU.STATE.{time.strftime('%Y%m%d')}", default_state())
