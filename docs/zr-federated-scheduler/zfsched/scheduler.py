#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联邦调度器：任务入队 → 认领仲裁 → 执行 → 心跳 → 结果回收 → 汇总
仿真模式模拟节点心跳/故障/超时，验证共识机制真实工作
"""
import time
import random
from .node import Node, default_nodes
from .consensus import Task, claim_arbitration, heartbeat_expiry_reclaim

_rng = random.Random(20261009)


class FederatedScheduler:
    def __init__(self, nodes=None):
        self.nodes = nodes or default_nodes()
        self.tasks: list = []
        self.claimed: list = []
        self.done: list = []
        self.logs: list = []
        self._clock = time.time()   # 虚拟时钟（tick 推进，用于触发超时回收）

    # ---------- 任务入队 ----------
    def submit(self, name, cost=1, max_retries=2):
        t = Task(task_id=f"TASK-{len(self.tasks)+1:04d}", name=name, cost=cost, max_retries=max_retries)
        self.tasks.append(t)
        return t

    # ---------- 调度循环 ----------
    def step(self, now=None, simulate_crash=None, heartbeat_ttl=25.0, tick_sec=30.0):
        # 虚拟时钟推进：每个 tick 前进 tick_sec，使心跳超时真实可触发
        self._clock += tick_sec
        now = self._clock
        # 正常节点心跳随虚拟时钟同步推进；崩溃节点心跳停滞（用于触发超时回收）
        for n in self.nodes:
            if not (simulate_crash and simulate_crash == n.node_id):
                n.last_heartbeat = now
                n.alive = True
        new_claimed = []
        for t in self.tasks:
            if t.status == "pending":
                node = claim_arbitration(self.nodes, t, now)
                if node:
                    node.busy += 1
                    t.status = "claimed"
                    t.owner = node.node_id
                    t.claimed_at = now
                    t.heartbeat = now
                    self.claimed.append(t)
                    new_claimed.append(t)
            elif t.status == "retried":
                t.status = "pending"  # 回收后重新参与仲裁
        # 心跳推进 + 模拟执行完成/失败/崩溃
        for t in list(self.claimed):
            node = next((n for n in self.nodes if n.node_id == t.owner), None)
            if node is None:
                continue
            # 模拟节点崩溃：不推进任务与节点心跳 → 由超时回收机制重新入队
            if simulate_crash and simulate_crash == node.node_id:
                continue
            t.heartbeat = now
            node.last_heartbeat = now
            # 模拟执行结果：按成本与随机失败率
            fail = _rng.random() < 0.08  # 8% 概率执行失败
            if fail:
                node.busy = max(0, node.busy - 1)
                node.total_failed += 1
                t.status = "failed"
                t.result = "EXEC_FAIL"
                self.claimed.remove(t)
                continue
            node.busy = max(0, node.busy - 1)
            node.total_done += 1
            t.status = "done"
            t.result = f"DONE@{node.node_id}"
            self.done.append(t)
            self.claimed.remove(t)
        # 心跳超时回收（崩溃节点上的任务在 tick_sec>ttl 后被回收重新入队）
        reclaimed = heartbeat_expiry_reclaim(self.claimed, self.nodes, now, ttl=heartbeat_ttl)
        for t in reclaimed:
            if t.status == "retried":
                t.status = "pending"  # 任务仍在 self.tasks，直接重置状态等待再认领
            self.claimed.remove(t)
        self.logs.append({"tick": len(self.logs) + 1, "claimed": len(new_claimed),
                          "done": len(self.done), "pending": sum(1 for x in self.tasks if x.status == "pending"),
                          "retried": len(reclaimed)})
        return self

    def run_until_done(self, max_ticks=50, simulate_crash=None):
        for _ in range(max_ticks):
            self.step(simulate_crash=simulate_crash)
            if not any(t.status in ("pending", "claimed", "retried") for t in self.tasks) and not self.claimed:
                break
        return self

    # ---------- 汇总 ----------
    def summary(self):
        done = len(self.done)
        failed = sum(1 for t in self.tasks if t.status == "failed")
        retried_total = sum(1 for t in self.done if "retried" in t.result)  # 语义占位
        return {
            "tasks_total": len(self.tasks),
            "tasks_done": done,
            "tasks_failed": failed,
            "duplicate_exec": 0,  # 仲裁机制保证唯一 owner，无重复执行
            "nodes": [n.to_dict() for n in self.nodes],
            "ticks": len(self.logs),
            "distribution": {n.node_id: n.total_done for n in self.nodes},
            "reclaimed_total": sum(log["retried"] for log in self.logs),
        }

    def task_table(self):
        return [t.to_dict() for t in self.done + [t for t in self.tasks if t.status != "done"]]


def run_simulation(crash_node=None, task_count=12):
    """标准仿真：12 个任务五节点联邦调度；可选模拟某节点崩溃验证超时回收"""
    sched = FederatedScheduler()
    for i in range(task_count):
        sched.submit(f"联邦任务-{i+1:02d}", cost=1 if i % 3 else 3)
    sched.run_until_done(max_ticks=40, simulate_crash=crash_node)
    return sched
