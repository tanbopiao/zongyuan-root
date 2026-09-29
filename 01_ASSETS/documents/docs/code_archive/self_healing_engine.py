#!/usr/bin/env python3
"""
火斗云智AIOS · 元内核统一自愈算子 V1.0
整合6个治理模块的自愈能力：检测→诊断→修复→验证→上报
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
零成本: 仅使用系统原生命令，不产生额外费用
"""

import os
import json
import time
import subprocess
import hashlib
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

# ============================================================
# 配置：自愈阈值（可从内核元规则覆盖）
# ============================================================
DEFAULT_THRESHOLDS = {
    "memory_warn_pct": 65,       # 内存告警阈值
    "memory_heal_pct": 75,       # 内存自愈阈值（释放页缓存）
    "disk_warn_pct": 80,         # 磁盘告警阈值
    "disk_critical_pct": 90,     # 磁盘紧急阈值
    "python_proc_warn": 60,      # Python进程告警阈值
    "python_proc_critical": 100, # Python进程紧急阈值
    "cpu_load_warn": 4.0,        # CPU负载告警（1分钟）
    "service_retry_max": 3,      # 服务异常重试次数
    "heal_cooldown_sec": 300,    # 同类自愈冷却时间（5分钟）
}

CORE_SERVICES = [
    {"name": "记忆网关", "port": 9120, "url": "http://localhost:9120/api/status", "critical": True, "location": "remote", "remote_url": "https://www.huodouai.com/api/report/status"},
    {"name": "知识图谱", "port": 8080, "url": "http://localhost:8080/health", "critical": True, "location": "local"},
    {"name": "向量服务", "port": 8014, "url": "http://localhost:8014/health", "critical": False, "location": "remote"},
    {"name": "飞书审批回调", "port": 8060, "url": "http://localhost:8060/health", "critical": False, "location": "remote"},
    {"name": "算子调度", "port": 8072, "url": "http://localhost:8072/health", "critical": False, "location": "remote"},
    {"name": "智能体工作台", "port": 8765, "url": "http://localhost:8765/health", "critical": False, "location": "remote"},
]

# ============================================================
# 数据结构
# ============================================================
@dataclass
class Alert:
    id: str
    timestamp: str
    level: str          # info / warn / critical
    category: str       # memory / disk / cpu / process / service / chain
    message: str
    value: str = ""
    threshold: str = ""
    healed: bool = False
    heal_action: str = ""
    heal_timestamp: str = ""

@dataclass
class HealAction:
    id: str
    timestamp: str
    alert_id: str
    action: str
    result: str         # success / failed / skipped
    detail: str = ""
    cooldown_until: float = 0

@dataclass
class HealthSnapshot:
    timestamp: str
    cpu_load: List[float]
    memory_total_mb: int
    memory_used_mb: int
    memory_pct: float
    disk_total_gb: float
    disk_used_gb: float
    disk_pct: float
    python_proc_count: int
    services: List[Dict]
    alerts: List[Dict]
    overall_status: str  # healthy / warning / critical

# ============================================================
# 内核路径
# ============================================================
KERNEL_PATH = os.path.expanduser("~/.zongyuan_root/kernel/kernel_state.json")
ALERT_LOG_PATH = os.path.expanduser("~/.zongyuan_root/kernel/healing_alerts.json")
HEAL_LOG_PATH = os.path.expanduser("~/.zongyuan_root/kernel/healing_actions.json")
SNAPSHOT_PATH = os.path.expanduser("~/.zongyuan_root/kernel/health_snapshots.json")

def ensure_dirs():
    os.makedirs(os.path.dirname(KERNEL_PATH), exist_ok=True)

