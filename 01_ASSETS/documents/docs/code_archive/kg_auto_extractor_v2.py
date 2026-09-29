#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 知识图谱自动抽取引擎 V2.0
功能: 从真值key命名模式中自动抽取实体和关系
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
        truths = data.get('truths', [])
        print(f"  获取真值数: {len(truths)}")
        return truths
    except Exception as e:
        print(f"  获取失败: {e}")
        return []

def extract_entities_from_keys(truth_keys):
    """从真值key中抽取实体"""
    print("[2/5] 从真值key中自动抽取实体...")
    
    entities = defaultdict(lambda: {
        "name": "", "type": "", "mentions": 0, 
        "sub_entities": set(), "patterns": set()
    })
    
    # 实体类型识别规则
    type_patterns = {
        "service": [r'^(GATEWAY|API|SERVICE|SERVER|ENDPOINT|PROXY)', r'(GATEWAY|API|SERVICE|SERVER|ENDPOINT|PROXY)$'],
        "tool": [r'^(ENGINE|TOOL|SCRIPT|SYSTEM|MODULE)', r'(ENGINE|TOOL|SCRIPT|SYSTEM|MODULE)$'],
        "node": [r'^(NODE|WINDOW|AGENT|INSTANCE)', r'(NODE|WINDOW|AGENT|INSTANCE)$'],
        "protocol": [r'^(PROTOCOL|RULE|LAW|POLICY|STANDARD)', r'(PROTOCOL|RULE|LAW|POLICY|STANDARD)$'],
        "metric": [r'^(STATUS|COUNT|RATE|TIME|SIZE|VERSION|CONFIG)', r'(STATUS|COUNT|RATE|TIME|SIZE|VERSION|CONFIG)$'],
        "data": [r'^(DATA|TRUTH|RECORD|LOG|SNAPSHOT|ARCHIVE)', r'(DATA|TRUTH|RECORD|LOG|SNAPSHOT|ARCHIVE)$'],
        "security": [r'^(SECURITY|AUTH|TOKEN|KEY|PERMISSION|ACCESS)', r'(SECURITY|AUTH|TOKEN|KEY|PERMISSION|ACCESS)$'],
        "operation": [r'^(OPERATION|TASK|JOB|SCHEDULE|MONITOR|HEAL)', r'(OPERATION|TASK|JOB|SCHEDULE|MONITOR|HEAL)$'],
    }
    
    # 已知的核心实体（从key前缀中提取）
    core_entities = set()
    
    for key in truth_keys:
        if not key or not isinstance(key, str):
            continue
        
        # 按.分割key
        parts = key.split('.')
        
        # 第一个部分通常是域/实体
        if len(parts) >= 1:
            domain = parts[0].upper()
            core_entities.add(domain)
            
            # 识别实体类型
            entity_type = "domain"
            for etype, patterns in type_patterns.items():
                for pattern in patterns:
                    if re.match(pattern, domain):
                        entity_type = etype
                        break
                if entity_type != "domain":
                    break
            
            eid = f"{entity_type}:{domain.lower()}"
            if eid not in entities:
                entities[eid] = {
                    "entity_id": eid,
                    "name": domain.lower(),
                    "type": entity_type,
                    "mentions": 0,
                    "sub_entities": set(),
                    "patterns": set(),
                    "first_seen": datetime.now().isoformat()
                }
            entities[eid]["mentions"] += 1
            entities[eid]["patterns"].add(key)
            
            # 提取子实体（第二部分）
            if len(parts) >= 2:
                sub = parts[1].upper()
                entities[eid]["sub_entities"].add(sub)
                
                # 子实体也作为独立实体
                sub_type = "component"
                for etype, patterns in type_patterns.items():
                    for pattern in patterns:
                        if re.match(pattern, sub):
                            sub_type = etype
                            break
                    if sub_type != "component":
                        break
                
                sub_eid = f"{sub_type}:{sub.lower()}"
                if sub_eid not in entities:
                    entities[sub_eid] = {
                        "entity_id": sub_eid,
                        "name": sub.lower(),
                        "type": sub_type,
                        "mentions": 0,
                        "sub_entities": set(),
                        "patterns": set(),
                        "first_seen": datetime.now().isoformat()
                    }
                entities[sub_eid]["mentions"] += 1
    
    # 过滤：只保留出现>=3次的实体
    filtered = {k: v for k, v in entities.items() if v["mentions"] >= 3}
    
    # 转换set为list以便JSON序列化
    result = []
    for e in filtered.values():
        e["sub_entities"] = list(e["sub_entities"])[:20]  # 限制数量
        e["patterns"] = list(e["patterns"])[:5]
        result.append(e)
    
    # 按类型统计
    type_stats = Counter(e["type"] for e in result)
    
    print(f"  抽取实体总数: {len(result)}")
    print(f"  类型分布: {dict(type_stats)}")
    
    return result

