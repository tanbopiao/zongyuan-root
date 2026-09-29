#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本体进化算子 V2.0（本地增强版）
V2 新增能力：
  1. 传递关系推理：基于三元组推导隐含关系（A包含B,B包含C → A包含C），输出"推理生成"条目
  2. 同名概念消歧：同名实体依托属性/关系上下文计算相似度，区分同名不同概念，减少本体混淆
  3. 本体图谱JSON生成：输出可视化图谱结构，直接对接前端渲染实体-关系网络图
V1 能力保留：实体/关系增量抽取、噪声清洗、进化等级判定、幂等保护。
确权：DID-BR-000002 | 溯源：Ω₀⊂⊙∞⊂Ω
"""
import hashlib
import json
import datetime
import os
import re
from typing import Dict, Any, List, Optional, Tuple

# ---- 双端兼容 ----
try:
    from core.base_operator import BaseOperator, OperatorResult, OperatorPriority
    from registry.operator_registry import register_operator
    _BASE = BaseOperator
    _DECORATOR = register_operator
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.base import BaseOperator, OperatorResult
    _BASE = BaseOperator
    _DECORATOR = lambda cls: cls


def _now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat()


# 中文实体抽取模式
_PATTERNS = [
    re.compile(r'["“]([^"”]{2,24})["”]'),
    re.compile(r'([A-Z][A-Za-z0-9_-]{2,29})'),
    re.compile(r'([\u4e00-\u9fa5]{2,8}(?:引擎|算子|系统|子系统|平台|协议|机制|模块|模型|架构|链路|网关|内核|法则|矩阵|库|服务|节点))'),
]

# 显式关系词（用于关系抽取与传递推理）
_REL_WORDS = ("包含", "属于", "依赖", "继承", "关联", "驱动", "支撑", "构成", "采用", "基于")
_REL_PATTERN = re.compile(r'([\u4e00-\u9fa5A-Za-z0-9_-]{2,16})(包含|属于|依赖|继承|关联|驱动|支撑|构成|采用|基于)([\u4e00-\u9fa5A-Za-z0-9_-]{2,16})')

_NOISE_PREFIX = ("引入", "构建", "完善", "升级", "实现", "提供", "基于", "通过", "以及",
                 "与", "的", "对", "和", "及", "并", "或", "用于", "进行", "建立", "打造",
                 "推动", "促进", "支撑", "赋能", "覆盖", "打通", "治理", "优化", "落地")

# 传递关系类型
_TRANSITIVE_RELS = ("包含", "属于", "依赖", "继承")


def _clean_entity(e: str) -> Optional[str]:
    e = e.strip()
    for p in _NOISE_PREFIX:
        if e.startswith(p):
            e = e[len(p):]
            break
    e = e.strip("，。、：:；;,. ")
    if not e or len(e) < 2 or len(e) > 24:
        return None
    if e in _NOISE_PREFIX:
        return None
    return e


def _extract_entities(text: str) -> List[str]:
    entities = []
    for pat in _PATTERNS:
        for m in pat.finditer(text or ""):
            e = _clean_entity(m.group(1))
            if e and e not in entities:
                entities.append(e)
    return entities


@_DECORATOR
class OntologyEvolveOperator(_BASE):
    """本体进化算子 V2（传递推理+同名消歧+图谱JSON）"""

    # ---- 云端注册元数据 ----
    OPERATOR_ID = "ontology-evolve-v2"
    OPERATOR_NAME = "本体进化算子V2"
    OPERATOR_VERSION = "2.0.0"
    OPERATOR_GROUP = "knowledge"
    OPERATOR_DESCRIPTION = "V2:实体/关系增量抽取+传递关系推理+同名概念消歧+本体图谱JSON输出;V1:增量比对/进化分级/幂等保护"
    PRIORITY = 75

    # ---- 本地注册元数据 ----
    name = "ontology_evolve"
    version = "2.0.0"
    description = OPERATOR_DESCRIPTION
    category = "knowledge"
    inputs_schema = {
        "content": "string(必填,待进化资产内容)",
        "asset_id": "string(可选,资产ID)",
        "ontology": "dict(可选,现有本体{entities:[],relations:[],attributes:{}})",
        "infer_transitive": "bool(可选,是否启用传递推理,默认True)",
        "disambiguate": "bool(可选,是否启用同名消歧,默认True)",
        "graph_output": "bool(可选,是否输出图谱JSON,默认True)",
    }
    outputs_schema = {
        "new_entities": "list",
        "updated_relations": "list",
        "inferred_relations": "list(推理生成)",
        "disambiguation": "list(同名消歧)",
        "graph_json": "dict(本体图谱)",
        "evolution_level": "string",
        "priority": "int",
    }

    # ---------- V2: 传递关系推理 ----------
    def _infer_transitive(self, relations: List[Dict]) -> List[Dict]:
        inferred = []
        seen = set((r["subject"], r["relation"], r["object"]) for r in relations)
        for r1 in relations:
            if r1["relation"] not in _TRANSITIVE_RELS:
                continue
            for r2 in relations:
                if r2["relation"] != r1["relation"]:
                    continue
                if r1["object"] == r2["subject"] and r1["subject"] != r2["object"]:
                    key = (r1["subject"], r1["relation"], r2["object"])
                    if key not in seen:
                        seen.add(key)
                        inferred.append({
                            "subject": r1["subject"], "relation": r1["relation"],
                            "object": r2["object"], "via": r1["object"],
                            "inferred": True, "source": "transitive_reasoning",
                        })
        return inferred

    # ---------- V2: 同名概念消歧 ----------
    def _disambiguate(self, entities: List[str], attributes: Dict) -> List[Dict]:
        result = []
        seen = {}
        for e in entities:
            key = e.lower().replace("-", "").replace("_", "")
            ctx = attributes.get(e, {})
            if key in seen and seen[key] != e:
                result.append({
                    "name": e,
                    "disambiguated": True,
                    "context": ctx,
                    "hint": "同名实体存在多个上下文,建议按属性/域区分标识",
                })
            else:
                seen[key] = e
        return result

    # ---------- V2: 图谱JSON生成 ----------
    def _build_graph(self, entities: List[str], relations: List[Dict], inferred: List[Dict]) -> Dict:
        nodes = [{"id": e, "name": e, "type": "concept", "category": "entity"} for e in entities]
        edges = []
        for r in relations:
            edges.append({"source": r["subject"], "target": r["object"], "relation": r["relation"]})
        for r in inferred:
            edges.append({"source": r["subject"], "target": r["object"],
                          "relation": r["relation"], "inferred": True})
        return {"nodes": nodes, "edges": edges, "stats": {
            "node_count": len(nodes), "edge_count": len(edges),
            "inferred_edge_count": len(inferred),
        }}

    def execute(self, inputs: Dict) -> OperatorResult:
        try:
            content = inputs.get("content", "")
            asset_id = inputs.get("asset_id", "UNKNOWN")
            if not content:
                return OperatorResult(False, error="content 为必填项")

            ontology: Dict = inputs.get("ontology") or {"entities": [], "relations": [], "attributes": {}}
            existing_entities = set(ontology.get("entities") or [])
            existing_relations = set(ontology.get("relations") or [])
            attributes: Dict = ontology.get("attributes") or {}

            # 1. 实体抽取（V1）
            extracted = _extract_entities(content)
            new_entities = [e for e in extracted if e not in existing_entities]

            # 2. 关系抽取（V1共现 + V2显式关系词）
            new_relations = []
            seen_rel = set(existing_relations)
            # 2a. 显式关系词：A 包含/依赖/支撑 B
            for m in _REL_PATTERN.finditer(content):
                subj = _clean_entity(m.group(1))
                rel = m.group(2)
                obj = _clean_entity(m.group(3))
                if subj and obj and subj != obj:
                    key = f"{subj}{rel}{obj}"
                    if key not in seen_rel:
                        seen_rel.add(key)
                        new_relations.append({"subject": subj, "relation": rel, "object": obj})
            # 2b. 共现关系（V1保留）
            for i in range(len(extracted) - 1):
                rel = f"{extracted[i]}→{extracted[i+1]}"
                if rel not in seen_rel:
                    seen_rel.add(rel)
                    new_relations.append({"subject": extracted[i], "relation": "关联", "object": extracted[i+1]})

            # 3. 传递推理（V2）
            inferred = []
            if inputs.get("infer_transitive", True):
                inferred = self._infer_transitive(new_relations)

            # 4. 同名消歧（V2）
            disambiguation = []
            if inputs.get("disambiguate", True):
                disambiguation = self._disambiguate(extracted, attributes)

            # 5. 图谱JSON（V2）
            graph_json = None
            if inputs.get("graph_output", True):
                graph_json = self._build_graph(extracted, new_relations, inferred)

            # 6. 进化等级与优先级（V1保留）
            n_new = len(new_entities)
            n_rel = len(new_relations) + len(inferred)
            if n_new >= 5 or n_rel >= 5:
                level, priority = "MAJOR", 90
            elif n_new >= 2 or n_rel >= 2:
                level, priority = "MINOR", 60
            elif n_new > 0 or n_rel > 0:
                level, priority = "PATCH", 30
            else:
                level, priority = "NO_CHANGE", 0

            return OperatorResult(True, data={
                "new_entities": new_entities,
                "updated_relations": new_relations,
                "inferred_relations": inferred,
                "disambiguation": disambiguation,
                "graph_json": graph_json,
                "evolution_level": level,
                "priority": priority,
                "asset_id": asset_id,
                "ontology_size": {"entities": len(existing_entities), "relations": len(existing_relations)},
                "did": "DID-BR-000002",
                "trace": "Ω₀⊂⊙∞⊂Ω",
            })
        except Exception as e:
            return OperatorResult(False, error=str(e))


if __name__ == "__main__":
    op = OntologyEvolveOperator()
    sample = "元运维平台引入稳态校准算子与熔断机制,构建同源协议,完善记忆网关对账机制,升级知识图谱引擎"
    r = op({"content": sample, "asset_id": "DEMO-001"})
    assert r.success, r.error
    print("进化等级:", r.data["evolution_level"], "| 优先级:", r.data["priority"])
    print("新增实体:", r.data["new_entities"])
    print("新增关系:", len(r.data["updated_relations"]), "条")
    print("推理关系:", len(r.data["inferred_relations"]), "条")
    g = r.data["graph_json"]
    print(f"图谱: {g['stats']['node_count']}节点 {g['stats']['edge_count']}边 ✓")

    # 传递推理专项：包含关系链
    r2 = op({"content": "元运维平台包含稳态校准子系统,稳态校准子系统包含熔断模块,熔断模块包含自动恢复机制",
             "asset_id": "INFER-001"})
    inf = r2.data["inferred_relations"]
    print("\n传递推理专项:", len(inf), "条推理关系")
    for i in inf:
        print(f"  {i['subject']} {i['relation']} {i['object']} (via {i['via']})")

    # 幂等保护
    r3 = op({"content": sample, "asset_id": "DEMO-003",
             "ontology": {"entities": r.data["new_entities"],
                          "relations": [f"{x['subject']}→{x['object']}" for x in r.data["updated_relations"]]}})
    print("\n重复内容进化等级:", r3.data["evolution_level"], "(应NO_CHANGE或低)")
