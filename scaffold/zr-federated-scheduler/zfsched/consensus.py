#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务模型 + 共识算法
- 认领仲裁：按节点优先级 → 负载 → 心跳新鲜度 排序，唯一认领，防多节点重复抢占
- 心跳超时回收：认领后心跳超时的任务重新入队
"""
from dataclasses import dataclass, field
import time
import uuid
from typing import Optional


@dataclass
class Task:
    task_id: str
    name: str
    cost: int = 1            # 估算消耗（轻量=1，重=3）
    max_retries: int = 2
    status: str = "pending"  # pending/claimed/running/done/failed/retried
    owner: str = ""
    retries: int = 0
    created_at: float = field(default_factory=time.time)
    claimed_at: Optional[float] = None
    heartbeat: Optional[float] = None
    result: str = ""

    def to_dict(self):
        return {
            "task_id": self.task_id, "name": self.name, "cost": self.cost,
            "status": self.status, "owner": self.owner, "retries": self.retries,
            "result": self.result[:80],
        }


def claim_arbitration(nodes, task: Task, now: float) -> Optional[object]:
    """
    认领仲裁共识：候选 = 存活 && 容量未满 && 心跳新鲜
    排序键：priority(升) → busy(升) → last_heartbeat(新优先)
    返回唯一被选中的节点；多节点同时抢同一任务时以该排序收敛到同一结果，避免重复执行
    """
    candidates = [n for n in nodes if n.can_take() and not n.is_stale(now)]
    if not candidates:
        return None
    candidates.sort(key=lambda n: (n.priority, n.busy, -n.last_heartbeat))
    return candidates[0]


def heartbeat_expiry_reclaim(tasks, nodes, now: float, ttl: float = 25.0):
    """
    心跳超时回收：任务认领后超过 ttl 无心跳 → 释放 owner 并重新入队（retries+1）
    防止节点崩溃导致任务卡死
    """
    reclaimed = []
    for t in tasks:
        if t.status == "claimed" and t.heartbeat and (now - t.heartbeat) > ttl:
            owner = next((n for n in nodes if n.node_id == t.owner), None)
            if owner:
                owner.busy = max(0, owner.busy - 1)
                owner.total_failed += 1
            t.owner = ""
            t.claimed_at = None
            t.heartbeat = None
            t.retries += 1
            if t.retries > t.max_retries:
                t.status = "failed"
            else:
                t.status = "retried"
                reclaimed.append(t)
    return reclaimed