def load_json(path, default=None):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except: pass
    return default if default is not None else {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
# 第一部分：系统健康检测
# ============================================================
def check_cpu() -> List[float]:
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().strip().split()
            return [float(parts[0]), float(parts[1]), float(parts[2])]
    except:
        return [0.0, 0.0, 0.0]

def check_memory() -> tuple:
    try:
        r = subprocess.run(["free", "-m"], capture_output=True, text=True)
        for line in r.stdout.split("\n"):
            if line.startswith("Mem:"):
                p = line.split()
                total, used = int(p[1]), int(p[2])
                return total, used, round(used/total*100, 1)
    except: pass
    return 0, 0, 0.0

def check_disk() -> tuple:
    try:
        r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
        lines = r.stdout.strip().split("\n")
        if len(lines) > 1:
            p = lines[1].split()
            total = float(p[1].replace("G","").replace("M",""))
            used = float(p[2].replace("G","").replace("M",""))
            pct = int(p[4].replace("%",""))
            return total, used, pct
    except: pass
    return 0.0, 0.0, 0

def check_processes() -> int:
    try:
        r = subprocess.run(["bash", "-c", "ps aux | grep python | grep -v grep | wc -l"],
                          capture_output=True, text=True)
        return int(r.stdout.strip())
    except: return 0

def check_services() -> List[Dict]:
    results = []
    for svc in CORE_SERVICES:
        status = "unknown"
        http_code = 0
        location = svc.get("location", "local")

        if location == "remote" and "remote_url" in svc:
            # 云端服务：检查远程URL
            try:
                r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                   "--max-time", "5", svc["remote_url"]],
                                  capture_output=True, text=True)
                http_code = int(r.stdout.strip() or "0")
                status = "healthy" if http_code == 200 else f"remote_http_{http_code}"
                listening = http_code == 200
            except:
                status = "remote_unreachable"
                listening = False
        else:
            # 本地服务：检查端口+HTTP
            try:
                r = subprocess.run(["ss", "-tln"], capture_output=True, text=True)
                listening = f":{svc['port']}" in r.stdout
            except:
                listening = False
            if listening:
                try:
                    r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                       "--max-time", "3", svc["url"]],
                                      capture_output=True, text=True)
                    http_code = int(r.stdout.strip() or "0")
                    status = "healthy" if http_code == 200 else f"http_{http_code}"
                except:
                    status = "port_open_no_http"
            else:
                status = "not_listening"

        results.append({
            "name": svc["name"],
            "port": svc["port"],
            "location": location,
            "listening": listening,
            "http_code": http_code,
            "status": status,
            "critical": svc["critical"]
        })
    return results

# ============================================================
# 第二部分：告警生成
# ============================================================
def generate_alerts(snapshot: HealthSnapshot, thresholds: Dict) -> List[Alert]:
    alerts = []
    ts = snapshot.timestamp
    aid = lambda cat: hashlib.md5(f"{cat}_{ts}".encode()).hexdigest()[:12]

    # 内存
    if snapshot.memory_pct >= thresholds["memory_heal_pct"]:
        alerts.append(Alert(id=aid("mem_crit"), timestamp=ts, level="critical",
            category="memory", message=f"内存使用率超过自愈阈值{thresholds['memory_heal_pct']}%",
            value=f"{snapshot.memory_pct}%", threshold=f"{thresholds['memory_heal_pct']}%"))
    elif snapshot.memory_pct >= thresholds["memory_warn_pct"]:
        alerts.append(Alert(id=aid("mem_warn"), timestamp=ts, level="warn",
            category="memory", message=f"内存使用率超过告警阈值{thresholds['memory_warn_pct']}%",
            value=f"{snapshot.memory_pct}%", threshold=f"{thresholds['memory_warn_pct']}%"))

    # 磁盘
    if snapshot.disk_pct >= thresholds["disk_critical_pct"]:
        alerts.append(Alert(id=aid("disk_crit"), timestamp=ts, level="critical",
            category="disk", message=f"磁盘使用率超过紧急阈值{thresholds['disk_critical_pct']}%",
            value=f"{snapshot.disk_pct}%", threshold=f"{thresholds['disk_critical_pct']}%"))
    elif snapshot.disk_pct >= thresholds["disk_warn_pct"]:
        alerts.append(Alert(id=aid("disk_warn"), timestamp=ts, level="warn",
            category="disk", message=f"磁盘使用率超过告警阈值{thresholds['disk_warn_pct']}%",
            value=f"{snapshot.disk_pct}%", threshold=f"{thresholds['disk_warn_pct']}%"))

    # CPU
    if snapshot.cpu_load[0] >= thresholds["cpu_load_warn"]:
        alerts.append(Alert(id=aid("cpu_warn"), timestamp=ts, level="warn",
            category="cpu", message=f"CPU 1分钟负载超过阈值{thresholds['cpu_load_warn']}",
            value=f"{snapshot.cpu_load[0]}", threshold=f"{thresholds['cpu_load_warn']}"))

    # 进程
    if snapshot.python_proc_count >= thresholds["python_proc_critical"]:
        alerts.append(Alert(id=aid("proc_crit"), timestamp=ts, level="critical",
            category="process", message=f"Python进程数超过紧急阈值{thresholds['python_proc_critical']}",
            value=str(snapshot.python_proc_count), threshold=str(thresholds["python_proc_critical"])))
    elif snapshot.python_proc_count >= thresholds["python_proc_warn"]:
        alerts.append(Alert(id=aid("proc_warn"), timestamp=ts, level="warn",
            category="process", message=f"Python进程数超过告警阈值{thresholds['python_proc_warn']}",
            value=str(snapshot.python_proc_count), threshold=str(thresholds["python_proc_warn"])))

    # 服务
    for svc in snapshot.services:
        if svc["critical"] and svc["status"] != "healthy":
            level = "critical" if svc["critical"] else "warn"
            alerts.append(Alert(id=aid(f"svc_{svc['port']}"), timestamp=ts, level=level,
                category="service", message=f"核心服务异常: {svc['name']}({svc['port']}) - {svc['status']}",
                value=svc["status"], threshold="healthy"))

    return alerts

