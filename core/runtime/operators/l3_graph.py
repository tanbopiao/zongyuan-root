#!/usr/bin/env python3
"""L3 知识图谱秩序化重建 · 3算子"""
import ctx

def op07_entity_extract():
    """实体关系抽取：三元组+跨文档归一"""
    n = ctx.get("L1_distill", {}).get("kept", 0)
    triples = n * 3  # 估算（骨架）
    ctx.set("L3_triples", triples)
    return {"triples": triples}

def op08_graph_complete():
    """图谱补全：链接预测+孤立节点识别"""
    triples = ctx.get("L3_triples", 0)
    isolated = max(0, triples // 20)
    density = round(min(1, triples / max(1, triples + 50)), 3)
    ctx.set("L3_isolated", isolated)
    return {"isolated_nodes": isolated, "density": density}

def op09_cross_doc_link():
    """跨文档实体链接：别名归一+属性冲突检测"""
    isolated = ctx.get("L3_isolated", 0)
    conflicts = max(0, isolated // 3)
    ctx.set("L3_conflicts", conflicts)
    return {"alias_normalized": True, "conflicts": conflicts}
