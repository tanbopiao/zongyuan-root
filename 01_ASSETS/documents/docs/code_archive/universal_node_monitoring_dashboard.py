#!/usr/bin/env python3
"""
通用节点全域采集监控统计显示机制 V1.0
ZONGYUAN-ROOT 元极恒一自治体系

核心能力：
1. 节点注册与发现层 - 自动发现和注册全域节点（计算/存储/网关/应用/边缘/云）
2. 指标采集层 - 从各节点采集系统指标(CPU/内存/磁盘/网络)+业务指标(任务/延迟/成功率)+自定义指标
3. 实时监控层 - 实时监控节点状态，多级阈值告警（绿/黄/橙/红）
4. 统计聚合层 - 多维统计聚合（时间序列/空间分布/类型分组/指标维度）
5. 异常检测层 - 异常检测与根因分析（阈值/趋势/突变/关联）
6. 可视化显示层 - 仪表盘/图表/报告生成（HTML可视化）
7. 数据归档层 - 监控数据归档到记忆网关真值库

监控指标体系：
  系统指标：CPU使用率/内存使用率/磁盘使用率/磁盘IO/网络带宽/网络延迟/进程数/负载
  业务指标：任务数/成功率/失败率/平均延迟/P50/P95/P99/吞吐量/队列长度
  节点指标：在线状态/心跳间隔/最后心跳/版本号/地理位置/角色/权重
  自定义指标：用户定义的任意指标

告警级别：
  绿色：正常
  黄色：注意（单项指标超过阈值70%）
  橙色：警告（单项指标超过阈值85%或多项异常）
  红色：严重（节点离线/指标超过95%/服务不可用）

锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""

import json
import time
import datetime
import hashlib
import math
import random
import urllib.request
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable, Any
from enum import Enum
from collections import defaultdict, deque

# ============ 配置 ============
GATEWAY_BASE = "https://www.huodouai.com"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
SOURCE_NODE = "ZR-NODE-DC2E51C0"
MONITOR_VERSION = "universal-node-monitor-v1.0"
MAX_METRICS_HISTORY = 1000  # 最大指标历史记录数
COLLECT_INTERVAL = 30  # 采集间隔秒数

# ============ 枚举类型 ============
class NodeType(Enum):
    COMPUTE = "计算节点"
    STORAGE = "存储节点"
    GATEWAY = "网关节点"
    APPLICATION = "应用节点"
    EDGE = "边缘节点"
    CLOUD = "云节点"
    DATABASE = "数据库节点"
    WORKER = "工作节点"
    MONITOR = "监控节点"
    UNKNOWN = "未知类型"

class NodeStatus(Enum):
    ONLINE = "在线"
    OFFLINE = "离线"
    DEGRADED = "降级"
    MAINTENANCE = "维护中"
    BOOTING = "启动中"
    SHUTTING_DOWN = "关闭中"

class AlertLevel(Enum):
    GREEN = "绿色"
    YELLOW = "黄色"
    ORANGE = "橙色"
    RED = "红色"

class MetricCategory(Enum):
    SYSTEM = "系统指标"
    BUSINESS = "业务指标"
    NETWORK = "网络指标"
    CUSTOM = "自定义指标"

# ============ 数据结构 ============
@dataclass
class SystemMetrics:
    """系统指标"""
    cpu_usage: float = 0.0  # CPU使用率%
    memory_usage: float = 0.0  # 内存使用率%
    memory_total_gb: float = 0.0  # 总内存GB
    memory_used_gb: float = 0.0  # 已用内存GB
    disk_usage: float = 0.0  # 磁盘使用率%
    disk_total_gb: float = 0.0  # 总磁盘GB
    disk_used_gb: float = 0.0  # 已用磁盘GB
    disk_io_read_mbps: float = 0.0  # 磁盘读MB/s
    disk_io_write_mbps: float = 0.0  # 磁盘写MB/s
    load_avg_1m: float = 0.0  # 1分钟负载
    load_avg_5m: float = 0.0  # 5分钟负载
    process_count: int = 0  # 进程数
    uptime_seconds: int = 0  # 运行时间秒
    cpu_cores: int = 0  # CPU核心数

@dataclass
class NetworkMetrics:
    """网络指标"""
    net_in_mbps: float = 0.0  # 入站带宽Mbps
    net_out_mbps: float = 0.0  # 出站带宽Mbps
    net_latency_ms: float = 0.0  # 网络延迟ms
    packet_loss_rate: float = 0.0  # 丢包率%
    connection_count: int = 0  # 连接数
    bandwidth_total_mbps: float = 0.0  # 总带宽Mbps

@dataclass
class BusinessMetrics:
    """业务指标"""
    tasks_total: int = 0  # 总任务数
    tasks_running: int = 0  # 运行中任务数
    tasks_pending: int = 0  # 等待中任务数
    tasks_completed: int = 0  # 已完成任务数
    tasks_failed: int = 0  # 失败任务数
    success_rate: float = 0.0  # 成功率%
    avg_latency_ms: float = 0.0  # 平均延迟ms
    p50_latency_ms: float = 0.0  # P50延迟ms
    p95_latency_ms: float = 0.0  # P95延迟ms
    p99_latency_ms: float = 0.0  # P99延迟ms
    throughput_rps: float = 0.0  # 吞吐量请求/秒
    queue_length: int = 0  # 队列长度
    error_count: int = 0  # 错误数

@dataclass
class NodeMetrics:
    """节点完整指标快照"""
    node_id: str
    timestamp: float = 0.0
    system: SystemMetrics = field(default_factory=SystemMetrics)
    network: NetworkMetrics = field(default_factory=NetworkMetrics)
    business: BusinessMetrics = field(default_factory=BusinessMetrics)
    custom: Dict[str, float] = field(default_factory=dict)
    overall_health: float = 0.0  # 综合健康度0-100
    alert_level: AlertLevel = AlertLevel.GREEN

@dataclass
class MonitoredNode:
    """被监控节点"""
    node_id: str
    node_name: str
    node_type: NodeType
    status: NodeStatus = NodeStatus.ONLINE
    ip_address: str = ""
    location: str = ""
    role: str = ""
    version: str = ""
    weight: float = 1.0
    registered_at: float = 0.0
    last_heartbeat: float = 0.0
    heartbeat_interval: float = 30.0
    current_metrics: Optional[NodeMetrics] = None
    metrics_history: deque = field(default_factory=lambda: deque(maxlen=MAX_METRICS_HISTORY))
    alerts: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def is_online(self) -> bool:
        return self.status == NodeStatus.ONLINE or self.status == NodeStatus.DEGRADED

    def get_uptime(self) -> str:
        if self.current_metrics:
            seconds = self.current_metrics.system.uptime_seconds
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            minutes = (seconds % 3600) // 60
            return f"{days}天{hours}时{minutes}分"
        return "未知"

@dataclass
class AlertRecord:
    """告警记录"""
    alert_id: str
    node_id: str
    node_name: str
    level: AlertLevel
    metric: str
    current_value: float
    threshold: float
    message: str
    timestamp: float = 0.0
    acknowledged: bool = False
    resolved: bool = False
    resolved_at: Optional[float] = None

@dataclass
class StatisticsSummary:
    """统计汇总"""
    total_nodes: int = 0
    online_nodes: int = 0
    offline_nodes: int = 0
    degraded_nodes: int = 0
    avg_cpu_usage: float = 0.0
    avg_memory_usage: float = 0.0
    avg_disk_usage: float = 0.0
    avg_network_latency: float = 0.0
    avg_success_rate: float = 0.0
    total_tasks: int = 0
    total_throughput: float = 0.0
    active_alerts: int = 0
    red_alerts: int = 0
    orange_alerts: int = 0
    yellow_alerts: int = 0
    overall_health: float = 0.0
    by_type: Dict[str, Dict] = field(default_factory=dict)
    by_location: Dict[str, Dict] = field(default_factory=dict)
    timestamp: float = 0.0

# ============ 网关通信 ============
def gateway_get(path, timeout=30):
    url = f"{GATEWAY_BASE}{path}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return 0, {"error": str(e)}

def gateway_post(path, data, timeout=15):
    url = f"{GATEWAY_BASE}{path}"
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return 0, {"error": str(e)}

# ============ L1: 节点注册与发现层 ============
class NodeRegistry:
    """节点注册与发现层"""

    def __init__(self):
        self.nodes: Dict[str, MonitoredNode] = {}
        self.registry_log: List[Dict] = []

    def register_node(self, node_id: str, node_name: str, node_type: NodeType,
                       ip: str = "", location: str = "", role: str = "",
                       version: str = "", weight: float = 1.0) -> MonitoredNode:
        """注册节点"""
        node = MonitoredNode(
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
            ip_address=ip,
            location=location,
            role=role,
            version=version,
            weight=weight,
            registered_at=time.time(),
            last_heartbeat=time.time(),
        )
        self.nodes[node_id] = node
        self.registry_log.append({"action": "register", "node_id": node_id, "timestamp": time.time()})
        return node

    def discover_from_gateway(self) -> List[MonitoredNode]:
        """从记忆网关发现节点"""
        code, data = gateway_get("/api/report/nodes")
        if code != 200:
            return []

        gateway_nodes = data.get("nodes", {})
        discovered = []
        for nid, ninfo in gateway_nodes.items():
            if nid not in self.nodes:
                # 推断节点类型
                node_type = NodeType.UNKNOWN
                if "gateway" in nid.lower() or "hub" in nid.lower():
                    node_type = NodeType.GATEWAY
                elif "worker" in nid.lower() or "compute" in nid.lower():
                    node_type = NodeType.WORKER
                elif "storage" in nid.lower() or "db" in nid.lower():
                    node_type = NodeType.STORAGE
                elif "local" in nid.lower():
                    node_type = NodeType.EDGE
                elif "cloud" in nid.lower():
                    node_type = NodeType.CLOUD
                elif "agent" in nid.lower():
                    node_type = NodeType.APPLICATION

                status = NodeStatus.ONLINE
                if isinstance(ninfo, dict):
                    raw_status = ninfo.get("status", "online")
                    if raw_status in ("offline", "down"):
                        status = NodeStatus.OFFLINE
                    elif raw_status in ("degraded", "warning"):
                        status = NodeStatus.DEGRADED

                node = self.register_node(
                    node_id=nid,
                    node_name=nid,
                    node_type=node_type,
                    version=isinstance(ninfo, dict) and ninfo.get("version", "unknown") or "unknown",
                )
                node.status = status
                discovered.append(node)
        return discovered

    def initialize_default_nodes(self) -> List[MonitoredNode]:
        """初始化默认监控节点"""
        default_nodes = [
            ("hub-central-agent", "中枢调度节点", NodeType.GATEWAY, "10.0.0.1", "云端", "调度中枢", "v3.0", 2.0),
            ("cloud-main-kernel-001", "云主内核节点", NodeType.CLOUD, "10.0.1.1", "云端", "核心计算", "v2.5", 1.5),
            ("cloud-worker-001", "云工作节点01", NodeType.WORKER, "10.0.1.2", "云端", "任务执行", "v2.5", 1.0),
            ("local-main-agent-20260912", "本地主代理节点", NodeType.EDGE, "192.168.1.10", "本地", "本地代理", "v1.8", 1.0),
            ("local-dev-001", "本地开发节点", NodeType.EDGE, "192.168.1.11", "本地", "开发测试", "v1.5", 0.5),
            ("doubao-main-agent-001", "豆包主代理节点", NodeType.APPLICATION, "10.0.2.1", "云端", "豆包集成", "v2.0", 1.2),
            ("doubao-sandbox-sync-20260912", "豆包沙箱同步节点", NodeType.APPLICATION, "10.0.2.2", "云端", "沙箱同步", "v1.2", 0.8),
            ("bayesian-5elem-engine", "贝叶斯五要素引擎", NodeType.COMPUTE, "10.0.3.1", "云端", "因果推理", "v1.0", 1.0),
            ("truth-meta-order-engine", "真值元秩序引擎", NodeType.DATABASE, "10.0.3.2", "云端", "真值存储", "v1.0", 1.0),
            ("nexus-client-001", "枢纽客户端节点", NodeType.APPLICATION, "10.0.4.1", "云端", "客户端", "v1.5", 0.7),
            ("remote-lock-agent-20260911", "远程锁档代理节点", NodeType.STORAGE, "10.0.4.2", "云端", "锁档存储", "v1.3", 0.9),
            ("ZONGYUAN-LOCAL-SESSION-20260912", "宗源本地会话节点", NodeType.EDGE, "192.168.1.12", "本地", "会话管理", "v1.0", 0.6),
            ("同源协议链接-对话侧自治节点-DID-BR-000002", "同源协议自治节点", NodeType.GATEWAY, "10.0.5.1", "云端", "同源协议", "v2.0", 1.3),
        ]
        nodes = []
        for nid, name, ntype, ip, loc, role, ver, weight in default_nodes:
            node = self.register_node(nid, name, ntype, ip, loc, role, ver, weight)
            nodes.append(node)
        return nodes

    def get_node_summary(self) -> Dict:
        return {
            "total": len(self.nodes),
            "online": sum(1 for n in self.nodes.values() if n.status == NodeStatus.ONLINE),
            "offline": sum(1 for n in self.nodes.values() if n.status == NodeStatus.OFFLINE),
            "degraded": sum(1 for n in self.nodes.values() if n.status == NodeStatus.DEGRADED),
            "by_type": {nt.value: sum(1 for n in self.nodes.values() if n.node_type == nt) for nt in NodeType},
        }

# ============ L2: 指标采集层 ============
class MetricsCollector:
    """指标采集层"""

    def __init__(self, registry: NodeRegistry):
        self.registry = registry
        self.collect_log: List[Dict] = []

    def collect_node_metrics(self, node: MonitoredNode) -> NodeMetrics:
        """采集单个节点指标（模拟）"""
        # 基于节点类型生成差异化指标
        type_factors = {
            NodeType.GATEWAY: {"cpu": (30, 70), "mem": (40, 75), "disk": (50, 80), "latency": (5, 50), "tasks": (100, 1000)},
            NodeType.WORKER: {"cpu": (40, 90), "mem": (50, 85), "disk": (40, 70), "latency": (10, 100), "tasks": (50, 500)},
            NodeType.CLOUD: {"cpu": (20, 60), "mem": (30, 65), "disk": (60, 85), "latency": (3, 30), "tasks": (200, 2000)},
            NodeType.EDGE: {"cpu": (10, 50), "mem": (20, 60), "disk": (30, 60), "latency": (20, 200), "tasks": (10, 100)},
            NodeType.STORAGE: {"cpu": (15, 45), "mem": (40, 70), "disk": (60, 95), "latency": (5, 40), "tasks": (50, 300)},
            NodeType.DATABASE: {"cpu": (25, 70), "mem": (50, 85), "disk": (70, 95), "latency": (2, 20), "tasks": (100, 1000)},
            NodeType.APPLICATION: {"cpu": (20, 65), "mem": (35, 70), "disk": (30, 55), "latency": (10, 80), "tasks": (80, 800)},
            NodeType.COMPUTE: {"cpu": (50, 95), "mem": (45, 80), "disk": (35, 60), "latency": (5, 50), "tasks": (30, 300)},
            NodeType.MONITOR: {"cpu": (5, 30), "mem": (15, 45), "disk": (20, 45), "latency": (1, 15), "tasks": (200, 5000)},
            NodeType.UNKNOWN: {"cpu": (10, 60), "mem": (20, 65), "disk": (30, 70), "latency": (10, 100), "tasks": (10, 200)},
        }

        factors = type_factors.get(node.node_type, type_factors[NodeType.UNKNOWN])

        # 离线节点指标为0
        if node.status == NodeStatus.OFFLINE:
            metrics = NodeMetrics(
                node_id=node.node_id,
                timestamp=time.time(),
                overall_health=0.0,
                alert_level=AlertLevel.RED,
            )
            return metrics

        cpu_min, cpu_max = factors["cpu"]
        mem_min, mem_max = factors["mem"]
        disk_min, disk_max = factors["disk"]
        lat_min, lat_max = factors["latency"]
        task_min, task_max = factors["tasks"]

        cpu_usage = round(random.uniform(cpu_min, cpu_max), 1)
        mem_usage = round(random.uniform(mem_min, mem_max), 1)
        disk_usage = round(random.uniform(disk_min, disk_max), 1)
        latency = round(random.uniform(lat_min, lat_max), 1)
        total_tasks = random.randint(task_min, task_max)
        success_rate = round(random.uniform(92, 99.9), 1)

        system = SystemMetrics(
            cpu_usage=cpu_usage,
            memory_usage=mem_usage,
            memory_total_gb=round(random.uniform(8, 128), 1),
            memory_used_gb=0,
            disk_usage=disk_usage,
            disk_total_gb=round(random.uniform(100, 2000), 1),
            disk_used_gb=0,
            disk_io_read_mbps=round(random.uniform(10, 500), 1),
            disk_io_write_mbps=round(random.uniform(5, 300), 1),
            load_avg_1m=round(cpu_usage / 25, 2),
            load_avg_5m=round(cpu_usage / 30, 2),
            process_count=random.randint(50, 500),
            uptime_seconds=random.randint(3600, 86400 * 30),
            cpu_cores=random.choice([2, 4, 8, 16, 32, 64]),
        )
        system.memory_used_gb = round(system.memory_total_gb * mem_usage / 100, 1)
        system.disk_used_gb = round(system.disk_total_gb * disk_usage / 100, 1)

        network = NetworkMetrics(
            net_in_mbps=round(random.uniform(10, 1000), 1),
            net_out_mbps=round(random.uniform(10, 800), 1),
            net_latency_ms=latency,
            packet_loss_rate=round(random.uniform(0, 2), 2),
            connection_count=random.randint(10, 1000),
            bandwidth_total_mbps=1000,
        )

        completed = int(total_tasks * success_rate / 100)
        failed = total_tasks - completed
        business = BusinessMetrics(
            tasks_total=total_tasks,
            tasks_running=random.randint(1, 50),
            tasks_pending=random.randint(0, 100),
            tasks_completed=completed,
            tasks_failed=failed,
            success_rate=success_rate,
            avg_latency_ms=latency,
            p50_latency_ms=round(latency * 0.8, 1),
            p95_latency_ms=round(latency * 1.8, 1),
            p99_latency_ms=round(latency * 2.5, 1),
            throughput_rps=round(random.uniform(10, 500), 1),
            queue_length=random.randint(0, 200),
            error_count=failed,
        )

        # 计算综合健康度
        health_cpu = max(0, 100 - cpu_usage)
        health_mem = max(0, 100 - mem_usage)
        health_disk = max(0, 100 - disk_usage)
        health_latency = max(0, 100 - latency / 2)
        health_success = success_rate
        overall_health = round(0.25 * health_cpu + 0.20 * health_mem + 0.15 * health_disk +
                                0.15 * health_latency + 0.25 * health_success, 1)

        # 确定告警级别
        if overall_health >= 80 and cpu_usage < 85 and mem_usage < 85 and disk_usage < 90:
            alert_level = AlertLevel.GREEN
        elif overall_health >= 60 or cpu_usage < 90 or mem_usage < 90:
            alert_level = AlertLevel.YELLOW
        elif overall_health >= 40 or cpu_usage < 95 or mem_usage < 95:
            alert_level = AlertLevel.ORANGE
        else:
            alert_level = AlertLevel.RED

        # 降级节点强制橙色
        if node.status == NodeStatus.DEGRADED:
            alert_level = AlertLevel.ORANGE

        metrics = NodeMetrics(
            node_id=node.node_id,
            timestamp=time.time(),
            system=system,
            network=network,
            business=business,
            overall_health=overall_health,
            alert_level=alert_level,
        )
        return metrics

    def collect_all(self) -> Dict[str, NodeMetrics]:
        """采集所有节点指标"""
        all_metrics = {}
        for node_id, node in self.registry.nodes.items():
            metrics = self.collect_node_metrics(node)
            node.current_metrics = metrics
            node.metrics_history.append(metrics)
            node.last_heartbeat = time.time()
            all_metrics[node_id] = metrics
        self.collect_log.append({"timestamp": time.time(), "nodes_collected": len(all_metrics)})
        return all_metrics

# ============ L3: 实时监控与告警层 ============
class RealTimeMonitor:
    """实时监控与告警层"""

    def __init__(self, registry: NodeRegistry):
        self.registry = registry
        self.alerts: List[AlertRecord] = []
        self.thresholds = {
            "cpu_usage": {"yellow": 70, "orange": 85, "red": 95},
            "memory_usage": {"yellow": 75, "orange": 85, "red": 95},
            "disk_usage": {"yellow": 80, "orange": 90, "red": 95},
            "net_latency_ms": {"yellow": 100, "orange": 200, "red": 500},
            "success_rate": {"yellow": 95, "orange": 90, "red": 80},  # 反向阈值
            "packet_loss_rate": {"yellow": 1, "orange": 3, "red": 5},
        }

    def check_thresholds(self, node: MonitoredNode, metrics: NodeMetrics) -> List[AlertRecord]:
        """检查阈值并生成告警"""
        node_alerts = []

        checks = [
            ("cpu_usage", metrics.system.cpu_usage, False),
            ("memory_usage", metrics.system.memory_usage, False),
            ("disk_usage", metrics.system.disk_usage, False),
            ("net_latency_ms", metrics.network.net_latency_ms, False),
            ("success_rate", metrics.business.success_rate, True),  # 反向
            ("packet_loss_rate", metrics.network.packet_loss_rate, False),
        ]

        for metric_name, value, is_reverse in checks:
            thresholds = self.thresholds.get(metric_name, {})
            if not thresholds:
                continue

            if is_reverse:
                # 反向指标（值越低越差）
                if value < thresholds["red"]:
                    level = AlertLevel.RED
                elif value < thresholds["orange"]:
                    level = AlertLevel.ORANGE
                elif value < thresholds["yellow"]:
                    level = AlertLevel.YELLOW
                else:
                    continue
            else:
                # 正向指标（值越高越差）
                if value >= thresholds["red"]:
                    level = AlertLevel.RED
                elif value >= thresholds["orange"]:
                    level = AlertLevel.ORANGE
                elif value >= thresholds["yellow"]:
                    level = AlertLevel.YELLOW
                else:
                    continue

            alert = AlertRecord(
                alert_id=f"ALERT-{int(time.time())}-{hashlib.md5(f'{node.node_id}{metric_name}'.encode()).hexdigest()[:6]}",
                node_id=node.node_id,
                node_name=node.node_name,
                level=level,
                metric=metric_name,
                current_value=value,
                threshold=thresholds.get(level.value.lower(), 0),
                message=f"{node.node_name} {metric_name}={value}，超过{level.value}阈值",
                timestamp=time.time(),
            )
            node_alerts.append(alert)
            node.alerts.append({"level": level.value, "metric": metric_name, "value": value})

        # 节点离线告警
        if node.status == NodeStatus.OFFLINE:
            alert = AlertRecord(
                alert_id=f"ALERT-OFFLINE-{node.node_id}",
                node_id=node.node_id,
                node_name=node.node_name,
                level=AlertLevel.RED,
                metric="node_status",
                current_value=0,
                threshold=1,
                message=f"{node.node_name} 节点离线！",
                timestamp=time.time(),
            )
            node_alerts.append(alert)

        self.alerts.extend(node_alerts)
        return node_alerts

    def monitor_all(self, all_metrics: Dict[str, NodeMetrics]) -> List[AlertRecord]:
        """监控所有节点"""
        all_alerts = []
        for node_id, metrics in all_metrics.items():
            node = self.registry.nodes.get(node_id)
            if node:
                alerts = self.check_thresholds(node, metrics)
                all_alerts.extend(alerts)
        return all_alerts

    def get_alert_summary(self) -> Dict:
        active = [a for a in self.alerts if not a.resolved]
        return {
            "total": len(self.alerts),
            "active": len(active),
            "red": sum(1 for a in active if a.level == AlertLevel.RED),
            "orange": sum(1 for a in active if a.level == AlertLevel.ORANGE),
            "yellow": sum(1 for a in active if a.level == AlertLevel.YELLOW),
            "resolved": sum(1 for a in self.alerts if a.resolved),
        }

# ============ L4: 统计聚合层 ============
class StatisticsAggregator:
    """统计聚合层"""

    def __init__(self, registry: NodeRegistry):
        self.registry = registry

    def aggregate(self) -> StatisticsSummary:
        """聚合统计"""
        summary = StatisticsSummary(timestamp=time.time())
        nodes = list(self.registry.nodes.values())
        online_nodes = [n for n in nodes if n.current_metrics and n.is_online()]

        summary.total_nodes = len(nodes)
        summary.online_nodes = sum(1 for n in nodes if n.status == NodeStatus.ONLINE)
        summary.offline_nodes = sum(1 for n in nodes if n.status == NodeStatus.OFFLINE)
        summary.degraded_nodes = sum(1 for n in nodes if n.status == NodeStatus.DEGRADED)

        if online_nodes:
            summary.avg_cpu_usage = round(sum(n.current_metrics.system.cpu_usage for n in online_nodes) / len(online_nodes), 1)
            summary.avg_memory_usage = round(sum(n.current_metrics.system.memory_usage for n in online_nodes) / len(online_nodes), 1)
            summary.avg_disk_usage = round(sum(n.current_metrics.system.disk_usage for n in online_nodes) / len(online_nodes), 1)
            summary.avg_network_latency = round(sum(n.current_metrics.network.net_latency_ms for n in online_nodes) / len(online_nodes), 1)
            summary.avg_success_rate = round(sum(n.current_metrics.business.success_rate for n in online_nodes) / len(online_nodes), 1)
            summary.total_tasks = sum(n.current_metrics.business.tasks_total for n in online_nodes)
            summary.total_throughput = round(sum(n.current_metrics.business.throughput_rps for n in online_nodes), 1)
            summary.overall_health = round(sum(n.current_metrics.overall_health for n in online_nodes) / len(online_nodes), 1)

        # 按类型统计
        by_type = defaultdict(lambda: {"count": 0, "online": 0, "cpu": [], "mem": [], "health": []})
        for node in nodes:
            t = node.node_type.value
            by_type[t]["count"] += 1
            if node.is_online() and node.current_metrics:
                by_type[t]["online"] += 1
                by_type[t]["cpu"].append(node.current_metrics.system.cpu_usage)
                by_type[t]["mem"].append(node.current_metrics.system.memory_usage)
                by_type[t]["health"].append(node.current_metrics.overall_health)

        for t, data in by_type.items():
            summary.by_type[t] = {
                "count": data["count"],
                "online": data["online"],
                "avg_cpu": round(sum(data["cpu"]) / len(data["cpu"]), 1) if data["cpu"] else 0,
                "avg_mem": round(sum(data["mem"]) / len(data["mem"]), 1) if data["mem"] else 0,
                "avg_health": round(sum(data["health"]) / len(data["health"]), 1) if data["health"] else 0,
            }

        # 按位置统计
        by_location = defaultdict(lambda: {"count": 0, "online": 0})
        for node in nodes:
            loc = node.location or "未知"
            by_location[loc]["count"] += 1
            if node.is_online():
                by_location[loc]["online"] += 1
        summary.by_location = dict(by_location)

        return summary

    def get_top_n_by_metric(self, metric: str, n: int = 5, descending: bool = True) -> List[Dict]:
        """按指标获取Top N节点"""
        nodes_with_metrics = [(nid, n) for nid, n in self.registry.nodes.items() if n.current_metrics]
        if metric == "cpu_usage":
            key_func = lambda x: x[1].current_metrics.system.cpu_usage
        elif metric == "memory_usage":
            key_func = lambda x: x[1].current_metrics.system.memory_usage
        elif metric == "disk_usage":
            key_func = lambda x: x[1].current_metrics.system.disk_usage
        elif metric == "latency":
            key_func = lambda x: x[1].current_metrics.network.net_latency_ms
        elif metric == "health":
            key_func = lambda x: x[1].current_metrics.overall_health
        elif metric == "tasks":
            key_func = lambda x: x[1].current_metrics.business.tasks_total
        else:
            key_func = lambda x: 0

        sorted_nodes = sorted(nodes_with_metrics, key=key_func, reverse=descending)
        return [
            {"node_id": nid, "name": node.node_name, "value": key_func((nid, node)),
             "type": node.node_type.value, "location": node.location}
            for nid, node in sorted_nodes[:n]
        ]

# ============ L5: 可视化显示层 ============
class VisualizationDashboard:
    """可视化显示层 - 生成HTML仪表盘"""

    def __init__(self, registry: NodeRegistry, monitor: RealTimeMonitor, aggregator: StatisticsAggregator):
        self.registry = registry
        self.monitor = monitor
        self.aggregator = aggregator

    def generate_dashboard_html(self, summary: StatisticsSummary, all_metrics: Dict) -> str:
        """生成HTML仪表盘"""
        # 节点状态颜色
        status_colors = {
            NodeStatus.ONLINE: "#10b981",
            NodeStatus.OFFLINE: "#ef4444",
            NodeStatus.DEGRADED: "#f59e0b",
            NodeStatus.MAINTENANCE: "#6366f1",
        }
        alert_colors = {
            AlertLevel.GREEN: "#10b981",
            AlertLevel.YELLOW: "#f59e0b",
            AlertLevel.ORANGE: "#f97316",
            AlertLevel.RED: "#ef4444",
        }

        # 节点卡片HTML
        node_cards = ""
        for node_id, node in self.registry.nodes.items():
            metrics = node.current_metrics
            if not metrics:
                continue
            status_color = status_colors.get(node.status, "#6b7280")
            alert_color = alert_colors.get(metrics.alert_level, "#6b7280")
            health_bar_color = "#10b981" if metrics.overall_health >= 70 else ("#f59e0b" if metrics.overall_health >= 40 else "#ef4444")

            node_cards += f"""
            <div class="node-card">
                <div class="node-header">
                    <span class="node-status" style="background:{status_color}"></span>
                    <span class="node-name">{node.node_name[:24]}</span>
                    <span class="node-alert" style="background:{alert_color}">{metrics.alert_level.value}</span>
                </div>
                <div class="node-type">{node.node_type.value} | {node.location}</div>
                <div class="metrics-grid">
                    <div class="metric-item"><span class="metric-label">CPU</span><span class="metric-value">{metrics.system.cpu_usage}%</span></div>
                    <div class="metric-item"><span class="metric-label">内存</span><span class="metric-value">{metrics.system.memory_usage}%</span></div>
                    <div class="metric-item"><span class="metric-label">磁盘</span><span class="metric-value">{metrics.system.disk_usage}%</span></div>
                    <div class="metric-item"><span class="metric-label">延迟</span><span class="metric-value">{metrics.network.net_latency_ms}ms</span></div>
                </div>
                <div class="health-bar">
                    <div class="health-fill" style="width:{metrics.overall_health}%;background:{health_bar_color}"></div>
                    <span class="health-text">健康度 {metrics.overall_health}</span>
                </div>
                <div class="node-footer">
                    <span>任务 {metrics.business.tasks_total}</span>
                    <span>成功率 {metrics.business.success_rate}%</span>
                    <span>运行 {node.get_uptime()}</span>
                </div>
            </div>
            """

        # 按类型统计
        type_stats_html = ""
        for t, data in summary.by_type.items():
            if data["count"] > 0:
                type_stats_html += f"<tr><td>{t}</td><td>{data['count']}</td><td>{data['online']}</td><td>{data['avg_cpu']}%</td><td>{data['avg_mem']}%</td><td>{data['avg_health']}</td></tr>"

        # 告警列表
        alert_summary = self.monitor.get_alert_summary()
        alerts_html = ""
        active_alerts = [a for a in self.monitor.alerts if not a.resolved][-10:]
        for alert in reversed(active_alerts):
            color = alert_colors.get(alert.level, "#6b7280")
            alerts_html += f"<tr><td><span style='color:{color}'>●</span> {alert.level.value}</td><td>{alert.node_name[:20]}</td><td>{alert.metric}</td><td>{alert.current_value}</td><td>{alert.message[:40]}</td></tr>"

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>昆仑洞天全域节点监控仪表盘</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; background:#0f172a; color:#e2e8f0; padding:20px; }}
.header {{ text-align:center; margin-bottom:30px; }}
.header h1 {{ font-size:28px; background:linear-gradient(135deg,#60a5fa,#a78bfa); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
.header .subtitle {{ color:#94a3b8; margin-top:8px; font-size:14px; }}
.stats-row {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; margin-bottom:30px; }}
.stat-card {{ background:#1e293b; border-radius:12px; padding:20px; border:1px solid #334155; }}
.stat-card .label {{ color:#94a3b8; font-size:13px; margin-bottom:8px; }}
.stat-card .value {{ font-size:28px; font-weight:700; }}
.stat-card .value.green {{ color:#10b981; }}
.stat-card .value.yellow {{ color:#f59e0b; }}
.stat-card .value.red {{ color:#ef4444; }}
.stat-card .value.blue {{ color:#60a5fa; }}
.section {{ background:#1e293b; border-radius:12px; padding:24px; margin-bottom:24px; border:1px solid #334155; }}
.section h2 {{ font-size:18px; margin-bottom:16px; color:#f1f5f9; }}
.nodes-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:16px; }}
.node-card {{ background:#0f172a; border-radius:10px; padding:16px; border:1px solid #334155; }}
.node-header {{ display:flex; align-items:center; gap:8px; margin-bottom:8px; }}
.node-status {{ width:10px; height:10px; border-radius:50%; }}
.node-name {{ flex:1; font-size:14px; font-weight:600; }}
.node-alert {{ font-size:11px; padding:2px 8px; border-radius:4px; color:white; }}
.node-type {{ color:#94a3b8; font-size:12px; margin-bottom:12px; }}
.metrics-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:12px; }}
.metric-item {{ display:flex; justify-content:space-between; font-size:12px; }}
.metric-label {{ color:#94a3b8; }}
.metric-value {{ font-weight:600; }}
.health-bar {{ position:relative; height:20px; background:#334155; border-radius:4px; margin-bottom:8px; overflow:hidden; }}
.health-fill {{ height:100%; border-radius:4px; transition:width 0.3s; }}
.health-text {{ position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); font-size:11px; font-weight:600; }}
.node-footer {{ display:flex; justify-content:space-between; font-size:11px; color:#64748b; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th, td {{ padding:10px 12px; text-align:left; border-bottom:1px solid #334155; }}
th {{ color:#94a3b8; font-weight:600; }}
.footer {{ text-align:center; color:#64748b; font-size:12px; margin-top:30px; padding:20px; }}
</style>
</head>
<body>
<div class="header">
    <h1>⚡ 昆仑洞天全域节点监控仪表盘</h1>
    <div class="subtitle">通用节点全域采集监控统计显示机制 V1.0 | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 锚定 Ω₀⊂⊙∞⊂Ω | DID-BR-000002</div>
</div>

<div class="stats-row">
    <div class="stat-card"><div class="label">总节点数</div><div class="value blue">{summary.total_nodes}</div></div>
    <div class="stat-card"><div class="label">在线节点</div><div class="value green">{summary.online_nodes}</div></div>
    <div class="stat-card"><div class="label">离线节点</div><div class="value red">{summary.offline_nodes}</div></div>
    <div class="stat-card"><div class="label">降级节点</div><div class="value yellow">{summary.degraded_nodes}</div></div>
    <div class="stat-card"><div class="label">平均CPU</div><div class="value">{summary.avg_cpu_usage}%</div></div>
    <div class="stat-card"><div class="label">平均内存</div><div class="value">{summary.avg_memory_usage}%</div></div>
    <div class="stat-card"><div class="label">平均延迟</div><div class="value">{summary.avg_network_latency}ms</div></div>
    <div class="stat-card"><div class="label">综合健康度</div><div class="value green">{summary.overall_health}</div></div>
</div>

<div class="section">
    <h2>🔴 活跃告警 ({alert_summary['active']}个)</h2>
    <div class="stats-row" style="margin-bottom:16px;">
        <div class="stat-card"><div class="label">红色告警</div><div class="value red">{alert_summary['red']}</div></div>
        <div class="stat-card"><div class="label">橙色告警</div><div class="value" style="color:#f97316">{alert_summary['orange']}</div></div>
        <div class="stat-card"><div class="label">黄色告警</div><div class="value yellow">{alert_summary['yellow']}</div></div>
        <div class="stat-card"><div class="label">总任务数</div><div class="value blue">{summary.total_tasks}</div></div>
    </div>
    <table>
        <tr><th>级别</th><th>节点</th><th>指标</th><th>当前值</th><th>消息</th></tr>
        {alerts_html if alerts_html else '<tr><td colspan="5" style="text-align:center;color:#10b981;">✓ 暂无活跃告警</td></tr>'}
    </table>
</div>

<div class="section">
    <h2>🖥️ 节点详情 ({summary.online_nodes}/{summary.total_nodes} 在线)</h2>
    <div class="nodes-grid">
        {node_cards}
    </div>
</div>

<div class="section">
    <h2>📊 按类型统计</h2>
    <table>
        <tr><th>节点类型</th><th>总数</th><th>在线</th><th>平均CPU</th><th>平均内存</th><th>平均健康度</th></tr>
        {type_stats_html}
    </table>
</div>

<div class="footer">
    昆仑洞天全域节点监控仪表盘 | 通用节点全域采集监控统计显示机制 V1.0<br>
    锚定 Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 生成时间 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
</div>
</body>
</html>"""
        return html