# ============================================================
# 第三部分：自愈动作执行
# ============================================================
def execute_heal(alert: Alert, thresholds: Dict) -> HealAction:
    ts = datetime.now().isoformat()
    hid = hashlib.md5(f"heal_{alert.id}_{ts}".encode()).hexdigest()[:12]
    action = HealAction(id=hid, timestamp=ts, alert_id=alert.id, action="", result="skipped")

    # 冷却检查
    heal_log = load_json(HEAL_LOG_PATH, [])
    now = time.time()
    for h in heal_log[-20:]:
        if h.get("alert_id") == alert.id and h.get("cooldown_until", 0) > now:
            action.result = "skipped"
            action.detail = f"冷却中，剩余{int(h['cooldown_until']-now)}秒"
            return action

    if alert.category == "memory" and alert.level == "critical":
        action.action = "drop_caches"
        try:
            subprocess.run(["sync"], check=True)
            subprocess.run(["bash", "-c", "echo 3 > /proc/sys/vm/drop_caches"], check=True)
            action.result = "success"
            action.detail = "已执行sync + drop_caches释放页缓存"
        except Exception as e:
            action.result = "failed"
            action.detail = str(e)

    elif alert.category == "disk" and alert.level in ("warn", "critical"):
        action.action = "clean_temp_files"
        try:
            cleaned = 0
            for tmpdir in ["/tmp", os.path.expanduser("~/.cache")]:
                if os.path.exists(tmpdir):
                    r = subprocess.run(["find", tmpdir, "-type", "f", "-atime", "+7", "-delete"],
                                      capture_output=True, text=True)
                    cleaned += 1
            action.result = "success"
            action.detail = f"已清理7天前临时文件"
        except Exception as e:
            action.result = "failed"
            action.detail = str(e)

    elif alert.category == "process" and alert.level == "critical":
        action.action = "kill_redundant_processes"
        try:
            # 只杀重复的非核心进程（这里只记录，不实际杀，避免误杀）
            action.result = "skipped"
            action.detail = "检测到冗余进程，需人工确认后清理（自动杀进程风险高）"
        except Exception as e:
            action.result = "failed"
            action.detail = str(e)

    elif alert.category == "service" and alert.level == "critical":
        action.action = "restart_service"
        # 服务重启需要知道systemd服务名，这里只记录建议
        action.result = "skipped"
        action.detail = f"建议重启服务: {alert.message}，需确认systemd服务名后执行"

    else:
        action.action = "monitor_only"
        action.result = "skipped"
        action.detail = "告警级别未达到自愈阈值，仅监控"

    action.cooldown_until = now + thresholds["heal_cooldown_sec"]
    return action

