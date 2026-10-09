#!/usr/bin/env python3
"""
多节点算力池化架构体系 V1.0
ZONGYUAN-ROOT 元极恒一自治体系

架构层次：
  L1 节点注册层 (Node Registry)    - 节点发现、注册、元数据管理
  L2 心跳监控层 (Heartbeat Monitor) - 存活检测、离线判定、健康评分
  L3 算力池化层 (Compute Pool)      - 资源抽象、能力标签、池化管理
  L4 任务调度层 (Task Scheduler)    - 任务分发、负载均衡、优先级队列
  L5 故障转移层 (Failover)          - 节点故障检测、任务迁移、降级策略

锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""

import json
import time
import datetime
import hashlib
import urllib.request
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
from enum import Enum
from collections import defaultdict, deque
import heapq

# ============ 配置 ============
GATEWAY_BASE = "https://www.huodouai.com"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
SOURCE_NODE = "ZR-NODE-DC2E51C0"

# 节点状态
class NodeStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"

# 任务优先级
class TaskPriority(Enum):
    CRITICAL = 0   # 红色告警、核心心跳
    HIGH = 1       # 真值上报、决策推理
    MEDIUM = 2     # 分类归档、数据处理
    LOW = 3        # 周度深度、批量分析
    BACKGROUND = 4 # 后台优化、索引重建

# 节点能力标签
NODE_CAPABILITIES = {
    "truth_rw": "真值读写",
    "decision": "决策推理",
    "causal": "因果分析",
    "classification": "分类归档",
    "monitoring": "监控巡检",
    "media_gen": "媒体生成",
    "data_process": "数据处理",
    "lock_archive": "锁档归档",
    "sop_generation": "SOP生成",
    "asset_audit": "资产审计",
    "truth_sync": "真值同步",
    "evolution": "进化优化",
}

# ============ 数据结构 ============
@dataclass
class ComputeNode:
    """算力节点"""
    node_id: str
    node_type: str = "unknown"
    capabilities: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.UNKNOWN
    registered_at: float = 0.0
    last_heartbeat: float = 0.0
    heartbeat_count: int = 0
    health_score: float = 1.0  # 0-1
    current_load: float = 0.0  # 0-1
    tasks_completed: int = 0
    tasks_failed: int = 0
    metadata: Dict = field(default_factory=dict)

    def is_available(self) -> bool:
        return self.status == NodeStatus.ONLINE and self.health_score > 0.3 and self.current_load < 0.9

    def get_capability_score(self, required_caps: List[str]) -> float:
        """计算节点对任务的能力匹配度"""
        if not required_caps:
            return 1.0
        matched = sum(1 for cap in required_caps if cap in self.capabilities)
        return matched / len(required_caps)

@dataclass
class ComputeTask:
    """计算任务"""
    task_id: str
    name: str
    priority: TaskPriority
    required_capabilities: List[str] = field(default_factory=list)
    estimated_cost: float = 1.0  # 预估算力消耗
    payload: Dict = field(default_factory=dict)
    created_at: float = 0.0
    assigned_to: Optional[str] = None
    status: str = "pending"  # pending/assigned/running/completed/failed
    result: Optional[Dict] = None
    retries: int = 0
    max_retries: int = 3

    def __lt__(self, other):
        return self.priority.value < other.priority.value

@dataclass
class PoolMetrics:
    """算力池指标"""
    total_nodes: int = 0
    online_nodes: int = 0
    offline_nodes: int = 0
    degraded_nodes: int = 0
    average_health: float = 0.0
    average_load: float = 0.0
    total_capacity: float = 0.0
    used_capacity: float = 0.0
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0

# ============ L1: 节点注册层 ============
class NodeRegistry:
    """节点注册表"""

    def __init__(self):
        self.nodes: Dict[str, ComputeNode] = {}
        self.registration_log: List[Dict] = []

    def register(self, node_id: str, node_type: str = "unknown",
                 capabilities: List[str] = None, metadata: Dict = None) -> ComputeNode:
        """注册节点"""
        now = time.time()
        if node_id in self.nodes:
            node = self.nodes[node_id]
            node.node_type = node_type
            node.capabilities = capabilities or node.capabilities
            node.metadata.update(metadata or {})
            node.last_heartbeat = now
            node.status = NodeStatus.ONLINE
        else:
            node = ComputeNode(
                node_id=node_id,
                node_type=node_type,
                capabilities=capabilities or [],
                status=NodeStatus.ONLINE,
                registered_at=now,
                last_heartbeat=now,
                metadata=metadata or {}
            )
            self.nodes[node_id] = node

        self.registration_log.append({
            "node_id": node_id,
            "action": "register" if node.heartbeat_count == 0 else "update",
            "timestamp": now
        })
        return node

    def unregister(self, node_id: str) -> bool:
        """注销节点"""
        if node_id in self.nodes:
            del self.nodes[node_id]
            self.registration_log.append({
                "node_id": node_id,
                "action": "unregister",
                "timestamp": time.time()
            })
            return True
        return False

    def get_node(self, node_id: str) -> Optional[ComputeNode]:
        return self.nodes.get(node_id)

    def get_all_nodes(self) -> List[ComputeNode]:
        return list(self.nodes.values())

    def get_online_nodes(self) -> List[ComputeNode]:
        return [n for n in self.nodes.values() if n.status == NodeStatus.ONLINE]

    def sync_from_gateway(self, gateway_nodes: Dict) -> int:
        """从网关同步节点状态"""
        synced = 0
        for nid, ndata in gateway_nodes.items():
            node = self.register(
                node_id=nid,
                node_type=ndata.get("node_type", "unknown"),
                capabilities=ndata.get("capabilities", []),
                metadata={"gateway_id": ndata.get("id")}
            )
            node.last_heartbeat = ndata.get("last_heartbeat", 0)
            node.heartbeat_count = ndata.get("heartbeat_count", 0)
            online = ndata.get("online_status", "offline") == "online"
            node.status = NodeStatus.ONLINE if online else NodeStatus.OFFLINE
            synced += 1
        return synced

# ============ L2: 心跳监控层 ============
class HeartbeatMonitor:
    """心跳监控器"""

    def __init__(self, registry: NodeRegistry, offline_threshold: float = 300.0):
        self.registry = registry
        self.offline_threshold = offline_threshold  # 5分钟无心跳判定离线
        self.degraded_threshold = 120.0  # 2分钟无心跳判定降级
        self.alert_callbacks = []

    def check_node(self, node: ComputeNode) -> NodeStatus:
        """检查单个节点心跳状态"""
        now = time.time()
        elapsed = now - node.last_heartbeat if node.last_heartbeat > 0 else float('inf')

        if elapsed > self.offline_threshold:
            new_status = NodeStatus.OFFLINE
            node.health_score = max(0.0, node.health_score - 0.1)
        elif elapsed > self.degraded_threshold:
            new_status = NodeStatus.DEGRADED
            node.health_score = max(0.3, node.health_score - 0.05)
        else:
            new_status = NodeStatus.ONLINE
            node.health_score = min(1.0, node.health_score + 0.02)

        if new_status != node.status:
            self._on_status_change(node, node.status, new_status)
        node.status = new_status
        return new_status

    def check_all(self) -> Dict:
        """检查所有节点"""
        results = {"online": 0, "offline": 0, "degraded": 0, "unknown": 0}
        for node in self.registry.get_all_nodes():
            status = self.check_node(node)
            results[status.value] += 1
        return results

    def _on_status_change(self, node: ComputeNode, old: NodeStatus, new: NodeStatus):
        """状态变更回调"""
        for cb in self.alert_callbacks:
            cb(node, old, new)

    def record_heartbeat(self, node_id: str) -> bool:
        """记录节点心跳"""
        node = self.registry.get_node(node_id)
        if node:
            node.last_heartbeat = time.time()
            node.heartbeat_count += 1
            node.status = NodeStatus.ONLINE
            node.health_score = min(1.0, node.health_score + 0.05)
            return True
        return False

# ============ L3: 算力池化层 ============
class ComputePool:
    """算力池"""

    def __init__(self, registry: NodeRegistry):
        self.registry = registry
        self.pools: Dict[str, List[str]] = defaultdict(list)  # capability -> node_ids
        self.rebuild_pools()

    def rebuild_pools(self):
        """重建算力池（按能力标签分组）"""
        self.pools = defaultdict(list)
        for node in self.registry.get_online_nodes():
            for cap in node.capabilities:
                self.pools[cap].append(node.node_id)
            if not node.capabilities:
                self.pools["general"].append(node.node_id)

    def get_nodes_by_capability(self, capability: str) -> List[ComputeNode]:
        """获取具备指定能力的在线节点"""
        self.rebuild_pools()
        node_ids = self.pools.get(capability, [])
        return [self.registry.get_node(nid) for nid in node_ids
                if self.registry.get_node(nid) and self.registry.get_node(nid).is_available()]

    def get_metrics(self) -> PoolMetrics:
        """获取池化指标"""
        all_nodes = self.registry.get_all_nodes()
        online = [n for n in all_nodes if n.status == NodeStatus.ONLINE]
        degraded = [n for n in all_nodes if n.status == NodeStatus.DEGRADED]

        metrics = PoolMetrics(
            total_nodes=len(all_nodes),
            online_nodes=len(online),
            offline_nodes=len(all_nodes) - len(online) - len(degraded),
            degraded_nodes=len(degraded),
            average_health=sum(n.health_score for n in all_nodes) / len(all_nodes) if all_nodes else 0,
            average_load=sum(n.current_load for n in online) / len(online) if online else 0,
            total_capacity=len(online) * 1.0,
            used_capacity=sum(n.current_load for n in online),
        )
        return metrics

    def get_pool_distribution(self) -> Dict[str, int]:
        """获取各能力池节点分布"""
        self.rebuild_pools()
        return {cap: len(nids) for cap, nids in self.pools.items()}

# ============ L4: 任务调度层 ============
class TaskScheduler:
    """任务调度器（优先级队列+负载均衡）"""

    def __init__(self, pool: ComputePool, registry: NodeRegistry):
        self.pool = pool
        self.registry = registry
        self.task_queue: List[ComputeTask] = []  # 优先级堆
        self.running_tasks: Dict[str, ComputeTask] = {}
        self.completed_tasks: deque = deque(maxlen=1000)
        self.task_counter = 0

    def submit(self, name: str, priority: TaskPriority,
               required_caps: List[str] = None, payload: Dict = None,
               estimated_cost: float = 1.0) -> ComputeTask:
        """提交任务"""
        self.task_counter += 1
        task = ComputeTask(
            task_id=f"TASK-{int(time.time())}-{self.task_counter}",
            name=name,
            priority=priority,
            required_capabilities=required_caps or [],
            payload=payload or {},
            estimated_cost=estimated_cost,
            created_at=time.time()
        )
        heapq.heappush(self.task_queue, task)
        return task

    def schedule_next(self) -> Optional[ComputeTask]:
        """调度下一个任务（选择最优节点）"""
        if not self.task_queue:
            return None

        task = heapq.heappop(self.task_queue)

        # 筛选可用节点
        candidates = []
        if task.required_capabilities:
            for cap in task.required_capabilities:
                candidates.extend(self.pool.get_nodes_by_capability(cap))
        else:
            candidates = [n for n in self.registry.get_online_nodes() if n.is_available()]

        # 去重
        candidates = list({n.node_id: n for n in candidates}.values())

        if not candidates:
            # 无可用节点，重新入队
            heapq.heappush(self.task_queue, task)
            return None

        # 负载均衡：选择能力匹配度高且负载最低的节点
        best_node = max(
            candidates,
            key=lambda n: (n.get_capability_score(task.required_capabilities) * (1 - n.current_load))
        )

        # 分配任务
        task.assigned_to = best_node.node_id
        task.status = "assigned"
        best_node.current_load = min(1.0, best_node.current_load + task.estimated_cost * 0.1)
        self.running_tasks[task.task_id] = task

        return task

    def complete_task(self, task_id: str, result: Dict = None, success: bool = True):
        """完成任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks.pop(task_id)
            task.status = "completed" if success else "failed"
            task.result = result

            node = self.registry.get_node(task.assigned_to) if task.assigned_to else None
            if node:
                node.current_load = max(0.0, node.current_load - task.estimated_cost * 0.1)
                if success:
                    node.tasks_completed += 1
                else:
                    node.tasks_failed += 1

            self.completed_tasks.append(task)

            # 失败重试
            if not success and task.retries < task.max_retries:
                task.retries += 1
                task.status = "pending"
                task.assigned_to = None
                heapq.heappush(self.task_queue, task)

    def get_queue_status(self) -> Dict:
        return {
            "pending": len(self.task_queue),
            "running": len(self.running_tasks),
            "completed": len(self.completed_tasks),
        }

