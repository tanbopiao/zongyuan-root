#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块B：多模态生产矩阵
- 任务类型：text / image / video / audio / drama（短剧）
- 节点能力：每节点声明支持模态 + 并发容量 + 单位成本
- 最优稳态分配：能力匹配 + 容量约束下成本最小（三维稳态：利益/风险/成本）
- 输出：分配矩阵、总成本、利用率、完成率
"""
import random


# 默认节点能力（对齐 ZONGYUAN-ROOT 真实节点布局）
DEFAULT_NODES = [
    {"id": "hub-central-agent", "cap": ["text", "audio"], "capacity": 4, "cost": 1.0},
    {"id": "node-cloud-worker", "cap": ["text", "image", "video"], "capacity": 3, "cost": 1.5},
    {"id": "node-gpu-edge",     "cap": ["image", "video", "drama"], "capacity": 2, "cost": 2.0},
    {"id": "node-edge-sync",    "cap": ["text"], "capacity": 2, "cost": 0.8},
    {"id": "node-dev-doubao",   "cap": ["text", "audio", "image"], "capacity": 3, "cost": 1.2},
]

MODALITY_COST = {"text": 0.5, "audio": 1.0, "image": 2.0, "video": 3.0, "drama": 4.0}


def make_tasks(n=20, seed=5):
    """确定性生成多模态任务队列"""
    rng = random.Random(seed)
    modalities = list(MODALITY_COST)
    tasks = []
    for i in range(n):
        m = modalities[i % len(modalities)]
        tasks.append({
            "id": f"task-{i:03d}", "modality": m,
            "load": rng.randint(1, 2), "priority": i % 3,
        })
    return tasks


class MultimodalMatrix:
    def __init__(self, nodes=None):
        self.nodes = nodes or DEFAULT_NODES
        self.assignment = {}    # task_id -> node_id
        self.usage = {n["id"]: 0 for n in self.nodes}

    def assign(self, tasks):
        """能力匹配 + 容量约束 + 成本最小（含模态成本与节点成本加权）"""
        self.assignment = {}
        self.usage = {n["id"]: 0 for n in self.nodes}
        dropped = 0
        for t in sorted(tasks, key=lambda x: -x["priority"]):
            best = None
            best_cost = float("inf")
            for nd in self.nodes:
                if t["modality"] not in nd["cap"]:
                    continue
                if self.usage[nd["id"]] + t["load"] > nd["capacity"]:
                    continue
                cost = nd["cost"] * t["load"] + MODALITY_COST[t["modality"]]
                if cost < best_cost:
                    best_cost = cost
                    best = nd["id"]
            if best:
                self.assignment[t["id"]] = best
                self.usage[best] += t["load"]
            else:
                dropped += 1
        return self

    def stats(self):
        total_cost = 0.0
        modality_dist = {}
        for t_id, n_id in self.assignment.items():
            total_cost += 1.0  # 简化：按节点成本累加
        # 重新按真实成本计算
        total_cost = 0.0
        task_map = {t["id"]: t for t in self.tasks}
        for t_id, n_id in self.assignment.items():
            t = task_map[t_id]
            total_cost += self._node(n_id)["cost"] * t["load"] + MODALITY_COST[t["modality"]]
            modality_dist[t["modality"]] = modality_dist.get(t["modality"], 0) + 1
        total_cap = sum(n["capacity"] for n in self.nodes)
        total_used = sum(self.usage.values())
        return {
            "tasks_total": len(self.tasks),
            "assigned": len(self.assignment),
            "dropped": len(self.tasks) - len(self.assignment),
            "assign_rate": round(100.0 * len(self.assignment) / len(self.tasks), 1),
            "total_cost": round(total_cost, 1),
            "capacity_util": round(100.0 * total_used / total_cap, 1),
            "modality_dist": modality_dist,
            "usage": self.usage,
            "assignment": self.assignment,
        }

    def _node(self, nid):
        for nd in self.nodes:
            if nd["id"] == nid:
                return nd
        raise KeyError(nid)

    def run(self, tasks):
        self.tasks = tasks
        return self.assign(tasks)


def run_matrix(task_count=20, seed=5):
    m = MultimodalMatrix()
    m.run(make_tasks(task_count, seed=seed))
    return m.stats()
