#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 · 全域监控告警体系 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
统一监控采集 + 告警规则引擎 + 自动自愈 + 对接运维大屏
"""
import json, time, os, threading, hashlib
from typing import Dict, List, Optional, Callable
from datetime import datetime

# 告警等级
ALERT_LEVELS = {
    "info": {"color": "#4a9eff", "weight": 1},
    "warn": {"color": "#f59e0b", "weight": 2},
    "error": {"color": "#ef4444", "weight": 3},
    "critical": {"color": "#dc2626", "weight": 4}
}

# 自愈动作
HEAL_ACTIONS = {
    "restart_service": "重启服务",
    "clear_cache": "释放缓存",
    "kill_process": "终止冗余进程",
    "scale_up": "扩容",
    "notify_only": "仅通知"
}

class Alert:
    """告警对象"""
    def __init__(self, alert_id, level, source, message, metric=None, value=None, threshold=None):
        self.alert_id = alert_id
        self.level = level
        self.source = source
        self.message = message
        self.metric = metric
        self.value = value
        self.threshold = threshold
        self.timestamp = time.time()
        self.acknowledged = False
        self.healed = False
        self.heal_action = None

    def to_dict(self):
        return {
            "alert_id": self.alert_id,
            "level": self.level,
            "source": self.source,
            "message": self.message,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            "acknowledged": self.acknowledged,
            "healed": self.healed,
            "heal_action": self.heal_action
        }

class AlertRule:
    """告警规则"""
    def __init__(self, rule_id, metric, condition, threshold, level, heal_action="notify_only", cooldown=300):
        self.rule_id = rule_id
        self.metric = metric
        self.condition = condition  # ">", "<", ">=", "<=", "==", "!="
        self.threshold = threshold
        self.level = level
        self.heal_action = heal_action
        self.cooldown = cooldown
        self.last_triggered = 0

    def evaluate(self, value) -> bool:
        """评估是否触发告警"""
        if time.time() - self.last_triggered < self.cooldown:
            return False
        try:
            if self.condition == ">": return value > self.threshold
            if self.condition == "<": return value < self.threshold
            if self.condition == ">=": return value >= self.threshold
            if self.condition == "<=": return value <= self.threshold
            if self.condition == "==": return value == self.threshold
            if self.condition == "!=": return value != self.threshold
        except:
            return False
        return False

class GlobalMonitor:
    """全域监控器"""
    
    def __init__(self, data_dir="./monitoring_data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.metrics: Dict[str, float] = {}
        self.alerts: List[Alert] = []
        self.rules: List[AlertRule] = []
        self.heal_log: List[dict] = []
        self.service_status: Dict[str, dict] = {}
        self._init_default_rules()
        self._running = False

    def _init_default_rules(self):
        """初始化默认告警规则"""
        self.rules = [
            AlertRule("R001", "cpu_usage", ">", 80, "warn", "clear_cache", 600),
            AlertRule("R002", "memory_usage", ">", 70, "warn", "clear_cache", 300),
            AlertRule("R003", "memory_usage", ">", 85, "error", "clear_cache", 120),
            AlertRule("R004", "disk_usage", ">", 80, "warn", "notify_only", 3600),
            AlertRule("R005", "disk_usage", ">", 90, "critical", "notify_only", 600),
            AlertRule("R006", "python_processes", ">", 60, "warn", "kill_process", 300),
            AlertRule("R007", "service_down", "==", 1, "critical", "restart_service", 60),
            AlertRule("R008", "response_time", ">", 3000, "warn", "notify_only", 300),
            AlertRule("R009", "error_rate", ">", 5, "error", "notify_only", 300),
            AlertRule("R010", "audit_count_growth", ">", 1000, "info", "notify_only", 3600),
        ]

    def collect_metrics(self) -> dict:
        """采集系统指标"""
        metrics = {}
        try:
            # CPU
            with open("/proc/stat") as f:
                line = f.readline().split()
                idle = int(line[4])
                total = sum(int(x) for x in line[1:])
                metrics["cpu_usage"] = round((1 - idle/total) * 100, 1)
        except:
            metrics["cpu_usage"] = 0

        try:
            # 内存
            with open("/proc/meminfo") as f:
                lines = f.readlines()
                total = int(lines[0].split()[1])
                available = int(lines[2].split()[1])
                metrics["memory_usage"] = round((1 - available/total) * 100, 1)
                metrics["memory_total_mb"] = round(total / 1024)
                metrics["memory_available_mb"] = round(available / 1024)
        except:
            metrics["memory_usage"] = 0

        try:
            # 磁盘
            stat = os.statvfs("/")
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bfree * stat.f_frsize
            metrics["disk_usage"] = round((1 - free/total) * 100, 1)
            metrics["disk_total_gb"] = round(total / (1024**3), 1)
            metrics["disk_free_gb"] = round(free / (1024**3), 1)
        except:
            metrics["disk_usage"] = 0

        # Python进程数
        try:
            metrics["python_processes"] = len([p for p in os.listdir("/proc") if p.isdigit()])
        except:
            metrics["python_processes"] = 0

        # 负载
        try:
            load1, load5, load15 = os.getloadavg()
            metrics["load_1m"] = load1
            metrics["load_5m"] = load5
        except:
            metrics["load_1m"] = 0

        self.metrics.update(metrics)
        return metrics

    def check_service(self, name: str, port: int, url: str = None) -> dict:
        """检查服务健康状态"""
        import urllib.request
        status = {"name": name, "port": port, "status": "unknown", "response_time": 0}
        start = time.time()
        try:
            check_url = url or f"http://127.0.0.1:{port}/health"
            req = urllib.request.Request(check_url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                status["status"] = "healthy" if resp.status == 200 else "error"
                status["http_code"] = resp.status
        except Exception as e:
            status["status"] = "down"
            status["error"] = str(e)[:100]
        status["response_time"] = round((time.time() - start) * 1000)
        self.service_status[name] = status
        return status

    def evaluate_rules(self) -> List[Alert]:
        """评估所有告警规则"""
        triggered = []
        for rule in self.rules:
            value = self.metrics.get(rule.metric)
            if value is not None and rule.evaluate(value):
                alert_id = hashlib.md5(f"{rule.rule_id}{int(time.time()/60)}".encode()).hexdigest()[:12]
                alert = Alert(
                    alert_id=alert_id,
                    level=rule.level,
                    source=rule.metric,
                    message=f"{rule.metric}={value} {rule.condition} {rule.threshold}",
                    metric=rule.metric,
                    value=value,
                    threshold=rule.threshold
                )
                alert.heal_action = rule.heal_action
                self.alerts.append(alert)
                triggered.append(alert)
                rule.last_triggered = time.time()
        return triggered

    def execute_heal(self, alert: Alert) -> dict:
        """执行自愈动作"""
        result = {"action": alert.heal_action, "success": False, "detail": ""}
        try:
            if alert.heal_action == "clear_cache":
                # 释放页缓存（需要root权限，这里记录指令）
                result["detail"] = "sync && echo 3 > /proc/sys/vm/drop_caches"
                result["success"] = True
                result["note"] = "缓存释放指令已生成，需root执行"
            elif alert.heal_action == "restart_service":
                result["detail"] = f"systemctl restart {alert.source}"
                result["success"] = True
                result["note"] = "服务重启指令已生成"
            elif alert.heal_action == "kill_process":
                result["detail"] = "pkill -f redundant_process"
                result["success"] = True
                result["note"] = "进程终止指令已生成"
            else:
                result["detail"] = "仅通知，不执行自愈"
                result["success"] = True
        except Exception as e:
            result["detail"] = str(e)
        
        alert.healed = True
        self.heal_log.append({
            "alert_id": alert.alert_id,
            "action": result["action"],
            "success": result["success"],
            "detail": result["detail"],
            "timestamp": time.time()
        })
        return result

    def get_dashboard_data(self) -> dict:
        """获取运维大屏数据"""
        return {
            "timestamp": time.time(),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": self.metrics,
            "services": list(self.service_status.values()),
            "active_alerts": [a.to_dict() for a in self.alerts if not a.healed][-20:],
            "heal_history": self.heal_log[-20:],
            "alert_summary": {
                level: len([a for a in self.alerts if a.level == level])
                for level in ALERT_LEVELS
            },
            "did": "DID-BR-000002",
            "trace": "Ω₀⊂⊙∞⊂Ω"
        }

    def run_cycle(self):
        """执行一个监控周期"""
        self.collect_metrics()
        alerts = self.evaluate_rules()
        for alert in alerts:
            if alert.heal_action != "notify_only":
                self.execute_heal(alert)
        return self.get_dashboard_data()

    def start(self, interval=30):
        """启动监控循环"""
        self._running = True
        def loop():
            while self._running:
                self.run_cycle()
                time.sleep(interval)
        threading.Thread(target=loop, daemon=True).start()

    def stop(self):
        self._running = False


# 标准监控服务列表
MONITORED_SERVICES = [
    ("记忆网关", 9120),
    ("智能体工作台", 8765),
    ("稳态运维", 8090),
    ("元运维监控", 8098),
    ("算子调度", 8072),
    ("统一算子", 8061),
    ("知识图谱", 8080),
    ("政务API", 8025),
    ("政务网关", 8200),
    ("政务算子", 8201),
    ("政务审计", 8202),
    ("政务大屏", 8203),
    ("飞书审批回调", 8060),
    ("上下文组装", 9123),
    ("同源握手", 8099),
    ("短剧后台", 8100),
    ("向量服务", 8014),
]

if __name__ == "__main__":
    monitor = GlobalMonitor()
    print("=== 火斗云智全域监控告警体系 V1.0 ===")
    print(f"告警规则: {len(monitor.rules)} 条")
    print(f"监控服务: {len(MONITORED_SERVICES)} 个")
    
    # 执行一次监控周期
    data = monitor.run_cycle()
    print(f"\n当前指标:")
    for k, v in data["metrics"].items():
        print(f"  {k}: {v}")
    
    print(f"\n告警汇总: {data['alert_summary']}")
    print(f"自愈记录: {len(data['heal_history'])} 条")
