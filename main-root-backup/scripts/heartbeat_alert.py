#!/usr/bin/env python3
"""心跳异常本地告警（飞书连接器关闭期间降级为本地日志+标记）"""
import json, os, datetime, urllib.request

LOGDIR = "/home/user/Doubao/chats/38439570362876674/ZONGYUAN-ROOT/logs"
ALERT_FILE = os.path.join(LOGDIR, "heartbeat_alerts.jsonl")

def check():
    try:
        with urllib.request.urlopen("https://www.huodouai.com/api/report/status", timeout=10) as r:
            d = json.load(r)
        ok = d.get("status") == "ok" and d.get("stats", {}).get("truths", 0) > 0
        info = {"ok": ok, "truths": d.get("stats", {}).get("truths"), "nodes": d.get("stats", {}).get("nodes")}
    except Exception as e:
        info = {"ok": False, "error": str(e)}
    entry = {"time": datetime.datetime.now().isoformat(timespec="seconds"), "did": "DID-BR-000002", **info}
    os.makedirs(LOGDIR, exist_ok=True)
    if not info["ok"]:
        with open(ALERT_FILE, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"ALERT: 心跳异常已记录 -> {entry}")
    else:
        print(f"OK: 心跳正常 truths={info.get('truths')} nodes={info.get('nodes')}")
    return info["ok"]

if __name__ == "__main__":
    check()