def extract_relations_from_keys(entities, truth_keys):
    """从真值key中抽取实体间关系"""
    print("[3/5] 从真值key中自动抽取实体关系...")
    
    relations = []
    entity_names = {e["name"].upper(): e for e in entities}
    
    relation_set = set()
    
    for key in truth_keys:
        if not key or not isinstance(key, str):
            continue
        
        parts = key.split('.')
        
        # 从key结构中推断关系
        if len(parts) >= 2:
            source = parts[0].upper()
            target = parts[1].upper()
            
            if source in entity_names and target in entity_names and source != target:
                # 根据key模式推断关系类型
                rel_type = "contains"
                confidence = 0.6
                
                # 更精确的关系推断
                if any(w in target for w in ['STATUS', 'CONFIG', 'VERSION', 'COUNT']):
                    rel_type = "has_property"
                    confidence = 0.8
                elif any(w in target for w in ['LOG', 'RECORD', 'DATA', 'SNAPSHOT']):
                    rel_type = "produces"
                    confidence = 0.7
                elif any(w in target for w in ['API', 'GATEWAY', 'ENDPOINT', 'SERVICE']):
                    rel_type = "exposes"
                    confidence = 0.7
                elif any(w in target for w in ['RULE', 'PROTOCOL', 'POLICY', 'LAW']):
                    rel_type = "follows"
                    confidence = 0.75
                elif any(w in target for w in ['ENGINE', 'MODULE', 'COMPONENT']):
                    rel_type = "includes"
                    confidence = 0.65
                
                rel_key = f"{source}|{rel_type}|{target}"
                if rel_key not in relation_set:
                    relation_set.add(rel_key)
                    relations.append({
                        "source": source.lower(),
                        "target": target.lower(),
                        "relation": rel_type,
                        "confidence": confidence,
                        "type": "auto_extracted_from_key_pattern",
                        "evidence_key": key
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
        "extraction_method": "auto_from_truth_key_patterns",
        "total_entities": len(entities),
        "total_relations": len(relations),
        "entities": entities,
        "relations": relations,
        "graph_stats": {
            "entity_types": dict(Counter(e["type"] for e in entities)),
            "relation_types": dict(Counter(r["relation"] for r in relations)),
            "avg_mentions": sum(e["mentions"] for e in entities) / len(entities) if entities else 0,
            "density": len(relations) / (len(entities) * (len(entities) - 1)) if len(entities) > 1 else 0
        }
    }
    
    # 保存
    output_file = os.path.join(OUTPUT_DIR, "knowledge_graph_auto_v2.json")
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
    
    top_entities = sorted(entities, key=lambda x: x["mentions"], reverse=True)[:15]
    
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
        "relation_type_distribution": graph["graph_stats"]["relation_types"],
        "entity_type_distribution": graph["graph_stats"]["entity_types"]
    }
    
    # 保存分析结果
    analysis_file = os.path.join(OUTPUT_DIR, "graph_analysis_v2.json")
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    print(f"  分析完成: {analysis_file}")
    print()
    print("=" * 60)
    print("  📊 知识图谱自动抽取结果 (V2.0)")
    print("=" * 60)
    print(f"  实体总数: {len(entities)}")
    print(f"  关系总数: {len(relations)}")
    print(f"  图谱密度: {graph['graph_stats']['density']:.4f}")
    print(f"  平均提及数: {graph['graph_stats']['avg_mentions']:.1f}")
    print()
    print("  【实体类型分布】")
    for etype, count in sorted(graph["graph_stats"]["entity_types"].items(), key=lambda x: -x[1]):
        print(f"    {etype}: {count}")
    print()
    print("  【关系类型分布】")
    for rtype, count in sorted(graph["graph_stats"]["relation_types"].items(), key=lambda x: -x[1]):
        print(f"    {rtype}: {count}")
    print()
    print("  【提及最多的Top15实体】")
    for i, e in enumerate(top_entities[:15], 1):
        print(f"    {i:2d}. {e['name']:30s} ({e['type']:12s}) - {e['mentions']:4d}次提及")
    print("=" * 60)
    
    return analysis

def main():
    print("=" * 60)
    print("  🧠 ZONGYUAN-ROOT 知识图谱自动抽取引擎 V2.0")
    print("  从真值key命名模式中自动抽取实体和关系")
    print("=" * 60)
    print()
    
    # 1. 获取真值
    truth_keys = fetch_truths()
    if not truth_keys:
        print("❌ 无法获取真值数据")
        return
    
    # 2. 抽取实体
    entities = extract_entities_from_keys(truth_keys)
    
    # 3. 抽取关系
    relations = extract_relations_from_keys(entities, truth_keys)
    
    # 4. 构建图谱
    graph = build_knowledge_graph(entities, relations)
    
    # 5. 分析图谱
    analysis = analyze_graph(graph)
    
    print()
    print("✅ 知识图谱自动抽取完成！")
    print(f"   输出目录: {OUTPUT_DIR}")
    print(f"   实体数: {len(entities)}, 关系数: {len(relations)}")

if __name__ == "__main__":
    main()
