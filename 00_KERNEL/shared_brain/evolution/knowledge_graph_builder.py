#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS — 共享大脑知识图谱构建引擎（EVO-P1-001）

功能：
  1. 从全量真值库中抽取实体（人物/机构/技术/产品/事件）
  2. 建立实体间关系（投资/合作/竞争/引用/演进）
  3. 存储为 JSON 邻接表（可迁移 Neo4j）
  4. 生成知识图谱统计报告

使用方式：
  python3 knowledge_graph_builder.py          # 全量构建/增量更新图谱
  python3 knowledge_graph_builder.py --stats  # 查看图谱统计
"""
import os
import sys
import json
import re
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Set

# ============ 路径配置 ============

WORKSPACE = Path("/workspace")
EVOLUTION_DIR = WORKSPACE / "evolution"
GRAPH_DIR = EVOLUTION_DIR / "knowledge_graph"
GRAPH_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = GRAPH_DIR / "builder.log"
GRAPH_FILE = GRAPH_DIR / "graph.json"
STATS_FILE = GRAPH_DIR / "stats.json"

SERVICES_DIR = WORKSPACE / "scripts" / "services"
sys.path.insert(0, str(SERVICES_DIR))

DID_TAG = "DID-BR-000002"


def log(level: str, message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# 实体类型识别规则
ENTITY_PATTERNS = {
    "person": [r"[\u4e00-\u9fa5]{2,4}(?:先生|女士|博士|教授|CEO|CTO|创始人|董事长)"],
    "org": [r"[\u4e00-\u9fa5A-Za-z]{2,20}(?:公司|集团|研究院|实验室|大学|学院|机构|联盟)"],
    "tech": [r"(?:大模型|LLM|GPT|BERT|Transformer|扩散模型|多模态|RAG|向量数据库|智能体|Agent|神经网络|深度学习|强化学习)"],
    "product": [r"[\u4e00-\u9fa5A-Za-z]{2,15}(?:平台|系统|引擎|助手|Bot|API|SDK)"],
    "event": [r"(?:发布|上线|开源|融资|并购|合作|突破)"],
}

# 关系类型识别
RELATION_PATTERNS = {
    "invest": [r"投资|融资|领投|跟投|估值"],
    "cooperate": [r"合作|联合|携手|战略合作"],
    "compete": [r"竞争|对抗|对标|挑战"],
    "cite": [r"引用|基于|参考|借鉴"],
    "evolve": [r"演进|升级|迭代|进化|突破"],
}


def extract_entities(text: str) -> List[Dict[str, str]]:
    """从文本中抽取实体。"""
    entities = []
    seen = set()
    for etype, patterns in ENTITY_PATTERNS.items():
        for pat in patterns:
            for m in re.finditer(pat, text):
                name = m.group(0)
                key = (etype, name)
                if key not in seen:
                    seen.add(key)
                    entities.append({"type": etype, "name": name})
    return entities


def extract_relations(text: str, entities: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """基于实体共现和关键词抽取关系。"""
    relations = []
    for rtype, patterns in RELATION_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text):
                # 将该文本中所有实体两两关联
                for i in range(len(entities)):
                    for j in range(i + 1, len(entities)):
                        relations.append({
                            "type": rtype,
                            "source": entities[i]["name"],
                            "target": entities[j]["name"],
                        })
    return relations


def build_graph(truths: List[Dict[str, Any]]) -> Dict[str, Any]:
    """从真值列表构建知识图谱。"""
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    for truth in truths:
        text = json.dumps(truth, ensure_ascii=False)
        entities = extract_entities(text)
        relations = extract_relations(text, entities)

        for ent in entities:
            nid = f"{ent['type']}:{ent['name']}"
            if nid not in nodes:
                nodes[nid] = {
                    "id": nid,
                    "name": ent["name"],
                    "type": ent["type"],
                    "truth_refs": [],
                }
            nodes[nid]["truth_refs"].append(truth.get("seq"))

        for rel in relations:
            edges.append({
                "source": rel["source"],
                "target": rel["target"],
                "type": rel["type"],
                "truth_ref": truth.get("seq"),
            })

    # 去重边
    seen_edges = set()
    deduped_edges = []
    for e in edges:
        key = (e["source"], e["target"], e["type"])
        if key not in seen_edges:
            seen_edges.add(key)
            deduped_edges.append(e)

    return {
        "nodes": list(nodes.values()),
        "edges": deduped_edges,
        "metadata": {
            "built_at": datetime.now().isoformat(),
            "truth_count": len(truths),
            "did_tag": DID_TAG,
        },
    }


def save_graph(graph: Dict[str, Any]):
    """保存图谱与统计。"""
    GRAPH_FILE.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")

    # 统计
    type_counts = {}
    for n in graph["nodes"]:
        t = n["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    rel_counts = {}
    for e in graph["edges"]:
        t = e["type"]
        rel_counts[t] = rel_counts.get(t, 0) + 1

    stats = {
        "generated_at": datetime.now().isoformat(),
        "total_nodes": len(graph["nodes"]),
        "total_edges": len(graph["edges"]),
        "node_type_distribution": type_counts,
        "edge_type_distribution": rel_counts,
        "did_tag": DID_TAG,
    }
    STATS_FILE.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


def main():
    parser = None
    try:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--stats", action="store_true")
        args = parser.parse_args()
    except Exception:
        args = type("Args", (), {"stats": "--stats" in sys.argv})()

    if args.stats:
        if STATS_FILE.exists():
            print(STATS_FILE.read_text(encoding="utf-8"))
        else:
            print("暂无图谱统计，请先运行构建")
        return 0

    log("INFO", "=" * 50)
    log("INFO", "知识图谱构建引擎启动 (EVO-P1-001)")
    log("INFO", "=" * 50)

    try:
        from autonomous_kernel import AutonomousKernel
        kernel = AutonomousKernel()
        truths = kernel.truths
        log("INFO", f"加载 {len(truths)} 条真值用于图谱构建")
    except Exception as e:
        log("WARN", f"自治内核加载失败: {e}，使用空数据集")
        truths = []

    if not truths:
        log("WARN", "无真值数据，生成空图谱")

    graph = build_graph(truths)
    stats = save_graph(graph)

    log("INFO", f"图谱构建完成: {stats['total_nodes']} 节点, {stats['total_edges']} 关系")
    log("INFO", f"节点类型: {stats['node_type_distribution']}")
    log("INFO", f"关系类型: {stats['edge_type_distribution']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(0)