# ============================================================
# 第四部分：验证与上报
# ============================================================
def verify_heal(alert: Alert, action: HealAction) -> bool:
    """自愈后重新检测，验证问题是否解决"""
    if action.result != "success":
        return False
    time.sleep(2)  # 等待生效
    if alert.category == "memory":
        _, _, pct = check_memory()
        return pct < 70
    elif alert.category == "disk":
        _, _, pct = check_disk()
        return pct < 80
    return True

def update_kernel(snapshot: HealthSnapshot, alerts: List[Alert], actions: List[HealAction]):
    """更新内核状态：注册自愈模块、写入告警和自愈历史"""
    kernel = load_json(KERNEL_PATH)

    # 注册自愈模块
    modules = kernel.get("active_modules", [])
    module_names = [m.get("name", str(m)) if isinstance(m, dict) else str(m) for m in modules]
    if "self_healing_engine" not in module_names:
        modules.append({
            "name": "self_healing_engine",
            "version": "V1.0",
            "status": "active",
            "description": "元内核统一自愈算子 - 检测→诊断→修复→验证→上报闭环",
            "capabilities": ["health_monitor", "alert_generation", "auto_heal", "heal_verification", "alert_persistence"],
            "activated_at": datetime.now().isoformat()
        })
        kernel["active_modules"] = modules
        kernel["module_count"] = len(modules)

    # 写入自愈状态
    kernel["self_healing"] = {
        "last_check": snapshot.timestamp,
        "overall_status": snapshot.overall_status,
        "active_alerts": len([a for a in alerts if not a.healed]),
        "total_alerts_history": len(load_json(ALERT_LOG_PATH, [])),
        "total_heal_actions": len(load_json(HEAL_LOG_PATH, [])),
        "heal_success_rate": calculate_heal_rate(),
        "thresholds": DEFAULT_THRESHOLDS
    }

    save_json(KERNEL_PATH, kernel)

def calculate_heal_rate() -> float:
    actions = load_json(HEAL_LOG_PATH, [])
    if not actions:
        return 100.0
    success = sum(1 for a in actions if a.get("result") == "success")
    return round(success / len(actions) * 100, 1)

def persist_alerts(alerts: List[Alert]):
    log = load_json(ALERT_LOG_PATH, [])
    for a in alerts:
        log.append(asdict(a))
    # 保留最近500条
    if len(log) > 500:
        log = log[-500:]
    save_json(ALERT_LOG_PATH, log)

def persist_heal_actions(actions: List[HealAction]):
    log = load_json(HEAL_LOG_PATH, [])
    for a in actions:
        log.append(asdict(a))
    if len(log) > 500:
        log = log[-500:]
    save_json(HEAL_LOG_PATH, log)

def persist_snapshot(snapshot: HealthSnapshot):
    log = load_json(SNAPSHOT_PATH, [])
    log.append(asdict(snapshot))
    if len(log) > 100:
        log = log[-100:]
    save_json(SNAPSHOT_PATH, log)

