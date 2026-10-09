#!/usr/bin/env python3
"""
多节点协同框架 V1.0
ZONGYUAN-ROOT 全域进化第三维度

核心能力：
1. 任务自动分发与负载均衡
2. 节点能力评估与匹配
3. 故障自动检测与转移
4. 任务状态追踪与重试
5. 协同计算与结果聚合
6. 节点健康监测与评分
"""

import hashlib
import time
import uuid
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"           # 待分配
    ASSIGNED = "assigned"         # 已分配
    RUNNING = "running"           # 执行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    RETRYING = "retrying"         # 重试中
    CANCELLED = "cancelled"       # 已取消


class NodeStatus(Enum):
    """节点状态"""
    ONLINE = "online"             # 在线
    BUSY = "busy"                 # 忙碌
    IDLE = "idle"                 # 空闲
    OFFLINE = "offline"           # 离线
    DEGRADED = "degraded"         # 降级
    MAINTENANCE = "maintenance"   # 维护中


class LoadBalancingStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"           # 轮询
    LEAST_LOADED = "least_loaded"         # 最少负载
    BEST_CAPABILITY = "best_capability"   # 最佳能力匹配
    LEAST_RESPONSE = "least_response"     # 最快响应
    RANDOM = "random"                      # 随机


@dataclass
class Task:
    """任务"""
    task_id: str
    name: str
    description: str
    task_type: str
    required_capabilities: List[str] = field(default_factory=list)
    priority: int = 5  # 1-10, 10最高
    status: TaskStatus = TaskStatus.PENDING
    assigned_node: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    result: Optional[Dict] = None
    error: Optional[str] = None
    execution_log: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "required_capabilities": self.required_capabilities,
            "priority": self.priority,
            "status": self.status.value,
            "assigned_node": self.assigned_node,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata
        }


@dataclass
class CollaboratorNode:
    """协同节点"""
    node_id: str
    name: str
    endpoint: str
    capabilities: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.ONLINE
    current_load: int = 0  # 当前任务数
    max_load: int = 10
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    avg_response_time_ms: float = 0.0
    success_rate: float = 1.0
    health_score: float = 100.0
    last_heartbeat: float = field(default_factory=time.time)
    assigned_tasks: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def can_accept_task(self, required_caps: List[str] = None) -> bool:
        """检查节点是否能接受任务"""
        if self.status not in [NodeStatus.ONLINE, NodeStatus.IDLE]:
            return False
        if self.current_load >= self.max_load:
            return False
        if required_caps:
            return all(cap in self.capabilities for cap in required_caps)
        return True

    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "endpoint": self.endpoint,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "current_load": self.current_load,
            "max_load": self.max_load,
            "total_tasks_completed": self.total_tasks_completed,
            "total_tasks_failed": self.total_tasks_failed,
            "avg_response_time_ms": self.avg_response_time_ms,
            "success_rate": self.success_rate,
            "health_score": self.health_score,
            "last_heartbeat": self.last_heartbeat,
            "assigned_tasks_count": len(self.assigned_tasks),
            "metadata": self.metadata
        }


