#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单双向同步脚本
- 上报本地状态到中枢
- 从中枢拉取任务（如果有的话）
"""
import requests
import json
import time
import os
from datetime import datetime

GATEWAY = "https://www.huodouai.com/api"
NODE_ID = "NODE-LOCAL-HUAWEI-LAPTOP-001"

def report_status():
    """上报本地状态到中枢"""
    try:
        # 获取本地系统状态
        import psutil
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\\\')
        
        data = {
            "key": f"NODE.STATUS.{NODE_ID}",
            "value": json.dumps({
                "memory_used_pct": mem.percent,
                "memory_available_mb": mem.available // 1024 // 1024,
                "disk_c_used_pct": (disk.used / disk.total) * 100,
                "timestamp": datetime.now().isoformat()
            }),
            "source_node": NODE_ID,
            "confidence": 1.0,
            "truth_type": "data"
        }
        
        r = requests.post(f"{GATEWAY}/report/truth", json=data, timeout=5)
        if r.status_code == 200:
            print(f"[{datetime.now()}] 状态上报成功")
            return True
    except Exception as e:
        print(f"[{datetime.now()}] 上报失败: {e}")
        return False

def pull_tasks():
    """从中枢拉取任务"""
    try:
        r = requests.get(f"{GATEWAY}/tasks?node={NODE_ID}", timeout=5)
        if r.status_code == 200:
            tasks = r.json()
            if tasks:
                print(f"[{datetime.now()}] 收到 {len(tasks)} 个任务")
                return tasks
            else:
                print(f"[{datetime.now()}] 暂无任务")
        return []
    except Exception as e:
        print(f"[{datetime.now()}] 拉取任务失败: {e}")
        return []

if __name__ == "__main__":
    print("=== 双向同步测试 ===")
    report_status()
    pull_tasks()