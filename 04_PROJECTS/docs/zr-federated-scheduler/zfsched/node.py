#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
节点模型：多节点联邦拓扑（本地/云端/GPU/边缘/主控）
"""
from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class Node:
    node_id: str
    role: str            # hub / worker / gpu / edge
    capacity: int        # 并发容量
    priority: int        # 认领优先级（数字越小越优先）
    alive: bool = True
    busy: int = 0        # 当前执行中任务数
    last_heartbeat: float = field(default_factory=time.time)
    heartbeat_ttl: float = 60.0   # 心跳超时阈值（秒），须大于调度 tick 步长(30s)
    total_done: int = 0
    total_failed: int = 0

    def heartbeat_now(self):
        self.last_heartbeat = time.time()
        self.alive = True

    def is_stale(self, now: float) -> bool:
        return (now - self.last_heartbeat) > self.heartbeat_ttl

    def can_take(self) -> bool:
        return self.alive and self.busy < self.capacity

    def to_dict(self):
        return {
            "node_id": self.node_id, "role": self.role, "capacity": self.capacity,
            "priority": self.priority, "alive": self.alive, "busy": self.busy,
            "last_heartbeat": time.strftime("%H:%M:%S", time.localtime(self.last_heartbeat)),
            "total_done": self.total_done, "total_failed": self.total_failed,
        }


def default_nodes():
    """默认五节点联邦拓扑（对齐 ZONGYUAN-ROOT 真实节点布局）"""
    return [
        Node("hub-central-agent", "hub",   4, 1),
        Node("node-cloud-worker", "worker", 3, 2),
        Node("node-gpu-edge",     "gpu",   2, 3),
        Node("node-edge-sync",    "edge",  2, 4),
        Node("node-dev-doubao",   "worker", 3, 2),
    ]
