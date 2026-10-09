#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联邦汇聚：多节点记忆池合并 → 联邦记忆池
- 汇聚：按 key 归并，同 key 多值冲突 → 全局置信度+时间仲裁
- 输出：各节点贡献度、跨节点重复率、冲突清单、最终联邦记忆
"""
import time
from .memory import MemoryPool, MemoryEntry, _fingerprint, _jaccard_similarity


class FederatedMemoryPool:
    def __init__(self):
        self.pools: dict = {}       # node_id -> MemoryPool
        self.merged: dict = {}      # key -> MemoryEntry（联邦统一视图）
        self.conflicts: list = []   # 冲突清单

    def add_pool(self, pool: MemoryPool):
        self.pools[pool.node_id] = pool

    def merge(self):
        """联邦汇聚：按 key 归并全部节点记忆，冲突按置信度+时间仲裁"""
        self.merged = {}
        self.conflicts = []
        for node_id, pool in self.pools.items():
            for key, e in pool.entries.items():
                if key not in self.merged:
                    self.merged[key] = e
                    continue
                cur = self.merged[key]
                # 冲突：同 key 不同指纹
                if cur.fingerprint != e.fingerprint:
                    self.conflicts.append({
                        "key": key, "value_a": cur.value, "node_a": cur.source_node,
                        "value_b": e.value, "node_b": e.source_node,
                    })
                    # 仲裁：置信度高者胜；持平则更新时间新者胜
                    if e.confidence > cur.confidence or (
                            e.confidence == cur.confidence and e.updated_at > cur.updated_at):
                        self.merged[key] = e
                        cur.conflicts += 1
                    else:
                        e.conflicts += 1
                else:
                    # 同指纹：语义一致，取置信度高者，提升层级
                    if e.confidence > cur.confidence:
                        cur.confidence = e.confidence
                        cur.source_node = e.source_node
                    cur.layer = "long" if cur.layer != "truth" else "truth"
                    cur.updated_at = time.time()
        return self

    def cross_node_duplicates(self) -> int:
        """跨节点重复指纹数（不同 key 同指纹，或同 key 同指纹多节点）"""
        fps = {}
        for e in self.merged.values():
            fps.setdefault(e.fingerprint, set()).add(e.source_node)
        return sum(1 for nodes in fps.values() if len(nodes) > 1)

    def contribution(self) -> dict:
        """各节点贡献度：该节点写入且最终被采纳的记忆数"""
        contrib = {n: 0 for n in self.pools}
        for e in self.merged.values():
            contrib[e.source_node] = contrib.get(e.source_node, 0) + 1
        return contrib

    def stats(self):
        layers = {}
        for e in self.merged.values():
            layers[e.layer] = layers.get(e.layer, 0) + 1
        return {
            "nodes": len(self.pools),
            "federated_total": len(self.merged),
            "local_total": sum(p.stats()["total"] for p in self.pools.values()),
            "layers": layers,
            "conflicts": len(self.conflicts),
            "cross_node_duplicates": self.cross_node_duplicates(),
            "contribution": self.contribution(),
        }

    def search(self, keyword=None, tag=None, node=None, layer=None):
        """联邦统一检索（在汇聚后的 merged 上检索）"""
        results = []
        for e in self.merged.values():
            if keyword and keyword not in e.value and keyword not in e.key:
                continue
            if tag and tag not in e.tags:
                continue
            if node and e.source_node != node:
                continue
            if layer and e.layer != layer:
                continue
            e.access_count += 1
            results.append(e)
        return results

    def entries(self):
        return list(self.merged.values())