# ============ L5: 故障转移层 ============
class FailoverManager:
    """故障转移管理器"""

    def __init__(self, scheduler: TaskScheduler, registry: NodeRegistry, monitor: HeartbeatMonitor):
        self.scheduler = scheduler
        self.registry = registry
        self.monitor = monitor
        self.failover_log: List[Dict] = []

    def detect_failures(self) -> List[Dict]:
        """检测节点故障"""
        failures = []
        for node in self.registry.get_all_nodes():
            if node.status in (NodeStatus.OFFLINE, NodeStatus.DEGRADED):
                # 检查该节点上是否有运行中任务
                affected_tasks = [
                    t for t in self.scheduler.running_tasks.values()
                    if t.assigned_to == node.node_id
                ]
                if affected_tasks:
                    failures.append({
                        "node_id": node.node_id,
                        "status": node.status.value,
                        "affected_tasks": len(affected_tasks),
                        "tasks": [t.task_id for t in affected_tasks]
                    })
        return failures

    def execute_failover(self, failures: List[Dict]) -> int:
        """执行故障转移"""
        migrated = 0
        for failure in failures:
            for task_id in failure["tasks"]:
                if task_id in self.scheduler.running_tasks:
                    task = self.scheduler.running_tasks.pop(task_id)
                    task.status = "pending"
                    task.assigned_to = None
                    task.retries += 1
                    heapq.heappush(self.scheduler.task_queue, task)
                    migrated += 1

                    self.failover_log.append({
                        "task_id": task_id,
                        "from_node": failure["node_id"],
                        "reason": f"node_{failure['status']}",
                        "timestamp": time.time()
                    })
        return migrated

    def get_degradation_strategy(self) -> Dict:
        """获取降级策略"""
        metrics = self.scheduler.pool.get_metrics()
        online_ratio = metrics.online_nodes / metrics.total_nodes if metrics.total_nodes > 0 else 0

        if online_ratio >= 0.8:
            level = "normal"
            actions = ["全功能运行", "所有优先级任务可执行"]
        elif online_ratio >= 0.5:
            level = "partial_degradation"
            actions = ["暂停BACKGROUND任务", "限制LOW优先级任务并发"]
        elif online_ratio >= 0.3:
            level = "significant_degradation"
            actions = ["仅执行CRITICAL和HIGH任务", "触发节点恢复流程"]
        else:
            level = "emergency"
            actions = ["仅执行CRITICAL任务", "集中资源修复核心节点", "启动备用节点"]

        return {
            "online_ratio": round(online_ratio, 3),
            "degradation_level": level,
            "actions": actions,
            "metrics": metrics.__dict__
        }