# ============================================================
# 主流程
# ============================================================
def run_check(auto_heal=True):
    """执行一次完整的健康检测+自愈循环"""
    ensure_dirs()
    ts = datetime.now().isoformat()

    print("=" * 60)
    print("  火斗云智AIOS · 元内核统一自愈算子 V1.0")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 60)

    # 1. 检测
    print("\n[1/5] 系统健康检测...")
    cpu = check_cpu()
    mem_total, mem_used, mem_pct = check_memory()
    disk_total, disk_used, disk_pct = check_disk()
    proc_count = check_processes()
    services = check_services()

    snapshot = HealthSnapshot(
        timestamp=ts, cpu_load=cpu,
        memory_total_mb=mem_total, memory_used_mb=mem_used, memory_pct=mem_pct,
        disk_total_gb=disk_total, disk_used_gb=disk_used, disk_pct=disk_pct,
        python_proc_count=proc_count, services=services,
        alerts=[], overall_status="healthy"
    )

    print(f"  CPU: {cpu[0]}/{cpu[1]}/{cpu[2]}")
    print(f"  内存: {mem_used}M/{mem_total}M ({mem_pct}%)")
    print(f"  磁盘: {disk_used}G/{disk_total}G ({disk_pct}%)")
    print(f"  Python进程: {proc_count}个")
    for svc in services:
        icon = "✅" if svc["status"] == "healthy" else "⚠️"
        print(f"  {icon} {svc['name']}({svc['port']}): {svc['status']}")

    # 2. 告警
    print("\n[2/5] 告警生成...")
    thresholds = DEFAULT_THRESHOLDS.copy()
    # 从内核读取自定义阈值（如果有）
    kernel = load_json(KERNEL_PATH)
    if "self_healing" in kernel and "thresholds" in kernel["self_healing"]:
        thresholds.update(kernel["self_healing"]["thresholds"])

    alerts = generate_alerts(snapshot, thresholds)
    if alerts:
        for a in alerts:
            icon = "🔴" if a.level == "critical" else "🟡"
            print(f"  {icon} [{a.level.upper()}] {a.category}: {a.message}")
    else:
        print("  ✅ 无告警")

    # 确定整体状态
    if any(a.level == "critical" for a in alerts):
        snapshot.overall_status = "critical"
    elif alerts:
        snapshot.overall_status = "warning"
    snapshot.alerts = [asdict(a) for a in alerts]

    # 3. 自愈
    print("\n[3/5] 自愈动作执行...")
    actions = []
    if auto_heal and alerts:
        for alert in alerts:
            action = execute_heal(alert, thresholds)
            actions.append(action)
            icon = "✅" if action.result == "success" else ("⏭️" if action.result == "skipped" else "❌")
            print(f"  {icon} {action.action}: {action.detail}")
            # 验证
            if action.result == "success":
                healed = verify_heal(alert, action)
                if healed:
                    alert.healed = True
                    alert.heal_action = action.action
                    alert.heal_timestamp = datetime.now().isoformat()
                    print(f"     ↳ 验证通过，问题已解决")
                else:
                    print(f"     ↳ 验证未通过，问题仍存在")
    else:
        print("  无需自愈或已禁用自动自愈")

    # 4. 持久化
    print("\n[4/5] 持久化到内核...")
    persist_alerts(alerts)
    persist_heal_actions(actions)
    persist_snapshot(snapshot)
    update_kernel(snapshot, alerts, actions)
    print("  ✅ 告警日志、自愈日志、健康快照已写入内核")

    # 5. 汇总
    print("\n[5/5] 汇总报告")
    print(f"  整体状态: {snapshot.overall_status.upper()}")
    print(f"  活跃告警: {len([a for a in alerts if not a.healed])}个")
    print(f"  自愈动作: {len(actions)}次 (成功{sum(1 for a in actions if a.result=='success')}次)")
    print(f"  自愈成功率: {calculate_heal_rate()}%")
    print(f"  历史告警总数: {len(load_json(ALERT_LOG_PATH, []))}")
    print(f"  历史自愈总数: {len(load_json(HEAL_LOG_PATH, []))}")
    print("\n" + "=" * 60)

    return snapshot, alerts, actions

def daemon_mode(interval=300):
    """守护进程模式：每interval秒检测一次"""
    print(f"自愈算子守护模式启动，每{interval}秒检测一次 (Ctrl+C停止)")
    while True:
        try:
            run_check(auto_heal=True)
        except Exception as e:
            print(f"自愈循环异常: {e}")
        time.sleep(interval)

# ============================================================
# CLI入口
# ============================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="元内核统一自愈算子")
    parser.add_argument("--once", action="store_true", help="执行一次检测后退出")
    parser.add_argument("--daemon", action="store_true", help="守护进程模式")
    parser.add_argument("--interval", type=int, default=300, help="守护模式检测间隔(秒)")
    parser.add_argument("--no-heal", action="store_true", help="只检测不执行自愈")
    parser.add_argument("--status", action="store_true", help="查看自愈状态")
    args = parser.parse_args()

    if args.status:
        kernel = load_json(KERNEL_PATH)
        sh = kernel.get("self_healing", {})
        print(json.dumps(sh, ensure_ascii=False, indent=2))
    elif args.daemon:
        daemon_mode(args.interval)
    else:
        run_check(auto_heal=not args.no_heal)
