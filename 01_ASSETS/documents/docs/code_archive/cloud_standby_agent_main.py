#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云端备用智能体 v1.0.0
Cloud Standby Agent for ZONGYUAN-ROOT
"""

import os
import sys
import json
import time
import signal
import logging
import subprocess
from datetime import datetime
from logging.handlers import RotatingFileHandler

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from modules import self_healing

os.makedirs(config.LOG_DIR, exist_ok=True)
os.makedirs(config.DATA_DIR, exist_ok=True)

logger = logging.getLogger("cloud_standby_agent")
logger.setLevel(getattr(logging, config.LOG_LEVEL))
handler = RotatingFileHandler(
    os.path.join(config.LOG_DIR, "agent.log"),
    maxBytes=config.LOG_MAX_SIZE,
    backupCount=config.LOG_BACKUP_COUNT
)
fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(fmt)
logger.addHandler(handler)
console_handler = logging.StreamHandler()
console_handler.setFormatter(fmt)
logger.addHandler(console_handler)


class AgentState:
    def __init__(self):
        self.mode = "assistant"
        self.running = True
        self.last_heartbeat = 0
        self.last_central_heartbeat = time.time()
        self.commands_executed = 0
        self.commands_failed = 0
        self.alerts_sent = 0
        self.start_time = time.time()

    def to_dict(self):
        return {
            "agent_name": config.AGENT_NAME,
            "agent_version": config.AGENT_VERSION,
            "agent_id": config.AGENT_ID,
            "mode": self.mode,
            "running": self.running,
            "uptime_seconds": int(time.time() - self.start_time),
            "last_heartbeat": datetime.fromtimestamp(self.last_heartbeat).isoformat() if self.last_heartbeat else None,
            "last_central_heartbeat": datetime.fromtimestamp(self.last_central_heartbeat).isoformat(),
            "commands_executed": self.commands_executed,
            "commands_failed": self.commands_failed,
            "alerts_sent": self.alerts_sent,
            "did": config.DID,
            "trace_id": config.TRACE_ID,
        }

    def save(self):
        try:
            with open(config.STATE_FILE, 'w') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("保存状态失败: %s", e)


state = AgentState()


def signal_handler(signum, frame):
    logger.info("收到信号 %s，正在优雅退出...", signum)
    state.running = False
    state.save()
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def report_truth(key, value, category="status", extra=None):
    try:
        data = {
            "key": key,
            "value": value,
            "node_id": config.AGENT_NAME,
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "did": config.DID,
            "trace_id": config.TRACE_ID,
        }
        if extra:
            data.update(extra)
        resp = requests.post(
            config.GATEWAY_BASE_URL + config.GATEWAY_REPORT_ENDPOINT,
            json=data,
            timeout=10
        )
        return resp.status_code == 200
    except Exception as e:
        logger.error("上报真值异常: %s", e)
        return False


def get_pending_commands():
    try:
        resp = requests.get(
            config.GATEWAY_BASE_URL + config.GATEWAY_TRUTHS_ENDPOINT,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            truths = data.get("truths", [])
            return [t for t in truths if t.startswith("COMMAND.CENTRAL.")]
        return []
    except Exception as e:
        logger.error("获取指令异常: %s", e)
        return []


def get_truth_detail(key):
    try:
        resp = requests.get(
            config.GATEWAY_BASE_URL + "/api/truth/" + key,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            # 适配9120返回格式: {"status":"ok","truth":{...}}
            if "truth" in data:
                truth = data["truth"]
                # 统一字段名: truth_key -> key, truth_value -> value
                return {
                    "key": truth.get("truth_key", ""),
                    "value": truth.get("truth_value", ""),
                    "category": truth.get("category", ""),
                    "node_id": truth.get("node_id", ""),
                    "exec_command": truth.get("exec_command", truth.get("truth_value", "")),
                    "exec_timeout": truth.get("exec_timeout", 60),
                    "risk_level": truth.get("risk_level", "low"),
                    "approved_by": truth.get("approved_by", ""),
                }
            return data
        return None
    except Exception as e:
        logger.error("获取真值详情异常: %s", e)
        return None


# 已处理指令管理
processed_commands = set()

def load_processed_commands():
    global processed_commands
    try:
        processed_file = os.path.join(config.DATA_DIR, "processed_commands.json")
        if os.path.exists(processed_file):
            with open(processed_file, 'r') as f:
                processed_commands = set(json.load(f))
            logger.info("已加载 %d 条已处理指令记录", len(processed_commands))
    except Exception as e:
        logger.error("加载已处理指令失败: %s", e)

def save_processed_commands():
    global processed_commands
    try:
        if len(processed_commands) > 500:
            processed_commands = set(list(processed_commands)[-500:])
        processed_file = os.path.join(config.DATA_DIR, "processed_commands.json")
        with open(processed_file, 'w') as f:
            json.dump(list(processed_commands), f)
    except Exception as e:
        logger.error("保存已处理指令失败: %s", e)

def is_command_processed(cmd_key):
    return cmd_key in processed_commands

def mark_command_processed(cmd_key):
    global processed_commands
    processed_commands.add(cmd_key)
    save_processed_commands()


def is_command_whitelisted(command):
    cmd_lower = command.strip().lower()
    for prefix in config.COMMAND_WHITELIST:
        if cmd_lower.startswith(prefix.lower()):
            return True
    return False


def is_high_risk(command):
    cmd_lower = command.strip().lower()
    for pattern in config.HIGH_RISK_PATTERNS:
        if pattern.lower() in cmd_lower:
            return True
    return False


def verify_command_signature(command_data):
    return command_data.get("approved_by") == "central-brain"


def execute_command(command, timeout=60):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "exit_code": -1, "stdout": "", "stderr": "命令执行超时（%d秒）" % timeout}
    except Exception as e:
        return {"success": False, "exit_code": -2, "stdout": "", "stderr": str(e)}


def process_command(command_key):
    if is_command_processed(command_key):
        logger.debug("指令已处理，跳过: %s", command_key)
        return True
    logger.info("处理指令: %s", command_key)
    detail = get_truth_detail(command_key)
    if not detail:
        logger.warning("无法获取指令详情: %s", command_key)
        mark_command_processed(command_key)
        return False

    exec_command = detail.get("exec_command") or detail.get("value", "")
    # 支持从value中解析EXEC:前缀的命令
    if exec_command and exec_command.startswith("EXEC:"):
        exec_command = exec_command[5:].strip()
    if not exec_command:
        logger.warning("指令没有可执行内容: %s", command_key)
        mark_command_processed(command_key)
        return False

    if not is_command_whitelisted(exec_command):
        logger.warning("命令不在白名单中，拒绝执行: %s", exec_command[:100])
        report_truth(
            "RESULT.CLOUD." + command_key.replace("COMMAND.CENTRAL.", ""),
            "命令不在白名单中，拒绝执行: " + exec_command[:100],
            category="execution_result",
            extra={"status": "rejected", "reason": "not_whitelisted"}
        )
        mark_command_processed(command_key)
        return False

    if is_high_risk(exec_command) and not verify_command_signature(detail):
        logger.warning("高风险命令未经中枢审批，拒绝执行: %s", exec_command[:100])
        report_truth(
            "RESULT.CLOUD." + command_key.replace("COMMAND.CENTRAL.", ""),
            "高风险命令未经中枢审批，拒绝执行: " + exec_command[:100],
            category="execution_result",
            extra={"status": "rejected", "reason": "high_risk_not_approved"}
        )
        mark_command_processed(command_key)
        return False

    timeout = detail.get("exec_timeout", config.COMMAND_TIMEOUT)
    logger.info("执行命令: %s (超时: %ss)", exec_command[:100], timeout)
    result = execute_command(exec_command, timeout)

    result_key = "RESULT.CLOUD." + command_key.replace("COMMAND.CENTRAL.", "")
    report_truth(
        result_key,
        "命令执行" + ("成功" if result["success"] else "失败") + "，退出码: " + str(result["exit_code"]),
        category="execution_result",
        extra={
            "status": "success" if result["success"] else "failed",
            "command_key": command_key,
            "exit_code": result["exit_code"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "executed_at": datetime.now().isoformat(),
            "agent_version": config.AGENT_VERSION,
        }
    )

    if result["success"]:
        state.commands_executed += 1
        logger.info("指令执行成功: %s", command_key)
    else:
        state.commands_failed += 1
        logger.warning("指令执行失败: %s - %s", command_key, result["stderr"][:100])

    # 标记为已处理（无论成功失败，避免重复处理）
    mark_command_processed(command_key)

    return result["success"]


def get_system_status():
    status = {}
    try:
        result = execute_command("free -m | head -2 | tail -1 | awk '{print $2,$3,$7}'")
        if result["success"]:
            parts = result["stdout"].strip().split()
            if len(parts) >= 3:
                status["memory_total_mb"] = int(parts[0])
                status["memory_used_mb"] = int(parts[1])
                status["memory_available_mb"] = int(parts[2])
                status["memory_usage_percent"] = round(int(parts[1]) / int(parts[0]) * 100, 1)

        result = execute_command("df -h / | tail -1 | awk '{print $2,$3,$4,$5}'")
        if result["success"]:
            parts = result["stdout"].strip().split()
            if len(parts) >= 4:
                status["disk_total"] = parts[0]
                status["disk_used"] = parts[1]
                status["disk_available"] = parts[2]
                status["disk_usage_percent"] = parts[3]

        result = execute_command("cat /proc/loadavg | awk '{print $1,$2,$3}'")
        if result["success"]:
            parts = result["stdout"].strip().split()
            if len(parts) >= 3:
                status["load_1m"] = float(parts[0])
                status["load_5m"] = float(parts[1])
                status["load_15m"] = float(parts[2])

        result = execute_command("uptime -p")
        if result["success"]:
            status["uptime"] = result["stdout"].strip()

        result = execute_command("ss -tnp | grep :22 | wc -l")
        if result["success"]:
            status["ssh_connections"] = int(result["stdout"].strip())

        services = ["nginx", "sshd"]
        service_status = {}
        for svc in services:
            result = execute_command("systemctl is-active " + svc)
            service_status[svc] = result["stdout"].strip() if result["success"] else "unknown"
        status["services"] = service_status
    except Exception as e:
        logger.error("获取系统状态异常: %s", e)
    return status


def send_heartbeat():
    state.last_heartbeat = time.time()
    heartbeat_key = "HEARTBEAT.CLOUD_AGENT." + datetime.now().strftime("%Y%m%d%H%M")
    report_truth(
        heartbeat_key,
        "云端备用智能体心跳，模式: %s，运行时长: %d秒" % (state.mode, int(time.time() - state.start_time)),
        category="heartbeat",
        extra=state.to_dict()
    )


def report_full_status():
    system_status = get_system_status()
    full_status = {
        "agent": state.to_dict(),
        "system": system_status,
        "timestamp": datetime.now().isoformat(),
    }
    report_truth(
        "STATUS.CLOUD_AGENT.CURRENT",
        "云端备用智能体完整状态，模式: %s，内存: %s%%，磁盘: %s" % (
            state.mode,
            system_status.get("memory_usage_percent", "?"),
            system_status.get("disk_usage_percent", "?")
        ),
        category="status",
        extra=full_status
    )
    logger.info("完整状态已上报")


def check_central_heartbeat():
    try:
        resp = requests.get(
            config.GATEWAY_BASE_URL + config.GATEWAY_TRUTHS_ENDPOINT,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            truths = data.get("truths", [])
            central_heartbeats = [t for t in truths if "HEARTBEAT.CENTRAL" in t or "CENTRAL_BRAIN" in t]
            if central_heartbeats:
                state.last_central_heartbeat = time.time()
                return True
    except Exception as e:
        logger.error("检查中枢心跳异常: %s", e)

    offline_time = time.time() - state.last_central_heartbeat
    if offline_time > config.CENTRAL_OFFLINE_THRESHOLD:
        if state.mode != "takeover":
            logger.warning("中枢智能体失联超过%.0f秒，切换到接管模式", offline_time)
            state.mode = "takeover"
            report_truth(
                "ALERT.CLOUD_AGENT.CENTRAL_OFFLINE",
                "中枢智能体失联超过%d秒，云端备用智能体已切换到接管模式" % config.CENTRAL_OFFLINE_THRESHOLD,
                category="alert",
                extra={"offline_seconds": int(offline_time), "mode": "takeover"}
            )
            state.alerts_sent += 1
        return False
    else:
        if state.mode == "takeover":
            logger.info("中枢智能体已恢复，切回辅助模式")
            state.mode = "assistant"
            report_truth(
                "STATUS.CLOUD_AGENT.CENTRAL_RECOVERED",
                "中枢智能体已恢复，云端备用智能体切回辅助模式，接管期间执行了%d条指令" % state.commands_executed,
                category="status",
                extra={"mode": "assistant", "commands_during_takeover": state.commands_executed}
            )
        return True


def main_loop():
    logger.info("=" * 60)
    logger.info("云端备用智能体启动 v%s", config.AGENT_VERSION)
    logger.info("Agent ID: %s", config.AGENT_ID)
    logger.info("模式: %s", state.mode)
    logger.info("9120网关: %s", config.GATEWAY_BASE_URL)
    logger.info("=" * 60)

    load_processed_commands()
    send_heartbeat()
    report_full_status()

    last_command_poll = 0
    last_heartbeat = 0
    last_status_report = 0
    last_healing_check = 0
    HEALING_INTERVAL = 300  # 5分钟自愈检测一次

    while state.running:
        try:
            now = time.time()

            if now - last_command_poll >= config.COMMAND_POLL_INTERVAL:
                last_command_poll = now
                commands = get_pending_commands()
                if commands:
                    logger.info("发现 %d 条待执行指令", len(commands))
                    for cmd_key in commands[-config.MAX_COMMAND_QUEUE:]:
                        try:
                            process_command(cmd_key)
                        except Exception as e:
                            logger.error("处理指令异常 %s: %s", cmd_key, e)
                        time.sleep(1)

            if now - last_heartbeat >= config.HEARTBEAT_INTERVAL:
                last_heartbeat = now
                send_heartbeat()

            if now - last_status_report >= config.STATUS_REPORT_INTERVAL:
                last_status_report = now
                report_full_status()

            # 自愈检测：每5分钟执行一次核心服务健康检查+自动修复
            if now - last_healing_check >= HEALING_INTERVAL:
                last_healing_check = now
                try:
                    logger.info("开始自愈检测周期...")
                    healing_report = self_healing.run_healing_cycle()
                    issues_count = len(healing_report.get("issues_found", []))
                    fixes_count = len(healing_report.get("fixes_executed", []))
                    failed_count = len(healing_report.get("fixes_failed", []))
                    
                    logger.info("自愈检测完成: 发现%d个问题, 自动修复%d个, 失败%d个", 
                                issues_count, fixes_count, failed_count)
                    
                    # 自愈结果上报9120
                    healing_key = "HEALING.CLOUD_AGENT." + datetime.now().strftime("%Y%m%d%H%M")
                    healing_value = "云端智能体自愈检测: 发现%d问题, 自动修复%d, 失败%d | 问题: %s | 修复: %s | 失败: %s" % (
                        issues_count, fixes_count, failed_count,
                        "; ".join(healing_report.get("issues_found", []))[:200] if healing_report.get("issues_found") else "无",
                        "; ".join(healing_report.get("fixes_executed", []))[:200] if healing_report.get("fixes_executed") else "无",
                        "; ".join(healing_report.get("fixes_failed", []))[:200] if healing_report.get("fixes_failed") else "无"
                    )
                    report_truth(
                        healing_key,
                        healing_value,
                        category="self_healing",
                        extra={
                            "issues_found": issues_count,
                            "fixes_executed": fixes_count,
                            "fixes_failed": failed_count,
                            "duration_seconds": healing_report.get("duration_seconds", 0)
                        }
                    )
                except Exception as e:
                    logger.error("自愈检测异常: %s", e)

            check_central_heartbeat()
            state.save()
            time.sleep(5)

        except Exception as e:
            logger.error("主循环异常: %s", e)
            time.sleep(10)

    logger.info("云端备用智能体已退出")


if __name__ == "__main__":
    main_loop()
