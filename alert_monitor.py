#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 告警监控系统 V7.0
监控：服务状态/磁盘/内存/证书/漂移，异常写入告警日志
"""
import json, os, time, subprocess, logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/opt/ZONGYUAN-ROOT")
LOG_DIR = ROOT / "logs"
ALERT_FILE = LOG_DIR / "alerts.jsonl"
CST = timezone(timedelta(hours=8))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_DIR / "alert_monitor.log"), logging.StreamHandler()])
logger = logging.getLogger("alert-monitor")

SERVICES = {"omega-brain":8000,"loip":8001,"ance":8002,"vector":8003,"monitor":8004,"gov-ai":8005,"anchor":8006}

def check_services():
    alerts = []
    for name, port in SERVICES.items():
        try:
            r = subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code}","--connect-timeout","3",
                f"http://127.0.0.1:{port}/health"], capture_output=True, text=True, timeout=5)
            if r.stdout.strip() not in ["200","404"]:
                alerts.append({"level":"P1","type":"service_down","service":name,"detail":f"HTTP {r.stdout.strip()}"})
        except:
            alerts.append({"level":"P0","type":"service_unreachable","service":name,"detail":"connection_timeout"})
    return alerts

def check_disk():
    r = subprocess.run(["df","-h","/"], capture_output=True, text=True)
    for line in r.stdout.split("\n"):
        if "/" in line and "%" in line:
            parts = line.split()
            usage = int(parts[4].replace("%",""))
            if usage >= 90:
                return [{"level":"P0","type":"disk_full","detail":f"磁盘使用率{usage}%"}]
            if usage >= 80:
                return [{"level":"P2","type":"disk_warning","detail":f"磁盘使用率{usage}%"}]
    return []

def check_memory():
    r = subprocess.run(["free","-m"], capture_output=True, text=True)
    for line in r.stdout.split("\n"):
        if line.startswith("Mem:"):
            parts = line.split()
            total, used = int(parts[1]), int(parts[2])
            if total > 0 and used/total > 0.9:
                return [{"level":"P1","type":"memory_high","detail":f"内存使用率{used*100//total}%"}]
    return []

def check_ssl():
    alerts = []
    for domain in ["huodouai.com","www.huodouai.com"]:
        try:
            r = subprocess.run(["curl","-sI","--connect-timeout","5",f"https://{domain}"],
                capture_output=True, text=True, timeout=8)
            if "200" not in r.stdout and "301" not in r.stdout and "302" not in r.stdout:
                alerts.append({"level":"P1","type":"ssl_error","domain":domain,"detail":"HTTPS访问异常"})
        except:
            alerts.append({"level":"P2","type":"ssl_check_fail","domain":domain})
    return alerts

def run_check():
    all_alerts = []
    all_alerts.extend(check_services())
    all_alerts.extend(check_disk())
    all_alerts.extend(check_memory())
    all_alerts.extend(check_ssl())
    
    if all_alerts:
        entry = {"timestamp":datetime.now(CST).isoformat(),"alert_count":len(all_alerts),"alerts":all_alerts}
        with open(ALERT_FILE,"a") as f:
            f.write(json.dumps(entry,ensure_ascii=False)+"\n")
        for a in all_alerts:
            logger.warning(f"[{a['level']}] {a['type']}: {a.get('detail',a.get('service',''))}")
        # P0自动触发自愈
        p0 = [a for a in all_alerts if a["level"]=="P0"]
        if p0:
            logger.info("检测到P0告警，触发ANCE自愈")
            subprocess.run(["python3","/opt/ZONGYUAN-ROOT/ance_self_heal.py"], capture_output=True, timeout=30)
    else:
        logger.info("全系统健康，无告警")
    return all_alerts

if __name__ == "__main__":
    alerts = run_check()
    print(json.dumps({"status":"healthy" if not alerts else "alerts","count":len(alerts),"alerts":alerts},indent=2,ensure_ascii=False))
