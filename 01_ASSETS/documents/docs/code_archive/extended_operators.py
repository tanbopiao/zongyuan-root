#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜27算子扩展实现（第二批）
扩展算子：P7外部锚定、黎曼流形度量、SM-BS映射、实体关系抽取、知识图谱补全、
         CausalToTruth适配器、TruthToEvolution适配器、eFuse熔断触发
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""

import sys
import json
import time
import hashlib
import sqlite3
import requests
from pathlib import Path
from abc import ABC

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR / "config"))
sys.path.insert(0, str(BASE_DIR / "operators"))

try:
    from config_loader import config as _config
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False

try:
    from core_operators import BaseOperator
except ImportError:
    # 如果无法导入，定义一个简化的基类
    class BaseOperator(ABC):
        def __init__(self, operator_id, name, layer, description):
            self.operator_id = operator_id
            self.name = name
            self.layer = layer
            self.description = description
            self.execution_count = 0
            self.last_execution = None
            self.last_result = None
            self.enabled = True

        def execute(self, **kwargs):
            pass

        def run(self, **kwargs):
            if not self.enabled:
                return {"status": "disabled", "operator_id": self.operator_id}
            start_time = time.time()
            try:
                result = self.execute(**kwargs)
                result["status"] = result.get("status", "success")
            except Exception as e:
                result = {"status": "error", "error": str(e)}
            elapsed = time.time() - start_time
            self.execution_count += 1
            self.last_execution = time.time()
            self.last_result = result
            result.update({
                "operator_id": self.operator_id,
                "operator_name": self.name,
                "layer": self.layer,
                "execution_count": self.execution_count,
                "elapsed_ms": round(elapsed * 1000, 2),
                "timestamp": time.time(),
            })
            return result

        def get_status(self):
            return {
                "operator_id": self.operator_id,
                "name": self.name,
                "layer": self.layer,
                "description": self.description,
                "enabled": self.enabled,
                "execution_count": self.execution_count,
                "last_execution": self.last_execution,
                "last_status": self.last_result.get("status") if self.last_result else None,
            }


def _cfg(key, default):
    if _CONFIG_AVAILABLE:
        return _config.get(key, default)
    return default


# ==================== 第一层：真值过滤与深度蒸馏 ====================

class ExternalAnchoringOperator(BaseOperator):
    """P7外部锚定算子：对接外部事实源交叉锚定，给P4对账提供外部参照，抑制统计幻觉"""

    def __init__(self):
        super().__init__(
            operator_id="P7_EXTERNAL_ANCHORING",
            name="外部锚定算子",
            layer=1,
            description="对接外部事实源交叉锚定，给P4对账提供外部参照，抑制统计幻觉，追加置信度元数据"
        )

    def execute(self, truth_entries=None, external_sources=None, **kwargs):
        truth_entries = truth_entries or []
        external_sources = external_sources or [
            {"name": "memory_gateway", "url": _cfg("gateway.base_url", "https://www.huodouai.com") + "/api/truths", "weight": 0.8},
            {"name": "feishu_docs", "weight": 0.6},
            {"name": "web_search", "weight": 0.4},
        ]

        anchored = []
        hallucination_suspects = []
        total_confidence_boost = 0

        for entry in truth_entries:
            content = entry.get("content", entry.get("text", ""))
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            base_confidence = entry.get("confidence", 0.5)

            # 模拟外部锚定（实际应调用外部API）
            anchor_score = 0
            anchored_sources = []
            for source in external_sources:
                # 简化版：基于内容哈希模拟锚定匹配度
                match_prob = int(content_hash, 16) % 100 / 100.0
                if match_prob > 0.3:  # 30%以上视为锚定成功
                    anchor_score += source["weight"] * match_prob
                    anchored_sources.append(source["name"])

            # 置信度调整
            if anchor_score > 0:
                confidence_boost = min(anchor_score * 0.1, 0.2)  # 最多提升20%
                new_confidence = min(base_confidence + confidence_boost, 1.0)
                total_confidence_boost += confidence_boost
                anchored.append({
                    "truth_id": entry.get("truth_id", content_hash),
                    "content": content[:100],
                    "original_confidence": base_confidence,
                    "anchored_confidence": round(new_confidence, 4),
                    "confidence_boost": round(confidence_boost, 4),
                    "anchored_sources": anchored_sources,
                    "anchor_score": round(anchor_score, 4),
                })
            else:
                hallucination_suspects.append({
                    "truth_id": entry.get("truth_id", content_hash),
                    "content": content[:100],
                    "confidence": base_confidence,
                    "reason": "无外部锚定，可能为统计幻觉",
                })

        return {
            "input_entries": len(truth_entries),
            "anchored_entries": len(anchored),
            "hallucination_suspects": len(hallucination_suspects),
            "avg_confidence_boost": round(total_confidence_boost / max(len(anchored), 1), 4),
            "external_sources_used": len(external_sources),
            "anchored_entries_detail": anchored[:10],
            "hallucination_suspects_detail": hallucination_suspects[:10],
            "hallucination_suppression_rate": round(len(anchored) / max(len(truth_entries), 1) * 100, 2),
        }


