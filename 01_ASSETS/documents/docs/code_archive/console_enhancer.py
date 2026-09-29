#!/usr/bin/env python3
"""
统一控制台增强模块：历史数据采集 + 告警机制
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import time
import requests
from datetime import datetime

HISTORY_FILE = "/opt/ZONGYUAN-ROOT/data/console_history.json"
ALERTS_FILE = "/opt/ZONGYUAN-ROOT/data/console_alerts.json"
MAX_HISTORY_POINTS = 288  # 24小时 * 12次/小时（每5分钟一次）

# 告警阈值
ALERT_THRESHOLDS = {
    "cpu_percent": {"warning": 70, "critical": 85, "name": "CPU使用率"},
    "memory_percent": {"warning": 75, "critical": 85, "name": "内存使用率"},
    "disk_percent": {"warning": 80, "critical": 90, "name": "磁盘使用率"},
}

def load_json(filepath, default):
    """加载JSON文件"""
    if os.path.exists(filepath):
        try:
            with open(filepath) as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(filepath, data):
    """保存JSON文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def collect_system_status():
    """采集系统状态"""
    try:
        resp = requests.get("http://127.0.0.1:9170/api/console/status", timeout=10)
        data = resp.json()
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": data.get("system", {}).get("cpu_percent", 0),
            "memory_percent": data.get("system", {}).get("memory_percent", 0),
            "disk_percent": data.get("system", {}).get("disk_percent", 0),
            "truth_count": data.get("knowledge_base", {}).get("truth_count", 0),
            "kg_nodes": data.get("knowledge_base", {}).get("kg_nodes", 0),
            "kg_edges": data.get("knowledge_base", {}).get("kg_edges", 0),
            "engines_active": data.get("engines", {}).get("active", 0),
            "engines_total": data.get("engines", {}).get("total", 0),
        }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "cpu_percent": 0,
            "memory_percent": 0,
            "disk_percent": 0,
            "truth_count": 0,
            "kg_nodes": 0,
            "kg_edges": 0,
            "engines_active": 0,
            "engines_total": 0,
        }

def check_alerts(status):
    """检查告警条件，返回新告警列表"""
    new_alerts = []
    
    for key, threshold in ALERT_THRESHOLDS.items():
        value = status.get(key, 0)
        name = threshold["name"]
        
        if value >= threshold["critical"]:
            new_alerts.append({
                "id": f"alert_{int(time.time())}_{key}",
                "timestamp": status["timestamp"],
                "level": "critical",
                "metric": key,
                "metric_name": name,
                "value": value,
                "threshold": threshold["critical"],
                "message": f"{name}达到{value}%，超过临界阈值{threshold['critical']}%",
                "acknowledged": False,
            })
        elif value >= threshold["warning"]:
            new_alerts.append({
                "id": f"alert_{int(time.time())}_{key}",
                "timestamp": status["timestamp"],
                "level": "warning",
                "metric": key,
                "metric_name": name,
                "value": value,
                "threshold": threshold["warning"],
                "message": f"{name}达到{value}%，超过警告阈值{threshold['warning']}%",
                "acknowledged": False,
            })
    
    return new_alerts

def run_collection():
    """执行一次采集+告警检查"""
    # 采集状态
    status = collect_system_status()
    
    # 保存历史数据
    history = load_json(HISTORY_FILE, {"data": []})
    history["data"].append(status)
    # 保留最近MAX_HISTORY_POINTS条
    if len(history["data"]) > MAX_HISTORY_POINTS:
        history["data"] = history["data"][-MAX_HISTORY_POINTS:]
    save_json(HISTORY_FILE, history)
    
    # 检查告警
    new_alerts = check_alerts(status)
    
    # 保存告警
    if new_alerts:
        alerts = load_json(ALERTS_FILE, {"alerts": []})
        alerts["alerts"].extend(new_alerts)
        # 保留最近100条告警
        if len(alerts["alerts"]) > 100:
            alerts["alerts"] = alerts["alerts"][-100:]
        save_json(ALERTS_FILE, alerts)
    
    return {
        "status": status,
        "new_alerts": new_alerts,
        "history_points": len(history["data"]),
        "total_alerts": len(load_json(ALERTS_FILE, {"alerts": []}).get("alerts", [])),
    }

def get_history(hours=24):
    """获取历史数据"""
    history = load_json(HISTORY_FILE, {"data": []})
    data = history.get("data", [])
    # 简单按时间过滤（每5分钟一个点，hours小时 = hours*12个点）
    points = hours * 12
    if len(data) > points:
        data = data[-points:]
    return data

def get_alerts(limit=20):
    """获取告警列表"""
    alerts = load_json(ALERTS_FILE, {"alerts": []})
    data = alerts.get("alerts", [])
    return data[-limit:] if len(data) > limit else data

def acknowledge_alert(alert_id):
    """确认告警"""
    alerts = load_json(ALERTS_FILE, {"alerts": []})
    for alert in alerts.get("alerts", []):
        if alert.get("id") == alert_id:
            alert["acknowledged"] = True
            alert["acknowledged_at"] = datetime.now().isoformat()
            save_json(ALERTS_FILE, alerts)
            return True
    return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "collect":
            result = run_collection()
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif cmd == "history":
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            data = get_history(hours)
            print(f"历史数据点: {len(data)}")
            if data:
                print(f"最早: {data[0]['timestamp']}")
                print(f"最新: {data[-1]['timestamp']}")
        elif cmd == "alerts":
            alerts = get_alerts()
            print(f"告警数量: {len(alerts)}")
            for alert in alerts[-5:]:
                print(f"  [{alert['level']}] {alert['message']}")
        else:
            print("用法: python console_enhancer.py [collect|history|alerts]")
    else:
        # 默认执行一次采集
        result = run_collection()
        print(json.dumps(result, ensure_ascii=False, indent=2))
