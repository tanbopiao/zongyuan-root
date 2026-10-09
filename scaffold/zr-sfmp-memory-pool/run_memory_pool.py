#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zr-sfmp-memory-pool 入口
用法：
  python3 run_memory_pool.py                     # 标准联邦仿真（5节点+重复+冲突）
  python3 run_memory_pool.py --nodes 5 --memory 40
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sfmp.memory import MemoryPool          # noqa: E402
from sfmp.federate import FederatedMemoryPool  # noqa: E402
from sfmp.report import to_json, to_html    # noqa: E402


def build_simulation(node_count=5, memory_per_node=8):
    """构建联邦仿真：多节点写入含重复表述与冲突对的记忆"""
    nodes = ["hub-central-agent", "node-cloud-worker", "node-gpu-edge",
             "node-edge-sync", "node-dev-doubao"][:node_count]
    base_topics = [
        ("sys.version", "内核V5.6-ROOTFIXED运行中"),
        ("truth.purity", "真值纯度评分100"),
        ("dag.height", "Merkle主链高度1400"),
        ("efuse.count", "eFuse熔断总数768"),
        ("zero.cost", "零成本元规则：默认零成本，付费需审批"),
        ("memory.anchor", "锚定Ω₀⊂⊙∞⊂Ω全域溯源"),
        ("deploy.channel", "飞书审批自动部署通道"),
        ("ssh.access", "SSH密钥池自动申领闭环"),
    ]
    pools = {}
    for ni, nid in enumerate(nodes):
        p = MemoryPool(node_id=nid)
        for i in range(memory_per_node):
            topic, val = base_topics[(ni * memory_per_node + i) % len(base_topics)]
            # 注入重复表述：同一 topic 多节点写入相同内容 → 跨节点去重
            # 注入冲突对：特定 key 高低置信度版本 → 冲突消解
            conf = 0.85 + (i % 3) * 0.05
            if (ni + i) % 7 == 0:
                p.write(f"{topic}.dup{i}", f"{val}（补充说明{i}）", confidence=conf, layer="short")
            if (ni + i) % 9 == 0:
                p.write(topic, f"{val}【冲突版本{ni}】", confidence=conf + 0.1, layer="short")
            else:
                p.write(topic, val, confidence=conf, layer="short" if i % 2 else "long")
        # 每节点升华一条为真值沉淀
        p.promote(base_topics[0][0], layer="truth")
        pools[nid] = p
    return pools


def main():
    ap = argparse.ArgumentParser(description="ZONGYUAN-ROOT SFMP 联邦记忆池")
    ap.add_argument("--nodes", type=int, default=5)
    ap.add_argument("--memory", type=int, default=8)
    ap.add_argument("--out-dir", default="reports")
    args = ap.parse_args()

    pools = build_simulation(node_count=args.nodes, memory_per_node=args.memory)
    fmp = FederatedMemoryPool()
    for p in pools.values():
        fmp.add_pool(p)
    fmp.merge()

    # 检索验证
    hits = [e.to_dict() for e in fmp.search(keyword="真值")]

    os.makedirs(args.out_dir, exist_ok=True)
    name = "SFMP-STD"
    to_json({"stats": fmp.stats(),
             "entries": [e.to_dict() for e in fmp.entries()],
             "conflicts": fmp.conflicts,
             "search_hits": hits}, os.path.join(args.out_dir, f"{name}.json"))
    to_html(fmp, path=os.path.join(args.out_dir, f"{name}.html"))

    print(json.dumps(fmp.stats(), ensure_ascii=False, indent=2))
    print(f"检索验证('真值'): {len(hits)} 条命中")
    print(f"✅ 报告: {args.out_dir}/{name}.json / .html")


if __name__ == "__main__":
    main()
