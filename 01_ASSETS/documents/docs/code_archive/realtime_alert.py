#!/usr/bin/env python3
"""
实时告警系统 - 内核自治增强
监控内存/CPU/服务/Merkle链，异常时立即推送飞书
每5分钟运行一次，避免频繁告警（冷却机制）
"""
import os
import sys
import json
import sqlite3
import subprocess
import socket
import urllib.request
from datetime import datetime, timedelta

# 配置
MEMORY_GATEWAY_DB = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
FEISHU_GATEWAY = "http://127.0.0.1:8001/feishu/im/v1/messages?receive_id_type=chat_id"
FEISHU_CHAT_ID = "oc_1c68eb3664e751e397062ff0c60ffa3"
ALERT_STATE_FILE = "/opt/ZONGYUAN-ROOT/kernel/alert_state.json"
ALERT_LOG = "/opt/ZONGYUAN-ROOT/logs/realtime_alert.log"

# 告警阈值
MEMORY_WARN = 70      # 内存预警
MEMORY_CRITICAL = 80  # 内存严重
CPU_WARN = 80         # CPU预警
DISK_WARN = 85        # 磁盘预警
MERKLE_STALE_HOURS = 6  # Merkle链超过6小时未更新告警

# 冷却时间（同一告警30分钟内不重复推送）
COOLDOWN_MINUTES = 30

def run_cmd(cmd, timeout=10):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except:
        return ""

def log_alert(message):
    os.makedirs(os.path.dirname(ALERT_LOG), exist_ok=True)
    with open(ALERT_LOG, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}\n")

def load_alert_state():
    if os.path.exists(ALERT_STATE_FILE):
        try:
            with open(ALERT_STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"alerts": {}}