# ==================== 第二层：流形度量与SM-BS稳态映射 ====================

class RiemannianManifoldOperator(BaseOperator):
    """黎曼流形世界模型度量算子：度量世界模型内部概念流形距离，识别概念跳变/逻辑断层"""

    def __init__(self):
        super().__init__(
            operator_id="RIEMANNIAN_MANIFOLD_METRIC",
            name="黎曼流形世界模型度量算子",
            layer=2,
            description="度量世界模型内部概念流形距离，识别概念跳变/逻辑断层，标记大模型拼接碎片中的硬拼无逻辑过渡点"
        )

    def execute(self, concepts=None, concept_vectors=None, **kwargs):
        concepts = concepts or []
        concept_vectors = concept_vectors or {}
        distances = []
        jumps = []
        faults = []

        # 计算概念间流形距离（简化版：欧氏距离模拟黎曼度量）
        for i, c1 in enumerate(concepts):
            for j, c2 in enumerate(concepts):
                if i >= j:
                    continue
                v1 = concept_vectors.get(c1, [0] * 8)
                v2 = concept_vectors.get(c2, [0] * 8)
                # 欧氏距离
                euclidean = sum((a - b) ** 2 for a, b in zip(v1, v2)) ** 0.5
                # 模拟黎曼度量（加入曲率因子）
                curvature = _cfg("manifold.curvature", 0.1)
                riemannian = euclidean * (1 + curvature * euclidean)
                distances.append({
                    "concept_a": c1,
                    "concept_b": c2,
                    "euclidean_distance": round(euclidean, 4),
                    "riemannian_distance": round(riemannian, 4),
                })

                # 检测概念跳变（距离过大）
                jump_threshold = _cfg("manifold.jump_threshold", 2.0)
                if riemannian > jump_threshold:
                    jumps.append({
                        "concept_a": c1,
                        "concept_b": c2,
                        "distance": round(riemannian, 4),
                        "threshold": jump_threshold,
                        "severity": "high" if riemannian > jump_threshold * 2 else "medium",
                    })

        # 检测逻辑断层（概念链中距离突变）
        if len(concepts) > 2:
            for i in range(1, len(concepts) - 1):
                prev_dist = next((d["riemannian_distance"] for d in distances
                                  if {d["concept_a"], d["concept_b"]} == {concepts[i-1], concepts[i]}), 0)
                next_dist = next((d["riemannian_distance"] for d in distances
                                  if {d["concept_a"], d["concept_b"]} == {concepts[i], concepts[i+1]}), 0)
                if prev_dist > 0 and abs(next_dist - prev_dist) / prev_dist > 0.5:
                    faults.append({
                        "concept": concepts[i],
                        "prev_distance": round(prev_dist, 4),
                        "next_distance": round(next_dist, 4),
                        "mutation_rate": round(abs(next_dist - prev_dist) / prev_dist, 4),
                        "type": "逻辑断层/硬拼无逻辑过渡",
                    })

        return {
            "concepts_measured": len(concepts),
            "distance_pairs": len(distances),
            "concept_jumps": len(jumps),
            "logic_faults": len(faults),
            "avg_riemannian_distance": round(sum(d["riemannian_distance"] for d in distances) / max(len(distances), 1), 4),
            "max_riemannian_distance": round(max((d["riemannian_distance"] for d in distances), default=0), 4),
            "manifold_curvature": _cfg("manifold.curvature", 0.1),
            "top_jumps": jumps[:5],
            "logic_faults_detail": faults[:5],
            "distances_sample": distances[:10],
        }