class MultiNodeCollaborationFramework:
    """多节点协同框架"""

    def __init__(self, load_balancing: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_LOADED):
        self.nodes: Dict[str, CollaboratorNode] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[str] = []  # 按优先级排序的任务ID
        self.completed_tasks: List[str] = []
        self.failed_tasks: List[str] = []
        self.load_balancing = load_balancing
        self.round_robin_index = 0
        self.collaboration_log: List[Dict] = []
        self.created_at = time.time()

    def register_node(self, node_id: str, name: str, endpoint: str,
                       capabilities: List[str] = None, max_load: int = 10) -> CollaboratorNode:
        """注册协同节点"""
        node = CollaboratorNode(
            node_id=node_id,
            name=name,
            endpoint=endpoint,
            capabilities=capabilities or [],
            max_load=max_load
        )
        self.nodes[node_id] = node
        self._log_event("node_registered", {"node_id": node_id, "name": name})
        return node

    def heartbeat(self, node_id: str, load: int = None) -> bool:
        """节点心跳"""
        if node_id not in self.nodes:
            return False
        node = self.nodes[node_id]
        node.last_heartbeat = time.time()
        if load is not None:
            node.current_load = load
        # 检查节点是否超时（超过60秒无心跳视为离线）
        if time.time() - node.last_heartbeat > 60:
            node.status = NodeStatus.OFFLINE
            node.health_score = max(0, node.health_score - 20)
        else:
            if node.status == NodeStatus.OFFLINE:
                node.status = NodeStatus.ONLINE
                node.health_score = min(100, node.health_score + 10)
        return True

    def create_task(self, name: str, description: str, task_type: str,
                    required_capabilities: List[str] = None,
                    priority: int = 5, max_retries: int = 3) -> Task:
        """创建任务"""
        task = Task(
            task_id=f"TASK-{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            task_type=task_type,
            required_capabilities=required_capabilities or [],
            priority=priority,
            max_retries=max_retries
        )
        self.tasks[task.task_id] = task
        self._insert_task_to_queue(task.task_id, priority)
        self._log_event("task_created", {"task_id": task.task_id, "name": name, "priority": priority})
        return task

    def _insert_task_to_queue(self, task_id: str, priority: int):
        """按优先级插入任务队列"""
        insert_pos = 0
        for i, tid in enumerate(self.task_queue):
            if self.tasks[tid].priority >= priority:
                insert_pos = i + 1
            else:
                break
        self.task_queue.insert(insert_pos, task_id)

    def get_eligible_nodes(self, required_caps: List[str] = None) -> List[CollaboratorNode]:
        """获取符合条件的节点"""
        eligible = []
        for node in self.nodes.values():
            if node.can_accept_task(required_caps):
                eligible.append(node)
        return eligible

    def select_node(self, task: Task) -> Optional[CollaboratorNode]:
        """根据负载均衡策略选择节点"""
        eligible = self.get_eligible_nodes(task.required_capabilities)
        if not eligible:
            return None

        if self.load_balancing == LoadBalancingStrategy.ROUND_ROBIN:
            node = eligible[self.round_robin_index % len(eligible)]
            self.round_robin_index += 1
            return node

        elif self.load_balancing == LoadBalancingStrategy.LEAST_LOADED:
            return min(eligible, key=lambda n: n.current_load)

        elif self.load_balancing == LoadBalancingStrategy.BEST_CAPABILITY:
            # 能力匹配度最高的节点
            def capability_match(node):
                if not task.required_capabilities:
                    return len(node.capabilities)
                matched = sum(1 for cap in task.required_capabilities if cap in node.capabilities)
                return matched / len(task.required_capabilities)
            return max(eligible, key=capability_match)

        elif self.load_balancing == LoadBalancingStrategy.LEAST_RESPONSE:
            return min(eligible, key=lambda n: n.avg_response_time_ms)

        elif self.load_balancing == LoadBalancingStrategy.RANDOM:
            import random
            return random.choice(eligible)

        return eligible[0]

    def assign_task(self, task_id: str) -> Dict:
        """分配任务"""
        task = self.tasks.get(task_id)
        if not task:
            return {"success": False, "error": "Task not found"}
        if task.status != TaskStatus.PENDING:
            return {"success": False, "error": f"Task is {task.status.value}, not pending"}

        node = self.select_node(task)
        if not node:
            return {"success": False, "error": "No eligible node available"}

        # 分配任务
        task.status = TaskStatus.ASSIGNED
        task.assigned_node = node.node_id
        task.started_at = time.time()
        node.current_load += 1
        node.assigned_tasks.append(task_id)

        # 从队列移除
        if task_id in self.task_queue:
            self.task_queue.remove(task_id)

        self._log_event("task_assigned", {"task_id": task_id, "node_id": node.node_id})
        return {"success": True, "task_id": task_id, "assigned_node": node.node_id}

    def complete_task(self, task_id: str, result: Dict = None) -> Dict:
        """完成任务"""
        task = self.tasks.get(task_id)
        if not task:
            return {"success": False, "error": "Task not found"}

        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.result = result or {}

        # 更新节点统计
        if task.assigned_node and task.assigned_node in self.nodes:
            node = self.nodes[task.assigned_node]
            node.current_load = max(0, node.current_load - 1)
            node.total_tasks_completed += 1
            if task_id in node.assigned_tasks:
                node.assigned_tasks.remove(task_id)
            # 更新成功率和响应时间
            total = node.total_tasks_completed + node.total_tasks_failed
            node.success_rate = node.total_tasks_completed / total if total > 0 else 1.0
            if task.started_at:
                duration = (task.completed_at - task.started_at) * 1000
                node.avg_response_time_ms = (node.avg_response_time_ms + duration) / 2

        self.completed_tasks.append(task_id)
        self._log_event("task_completed", {"task_id": task_id, "duration_ms": (task.completed_at - task.started_at) * 1000 if task.started_at else 0})
        return {"success": True, "task_id": task_id, "result": result}

    def fail_task(self, task_id: str, error: str) -> Dict:
        """任务失败（自动重试）"""
        task = self.tasks.get(task_id)
        if not task:
            return {"success": False, "error": "Task not found"}

        task.error = error
        task.retry_count += 1

        # 更新节点统计
        if task.assigned_node and task.assigned_node in self.nodes:
            node = self.nodes[task.assigned_node]
            node.current_load = max(0, node.current_load - 1)
            node.total_tasks_failed += 1
            node.health_score = max(0, node.health_score - 5)
            if task_id in node.assigned_tasks:
                node.assigned_tasks.remove(task_id)

        # 检查是否可以重试
        if task.retry_count < task.max_retries:
            task.status = TaskStatus.RETRYING
            task.assigned_node = None
            task.started_at = None
            self._insert_task_to_queue(task_id, task.priority)
            self._log_event("task_retrying", {"task_id": task_id, "retry_count": task.retry_count, "error": error})
            return {"success": True, "task_id": task_id, "status": "retrying", "retry_count": task.retry_count}
        else:
            task.status = TaskStatus.FAILED
            self.failed_tasks.append(task_id)
            self._log_event("task_failed", {"task_id": task_id, "error": error, "retries": task.retry_count})
            return {"success": True, "task_id": task_id, "status": "failed", "error": error}

    def process_task_queue(self, max_tasks: int = 5) -> List[Dict]:
        """处理任务队列（分配待处理任务）"""
        results = []
        tasks_to_process = min(max_tasks, len(self.task_queue))
        for _ in range(tasks_to_process):
            if not self.task_queue:
                break
            task_id = self.task_queue[0]  # 最高优先级
            result = self.assign_task(task_id)
            results.append(result)
        return results

    def get_collaboration_status(self) -> Dict:
        """获取协同状态总览"""
        status_counts = {}
        for task in self.tasks.values():
            s = task.status.value
            status_counts[s] = status_counts.get(s, 0) + 1

        node_stats = {
            "total": len(self.nodes),
            "online": sum(1 for n in self.nodes.values() if n.status in [NodeStatus.ONLINE, NodeStatus.IDLE]),
            "busy": sum(1 for n in self.nodes.values() if n.status == NodeStatus.BUSY),
            "offline": sum(1 for n in self.nodes.values() if n.status == NodeStatus.OFFLINE),
            "total_load": sum(n.current_load for n in self.nodes.values()),
            "avg_health_score": sum(n.health_score for n in self.nodes.values()) / len(self.nodes) if self.nodes else 0
        }

        return {
            "framework": "multi_node_collaboration_v1.0",
            "load_balancing_strategy": self.load_balancing.value,
            "total_tasks": len(self.tasks),
            "task_status_distribution": status_counts,
            "pending_queue_length": len(self.task_queue),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "node_statistics": node_stats,
            "total_collaboration_events": len(self.collaboration_log),
            "created_at": self.created_at
        }

    def _log_event(self, event_type: str, data: Dict):
        """记录协同事件"""
        self.collaboration_log.append({
            "event_type": event_type,
            "timestamp": time.time(),
            "data": data
        })


