#!/usr/bin/env python3
"""ZONGYUAN-ROOT 飞书告警通知模块"""
import json, urllib.request, os, datetime, subprocess

CONFIG_PATH = "/opt/ZONGYUAN-ROOT/alert/alert_config.json"

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"feishu_webhook": "", "enabled": False, "min_level": "P1"}

def send_feishu(title, content, level="P2"):
    cfg = load_config()
    if not cfg.get("enabled") or not cfg.get("feishu_webhook") or "在此处" in str(cfg.get("feishu_webhook","")):
        log_path = "/opt/ZONGYUAN-ROOT/logs/alerts.log"
        with open(log_path, "a") as f:
            f.write(f"[{datetime.datetime.now().isoformat()}] [{level}] {title}: {content}\n")
        return {"status": "local_log"}
    level_color = {"P0": "red", "P1": "orange", "P2": "yellow", "P3": "blue"}.get(level, "grey")
    payload = {"msg_type":"interactive","card":{"header":{"title":{"tag":"plain_text","content":f"[{level}] {title}"},"template":level_color},"elements":[{"tag":"div","text":{"tag":"lark_md","content":content}},{"tag":"note","elements":[{"tag":"plain_text","content":f"ZONGYUAN-ROOT · {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}]}]}}
    try:
        req = urllib.request.Request(cfg["feishu_webhook"], data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        return {"status":"sent"}
    except Exception as e:
        return {"status":"failed","error":str(e)}

def check_and_alert():
    alerts = []
    services = ["zongyuan-omega","zongyuan-smartai","zongyuan-platform","zongyuan-gov","zongyuan-meta","zongyuan-vector","zongyuan-loip","zongyuan-ance","zongyuan-monitor","zongyuan-anchor","zongyuan-license","zongyuan-event","zongyuan-federation","frps"]
    failed = []
    for svc in services:
        r = subprocess.run(["systemctl","is-active",svc], capture_output=True, text=True)
        if r.stdout.strip() != "active":
            failed.append(svc)
    if failed:
        alerts.append(("服务异常", f"以下服务未运行: {', '.join(failed)}", "P0"))
    r = subprocess.run(["free","-m"], capture_output=True, text=True)
    mem_line = [l for l in r.stdout.split("\n") if l.startswith("Mem:")][0]
    available = int(mem_line.split()[6])
    if available < 200:
        alerts.append(("内存不足", f"可用内存仅 {available}MB", "P1"))
    r = subprocess.run(["df","-h","/"], capture_output=True, text=True)
    usage = int(r.stdout.split("\n")[1].split()[4].replace("%",""))
    if usage > 85:
        alerts.append(("磁盘不足", f"根分区使用率 {usage}%", "P1"))
    for title, content, level in alerts:
        result = send_feishu(title, content, level)
        print(f"[{level}] {title}: {result['status']}")
    if not alerts:
        print("巡检完成，无告警")
    return alerts

if __name__ == "__main__":
    check_and_alert()