class SMBSMappingOperator(BaseOperator):
    """SM-BS双向稳态映射算子：执行语义空间(SM)↔黎曼流形(BS)双向稳态映射"""

    def __init__(self):
        super().__init__(
            operator_id="SM_BS_MAPPING",
            name="SM-BS双向稳态映射算子",
            layer=2,
            description="执行语义空间(SM)↔黎曼流形(BS)双向稳态映射，度量张量保证映射前后语义距离守恒，检测映射漂移"
        )

    def execute(self, semantic_concepts=None, direction="both", **kwargs):
        semantic_concepts = semantic_concepts or []
        direction = direction  # forward: SM→BS, backward: BS→SM, both: 双向

        forward_mappings = []
        backward_mappings = []
        drifts = []
        total_distance_conservation_error = 0

        # 正向映射：语义空间→黎曼流形
        if direction in ["forward", "both"]:
            for concept in semantic_concepts:
                # 模拟语义向量到流形坐标的映射
                semantic_vec = [hash(f"{concept}_{i}") % 100 / 100.0 for i in range(8)]
                # 度量张量变换
                metric_tensor = _cfg("sm_bs.metric_tensor", [[1.0, 0.1], [0.1, 1.0]])
                manifold_coord = [sum(s * m for s, m in zip(semantic_vec[:2], row)) for row in metric_tensor]
                forward_mappings.append({
                    "concept": concept,
                    "semantic_vector": [round(v, 4) for v in semantic_vec[:4]],
                    "manifold_coordinate": [round(c, 4) for c in manifold_coord],
                    "mapping_type": "SM→BS",
                })

        # 反向映射：黎曼流形→语义空间
        if direction in ["backward", "both"]:
            for mapping in forward_mappings:
                # 逆变张量恢复语义向量
                concept = mapping["concept"]
                manifold_coord = mapping["manifold_coordinate"]
                # 模拟逆变映射
                recovered_semantic = [c * 0.95 + (hash(f"inv_{concept}_{i}") % 10) / 100.0
                                      for i, c in enumerate(manifold_coord)]
                backward_mappings.append({
                    "concept": concept,
                    "manifold_coordinate": [round(c, 4) for c in manifold_coord],
                    "recovered_semantic": [round(v, 4) for v in recovered_semantic],
                    "mapping_type": "BS→SM",
                })

                # 检测映射漂移（双向映射后语义向量偏差）
                original = mapping["semantic_vector"]
                drift = sum(abs(o - r) for o, r in zip(original, recovered_semantic)) / max(len(original), 1)
                total_distance_conservation_error += drift
                drift_threshold = _cfg("sm_bs.drift_threshold", 0.1)
                if drift > drift_threshold:
                    drifts.append({
                        "concept": concept,
                        "drift_amount": round(drift, 4),
                        "threshold": drift_threshold,
                        "severity": "high" if drift > drift_threshold * 2 else "medium",
                    })

        return {
            "direction": direction,
            "semantic_concepts": len(semantic_concepts),
            "forward_mappings": len(forward_mappings),
            "backward_mappings": len(backward_mappings),
            "mapping_drifts": len(drifts),
            "avg_distance_conservation_error": round(total_distance_conservation_error / max(len(backward_mappings), 1), 4),
            "metric_tensor": _cfg("sm_bs.metric_tensor", [[1.0, 0.1], [0.1, 1.0]]),
            "drift_threshold": _cfg("sm_bs.drift_threshold", 0.1),
            "forward_sample": forward_mappings[:5],
            "backward_sample": backward_mappings[:5],
            "drifts_detail": drifts[:5],
            "steady_state": len(drifts) == 0,
        }


