#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一网关上报器（gateway_report）｜ urllib 直连主通道 + 备份通道，稳定通道（规避沙箱代理间歇挂起）
锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
用法：python3 gateway_report.py '<key>' '<json-value>'
返回：{"ok": true, "truth_count": "...", "channel": "..."} 或 {"ok": false}
"""
import json, sys, urllib.request

DID = "DID-BR-000002"
CHANNELS = [
    "https://www.huodouai.com/api/report/truth",
    "https://drama.huodouai.com/api/report/truth",
]


def clean(v):
    """递归清洗：替换无效 surrogate 字符，保证 UTF-8 可编码"""
    if isinstance(v, str):
        return v.encode("utf-8", errors="replace").decode("utf-8")
    if isinstance(v, dict):
        return {clean(k): clean(x) for k, x in v.items()}
    if isinstance(v, list):
        return [clean(x) for x in v]
    return v


def report(key: str, value) -> dict:
    value = clean(value)
    payload = json.dumps({"key": key, "value": value}, ensure_ascii=False).encode("utf-8")
    for url in CHANNELS:
        req = urllib.request.Request(url, data=payload, headers={"X-DID": DID, "Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req, timeout=15)
            body = r.read().decode("utf-8", errors="replace")
            if "真值写入成功" in body:
                d = json.loads(body)
                return {"ok": True, "truth_count": d.get("truth_count", ""), "channel": url}
        except Exception:
            continue
    return {"ok": False}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "reason": "args"}))
        sys.exit(1)
    try:
        val = json.loads(sys.argv[2])
    except Exception:
        val = {"raw": sys.argv[2]}
    print(json.dumps(report(sys.argv[1], val), ensure_ascii=False))
