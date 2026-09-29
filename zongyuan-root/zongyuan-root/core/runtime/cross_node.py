#!/usr/bin/env python3
"""跨节点协同 执行态：分发分片到节点+汇总"""
def dispatch(shards, nodes):
    return {nodes[i%len(nodes)]: shards[i] for i in range(len(shards))}
def collect(results):
    merged = []
    for r in results.values(): merged.extend(r if isinstance(r,list) else [r])
    return merged
if __name__ == "__main__":
    d = dispatch([[1,2],[3,4],[5,6]], ["node-A","node-B"])
    print(f"  分发: {d}")
    print(f"  汇总: {collect(d)}")