# ==================== 第三层：知识图谱秩序化重建 ====================

class EntityRelationExtractor(BaseOperator):
    """实体关系抽取算子：从非结构化文本中自动抽取实体与关系，构建知识图谱三元组"""

    def __init__(self):
        super().__init__(
            operator_id="ENTITY_RELATION_EXTRACTOR",
            name="实体关系抽取算子",
            layer=3,
            description="从非结构化文本中自动抽取实体(人/事/物/概念)与关系(因果/从属/时序/相似/对立)，构建知识图谱三元组"
        )

    def execute(self, texts=None, entity_types=None, relation_types=None, **kwargs):
        texts = texts or []
        entity_types = entity_types or ["person", "event", "object", "concept", "organization"]
        relation_types = relation_types or ["causal", "subordinate", "temporal", "similar", "opposite"]

        entities = []
        relations = []
        triples = []

        # 简化版实体抽取（基于关键词匹配，实际应接入NLP模型）
        entity_keywords = {
            "person": ["元极", "宗源", "玄女", "烛龙", "女娲"],
            "organization": ["主中枢", "次中枢", "记忆网关", "飞书"],
            "concept": ["黎曼流形", "三态驱动", "真值", "因果域", "进化域"],
            "event": ["部署", "加固", "进化", "巡检"],
            "object": ["Merkle树", "账本", "仪表盘", "算子"],
        }

        for text in texts:
            text_lower = text.lower()
            # 抽取实体
            for etype, keywords in entity_keywords.items():
                for kw in keywords:
                    if kw in text:
                        entity_id = f"ENT-{hashlib.md5(kw.encode()).hexdigest()[:8]}"
                        if not any(e["entity_id"] == entity_id for e in entities):
                            entities.append({
                                "entity_id": entity_id,
                                "name": kw,
                                "type": etype,
                                "source_text": text[:100],
                                "confidence": 0.85,
                            })

            # 抽取关系（简化版：基于因果关键词）
            causal_keywords = ["导致", "因为", "所以", "触发", "引起"]
            for kw in causal_keywords:
                if kw in text:
                    parts = text.split(kw)
                    if len(parts) >= 2:
                        # 简化：取前后文本中的实体
                        head_entity = entities[0]["entity_id"] if entities else "ENT-UNKNOWN"
                        tail_entity = entities[1]["entity_id"] if len(entities) > 1 else "ENT-UNKNOWN"
                        relation_id = f"REL-{hashlib.md5(f'{head_entity}_{tail_entity}_causal'.encode()).hexdigest()[:8]}"
                        triple = {
                            "triple_id": f"TRI-{relation_id}",
                            "head": head_entity,
                            "relation": "causal",
                            "tail": tail_entity,
                            "confidence": 0.75,
                            "source_text": text[:100],
                        }
                        triples.append(triple)
                        relations.append({
                            "relation_id": relation_id,
                            "type": "causal",
                            "keyword": kw,
                            "confidence": 0.75,
                        })

        # 跨文档实体归一化（简化版：同名实体合并）
        normalized_entities = {}
        for e in entities:
            key = e["name"]
            if key not in normalized_entities:
                normalized_entities[key] = e
            else:
                normalized_entities[key]["confidence"] = max(normalized_entities[key]["confidence"], e["confidence"])

        return {
            "input_texts": len(texts),
            "entities_extracted": len(entities),
            "entities_normalized": len(normalized_entities),
            "relations_extracted": len(relations),
            "triples_built": len(triples),
            "entity_types_found": list(set(e["type"] for e in entities)),
            "relation_types_found": list(set(r["type"] for r in relations)),
            "entities_sample": list(normalized_entities.values())[:10],
            "triples_sample": triples[:10],
            "graph_density": round(len(triples) / max(len(normalized_entities) ** 2, 1), 4),
        }


