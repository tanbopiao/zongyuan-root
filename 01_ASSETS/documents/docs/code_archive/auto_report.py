
#!/usr/bin/env python3
"""
火斗云智AIOS 全自动上报机制
定期上报系统状态、真值数量、在线页面到9120记忆网关
"""
import requests
import json
import time
from datetime import datetime
import subprocess

GATEWAY_URL = "http://127.0.0.1:9120/api/truth/upsert"
INTERVAL = 3600  # 每小时上报一次

def get_system_status():
    """获取系统状态"""
    try:
        # 获取API网关状态
        api_resp = requests.get("http://127.0.0.1:8000/v1/status", 
                              headers={"Authorization": "Bearer huodou-pro-001"},
                              timeout=5)
        api_status = api_resp.json()
    except:
        api_status = {"status": "offline"}
    
    # 获取磁盘使用
    disk_usage = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
    disk_line = disk_usage.stdout.strip().split("\n")[-1]
    disk_parts = disk_line.split()
    disk_used = disk_parts[4] if len(disk_parts) > 4 else "unknown"
    
    # 获取内存使用
    mem_usage = subprocess.run(["free", "-h"], capture_output=True, text=True)
    mem_line = mem_usage.stdout.strip().split("\n")[1]
    mem_parts = mem_line.split()
    mem_used = mem_parts[2] if len(mem_parts) > 2 else "unknown"
    
    return {
        "api_gateway": "online" if api_status.get("service") else "offline",
        "disk_used": disk_used,
        "memory_used": mem_used,
        "report_time": datetime.now().isoformat()
    }

def report_status():
    """上报系统状态"""
    status = get_system_status()
    
    payload = {
        "key": f"SYSTEM.HEARTBEAT.{datetime.now().strftime('%Y%m%d%H%M')}",
        "value": f"系统心跳：API={status['api_gateway']}, 磁盘={status['disk_used']}, 内存={status['memory_used']}",
        "metadata": status
    }
    
    try:
        resp = requests.post(GATEWAY_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"[{datetime.now()}] ✅ 心跳上报成功")
        else:
            print(f"[{datetime.now()}] ❌ 心跳上报失败: {resp.status_code}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ 心跳上报错误: {e}")

def main():
    print("=" * 50)
    print("火斗云智AIOS 全自动上报机制启动")
    print(f"上报间隔: {INTERVAL}秒")
    print(f"网关地址: {GATEWAY_URL}")
    print("=" * 50)
    
    while True:
        report_status()
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