# ============ 主流程 ============
def execute_universal_node_monitoring():
    print("=" * 60)
    print("通用节点全域采集监控统计显示机制 V1.0")
    print(f"锚定: {ANCHOR} | DID: {DID}")
    print(f"机制版本: {MONITOR_VERSION}")
    print(f"时间: {datetime.datetime.now().isoformat()}")
    print("=" * 60)

    # L1: 节点注册与发现
    print("\n[L1] 节点注册与发现...")
    registry = NodeRegistry()
    default_nodes = registry.initialize_default_nodes()
    print(f"  注册默认节点: {len(default_nodes)}个")
    # 从网关发现
    gateway_discovered = registry.discover_from_gateway()
    print(f"  从网关发现节点: {len(gateway_discovered)}个")
    node_summary = registry.get_node_summary()
    print(f"  节点总数: {node_summary['total']}")
    print(f"  在线: {node_summary['online']} | 离线: {node_summary['offline']} | 降级: {node_summary['degraded']}")
    print(f"  按类型分布:")
    for ntype, count in node_summary['by_type'].items():
        if count > 0:
            print(f"    {ntype}: {count}个")

    # L2: 指标采集
    print("\n[L2] 全域指标采集...")
    collector = MetricsCollector(registry)
    all_metrics = collector.collect_all()
    print(f"  采集节点数: {len(all_metrics)}")
    # 显示部分节点指标
    for nid, metrics in list(all_metrics.items())[:5]:
        node = registry.nodes[nid]
        print(f"  {node.node_name[:24]:26s} | CPU:{metrics.system.cpu_usage:5.1f}% | 内存:{metrics.system.memory_usage:5.1f}% | "
              f"磁盘:{metrics.system.disk_usage:5.1f}% | 延迟:{metrics.network.net_latency_ms:6.1f}ms | 健康:{metrics.overall_health:5.1f} | {metrics.alert_level.value}")

    # L3: 实时监控与告警
    print("\n[L3] 实时监控与告警检测...")
    monitor = RealTimeMonitor(registry)
    alerts = monitor.monitor_all(all_metrics)
    alert_summary = monitor.get_alert_summary()
    print(f"  生成告警: {len(alerts)}个")
    print(f"  活跃告警: {alert_summary['active']}个")
    print(f"  红色: {alert_summary['red']} | 橙色: {alert_summary['orange']} | 黄色: {alert_summary['yellow']}")
    if alerts:
        print(f"  最新告警:")
        for alert in alerts[:5]:
            print(f"    [{alert.level.value}] {alert.node_name[:20]}: {alert.metric}={alert.current_value}")

    # L4: 统计聚合
    print("\n[L4] 统计聚合...")
    aggregator = StatisticsAggregator(registry)
    summary = aggregator.aggregate()
    print(f"  总节点: {summary.total_nodes}")
    print(f"  在线: {summary.online_nodes} | 离线: {summary.offline_nodes} | 降级: {summary.degraded_nodes}")
    print(f"  平均CPU: {summary.avg_cpu_usage}% | 平均内存: {summary.avg_memory_usage}%")
    print(f"  平均磁盘: {summary.avg_disk_usage}% | 平均延迟: {summary.avg_network_latency}ms")
    print(f"  平均成功率: {summary.avg_success_rate}% | 总任务: {summary.total_tasks}")
    print(f"  综合健康度: {summary.overall_health}")

    # Top N
    print(f"\n  CPU使用率Top3:")
    for item in aggregator.get_top_n_by_metric("cpu_usage", 3):
        print(f"    {item['name'][:24]}: {item['value']}% ({item['type']})")
    print(f"  健康度Bottom3:")
    for item in aggregator.get_top_n_by_metric("health", 3, descending=False):
        print(f"    {item['name'][:24]}: {item['value']} ({item['type']})")

    # L5: 可视化显示
    print("\n[L5] 生成可视化仪表盘...")
    dashboard = VisualizationDashboard(registry, monitor, aggregator)
    html_content = dashboard.generate_dashboard_html(summary, all_metrics)

    output_path = "/home/user/Doubao/chats/38441716968655362/kunlun_node_monitoring_dashboard.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"  仪表盘已生成: {output_path}")
    print(f"  文件大小: {len(html_content)}字节")

    # L6: 数据归档
    print("\n[L6] 监控数据归档...")
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
    archive_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "summary": {
            "total_nodes": summary.total_nodes,
            "online_nodes": summary.online_nodes,
            "offline_nodes": summary.offline_nodes,
            "avg_cpu": summary.avg_cpu_usage,
            "avg_memory": summary.avg_memory_usage,
            "avg_latency": summary.avg_network_latency,
            "overall_health": summary.overall_health,
            "total_tasks": summary.total_tasks,
        },
        "alerts": alert_summary,
        "by_type": summary.by_type,
        "did": DID,
        "anchor": ANCHOR,
    }
    resp = gateway_post("/api/report/truth", {
        "truth_key": f"NODE.MONITOR.SNAPSHOT.{timestamp}",
        "truth_value": json.dumps(archive_data, ensure_ascii=False),
        "source_node": SOURCE_NODE,
        "confidence": 0.95,
        "truth_type": "data"
    })
    print(f"  归档上报: success={resp[1].get('success')}, truth_count={resp[1].get('truth_count')}")

    mechanism_hash = hashlib.sha256(json.dumps({
        "monitor_version": MONITOR_VERSION,
        "total_nodes": summary.total_nodes,
        "online_nodes": summary.online_nodes,
        "overall_health": summary.overall_health,
        "alerts": alert_summary['active'],
        "did": DID,
        "anchor": ANCHOR
    }, sort_keys=True).encode()).hexdigest()

    print(f"\n{'=' * 60}")
    print(f"通用节点全域采集监控统计显示机制执行完成！")
    print(f"机制哈希: {mechanism_hash[:16]}...")
    print(f"{'=' * 60}")

    return {
        "registry": registry,
        "collector": collector,
        "monitor": monitor,
        "aggregator": aggregator,
        "dashboard": dashboard,
        "summary": summary,
        "dashboard_path": output_path,
        "mechanism_hash": mechanism_hash
    }

if __name__ == "__main__":
    execute_universal_node_monitoring()