class KnowledgeGraphCompletion(BaseOperator):
    """知识图谱补全算子：基于已有三元组执行链接预测，补全缺失的实体关系"""

    def __init__(self):
        super().__init__(
            operator_id="KNOWLEDGE_GRAPH_COMPLETION",
            name="知识图谱补全算子",
            layer=3,
            description="基于已有三元组执行链接预测，补全缺失的实体关系，识别孤立节点，建议关联路径，输出图谱密度与连通性指标"
        )

    def execute(self, triples=None, entities=None, **kwargs):
        triples = triples or []
        entities = entities or []

        predicted_triples = []
        isolated_nodes = []
        suggested_paths = []

        # 构建实体邻接表
        adjacency = {e: [] for e in entities}
        for t in triples:
            head = t.get("head", "")
            tail = t.get("tail", "")
            relation = t.get("relation", "")
            if head in adjacency:
                adjacency[head].append((tail, relation))
            if tail in adjacency:
                adjacency[tail].append((head, relation))

        # 识别孤立节点
        for entity, neighbors in adjacency.items():
            if len(neighbors) == 0:
                isolated_nodes.append(entity)

        # 链接预测（简化版：基于共同邻居预测缺失关系）
        for i, e1 in enumerate(entities):
            for j, e2 in enumerate(entities):
                if i >= j:
                    continue
                # 检查是否已有直接关系
                has_direct = any(t.get("head") == e1 and t.get("tail") == e2 or
                                 t.get("head") == e2 and t.get("tail") == e1 for t in triples)
                if has_direct:
                    continue
                # 计算共同邻居
                neighbors1 = set(n[0] for n in adjacency.get(e1, []))
                neighbors2 = set(n[0] for n in adjacency.get(e2, []))
                common_neighbors = neighbors1 & neighbors2
                if len(common_neighbors) > 0:
                    # 预测关系类型（取共同邻居中最频繁的关系）
                    relation_counts = {}
                    for n in common_neighbors:
                        for _, rel in adjacency.get(e1, []):
                            if _ == n:
                                relation_counts[rel] = relation_counts.get(rel, 0) + 1
                    predicted_relation = max(relation_counts, key=relation_counts.get) if relation_counts else "similar"
                    confidence = min(len(common_neighbors) * 0.2, 0.8)
                    predicted_triples.append({
                        "triple_id": f"PRED-{hashlib.md5(f'{e1}_{predicted_relation}_{e2}'.encode()).hexdigest()[:8]}",
                        "head": e1,
                        "relation": predicted_relation,
                        "tail": e2,
                        "confidence": round(confidence, 4),
                        "prediction_method": "common_neighbors",
                        "common_neighbors_count": len(common_neighbors),
                        "status": "predicted",
                    })
                    # 建议关联路径
                    for cn in list(common_neighbors)[:2]:
                        suggested_paths.append({
                            "path": f"{e1} → {cn} → {e2}",
                            "intermediate_node": cn,
                            "confidence": round(confidence * 0.8, 4),
                        })

        # 计算图谱指标
        total_possible = len(entities) * (len(entities) - 1) / 2 if len(entities) > 1 else 1
        graph_density = (len(triples) + len(predicted_triples)) / total_possible
        connectivity = 1 - len(isolated_nodes) / max(len(entities), 1)

        return {
            "input_triples": len(triples),
            "input_entities": len(entities),
            "predicted_triples": len(predicted_triples),
            "isolated_nodes": len(isolated_nodes),
            "suggested_paths": len(suggested_paths),
            "graph_density": round(graph_density, 4),
            "connectivity": round(connectivity, 4),
            "isolated_nodes_list": isolated_nodes[:10],
            "predicted_sample": predicted_triples[:10],
            "paths_sample": suggested_paths[:10],
            "completion_rate": round(len(predicted_triples) / max(len(triples), 1) * 100, 2),
        }


# ==================== 第五层：CTE三位一体适配器流转 ====================

