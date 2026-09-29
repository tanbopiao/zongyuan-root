#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 因果路径计算引擎 V1.0
功能: 基于知识图谱实现真正的因果路径计算，不是模板
"""

import json
import heapq
from datetime import datetime
from collections import defaultdict, deque
from urllib import request

# 配置
CAPTURE_TOKEN = "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"
NODE_ID = "sandbox-agent-001"
DID = "DID-BR-000002"
OUTPUT_DIR = "/home/user/Doubao/chats/38439832899843586/causal_reasoning"

import os
os.makedirs(OUTPUT_DIR, exist_ok=True)

class CausalGraph:
    """因果图：支持因果路径计算"""
    
    def __init__(self):
        self.nodes = {}  # node_id -> node_data
        self.edges = defaultdict(list)  # source -> [(target, relation, weight)]
        self.edge_weights = {}  # (source, target) -> weight
    
    def add_node(self, node_id, node_data=None):
        if node_id not in self.nodes:
            self.nodes[node_id] = node_data or {"name": node_id}
    
    def add_edge(self, source, target, relation, weight=0.5):
        self.add_node(source)
        self.add_node(target)
        self.edges[source].append((target, relation, weight))
        self.edge_weights[(source, target)] = weight
    
    def get_shortest_path(self, start, end, max_depth=10):
        """Dijkstra最短路径算法"""
        if start not in self.nodes or end not in self.nodes:
            return None
        
        # 优先队列: (distance, node, path)
        pq = [(0, start, [start])]
        visited = set()
        
        while pq:
            dist, current, path = heapq.heappop(pq)
            
            if current in visited:
                continue
            visited.add(current)
            
            if current == end:
                return {
                    "path": path,
                    "length": len(path) - 1,
                    "total_weight": dist,
                    "avg_weight": dist / (len(path) - 1) if len(path) > 1 else 0
                }
            
            if len(path) > max_depth:
                continue
            
            for target, relation, weight in self.edges.get(current, []):
                if target not in visited:
                    new_dist = dist + (1 - weight)  # 权重越高，距离越短
                    heapq.heappush(pq, (new_dist, target, path + [target]))
        
        return None
    
    def get_all_paths(self, start, end, max_depth=5, max_paths=10):
        """获取所有路径（BFS，限制深度和数量）"""
        if start not in self.nodes or end not in self.nodes:
            return []
        
        paths = []
        queue = deque([(start, [start])])
        
        while queue and len(paths) < max_paths:
            current, path = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            for target, relation, weight in self.edges.get(current, []):
                if target == end:
                    full_path = path + [target]
                    paths.append({
                        "path": full_path,
                        "length": len(full_path) - 1,
                        "relations": self._get_relations(full_path),
                        "total_weight": sum(self.edge_weights.get((full_path[i], full_path[i+1]), 0.5) for i in range(len(full_path) - 1))
                    })
                elif target not in path:  # 避免循环
                    queue.append((target, path + [target]))
        
        return paths[:max_paths]
    
    def _get_relations(self, path):
        """获取路径上的关系类型"""
        relations = []
        for i in range(len(path) - 1):
            source, target = path[i], path[i+1]
            for t, r, w in self.edges.get(source, []):
                if t == target:
                    relations.append(r)
                    break
        return relations
    
    def get_causal_chain(self, event, direction="forward", max_depth=5):
        """获取因果链：向前（结果）或向后（原因）"""
        if event not in self.nodes:
            return []
        
        chain = []
        visited = set()
        queue = deque([(event, 0, [event])])
        
        while queue:
            current, depth, path = queue.popleft()
            
            if depth > max_depth or current in visited:
                continue
            visited.add(current)
            
            if depth > 0:
                chain.append({
                    "node": current,
                    "depth": depth,
                    "path": path,
                    "causal_strength": 1.0 / (depth + 1)  # 距离越远，因果强度越弱
                })
            
            # 向前：找下游节点（当前节点指向的）
            if direction == "forward":
                for target, relation, weight in self.edges.get(current, []):
                    if target not in visited:
                        queue.append((target, depth + 1, path + [target]))
            # 向后：找上游节点（指向当前节点的）
            else:
                for source in self.nodes:
                    for target, relation, weight in self.edges.get(source, []):
                        if target == current and source not in visited:
                            queue.append((source, depth + 1, path + [source]))
        
        return chain
    
    def get_centrality(self):
        """计算节点中心性（度中心性+介数中心性简化版）"""
        centrality = {}
        
        for node in self.nodes:
            out_degree = len(self.edges.get(node, []))
            in_degree = sum(1 for s in self.nodes for t, r, w in self.edges.get(s, []) if t == node)
            centrality[node] = {
                "out_degree": out_degree,
                "in_degree": in_degree,
                "total_degree": out_degree + in_degree,
                "degree_centrality": (out_degree + in_degree) / (2 * (len(self.nodes) - 1)) if len(self.nodes) > 1 else 0
            }
        
        return centrality

def build_causal_graph_from_kg(kg_file):
    """从知识图谱构建因果图"""
    print("[1/4] 从知识图谱构建因果图...")
    
    with open(kg_file, 'r', encoding='utf-8') as f:
        kg = json.load(f)
    
    graph = CausalGraph()
    
    # 添加实体节点
    for entity in kg.get("entities", []):
        graph.add_node(entity["name"], entity)
    
    # 添加关系边（将关系类型映射为因果权重）
    relation_weights = {
        "causes": 0.9,
        "depends_on": 0.8,
        "produces": 0.75,
        "follows": 0.7,
        "includes": 0.6,
        "contains": 0.5,
        "uses": 0.65,
        "has_property": 0.4,
        "exposes": 0.55,
        "governs": 0.7,
        "monitors": 0.6,
        "repairs": 0.65
    }
    
    for relation in kg.get("relations", []):
        source = relation["source"]
        target = relation["target"]
        rel_type = relation["relation"]
        weight = relation_weights.get(rel_type, relation.get("confidence", 0.5))
        graph.add_edge(source, target, rel_type, weight)
    
    print(f"  因果图节点数: {len(graph.nodes)}")
    print(f"  因果图边数: {sum(len(v) for v in graph.edges.values())}")
    
    return graph

def analyze_causal_paths(graph):
    """分析因果路径"""
    print("[2/4] 分析因果路径...")
    
    # 找出度最高的节点作为分析起点
    centrality = graph.get_centrality()
    top_nodes = sorted(centrality.items(), key=lambda x: x[1]["total_degree"], reverse=True)[:10]
    
    print(f"  中心性最高的Top10节点:")
    for i, (node, data) in enumerate(top_nodes, 1):
        print(f"    {i}. {node}: 度={data['total_degree']}, 中心性={data['degree_centrality']:.4f}")
    
    # 计算关键节点间的因果路径
    key_nodes = [node for node, _ in top_nodes[:5]]
    path_analysis = []
    
    for i in range(len(key_nodes)):
        for j in range(i + 1, len(key_nodes)):
            source, target = key_nodes[i], key_nodes[j]
            
            # 最短路径
            shortest = graph.get_shortest_path(source, target)
            # 所有路径
            all_paths = graph.get_all_paths(source, target, max_depth=4, max_paths=5)
            
            if shortest or all_paths:
                path_analysis.append({
                    "source": source,
                    "target": target,
                    "shortest_path": shortest,
                    "all_paths_count": len(all_paths),
                    "sample_paths": all_paths[:3]
                })
    
    print(f"  分析的节点对: {len(path_analysis)}")
    print(f"  找到路径的节点对: {sum(1 for p in path_analysis if p['shortest_path'] or p['all_paths_count'] > 0)}")
    
    return path_analysis, centrality

def analyze_causal_chains(graph):
    """分析因果链"""
    print("[3/4] 分析因果链...")
    
    centrality = graph.get_centrality()
    top_nodes = sorted(centrality.items(), key=lambda x: x[1]["total_degree"], reverse=True)[:5]
    
    chain_analysis = []
    
    for node, _ in top_nodes:
        # 向前因果链（这个节点会导致什么）
        forward_chain = graph.get_causal_chain(node, direction="forward", max_depth=3)
        # 向后因果链（什么导致了这个节点）
        backward_chain = graph.get_causal_chain(node, direction="backward", max_depth=3)
        
        chain_analysis.append({
            "node": node,
            "forward_effects": [c["node"] for c in forward_chain[:10]],
            "forward_count": len(forward_chain),
            "backward_causes": [c["node"] for c in backward_chain[:10]],
            "backward_count": len(backward_chain)
        })
        
        print(f"  {node}: 影响{len(forward_chain)}个下游节点, 被{len(backward_chain)}个上游节点影响")
    
    return chain_analysis

def generate_causal_report(graph, path_analysis, centrality, chain_analysis):
    """生成因果分析报告"""
    print("[4/4] 生成因果分析报告...")
    
    report = {
        "report_id": "CAUSAL-" + datetime.now().strftime("%Y%m%d_%H%M%S"),
        "created_at": datetime.now().isoformat(),
        "node_id": NODE_ID,
        "did": DID,
        "analysis_method": "graph_based_causal_reasoning",
        "graph_stats": {
            "total_nodes": len(graph.nodes),
            "total_edges": sum(len(v) for v in graph.edges.values()),
            "avg_degree": sum(d["total_degree"] for d in centrality.values()) / len(centrality) if centrality else 0
        },
        "top_central_nodes": [
            {"node": node, **data}
            for node, data in sorted(centrality.items(), key=lambda x: x[1]["total_degree"], reverse=True)[:15]
        ],
        "path_analysis": path_analysis,
        "causal_chain_analysis": chain_analysis,
        "conclusions": {
            "key_hubs": [node for node, _ in sorted(centrality.items(), key=lambda x: x[1]["total_degree"], reverse=True)[:5]],
            "causal_density": sum(len(v) for v in graph.edges.values()) / (len(graph.nodes) * (len(graph.nodes) - 1)) if len(graph.nodes) > 1 else 0,
            "analysis_note": "本分析基于知识图谱的图结构计算，使用Dijkstra最短路径算法和BFS全路径搜索，因果强度基于关系类型权重和路径距离衰减"
        }
    }
    
    # 保存报告
    report_file = os.path.join(OUTPUT_DIR, "causal_analysis_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"  报告已保存: {report_file}")
    print()
    print("=" * 60)
    print("  🔗 因果推理计算结果")
    print("=" * 60)
    print(f"  因果图节点: {len(graph.nodes)}")
    print(f"  因果图边数: {sum(len(v) for v in graph.edges.values())}")
    print(f"  因果密度: {report['conclusions']['causal_density']:.4f}")
    print()
    print("  【关键枢纽节点Top5】")
    for i, node in enumerate(report["conclusions"]["key_hubs"], 1):
        data = centrality[node]
        print(f"    {i}. {node}: 总度={data['total_degree']}, 中心性={data['degree_centrality']:.4f}")
    print()
    print("  【因果链分析示例】")
    for chain in chain_analysis[:3]:
        print(f"    {chain['node']}:")
        print(f"      → 影响下游: {chain['forward_count']}个节点")
        print(f"      ← 被上游影响: {chain['backward_count']}个节点")
    print()
    print("  【计算方法说明】")
    print("    - 最短路径: Dijkstra算法（基于关系权重）")
    print("    - 全路径搜索: BFS广度优先（限制深度5）")
    print("    - 因果链: 向前/向后遍历（距离衰减模型）")
    print("    - 中心性: 度中心性（入度+出度）")
    print("=" * 60)
    
    return report

def main():
    print("=" * 60)
    print("  🔗 ZONGYUAN-ROOT 因果路径计算引擎 V1.0")
    print("  基于知识图谱的真正因果推理，不是模板")
    print("=" * 60)
    print()
    
    kg_file = "/home/user/Doubao/chats/38439832899843586/knowledge_graph_auto/knowledge_graph_auto_v2.json"
    
    if not os.path.exists(kg_file):
        print(f"❌ 知识图谱文件不存在: {kg_file}")
        print("请先运行知识图谱自动抽取引擎")
        return
    
    # 1. 构建因果图
    graph = build_causal_graph_from_kg(kg_file)
    
    # 2. 分析因果路径
    path_analysis, centrality = analyze_causal_paths(graph)
    
    # 3. 分析因果链
    chain_analysis = analyze_causal_chains(graph)
    
    # 4. 生成报告
    report = generate_causal_report(graph, path_analysis, centrality, chain_analysis)
    
    print()
    print("✅ 因果推理计算完成！")
    print(f"   输出目录: {OUTPUT_DIR}")
    print(f"   分析节点: {len(graph.nodes)}, 路径对: {len(path_analysis)}")

if __name__ == "__main__":
    main()