# 全局多节点协同框架实例
global_collaboration_framework = MultiNodeCollaborationFramework()


if __name__ == "__main__":
    print("=" * 60)
    print("ZONGYUAN-ROOT 多节点协同框架 V1.0 测试")
    print("=" * 60)

    # 注册节点
    print("\n【注册协同节点】")
    nodes = [
        ("CLOUD-MAIN", "云内核主节点", "http://123.207.202.158:8006", ["core_services", "truth_arbitration", "heavy_compute"], 10),
        ("LOCAL-WIN", "本地Windows管理端", "http://127.0.0.1:8899", ["management", "development", "light_compute"], 5),
        ("EDGE-001", "边缘计算节点", "http://edge-001:8080", ["data_collection", "edge_inference"], 3),
        ("CACHE-001", "缓存加速节点", "http://127.0.0.1:5000", ["git_cache", "object_storage", "cdn"], 8)
    ]

    for node_id, name, endpoint, caps, max_load in nodes:
        global_collaboration_framework.register_node(node_id, name, endpoint, caps, max_load)
        print(f"  ✅ {name} ({node_id}) - 能力: {caps} - 最大负载: {max_load}")

    # 创建任务
    print("\n【创建任务】")
    tasks = [
        ("真值校验任务", "对新提交的真值进行交叉验证", "truth_verification", ["truth_arbitration"], 8),
        ("资产归档任务", "将新资产生成哈希并归档到Merkle-DAG", "asset_archiving", ["core_services"], 6),
        ("边缘数据采集", "从边缘设备采集运行状态数据", "data_collection", ["data_collection"], 4),
        ("缓存预热任务", "预加载高频访问资产到缓存", "cache_warmup", ["git_cache", "object_storage"], 3),
        ("轻量计算任务", "执行轻量级数据处理", "light_compute", ["light_compute"], 5)
    ]

    for name, desc, task_type, caps, priority in tasks:
        task = global_collaboration_framework.create_task(name, desc, task_type, caps, priority)
        print(f"  ✅ {task.task_id}: {name} (优先级: {priority})")

    # 处理任务队列
    print("\n【处理任务队列（分配任务）】")
    results = global_collaboration_framework.process_task_queue(max_tasks=5)
    for result in results:
        if result.get("success"):
            print(f"  ✅ {result['task_id']} → {result['assigned_node']}")
        else:
            print(f"  ❌ {result.get('task_id', 'unknown')}: {result.get('error')}")

    # 模拟任务完成
    print("\n【模拟任务完成】")
    for task_id in list(global_collaboration_framework.tasks.keys())[:3]:
        result = global_collaboration_framework.complete_task(task_id, {"status": "success", "output": "task completed"})
        print(f"  ✅ {task_id}: 完成")

    # 模拟任务失败重试
    print("\n【模拟任务失败重试】")
    fail_task_id = list(global_collaboration_framework.tasks.keys())[3]
    result = global_collaboration_framework.fail_task(fail_task_id, "模拟执行错误")
    print(f"  ⚠️ {fail_task_id}: {result.get('status')} (重试次数: {result.get('retry_count')})")

    # 节点心跳
    print("\n【节点心跳更新】")
    for node_id in ["CLOUD-MAIN", "LOCAL-WIN", "EDGE-001"]:
        global_collaboration_framework.heartbeat(node_id)
        print(f"  ✅ {node_id} 心跳更新")

    # 获取协同状态
    print("\n【协同状态总览】")
    status = global_collaboration_framework.get_collaboration_status()
    print(f"  框架: {status['framework']}")
    print(f"  负载均衡策略: {status['load_balancing_strategy']}")
    print(f"  总任务数: {status['total_tasks']}")
    print(f"  任务状态分布: {status['task_status_distribution']}")
    print(f"  待处理队列: {status['pending_queue_length']}")
    print(f"  已完成: {status['completed_tasks']}")
    print(f"  失败: {status['failed_tasks']}")
    print(f"  节点统计: {status['node_statistics']}")
    print(f"  协同事件数: {status['total_collaboration_events']}")

    print("\n" + "=" * 60)
    print("✅ 多节点协同框架 V1.0 测试完成")
    print("=" * 60)