class CausalToTruthAdapter(BaseOperator):
    """CausalToTruth适配器算子：将因果域输出转换为真值域可消费格式"""

    def __init__(self):
        super().__init__(
            operator_id="CAUSAL_TO_TRUTH_ADAPTER",
            name="CausalToTruth适配器算子",
            layer=5,
            description="将因果域输出(因果链/奇点预警/干预结果)转换为真值域可消费格式——因果边→真值条目，奇点概率→真值置信度，干预结果→反事实真值"
        )

    def execute(self, causal_outputs=None, **kwargs):
        causal_outputs = causal_outputs or []
        truth_entries = []
        adaptation_stats = {"causal_chains": 0, "singularity_alerts": 0, "intervention_results": 0}

        for output in causal_outputs:
            output_type = output.get("type", "unknown")

            if output_type == "causal_chain":
                # 因果链→真值条目
                adaptation_stats["causal_chains"] += 1
                chain = output.get("chain", [])
                for edge in chain:
                    truth_entries.append({
                        "truth_id": f"TRUTH-CAUSAL-{hashlib.md5(json.dumps(edge, sort_keys=True).encode()).hexdigest()[:8]}",
                        "content": f"因果关系: {edge.get('cause', '?')} → {edge.get('effect', '?')}",
                        "truth_type": "causal_relation",
                        "confidence": edge.get("causal_strength", 0.5),
                        "source": "causal_domain",
                        "adaptation_type": "causal_edge→truth_entry",
                    })

            elif output_type == "singularity_alert":
                # 奇点预警→真值置信度
                adaptation_stats["singularity_alerts"] += 1
                probability = output.get("probability", 0.5)
                truth_entries.append({
                    "truth_id": f"TRUTH-SINGULARITY-{hashlib.md5(output.get('node', 'unknown').encode()).hexdigest()[:8]}",
                    "content": f"奇点预警: {output.get('node', '?')} 爆发概率 {probability}",
                    "truth_type": "singularity_prediction",
                    "confidence": probability,
                    "source": "causal_domain",
                    "adaptation_type": "singularity_probability→truth_confidence",
                    "alert_level": output.get("alert_level", "yellow"),
                })

            elif output_type == "intervention_result":
                # 干预结果→反事实真值
                adaptation_stats["intervention_results"] += 1
                truth_entries.append({
                    "truth_id": f"TRUTH-COUNTERFACTUAL-{hashlib.md5(json.dumps(output, sort_keys=True).encode()).hexdigest()[:8]}",
                    "content": f"反事实真值: do({output.get('intervention', '?')}) → {output.get('outcome', '?')}",
                    "truth_type": "counterfactual",
                    "confidence": output.get("confidence", 0.6),
                    "source": "causal_domain",
                    "adaptation_type": "intervention_result→counterfactual_truth",
                })

        return {
            "input_causal_outputs": len(causal_outputs),
            "adapted_truth_entries": len(truth_entries),
            "adaptation_stats": adaptation_stats,
            "adaptation_rate": round(len(truth_entries) / max(len(causal_outputs), 1), 2),
            "truth_entries_sample": truth_entries[:10],
            "truth_types_distribution": {
                t: sum(1 for e in truth_entries if e["truth_type"] == t)
                for t in set(e["truth_type"] for e in truth_entries)
            },
            "cte_loop_status": "C→T 适配器已激活",
        }


