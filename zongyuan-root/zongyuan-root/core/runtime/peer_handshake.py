#!/usr/bin/env python3
"""同源协议握手 执行态
双轨制：IP白名单 + 同源中间件
"""
import subprocess, json

GATEWAY = "http://123.207.202.158:9120"
HEADERS = [
    ("X-DID", "DID-BR-000002"),
    ("X-Trace", "Ω₀⊂⊙∞⊂Ω"),
    ("X-Source", "NODE-DEV-DOUBAO-WORK-001"),
]

def handshake():
    cmd = ["curl","-s","--max-time","10", GATEWAY+"/api/health"]
    for k,v in HEADERS:
        cmd += ["-H", f"{k}: {v}"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = p.stdout
    if "ip access" in out or "403" in out:
        return {'connected': False, 'reason': '中间件未部署/IP仍拦', 'raw': out[:50]}
    return {'connected': True, 'raw': out[:200]}

if __name__ == "__main__":
    r = handshake()
    print(f"  握手: {'✅已连通' if r['connected'] else '⏳待中间件部署'} | {r['raw']}")