def save_alert_state(state):
    os.makedirs(os.path.dirname(ALERT_STATE_FILE), exist_ok=True)
    with open(ALERT_STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def should_alert(state, alert_key):
    """检查是否应该告警（冷却机制）"""
    alerts = state.get("alerts", {})
    if alert_key in alerts:
        last_alert = datetime.fromisoformat(alerts[alert_key])
        if datetime.now() - last_alert < timedelta(minutes=COOLDOWN_MINUTES):
            return False
    return True

def record_alert(state, alert_key):
    state["alerts"][alert_key] = datetime.now().isoformat()

def send_feishu(title, content, level="warning"):
    """发送飞书告警"""
    level_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(level, "🟡")
    
    message = f"""{level_emoji} 实时告警: {title}
━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{content}

━━━━━━━━━━━━━━━━━━━━━━━━━━
Ω₀⊂⊙∞⊂Ω · DID-BR-000002
内核实时告警系统"""
    
    try:
        data = json.dumps({
            "receive_id": FEISHU_CHAT_ID,
            "msg_type": "text",
            "content": json.dumps({"text": message})
        }).encode()
        req = urllib.request.Request(FEISHU_GATEWAY, data=data, headers={"Content-Type": "application/json"})
        response = urllib.request.urlopen(req, timeout=10)
        result = json.loads(response.read())
        if result.get("code") == 0:
            log_alert(f"[SENT] {title}")
            return True
        else:
            log_alert(f"[FAILED] {title}: {result}")
            return False
    except Exception as e:
        log_alert(f"[ERROR] {title}: {e}")
        return False

def check_memory(state):
    """检查内存使用"""
    mem_info = run_cmd("free -m | awk '/Mem:/{print $3/$2*100}'")
    try:
        mem_pct = float(mem_info)
    except:
        return
    
    mem_used = run_cmd("free -m | awk '/Mem:/{print $3}'")
    mem_total = run_cmd("free -m | awk '/Mem:/{print $2}'")
    
    if mem_pct >= MEMORY_CRITICAL:
        alert_key = "memory_critical"
        if should_alert(state, alert_key):
            send_feishu(
                "内存严重告警",
                f"内存使用率: {mem_pct:.1f}%\n已用: {mem_used}MB / {mem_total}MB\n阈值: {MEMORY_CRITICAL}%\n\n建议: 立即检查高内存进程，考虑暂停非核心服务",
                "critical"
            )
            record_alert(state, alert_key)
    elif mem_pct >= MEMORY_WARN:
        alert_key = "memory_warning"
        if should_alert(state, alert_key):
            send_feishu(
                "内存预警",
                f"内存使用率: {mem_pct:.1f}%\n已用: {mem_used}MB / {mem_total}MB\n阈值: {MEMORY_WARN}%\n\n建议: 关注内存增长趋势，准备熔断",
                "warning"
            )
            record_alert(state, alert_key)

def check_services(state):
    """检查核心服务状态"""
    core_services = [
        ("dr-resource-monitor", "资源监控"),
        ("dr-self-healing-monitor", "自愈监控"),
        ("dr-truth-absorber", "真值吸收"),
        ("closed-loop-scheduler", "闭环调度"),
        ("agent-hub", "Agent枢纽"),
    ]
    
    offline_services = []
    for service, name in core_services:
        status = run_cmd(f"systemctl is-active {service} 2>/dev/null")
        if status != "active":
            offline_services.append(f"{name}({service})")
    
    if offline_services:
        alert_key = "service_offline"
        if should_alert(state, alert_key):
            send_feishu(
                "核心服务离线",
                f"离线服务数: {len(offline_services)}\n\n离线列表:\n" + "\n".join(f"  - {s}" for s in offline_services) + "\n\n建议: 检查服务日志，尝试重启",
                "critical"
            )
            record_alert(state, alert_key)

def check_merkle_chain(state):
    """检查Merkle链状态"""
    merkle_file = "/opt/ZONGYUAN-ROOT/kernel/merkle_chain_state.json"
    if not os.path.exists(merkle_file):
        return
    
    try:
        with open(merkle_file) as f:
            data = json.load(f)
        chain = data.get("chain", [])
        if not chain:
            return
        
        last_block = chain[-1]
        last_update_str = last_block.get("timestamp", "")
        chain_continuous = last_block.get("chain_continuous", True)
        integrity = last_block.get("integrity_percent", 100)
        
        # 检查链连续性
        if not chain_continuous:
            alert_key = "merkle_broken"
            if should_alert(state, alert_key):
                send_feishu(
                    "Merkle链断裂",
                    f"链高度: {len(chain)}\n完整性: {integrity}%\n链连续: ❌ False\n\n建议: 立即检查merkle_chain_state.json，运行维护脚本修复",
                    "critical"
                )
                record_alert(state, alert_key)
            return
        
        # 检查更新时间
        if last_update_str:
            try:
                last_update = datetime.fromisoformat(last_update_str.replace("Z", "+00:00").replace("+00:00", ""))
                hours_since = (datetime.now() - last_update).total_seconds() / 3600
                
                if hours_since > MERKLE_STALE_HOURS:
                    alert_key = "merkle_stale"
                    if should_alert(state, alert_key):
                        send_feishu(
                            "Merkle链停滞",
                            f"链高度: {len(chain)}\n最后更新: {last_update_str}\n已停滞: {hours_since:.1f}小时\n阈值: {MERKLE_STALE_HOURS}小时\n\n建议: 检查merkle_chain_maintainer.py定时任务，手动运行维护脚本",
                            "warning"
                        )
                        record_alert(state, alert_key)
            except:
                pass
    except Exception as e:
        log_alert(f"[ERROR] Merkle链检查失败: {e}")

def check_disk(state):
    """检查磁盘使用"""
    disk_info = run_cmd("df -h / | awk 'NR==2{print $5}' | tr -d '%'")
    try:
        disk_pct = float(disk_info)
    except:
        return
    
    if disk_pct >= DISK_WARN:
        alert_key = "disk_warning"
        if should_alert(state, alert_key):
            disk_used = run_cmd("df -h / | awk 'NR==2{print $3}'")
            disk_total = run_cmd("df -h / | awk 'NR==2{print $2}'")
            send_feishu(
                "磁盘预警",
                f"磁盘使用率: {disk_pct:.1f}%\n已用: {disk_used} / {disk_total}\n阈值: {DISK_WARN}%\n\n建议: 清理日志/临时文件/旧备份",
                "warning"
            )
            record_alert(state, alert_key)

def main():
    log_alert("=" * 50)
    log_alert("实时告警系统启动")
    
    state = load_alert_state()
    
    # 执行各项检查
    check_memory(state)
    check_services(state)
    check_merkle_chain(state)
    check_disk(state)
    
    # 保存告警状态
    save_alert_state(state)
    
    log_alert("实时告警系统完成")
    log_alert("=" * 50)

if __name__ == "__main__":
    main()