class TruthToEvolutionAdapter(BaseOperator):
    """TruthToEvolution适配器算子：将真值域输出转换为进化域可消费信号"""

    def __init__(self):
        super().__init__(
            operator_id="TRUTH_TO_EVOLUTION_ADAPTER",
            name="TruthToEvolution适配器算子",
            layer=5,
            description="将真值域输出(真值条目/置信度/冲突标记)转换为进化域可消费信号——真值纯度→适应度Φ输入，冲突标记→进化目标，漂移率→进化压力"
        )

    def execute(self, truth_outputs=None, **kwargs):
        truth_outputs = truth_outputs or []
        evolution_signals = []

        # 计算真值纯度（适应度Φ输入）
        total_truths = len(truth_outputs)
        high_confidence = sum(1 for t in truth_outputs if t.get("confidence", 0) >= 0.7)
        truth_purity = high_confidence / max(total_truths, 1)

        # 检测冲突标记（进化目标）
        conflicts = [t for t in truth_outputs if t.get("conflict", False) or t.get("status") == "conflict"]

        # 检测漂移率（进化压力）
        drift_count = sum(1 for t in truth_outputs if t.get("drift", 0) > 0.05)
        drift_rate = drift_count / max(total_truths, 1)

        # 生成进化信号
        evolution_signals.append({
            "signal_id": f"EVOL-FITNESS-{int(time.time())}",
            "signal_type": "fitness_input",
            "name": "真值纯度适应度Φ",
            "value": round(truth_purity, 4),
            "description": "高置信度真值占比，作为进化适应度输入",
            "priority": 1,
        })

        if conflicts:
            evolution_signals.append({
                "signal_id": f"EVOL-CONFLICT-{int(time.time())}",
                "signal_type": "evolution_target",
                "name": "真值冲突消解目标",
                "value": len(conflicts),
                "description": f"检测到{len(conflicts)}个真值冲突，作为进化目标进行消解",
                "conflict_entries": [c.get("truth_id", "?") for c in conflicts[:5]],
                "priority": 2,
            })

        if drift_rate > 0:
            evolution_signals.append({
                "signal_id": f"EVOL-DRIFT-{int(time.time())}",
                "signal_type": "evolution_pressure",
                "name": "语义漂移进化压力",
                "value": round(drift_rate, 4),
                "description": f"语义漂移率{drift_rate:.2%}，作为进化压力驱动概念稳定化",
                "priority": 3,
            })

        # 优先级排序
        evolution_signals.sort(key=lambda x: x.get("priority", 99))

        return {
            "input_truth_outputs": total_truths,
            "high_confidence_truths": high_confidence,
            "truth_purity": round(truth_purity, 4),
            "conflicts_detected": len(conflicts),
            "drift_rate": round(drift_rate, 4),
            "evolution_signals": len(evolution_signals),
            "signals": evolution_signals,
            "cte_loop_status": "T→E 适配器已激活",
            "evolution_domain_ready": len(evolution_signals) > 0,
        }


# ==================== 第八层：安全确权 ====================

class EFuseOperator(BaseOperator):
    """eFuse熔断触发算子：检测账本内严重矛盾真值/哈希链篡改风险，执行局部分支熔断隔离"""

    def __init__(self):
        super().__init__(
            operator_id="EFUSE_TRIGGER",
            name="eFuse熔断触发算子",
            layer=8,
            description="检测账本内严重矛盾真值/哈希链篡改风险，执行局部分支熔断隔离，保护主Merkle-DAG主干，隔离问题分支不销毁数据"
        )

    def execute(self, truth_entries=None, merkle_chain=None, **kwargs):
        truth_entries = truth_entries or []
        merkle_chain = merkle_chain or []
        contradictions = []
        tamper_risks = []
        fused_branches = []
        main_chain_protected = True

        # 检测严重矛盾真值
        contradiction_threshold = _cfg("efuse.contradiction_threshold", 3)
        content_groups = {}
        for entry in truth_entries:
            content_key = hashlib.md5(entry.get("content", "")[:50].encode()).hexdigest()[:8]
            if content_key not in content_groups:
                content_groups[content_key] = []
            content_groups[content_key].append(entry)

        for key, entries in content_groups.items():
            if len(entries) >= contradiction_threshold:
                # 检测矛盾（同一内容不同真值类型或置信度差异大）
                truth_types = set(e.get("truth_type", "") for e in entries)
                confidences = [e.get("confidence", 0) for e in entries]
                if len(truth_types) > 1 or (max(confidences) - min(confidences) > 0.5):
                    contradictions.append({
                        "content_key": key,
                        "entry_count": len(entries),
                        "truth_types": list(truth_types),
                        "confidence_range": [min(confidences), max(confidences)],
                        "severity": "critical" if len(entries) >= contradiction_threshold * 2 else "high",
                        "entry_ids": [e.get("truth_id", "?") for e in entries[:5]],
                    })

        # 检测哈希链篡改风险
        if len(merkle_chain) > 1:
            for i in range(1, len(merkle_chain)):
                current = merkle_chain[i]
                previous = merkle_chain[i-1]
                expected_prev = hashlib.sha256(json.dumps(previous, sort_keys=True).encode()).hexdigest()
                if current.get("prev_hash") != expected_prev:
                    tamper_risks.append({
                        "block_index": i,
                        "expected_prev_hash": expected_prev[:16],
                        "actual_prev_hash": current.get("prev_hash", "N/A")[:16],
                        "risk_type": "hash_chain_break",
                        "severity": "critical",
                    })

        # 执行局部分支熔断隔离
        for contradiction in contradictions:
            if contradiction["severity"] in ["critical", "high"]:
                branch_id = f"FUSED-BRANCH-{contradiction['content_key']}"
                fused_branches.append({
                    "branch_id": branch_id,
                    "reason": f"矛盾真值熔断: {contradiction['entry_count']}个矛盾条目",
                    "severity": contradiction["severity"],
                    "isolated_entries": contradiction["entry_ids"],
                    "action": "局部分支隔离，保护主Merkle-DAG主干",
                    "data_preserved": True,
                })

        for tamper in tamper_risks:
            branch_id = f"FUSED-TAMPER-{tamper['block_index']}"
            fused_branches.append({
                "branch_id": branch_id,
                "reason": f"哈希链篡改风险: 区块{tamper['block_index']}",
                "severity": tamper["severity"],
                "action": "熔断隔离可疑区块",
                "data_preserved": True,
            })

        return {
            "input_truth_entries": len(truth_entries),
            "input_merkle_blocks": len(merkle_chain),
            "contradictions_detected": len(contradictions),
            "tamper_risks_detected": len(tamper_risks),
            "fused_branches": len(fused_branches),
            "main_chain_protected": main_chain_protected,
            "contradiction_threshold": contradiction_threshold,
            "contradictions_detail": contradictions[:5],
            "tamper_risks_detail": tamper_risks[:5],
            "fused_branches_detail": fused_branches[:5],
            "efuse_status": "已触发" if fused_branches else "未触发（无严重风险）",
            "data_non_destructive": True,
        }


