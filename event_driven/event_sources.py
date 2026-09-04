"""4类事件源接入 - 服务状态/真值写入/客户反馈/资源告警"""
import json, os, subprocess, time
from datetime import datetime

EVENT_QUEUE = "/opt/ZONGYUAN-ROOT/event_driven/event_queue.json"

def load_queue():
    if os.path.exists(EVENT_QUEUE):
        with open(EVENT_QUEUE) as f:
            return json.load(f)
    return {"events": []}

def save_queue(q):
    with open(EVENT_QUEUE, "w") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)

def emit_event(event_type, source, data, priority="P2"):
    q = load_queue()
    event = {
        "id": f"EVT-{int(time.time())}-{len(q['events'])}",
        "type": event_type,
        "source": source,
        "data": data,
        "priority": priority,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    q["events"].append(event)
    save_queue(q)
    return event

# 事件源1: 服务状态监控
def monitor_services():
    """监控12个服务状态，crash触发P0自愈"""
    services = ["vector","omega-brain","loip","ance","anchor","gov","license","monitor","event","federation","meta","idle-engine"]
    crashed = []
    for svc in services:
        try:
            r = subprocess.run(["systemctl","is-active",f"zongyuan-{svc}"],capture_output=True,text=True,timeout=5)
            if "active" not in r.stdout:
                crashed.append(svc)
        except: pass
    if crashed:
        emit_event("service_crash", "service_monitor", {"crashed": crashed}, "P0")
        # 自动重启
        for svc in crashed:
            subprocess.run(["systemctl","restart",f"zongyuan-{svc}"])
        return {"crashed": crashed, "auto_restarted": True}
    return {"crashed": [], "auto_restarted": False}

# 事件源2: 真值写入监控
def monitor_truth_writes():
    """真值写入触发版本向量更新"""
    truth_file = "/opt/ZONGYUAN-ROOT/Ω-Brainμ/truth_index.json"
    if not os.path.exists(truth_file): return
    mtime = os.path.getmtime(truth_file)
    if time.time() - mtime < 60:  # 最近1分钟内修改
        emit_event("truth_written", "truth_monitor", {"file": truth_file, "mtime": mtime}, "P2")
        return {"detected": True}
    return {"detected": False}

# 事件源3: 资源告警监控
def monitor_resources():
    """CPU/内存/磁盘超阈值触发P0告警"""
    # 内存
    mem = subprocess.check_output(["free","-m"]).decode().split("\n")[1].split()
    mem_pct = int(mem[2]) / int(mem[1]) * 100
    # 磁盘
    disk = subprocess.check_output(["df","-h","/"]).decode().split("\n")[1].split()
    disk_pct = int(disk[4].replace("%",""))
    # CPU
    load = os.getloadavg()[0]
    
    alerts = []
    if mem_pct > 85: alerts.append({"type":"memory","value":f"{mem_pct:.1f}%","threshold":"85%"})
    if disk_pct > 85: alerts.append({"type":"disk","value":f"{disk_pct}%","threshold":"85%"})
    if load > 4: alerts.append({"type":"cpu_load","value":load,"threshold":"4.0"})
    
    if alerts:
        emit_event("resource_alert", "resource_monitor", {"alerts": alerts}, "P0" if mem_pct>90 or disk_pct>90 else "P1")
    return {"mem_pct": f"{mem_pct:.1f}%", "disk_pct": f"{disk_pct}%", "load": load, "alerts": alerts}

# 事件源4: 客户反馈监控
def monitor_customer_feedback():
    """客户授权到期/低健康度触发P2优化"""
    reminder_file = "/opt/ZONGYUAN-ROOT/customer_success/reminder_log.json"
    if os.path.exists(reminder_file):
        with open(reminder_file) as f:
            log = json.load(f)
        if log.get("expiring_count", 0) > 0:
            emit_event("customer_expiring", "customer_monitor", {"count": log["expiring_count"]}, "P2")
            return {"expiring": log["expiring_count"]}
    return {"expiring": 0}

def run_all_monitors():
    """运行所有事件源监控"""
    results = {
        "services": monitor_services(),
        "truth": monitor_truth_writes(),
        "resources": monitor_resources(),
        "customers": monitor_customer_feedback()
    }
    return results

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        results = run_all_monitors()
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("事件源监控器 V1.0")
        print("用法: python3 event_sources.py run")
