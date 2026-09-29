#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 自愈桥接器
- 定期检查核心服务/资源状态
- 发现故障时构造Alertmanager格式告警发送给自愈引擎(8161)
- 打通"监控→诊断→修复→验证"闭环
- 每60秒检查一次
"""
import json
import time
import os
import subprocess
import urllib.request
from datetime import datetime

# 配置
HEALING_ENGINE_URL = "http://127.0.0.1:8161/webhook/alertmanager"
CHECK_INTERVAL = 60
LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/healing_bridge.log"
STATE_FILE = "/opt/ZONGYUAN-ROOT/data/healing_bridge_state.json"
COOLDOWN = 300  # 同一故障5分钟内不重复告警

# 核心服务监控列表
CORE_SERVICES = [
    {"name": "zongyuan-unified-gateway", "port": 9120, "alertname": "InstanceDown"},
    {"name": "zongyuan-vector-server", "port": 8014, "alertname": "InstanceDown"},
    {"name": "llama-server", "port": 8081, "alertname": "InstanceDown"},
    {"name": "zongyuan-rag", "port": 8085, "alertname": "InstanceDown"},
    {"name": "self-healing-engine", "port": 8161, "alertname": "InstanceDown"},
    {"name": "zongyuan-operator-panel", "port": 8170, "alertname": "InstanceDown"},
    {"name": "closed-loop-scheduler", "port": 8094, "alertname": "InstanceDown"},
    {"name": "nginx", "port": 80, "alertname": "NginxDown"},
]

# 资源阈值
CPU_THRESHOLD = 90
MEM_THRESHOLD = 85
DISK_THRESHOLD = 85

def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{datetime.now()}] {msg}\n")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_alert": {}, "check_count": 0, "alert_count": 0}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_alert(alertname, labels, annotations):
    """发送告警给自愈引擎"""
    payload = {
        "alerts": [{
            "status": "firing",
            "labels": {"alertname": alertname, **labels},
            "annotations": annotations,
            "startsAt": datetime.now().isoformat()
        }]
    }
    try:
        req = urllib.request.Request(
            HEALING_ENGINE_URL,
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result
    except Exception as e:
        log(f"发送告警失败: {e}")
        return {"error": str(e)}

def check_service(svc):
    """检查服务状态"""
    # 检查端口
    try:
        result = subprocess.run(
            ['ss', '-tlnp'],
            capture_output=True, text=True, timeout=3
        )
        port_ok = f":{svc['port']} " in result.stdout
    except:
        port_ok = False
    
    # 检查进程
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', svc['name']],
            capture_output=True, text=True, timeout=3
        )
        process_ok = result.stdout.strip() == 'active'
    except:
        process_ok = False
    
    return process_ok and port_ok

def check_resources():
    """检查资源使用"""
    alerts = []
    
    # CPU
    try:
        with open('/proc/loadavg') as f:
            load1 = float(f.read().split()[0])
        cpu_cores = os.cpu_count() or 4
        cpu_usage = (load1 / cpu_cores) * 100
        if cpu_usage > CPU_THRESHOLD:
            alerts.append(("HighCPUUsage", 
                {"service": "system", "cpu_usage": str(round(cpu_usage, 1))},
                {"summary": f"CPU使用率过高: {round(cpu_usage,1)}%", "description": f"1分钟负载{load1}/{cpu_cores}核"}))
    except:
        pass
    
    # 内存
    try:
        result = subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=3)
        parts = result.stdout.split('\n')[1].split()
        mem_total = int(parts[1])
        mem_used = int(parts[2])
        mem_pct = mem_used / mem_total * 100
        if mem_pct > MEM_THRESHOLD:
            alerts.append(("HighMemoryUsage",
                {"service": "system", "memory_usage": str(round(mem_pct, 1))},
                {"summary": f"内存使用率过高: {round(mem_pct,1)}%", "description": f"{mem_used}MB/{mem_total}MB"}))
    except:
        pass
    
    # 磁盘
    try:
        result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, timeout=3)
        parts = result.stdout.split('\n')[1].split()
        disk_pct = int(parts[4].replace('%', ''))
        if disk_pct > DISK_THRESHOLD:
            alerts.append(("HighDiskUsage",
                {"service": "system", "disk_usage": str(disk_pct)},
                {"summary": f"磁盘使用率过高: {disk_pct}%", "description": "根分区磁盘空间不足"}))
    except:
        pass
    
    return alerts

def main():
    log("=" * 50)
    log("自愈桥接器启动")
    state = load_state()
    
    while True:
        state["check_count"] += 1
        now = time.time()
        
        # 检查核心服务
        for svc in CORE_SERVICES:
            if not check_service(svc):
                alert_key = f"service_{svc['name']}"
                last_time = state["last_alert"].get(alert_key, 0)
                if now - last_time > COOLDOWN:
                    log(f"检测到服务故障: {svc['name']} (端口{svc['port']})")
                    result = send_alert(
                        svc['alertname'],
                        {"instance": svc['name'], "service": svc['name'], "port": str(svc['port'])},
                        {"summary": f"服务{svc['name']}宕机", "description": f"端口{svc['port']}未监听或进程不活跃"}
                    )
                    log(f"  自愈引擎响应: {json.dumps(result, ensure_ascii=False)[:150]}")
                    state["last_alert"][alert_key] = now
                    state["alert_count"] += 1
        
        # 检查资源
        resource_alerts = check_resources()
        for alertname, labels, annotations in resource_alerts:
            alert_key = f"resource_{alertname}"
            last_time = state["last_alert"].get(alert_key, 0)
            if now - last_time > COOLDOWN:
                log(f"检测到资源告警: {alertname} - {annotations['summary']}")
                result = send_alert(alertname, labels, annotations)
                log(f"  自愈引擎响应: {json.dumps(result, ensure_ascii=False)[:150]}")
                state["last_alert"][alert_key] = now
                state["alert_count"] += 1
        
        save_state(state)
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