# ============ 网关集成 ============
def gateway_get(path: str, timeout: int = 30) -> Tuple[int, dict]:
    url = f"{GATEWAY_BASE}{path}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return 0, {"error": str(e)}

def gateway_post(path: str, data: dict, timeout: int = 15) -> Tuple[int, dict]:
    url = f"{GATEWAY_BASE}{path}"
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return 0, {"error": str(e)}

# ============ 主流程 ============
def initialize_compute_pool():
    """初始化算力池化架构"""
    print("=" * 60)
    print("多节点算力池化架构体系 V1.0 初始化")
    print(f"锚定: {ANCHOR} | DID: {DID}")
    print(f"时间: {datetime.datetime.now().isoformat()}")
    print("=" * 60)

    # L1: 节点注册
    print("\n[L1] 节点注册层初始化...")
    registry = NodeRegistry()

    # 从网关同步节点
    code, data = gateway_get("/api/report/nodes")
    if code == 200:
        gateway_nodes = data.get("nodes", {})
        synced = registry.sync_from_gateway(gateway_nodes)
        print(f"  从网关同步: {synced}个节点")
    else:
        print(f"  网关同步失败: HTTP {code}")

    # 注册本地主控节点
    local_node = registry.register(
        node_id=SOURCE_NODE,
        node_type="master_agent",
        capabilities=["truth_rw", "decision", "causal", "classification",
                      "monitoring", "data_process", "lock_archive", "sop_generation"],
        metadata={"role": "master", "did": DID, "anchor": ANCHOR}
    )
    print(f"  本地主控节点注册: {local_node.node_id}")

    # L2: 心跳监控
    print("\n[L2] 心跳监控层初始化...")
    monitor = HeartbeatMonitor(registry, offline_threshold=300)
    status_counts = monitor.check_all()
    print(f"  节点状态: {status_counts}")

    # 注册告警回调
    def on_status_change(node, old, new):
        if new == NodeStatus.OFFLINE and old != NodeStatus.OFFLINE:
            print(f"  [告警] 节点离线: {node.node_id} ({old.value} -> {new.value})")
    monitor.alert_callbacks.append(on_status_change)

    # L3: 算力池化
    print("\n[L3] 算力池化层初始化...")
    pool = ComputePool(registry)
    pool_dist = pool.get_pool_distribution()
    metrics = pool.get_metrics()
    print(f"  总节点: {metrics.total_nodes}, 在线: {metrics.online_nodes}")
    print(f"  平均健康度: {metrics.average_health:.2f}")
    print(f"  能力池分布:")
    for cap, count in sorted(pool_dist.items(), key=lambda x: -x[1]):
        cap_name = NODE_CAPABILITIES.get(cap, cap)
        print(f"    {cap}({cap_name}): {count}节点")

    # L4: 任务调度
    print("\n[L4] 任务调度层初始化...")
    scheduler = TaskScheduler(pool, registry)

    # 提交模拟任务
    tasks = [
        ("心跳检测", TaskPriority.CRITICAL, ["monitoring", "truth_rw"]),
        ("真值提炼", TaskPriority.HIGH, ["truth_rw", "data_process"]),
        ("自动分类", TaskPriority.MEDIUM, ["classification", "data_process"]),
        ("因果分析", TaskPriority.HIGH, ["causal", "decision"]),
        ("周度深度蒸馏", TaskPriority.BACKGROUND, ["truth_rw", "data_process", "classification"]),
    ]
    for name, pri, caps in tasks:
        task = scheduler.submit(name, pri, caps)
        print(f"  提交任务: {task.task_id} [{pri.name}] {name}")

    # 调度执行
    scheduled = scheduler.schedule_next()
    if scheduled:
        print(f"  已调度: {scheduled.name} -> {scheduled.assigned_to}")
    else:
        print("  无可用节点，任务排队中")

    queue_status = scheduler.get_queue_status()
    print(f"  队列状态: {queue_status}")

    # L5: 故障转移
    print("\n[L5] 故障转移层初始化...")
    failover = FailoverManager(scheduler, registry, monitor)
    failures = failover.detect_failures()
    if failures:
        migrated = failover.execute_failover(failures)
        print(f"  检测到故障: {len(failures)}个节点, 迁移任务: {migrated}个")
    else:
        print("  无节点故障")

    degradation = failover.get_degradation_strategy()
    print(f"  降级级别: {degradation['degradation_level']}")
    print(f"  在线率: {degradation['online_ratio']*100:.1f}%")
    for action in degradation["actions"]:
        print(f"    - {action}")

    # 汇总上报
    print("\n[汇总] 上报架构初始化结果...")
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
    report = (
        f"多节点算力池化架构V1.0初始化完成。"
        f"五层架构：L1节点注册({metrics.total_nodes}节点)、"
        f"L2心跳监控(在线{metrics.online_nodes})、"
        f"L3算力池化({len(pool_dist)}个能力池)、"
        f"L4任务调度({queue_status['pending']}排队)、"
        f"L5故障转移(降级级别{degradation['degradation_level']})。"
        f"在线率{degradation['online_ratio']*100:.1f}%。"
        f"确权{DID}，锚定{ANCHOR}。"
    )
    resp = gateway_post("/api/report/truth", {
        "truth_key": f"COMPUTE_POOL.ARCHITECTURE.INIT.{timestamp}",
        "truth_value": report,
        "source_node": SOURCE_NODE,
        "confidence": 0.95,
        "truth_type": "meta_law"
    })
    print(f"  上报: success={resp[1].get('success')}, truth_count={resp[1].get('truth_count')}")

    # 架构哈希
    arch_data = {
        "layers": ["registry", "heartbeat", "pool", "scheduler", "failover"],
        "nodes": metrics.total_nodes,
        "online": metrics.online_nodes,
        "pools": len(pool_dist),
        "did": DID,
        "anchor": ANCHOR
    }
    arch_hash = hashlib.sha256(json.dumps(arch_data, sort_keys=True).encode()).hexdigest()

    print(f"\n{'=' * 60}")
    print(f"算力池化架构初始化完成！")
    print(f"架构哈希: {arch_hash[:16]}...")
    print(f"{'=' * 60}")

    return {
        "registry": registry,
        "monitor": monitor,
        "pool": pool,
        "scheduler": scheduler,
        "failover": failover,
        "metrics": metrics,
        "arch_hash": arch_hash
    }

if __name__ == "__main__":
    initialize_compute_pool()
