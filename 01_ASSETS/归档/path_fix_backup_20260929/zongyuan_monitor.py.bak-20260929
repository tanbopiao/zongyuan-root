#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT云内核监控告警脚本
P0-5: 监控CPU/内存/磁盘/服务状态，异常时记录日志
"""

import os
import time
import subprocess
import json
from datetime import datetime

LOG_FILE = "/var/log/zongyuan_monitor.log"
ALERT_LOG = "/var/log/zongyuan_alerts.log"

# 监控阈值
THRESHOLDS = {
    "cpu_percent": 80,
    "memory_percent": 90,
    "disk_percent": 85,
    "swap_percent": 50,
}

# 需要监控的服务和端口
SERVICES = {
    "aios": 8765,
    "nginx": 80,
    "nginx_https": 443,
    "mysql": 3306,
    "redis": 6379,
    "frps": 7100,
    "omega_brain": 8000,
    "loip": 8001,
    "anchor": 8006,
    "gov_platform": 8010,
}

def log(message, level="INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)
    if level in ["WARNING", "CRITICAL", "ALERT"]:
        with open(ALERT_LOG, "a", encoding="utf-8") as f:
            f.write(log_line)
    print(log_line.strip())

def get_cpu_usage():
    """获取CPU使用率"""
    try:
        result = subprocess.run(["top", "-bn1"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split("\n"):
            if "%Cpu" in line or "CPU:" in line:
                parts = line.replace(",", " ").split()
                for i, part in enumerate(parts):
                    if "id" in part.lower() or "idle" in part.lower():
                        idle = float(parts[i-1].replace("%", ""))
                        return round(100 - idle, 1)
    except:
        pass
    return 0

def get_memory_usage():
    """获取内存使用率"""
    try:
        result = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            total = int(parts[1])
            available = int(parts[6]) if len(parts) > 6 else int(parts[3])
            used_percent = round((1 - available/total) * 100, 1)
            return used_percent, total, available
    except:
        pass
    return 0, 0, 0

def get_disk_usage():
    """获取磁盘使用率"""
    try:
        result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            used_percent = int(parts[4].replace("%", ""))
            total = parts[1]
            available = parts[3]
            return used_percent, total, available
    except:
        pass
    return 0, "0", "0"

def check_port(port):
    """检查端口是否在监听"""
    try:
        result = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, timeout=5)
        return f":{port}" in result.stdout
    except:
        return False

def check_service_health(url, timeout=3):
    """检查服务健康状态"""
    try:
        result = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url], 
                              capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() == "200"
    except:
        return False

def run_monitor():
    """执行一次监控检查"""
    log("=" * 60)
    log("ZONGYUAN-ROOT云内核监控检查开始")
    
    alerts = []
    
    # CPU检查
    cpu = get_cpu_usage()
    log(f"CPU使用率: {cpu}% (阈值: {THRESHOLDS['cpu_percent']}%)")
    if cpu > THRESHOLDS["cpu_percent"]:
        alert = f"CPU使用率过高: {cpu}% > {THRESHOLDS['cpu_percent']}%"
        alerts.append(alert)
        log(alert, "WARNING")
    
    # 内存检查
    mem_percent, mem_total, mem_available = get_memory_usage()
    log(f"内存使用率: {mem_percent}% (总计: {mem_total}MB, 可用: {mem_available}MB, 阈值: {THRESHOLDS['memory_percent']}%)")
    if mem_percent > THRESHOLDS["memory_percent"]:
        alert = f"内存使用率过高: {mem_percent}% > {THRESHOLDS['memory_percent']}%"
        alerts.append(alert)
        log(alert, "WARNING")
    
    # 磁盘检查
    disk_percent, disk_total, disk_available = get_disk_usage()
    log(f"磁盘使用率: {disk_percent}% (总计: {disk_total}, 可用: {disk_available}, 阈值: {THRESHOLDS['disk_percent']}%)")
    if disk_percent > THRESHOLDS["disk_percent"]:
        alert = f"磁盘使用率过高: {disk_percent}% > {THRESHOLDS['disk_percent']}%"
        alerts.append(alert)
        log(alert, "WARNING")
    
    # 服务端口检查
    log("\n服务端口检查:")
    for service, port in SERVICES.items():
        is_listening = check_port(port)
        status = "✅ 正常" if is_listening else "❌ 异常"
        log(f"  {service} (端口{port}): {status}")
        if not is_listening:
            alert = f"服务异常: {service} (端口{port})未监听"
            alerts.append(alert)
            log(alert, "CRITICAL")
    
    # 关键服务健康检查
    log("\n关键服务健康检查:")
    health_checks = [
        ("AIOS", "http://127.0.0.1:8765/health"),
        ("Ω-Brainμ", "http://127.0.0.1:8000/health"),
        ("政务中台", "http://127.0.0.1:8010/health"),
    ]
    for service, url in health_checks:
        is_healthy = check_service_health(url)
        status = "✅ 健康" if is_healthy else "❌ 异常"
        log(f"  {service}: {status}")
        if not is_healthy:
            alert = f"服务健康检查失败: {service} ({url})"
            alerts.append(alert)
            log(alert, "CRITICAL")
    
    # 汇总
    log("\n" + "=" * 60)
    if alerts:
        log(f"监控检查完成，发现 {len(alerts)} 个告警:", "ALERT")
        for i, alert in enumerate(alerts, 1):
            log(f"  {i}. {alert}", "ALERT")
    else:
        log("监控检查完成，所有指标正常 ✅")
    
    return alerts

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        # 守护进程模式，每5分钟检查一次
        log("监控守护进程启动，每5分钟检查一次")
        while True:
            try:
                run_monitor()
            except Exception as e:
                log(f"监控执行异常: {str(e)}", "ERROR")
            time.sleep(300)  # 5分钟
    else:
        # 单次检查
        run_monitor()
