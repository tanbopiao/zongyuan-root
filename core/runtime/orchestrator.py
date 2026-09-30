#!/usr/bin/env python3
"""OrganizerAgent 编排器 执行态：拆任务+分片+汇总"""
from runtime import adaptive_sharding as sh

def orchestrate(task_items, complexity=1.0):
    n = sh.adaptive_shard(len(task_items), complexity)
    chunks = [task_items[i::n] for i in range(n)]
    return {'shards': n, 'chunks': chunks, 'sizes': [len(c) for c in chunks]}

if __name__ == "__main__":
    items = list(range(30))
    plan = orchestrate(items, 1.0)
    print(f"  30项任务 → {plan['shards']}片, 各片大小:{plan['sizes']}")
