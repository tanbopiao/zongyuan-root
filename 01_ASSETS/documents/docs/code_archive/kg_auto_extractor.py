#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 知识图谱自动抽取引擎 V1.0
功能: 真正从云端真值数据中自动抽取实体和关系，不是手动定义
"""

import json
import re
import hashlib
from datetime import datetime
from collections import defaultdict, Counter
from urllib import request, error

# 配置
CAPTURE_TOKEN = "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"
TRUTH_URL = "https://drama.huodouai.com/api/gateway/truths?level=public"
NODE_ID = "sandbox-agent-001"
DID = "DID-BR-000002"
OUTPUT_DIR = "/home/user/Doubao/chats/38439832899843586/knowledge_graph_auto"

import os
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_truths():
    """从云端获取真值数据"""
    print("[1/5] 从云端获取真值数据...")
    try:
        req = request.Request(TRUTH_URL)
        req.add_header("X-Capture-Token", CAPTURE_TOKEN)
        req.add_header("Content-Type", "application/json")
        with request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return data
    except Exception as e:
        print(f"  获取失败: {e}")
        return None

def extract_entities_from_text(text, entity_type):
    """从文本中抽取特定类型的实体"""
    entities = set()
    
    if entity_type == "service":
        # 服务名: xxx服务、xxx API、xxx端点
        patterns = [
            r'([\w\-]+)(?:服务|API|端点|网关)',
            r'(?:服务|API|端点|网关)(?:名为|[:：]\s*)([\w\-]+)',
        ]
    elif entity_type == "tool":
        # 工具名: xxx工具、xxx脚本、xxx引擎
        patterns = [
            r'([\w\-]+)(?:工具|脚本|引擎|系统)',
            r'(?:工具|脚本|引擎|系统)(?:名为|[:：]\s*)([\w\-]+)',
        ]
    elif entity_type == "node":
        # 节点名: xxx节点、xxx窗口
        patterns = [
            r'([\w\-]+)(?:节点|窗口)',
            r'(?:节点|窗口)(?:名为|[:：]\s*)([\w\-]+)',
        ]
    elif entity_type == "protocol":
        # 协议名: xxx协议、xxx法则
        patterns = [
            r'([\w\-]+)(?:协议|法则|规则)',
            r'(?:协议|法则|规则)(?:名为|[:：]\s*)([\w\-]+)',
        ]
    elif entity_type == "metric":
        # 指标: xxx率、xxx时间、xxx数
        patterns = [
            r'([\w\-]+)(?:率|时间|数|量)',
        ]
    else:
        patterns = []
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            match = match.strip()
            if len(match) > 2 and len(match) < 50 and not match.isdigit():
                entities.add(match.lower())
    
    return entities

def extract_entities(truths_data):
    """从所有真值中抽取实体"""
    print("[2/5] 自动抽取实体...")
    
    all_entities = defaultdict(lambda: {"name": "", "type": "", "mentions": 0, "sources": []})
    entity_types = ["service", "tool", "node", "protocol", "metric"]
    
    # 处理真值数据
    truth_list = []
    if isinstance(truths_data, dict):
        if "truths" in truths_data:
            truths = truths_data["truths"]
            if isinstance(truths, dict):
                truth_list = [{"key": k, "value": str(v)} for k, v in truths.items()]
            elif isinstance(truths, list):
                truth_list = truths
        elif "data" in truths_data and isinstance(truths_data["data"], dict):
            truths = truths_data["data"].get("truths", {})
            if isinstance(truths, dict):
                truth_list = [{"key": k, "value": str(v)} for k, v in truths.items()]
    
    print(f"  处理真值数: {len(truth_list)}")
    
    for truth in truth_list[:1000]:  # 限制处理数量
        if isinstance(truth, dict):
            key = str(truth.get("key", ""))
            value = str(truth.get("value", ""))
            content = str(truth.get("content", ""))
            text = f"{key} {value} {content}"
        else:
            text = str(truth)
            key = hashlib.md5(text.encode()).hexdigest()[:16]
        
        for etype in entity_types:
            entities = extract_entities_from_text(text, etype)
            for entity in entities:
                eid = f"{etype}:{entity}"
                if eid not in all_entities:
                    all_entities[eid] = {
                        "entity_id": eid,
                        "name": entity,
                        "type": etype,
                        "mentions": 0,
                        "first_seen": datetime.now().isoformat(),
                        "sources": []
                    }
                all_entities[eid]["mentions"] += 1
                if key not in all_entities[eid]["sources"]:
                    all_entities[eid]["sources"].append(key)
    
    # 过滤：只保留出现>=2次的实体
    filtered = {k: v for k, v in all_entities.items() if v["mentions"] >= 2}
    
    # 按类型统计
    type_stats = Counter(v["type"] for v in filtered.values())
    
    print(f"  抽取实体总数: {len(filtered)}")
    print(f"  类型分布: {dict(type_stats)}")
    
    return list(filtered.values())

def extract_relations(entities, truths_data):
    """从真值中抽取实体间关系"""
    print("[3/5] 自动抽取实体关系...")
    
    relations = []
    entity_names = {e["name"]: e for e in entities}
    
    # 关系模式
    relation_patterns = [
        (r'([\w\-]+)\s*(?:依赖|取决于|需要)\s*([\w\-]+)', "depends_on", 0.7),
        (r'([\w\-]+)\s*(?:使用|调用|接入)\s*([\w\-]+)', "uses", 0.7),
        (r'([\w\-]+)\s*(?:包含|包括|集成)\s*([\w\-]+)', "includes", 0.6),
        (r'([\w\-]+)\s*(?:连接|通信|协同)\s*([\w\-]+)', "connects_to", 0.6),
        (r'([\w\-]+)\s*(?:管理|治理|控制)\s*([\w\-]+)', "governs", 0.6),
        (r'([\w\-]+)\s*(?:生成|产生|输出)\s*([\w\-]+)', "produces", 0.5),
        (r'([\w\-]+)\s*(?:监控|检测)\s*([\w\-]+)', "monitors", 0.6),
        (r'([\w\-]+)\s*(?:修复|恢复|处理)\s*([\w\-]+)', "repairs", 0.6),
    ]
    
    # 从真值key中也能抽取关系
    truth_list = []
    if isinstance(truths_data, dict):
        if "truths" in truths_data:
            truths = truths_data["truths"]
            if isinstance(truths, dict):
                truth_list = [{"key": k, "value": str(v)} for k, v in truths.items()]
    
    relation_set = set()
    
    for truth in truth_list[:500]:
        if isinstance(truth, dict):
            text = f"{truth.get('key', '')} {truth.get('value', '')}"
        else:
            text = str(truth)
        
        for pattern, rel_type, confidence in relation_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    source = match[0].lower().strip()
                    target = match[1].lower().strip()
                    
                    # 只保留已知实体间的关系
                    if source in entity_names and target in entity_names and source != target:
                        rel_key = f"{source}|{rel_type}|{target}"
                        if rel_key not in relation_set:
                            relation_set.add(rel_key)
                            relations.append({
                                "source": source,
                                "target": target,
                                "relation": rel_type,
                                "confidence": confidence,
                                "type": "auto_extracted"
                            })
    
    # 按关系类型统计
    rel_stats = Counter(r["relation"] for r in relations)
    
    print(f"  抽取关系数: {len(relations)}")
    print(f"  关系类型分布: {dict(rel_stats)}")
    
    return relations

def build_knowledge_graph(entities, relations):
    """构建知识图谱"""
    print("[4/5] 构建知识图谱...")
    
    graph = {
        "graph_id": "KG-AUTO-" + datetime.now().strftime("%Y%m%d_%H%M%S"),
        "created_at": datetime.now().isoformat(),
        "node_id": NODE_ID,
        "did": DID,
        "extraction_method": "auto_from_truths",
        "total_entities": len(entities),
        "total_relations": len(relations),
        "entities": entities,
        "relations": relations,
        "graph_stats": {
            "entity_types": Counter(e["type"] for e in entities),
            "relation_types": Counter(r["relation"] for r in relations),
            "avg_mentions": sum(e["mentions"] for e in entities) / len(entities) if entities else 0,
            "density": len(relations) / (len(entities) * (len(entities) - 1)) if len(entities) > 1 else 0
        }
    }
    
    # 保存
    output_file = os.path.join(OUTPUT_DIR, "knowledge_graph_auto.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    
    print(f"  图谱已保存: {output_file}")
    return graph

def analyze_graph(graph):
    """分析知识图谱"""
    print("[5/5] 分析知识图谱...")
    
    entities = graph["entities"]
    relations = graph["relations"]
    
    # 找出度最高的实体
    out_degree = Counter(r["source"] for r in relations)
    in_degree = Counter(r["target"] for r in relations)
    
    top_entities = sorted(entities, key=lambda x: x["mentions"], reverse=True)[:10]
    
    analysis = {
        "analysis_id": "KG-ANALYSIS-" + datetime.now().strftime("%Y%m%d_%H%M%S"),
        "analyzed_at": datetime.now().isoformat(),
        "graph_id": graph["graph_id"],
        "summary": {
            "total_entities": len(entities),
            "total_relations": len(relations),
            "graph_density": graph["graph_stats"]["density"],
            "avg_mentions": graph["graph_stats"]["avg_mentions"]
        },
        "top_entities_by_mentions": [
            {"name": e["name"], "type": e["type"], "mentions": e["mentions"]}
            for e in top_entities
        ],
        "top_entities_by_out_degree": [
            {"name": name, "out_degree": degree}
            for name, degree in out_degree.most_common(10)
        ],
        "top_entities_by_in_degree": [
            {"name": name, "in_degree": degree}
            for name, degree in in_degree.most_common(10)
        ],
        "relation_type_distribution": dict(graph["graph_stats"]["relation_types"]),
        "entity_type_distribution": dict(graph["graph_stats"]["entity_types"])
    }
    
    # 保存分析结果
    analysis_file = os.path.join(OUTPUT_DIR, "graph_analysis.json")
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    print(f"  分析完成: {analysis_file}")
    print()
    print("=" * 60)
    print("  📊 知识图谱自动抽取结果")
    print("=" * 60)
    print(f"  实体总数: {len(entities)}")
    print(f"  关系总数: {len(relations)}")
    print(f"  图谱密度: {graph['graph_stats']['density']:.4f}")
    print(f"  平均提及数: {graph['graph_stats']['avg_mentions']:.1f}")
    print()
    print("  【实体类型分布】")
    for etype, count in graph["graph_stats"]["entity_types"].most_common():
        print(f"    {etype}: {count}")
    print()
    print("  【关系类型分布】")
    for rtype, count in graph["graph_stats"]["relation_types"].most_common():
        print(f"    {rtype}: {count}")
    print()
    print("  【提及最多的Top10实体】")
    for i, e in enumerate(top_entities[:10], 1):
        print(f"    {i}. {e['name']} ({e['type']}) - {e['mentions']}次提及")
    print("=" * 60)
    
    return analysis

def main():
    print("=" * 60)
    print("  🧠 ZONGYUAN-ROOT 知识图谱自动抽取引擎 V1.0")
    print("=" * 60)
    print()
    
    # 1. 获取真值
    truths_data = fetch_truths()
    if truths_data is None:
        print("❌ 无法获取真值数据，使用空数据继续")
        truths_data = {}
    
    # 2. 抽取实体
    entities = extract_entities(truths_data)
    
    # 3. 抽取关系
    relations = extract_relations(entities, truths_data)
    
    # 4. 构建图谱
    graph = build_knowledge_graph(entities, relations)
    
    # 5. 分析图谱
    analysis = analyze_graph(graph)
    
    print()
    print("✅ 知识图谱自动抽取完成！")
    print(f"   输出目录: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
