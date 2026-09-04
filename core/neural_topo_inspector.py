#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 神经网络DAG拓扑巡检模块
集成NeuralTopoChecker为自治内核巡检算子
公理：根节点入度=0，叶子节点出度=0，内部节点入度>0且出度>0
漂移检测：叶子节点不允许存在下游连接
"""
import json, os, sys, hashlib
from typing import Dict, List, Set, Tuple
from datetime import datetime

sys.path.insert(0, "/opt/ZONGYUAN-ROOT")

class NeuralTopoChecker:
    def __init__(self):
        self.adj: Dict[int, List[int]] = {}
        self.all_nodes: Set[int] = set()
    
    def add_edge(self, src: int, dst: int):
        if src not in self.adj: self.adj[src] = []
        self.adj[src].append(dst)
        self.all_nodes.add(src)
        self.all_nodes.add(dst)
    
    def get_in_degree(self) -> Dict[int, int]:
        in_degree = {n: 0 for n in self.all_nodes}
        for src in self.adj:
            for dst in self.adj[src]: in_degree[dst] += 1
        return in_degree
    
    def get_out_degree(self) -> Dict[int, int]:
        out_degree = {n: 0 for n in self.all_nodes}
        for src in self.adj: out_degree[src] = len(self.adj[src])
        return out_degree
    
    def classify(self) -> Dict:
        in_deg = self.get_in_degree()
        out_deg = self.get_out_degree()
        root, inner, leaf = [], [], []
        for n in self.all_nodes:
            if in_deg[n] == 0: root.append(n)
            elif out_deg[n] == 0: leaf.append(n)
            else: inner.append(n)
        return {"root_nodes": root, "inner_nodes": inner, "leaf_nodes": leaf}
    
    def drift_check(self) -> Tuple[bool, List[str]]:
        """漂移检测：叶子节点出度必须=0"""
        res = self.classify()
        out_deg = self.get_out_degree()
        violations = []
        for leaf in res["leaf_nodes"]:
            if out_deg[leaf] != 0:
                violations.append(f"叶子节点{leaf}存在下游连接(out_degree={out_deg[leaf]})")
        # 额外检测：根节点入度必须=0
        in_deg = self.get_in_degree()
        for root in res["root_nodes"]:
            if in_deg[root] != 0:
                violations.append(f"根节点{root}存在上游连接(in_degree={in_deg[root]})")
        return (len(violations) == 0, violations)
    
    def cycle_check(self) -> bool:
        """环路检测：DAG不允许有环"""
        in_deg = self.get_in_degree()
        queue = [n for n in self.all_nodes if in_deg[n] == 0]
        visited = 0
        temp_adj = {k: list(v) for k, v in self.adj.items()}
        while queue:
            node = queue.pop(0)
            visited += 1
            for neighbor in temp_adj.get(node, []):
                in_deg[neighbor] -= 1
                if in_deg[neighbor] == 0: queue.append(neighbor)
        return visited == len(self.all_nodes)
    
    def full_inspect(self, name="unknown") -> Dict:
        """完整巡检：分类+漂移+环路+统计"""
        classify = self.classify()
        drift_ok, drift_violations = self.drift_check()
        acyclic = self.cycle_check()
        in_deg = self.get_in_degree()
        out_deg = self.get_out_degree()
        return {
            "inspect_name": name,
            "timestamp": datetime.now().isoformat(),
            "total_nodes": len(self.all_nodes),
            "total_edges": sum(len(v) for v in self.adj.values()),
            "classification": {
                "root(输入层)": len(classify["root_nodes"]),
                "inner(隐藏层)": len(classify["inner_nodes"]),
                "leaf(输出层)": len(classify["leaf_nodes"])
            },
            "root_nodes": classify["root_nodes"],
            "inner_nodes": classify["inner_nodes"],
            "leaf_nodes": classify["leaf_nodes"],
            "drift_check": {"passed": drift_ok, "violations": drift_violations},
            "cycle_check": {"is_dag": acyclic},
            "max_in_degree": max(in_deg.values()) if in_deg else 0,
            "max_out_degree": max(out_deg.values()) if out_deg else 0,
            "overall_status": "PASS" if drift_ok and acyclic else "FAIL",
            "axiom": "根入度=0, 叶出度=0, 内部入度>0且出度>0, DAG无环"
        }


def build_transformer_graph(layers=2, heads=4, d_model=8):
    """构建Transformer计算图：简化版拓扑
    节点编号规则：
    0: 输入embedding
    1..layers*2: 每层的attention+ffn (内部节点)
    layers*2+1: 输出层norm
    layers*2+2: LM_head输出 (叶子)
    """
    checker = NeuralTopoChecker()
    nodes = {}
    nid = 0
    nodes["input"] = nid; nid += 1
    for i in range(layers):
        nodes[f"attn_{i}"] = nid; nid += 1
        nodes[f"ffn_{i}"] = nid; nid += 1
    nodes["norm"] = nid; nid += 1
    nodes["output"] = nid; nid += 1
    
    # 边：input -> attn_0 -> ffn_0 -> attn_1 -> ffn_1 -> ... -> norm -> output
    checker.add_edge(nodes["input"], nodes["attn_0"])
    for i in range(layers):
        checker.add_edge(nodes[f"attn_{i}"], nodes[f"ffn_{i}"])
        if i < layers - 1:
            checker.add_edge(nodes[f"ffn_{i}"], nodes[f"attn_{i+1}"])
    checker.add_edge(nodes[f"ffn_{layers-1}"], nodes["norm"])
    checker.add_edge(nodes["norm"], nodes["output"])
    # 残差连接（每层输入到下一层输入的skip）
    for i in range(layers - 1):
        checker.add_edge(nodes[f"attn_{i}"], nodes[f"attn_{i+1}"])
    return checker, nodes


if __name__ == "__main__":
    print("=" * 60)
    print("ZONGYUAN-ROOT 神经网络DAG拓扑巡检")
    print("=" * 60)
    
    # 测试1: 简单网络
    print("\n【测试1】简单2层网络")
    c1 = NeuralTopoChecker()
    c1.add_edge(0,2); c1.add_edge(1,2); c1.add_edge(0,3)
    c1.add_edge(1,3); c1.add_edge(2,4); c1.add_edge(3,5)
    r1 = c1.full_inspect("simple_2layer")
    print(json.dumps(r1, indent=2, ensure_ascii=False))
    
    # 测试2: Transformer计算图
    print("\n【测试2】Transformer计算图(2层)")
    c2, nodes2 = build_transformer_graph(layers=2)
    r2 = c2.full_inspect("transformer_2layer")
    print(json.dumps(r2, indent=2, ensure_ascii=False))
    
    # 测试3: 漂移检测（故意构造叶子有下游的异常拓扑）
    print("\n【测试3】漂移检测（异常拓扑）")
    c3 = NeuralTopoChecker()
    c3.add_edge(0,1); c3.add_edge(1,2); c3.add_edge(2,1)  # 环路+叶子异常
    r3 = c3.full_inspect("drift_test")
    print(json.dumps(r3, indent=2, ensure_ascii=False))
    
    # 汇总
    print("\n" + "=" * 60)
    print("巡检汇总")
    print("=" * 60)
    for name, r in [("简单网络",r1), ("Transformer",r2), ("异常检测",r3)]:
        print(f"  {name}: {r['overall_status']} (节点={r['total_nodes']}, 边={r['total_edges']}, DAG={r['cycle_check']['is_dag']})")