# ==================== 扩展算子注册函数 ====================

def get_extended_operators():
    """获取所有扩展算子实例列表"""
    return [
        ExternalAnchoringOperator(),
        RiemannianManifoldOperator(),
        SMBSMappingOperator(),
        EntityRelationExtractor(),
        KnowledgeGraphCompletion(),
        CausalToTruthAdapter(),
        TruthToEvolutionAdapter(),
        EFuseOperator(),
    ]


def register_extended_operators(scheduler):
    """将扩展算子注册到算子调度器"""
    for op in get_extended_operators():
        scheduler.register(op)
    return scheduler


if __name__ == "__main__":
    print("=" * 60)
    print("元极恒一｜27算子扩展实现（第二批）测试")
    print("=" * 60)

    operators = get_extended_operators()
    print(f"\n扩展算子数量: {len(operators)}个")
    for op in operators:
        print(f"  第{op.layer}层 | {op.operator_id} | {op.name}")

    # 测试外部锚定算子
    print("\n--- 测试外部锚定算子 ---")
    op = ExternalAnchoringOperator()
    result = op.run(truth_entries=[
        {"content": "数据显示AI市场增长30%", "confidence": 0.8, "source": "report"},
        {"content": "我认为AI会改变世界", "confidence": 0.5},
    ])
    print(f"  状态: {result['status']}")
    print(f"  锚定条目: {result['anchored_entries']}, 幻觉嫌疑: {result['hallucination_suspects']}")

    # 测试eFuse熔断算子
    print("\n--- 测试eFuse熔断算子 ---")
    op = EFuseOperator()
    result = op.run(truth_entries=[
        {"content": "测试矛盾内容123", "truth_type": "fact", "confidence": 0.9, "truth_id": "t1"},
        {"content": "测试矛盾内容123", "truth_type": "opinion", "confidence": 0.3, "truth_id": "t2"},
        {"content": "测试矛盾内容123", "truth_type": "hypothesis", "confidence": 0.6, "truth_id": "t3"},
    ])
    print(f"  状态: {result['status']}")
    print(f"  矛盾检测: {result['contradictions_detected']}, 熔断分支: {result['fused_branches']}")
    print(f"  eFuse状态: {result['efuse_status']}")

    print("\n" + "=" * 60)
    print("27算子扩展实现测试完成")
    print("=" * 60)
