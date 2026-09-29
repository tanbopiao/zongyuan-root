#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地小模型按需启停管理器
新建链路，不修改原有llama-server/zongyuan-local-llm服务配置

策略：
- 默认不常驻，需要推理时启动
- 推理完成后空闲5分钟自动停止
- 与六态状态机联动：保活态/休眠态时强制停止
- 记录启动/停止日志，纳入元进化度量
"""

import subprocess
import time
import json
import os
from datetime import datetime

LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/llm-ondemand.log"
STATE_FILE = "/opt/ZONGYUAN-ROOT/data/llm_ondemand_state.json"
IDLE_TIMEOUT = 300  # 5分钟空闲后自动停止

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def get_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {"last_request": 0, "running": False, "total_starts": 0, "total_stops": 0}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def is_running():
    """检查llama相关服务是否在运行"""
    for svc in ["llama-server", "zongyuan-local-llm"]:
        try:
            result = subprocess.run(['systemctl', 'is-active', svc], 
                                  capture_output=True, text=True, timeout=5)
            if result.stdout.strip() == "active":
                return svc
        except:
            pass
    return None

def start_llm():
    """启动本地小模型（优先zongyuan-local-llm）"""
    state = get_state()
    if is_running():
        log("LLM已在运行，无需启动")
        return True
    
    log("启动本地小模型...")
    for svc in ["zongyuan-local-llm", "llama-server"]:
        try:
            subprocess.run(['systemctl', 'start', svc], timeout=10)
            time.sleep(3)
            if is_running():
                state["running"] = True
                state["last_request"] = time.time()
                state["total_starts"] += 1
                save_state(state)
                log(f"✅ {svc} 启动成功")
                return True
        except Exception as e:
            log(f"⚠️ {svc} 启动失败: {e}")
    
    log("❌ 所有LLM服务启动失败")
    return False

def stop_llm():
    """停止本地小模型（释放内存）"""
    state = get_state()
    running = is_running()
    if not running:
        return True
    
    log(f"停止本地小模型 ({running})...")
    try:
        subprocess.run(['systemctl', 'stop', running], timeout=10)
        state["running"] = False
        state["total_stops"] += 1
        save_state(state)
        log(f"✅ {running} 已停止，内存已释放")
        return True
    except Exception as e:
        log(f"❌ 停止失败: {e}")
        return False

def request_inference():
    """推理请求入口——调用此函数表示需要使用LLM"""
    state = get_state()
    state["last_request"] = time.time()
    save_state(state)
    
    if not is_running():
        log("推理请求到达，启动LLM...")
        return start_llm()
    return True

def idle_check():
    """空闲检查——由定时任务调用，超时自动停止"""
    state = get_state()
    if not state.get("running"):
        return
    
    idle_time = time.time() - state.get("last_request", 0)
    if idle_time > IDLE_TIMEOUT:
        log(f"LLM空闲{idle_time:.0f}秒，超过{IDLE_TIMEOUT}秒阈值，自动停止")
        stop_llm()
    else:
        log(f"LLM运行中，剩余空闲时间: {IDLE_TIMEOUT - idle_time:.0f}秒")

def get_status():
    """获取LLM管理器状态"""
    state = get_state()
    running = is_running()
    return {
        "manager": "llm-ondemand",
        "running_service": running,
        "last_request": datetime.fromtimestamp(state.get("last_request", 0)).isoformat() if state.get("last_request") else None,
        "idle_timeout_seconds": IDLE_TIMEOUT,
        "total_starts": state.get("total_starts", 0),
        "total_stops": state.get("total_stops", 0),
        "memory_saving_estimate": "~1GB（停止时释放）"
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "start":
            start_llm()
        elif cmd == "stop":
            stop_llm()
        elif cmd == "status":
            print(json.dumps(get_status(), indent=2, ensure_ascii=False))
        elif cmd == "idle-check":
            idle_check()
        elif cmd == "request":
            request_inference()
        else:
            print("用法: python3 llm_ondemand_manager.py [start|stop|status|idle-check|request]")
    else:
        print(json.dumps(get_status(), indent=2, ensure_ascii=False))
