#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
度量协调器（Metrics Coordinator）
解决LLM按需管理器与度量引擎的瞬时干扰问题：
度量时暂停LLM启动，避免内存瞬时波动导致D4被低估

工作流程：
1. 度量前：设置度量窗口标志，暂停LLM按需启动
2. 如果LLM正在运行，等待它完成或优雅停止
3. 执行度量
4. 度量后：清除度量窗口标志，恢复LLM按需管理
"""

import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime

LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/metrics-coordinator.log"
METRICS_LOCK = "/tmp/metrics_in_progress.lock"
METRICS_SCRIPT = "/opt/ZONGYUAN-ROOT/scripts/meta_evolution_metrics.py"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def is_llm_running():
    """检查本地LLM是否正在运行"""
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', 'llm-server.service'],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == "active"
    except:
        return False

def stop_llm_if_idle():
    """如果LLM空闲，停止它以释放内存"""
    if not is_llm_running():
        log("  LLM未运行，无需停止")
        return True
    
    # 检查LLM是否在处理请求（简单检查：端口连接数）
    try:
        result = subprocess.run(
            ['ss', '-tn', 'sport', '=', ':8081'],
            capture_output=True, text=True, timeout=5
        )
        connections = len(result.stdout.strip().split('\n')) - 1
        if connections > 0:
            log(f"  LLM正在处理{connections}个请求，等待完成...")
            time.sleep(10)
    except:
        pass
    
    # 停止LLM
    try:
        subprocess.run(['systemctl', 'stop', 'llm-server.service'], timeout=10)
        log("  ✅ LLM已停止（释放~700M内存）")
        return True
    except Exception as e:
        log(f"  ⚠️ LLM停止失败: {e}")
        return False

def start_llm_manager():
    """恢复LLM按需管理器"""
    try:
        # 确保llm_ondemand_manager的crontab在运行
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=5)
        if 'llm_ondemand' not in result.stdout:
            log("  ⚠️ LLM按需管理器不在crontab中，需要重新添加")
        else:
            log("  ✅ LLM按需管理器已恢复")
    except Exception as e:
        log(f"  ⚠️ 恢复LLM管理器失败: {e}")

def run_metrics_with_coordination():
    """带协调的度量执行"""
    log("=" * 50)
    log("🎯 度量协调器启动")
    
    # 1. 设置度量锁
    with open(METRICS_LOCK, 'w') as f:
        f.write(datetime.now().isoformat())
    log("  🔒 度量窗口已锁定（LLM按需管理器将跳过启动）")
    
    try:
        # 2. 停止LLM（如果空闲）
        log("  📦 检查LLM状态...")
        stop_llm_if_idle()
        
        # 3. 等待内存稳定
        log("  ⏳ 等待内存稳定(3秒)...")
        time.sleep(3)
        
        # 4. 执行度量
        log("  📊 执行元进化度量...")
        result = subprocess.run(
            ['python3', METRICS_SCRIPT],
            capture_output=True, text=True, timeout=60
        )
        
        # 输出关键结果
        for line in result.stdout.split('\n'):
            if any(k in line for k in ['元进化指数', '等级', 'D4_entropy', 'D1_paradigm', 'D6_loop']):
                log(f"  {line.strip()}")
        
        return result.stdout
        
    finally:
        # 5. 清除度量锁，恢复LLM管理
        if os.path.exists(METRICS_LOCK):
            os.remove(METRICS_LOCK)
        log("  🔓 度量窗口已解锁")
        start_llm_manager()
        log("=" * 50)

def get_status():
    """获取协调器状态"""
    return {
        "coordinator": "metrics_coordinator",
        "metrics_in_progress": os.path.exists(METRICS_LOCK),
        "llm_running": is_llm_running(),
        "note": "度量时自动暂停LLM启动，避免D4瞬时波动",
        "usage": "python3 metrics_coordinator.py run  # 执行带协调的度量"
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "run":
            run_metrics_with_coordination()
        elif cmd == "status":
            print(json.dumps(get_status(), indent=2, ensure_ascii=False))
        else:
            print("用法: python3 metrics_coordinator.py [run|status]")
    else:
        run_metrics_with_coordination()
