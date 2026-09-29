#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 实体关系抽取算子 v1.0
从锁档资产文本中自动抽取实体(人/事/物/概念)与关系(因果/从属/时序/相似/对立)
构建知识图谱三元组，支持跨文档实体归一化
"""
import json
import re
import hashlib
import os
from datetime import datetime, timezone

# 配置
KG_DIR = "/opt/ZONGYUAN-ROOT/knowledge_graph"
OUTPUT_TRIPLES = os.path.join(KG_DIR, "triples", "knowledge_graph_triples.jsonl")
OUTPUT_ENTITIES = os.path.join(KG_DIR, "entities", "entity_registry.json")
OUTPUT_RELATIONS = os.path.join(KG_DIR, "relations", "relation_registry.json")

# 实体类型定义
ENTITY_TYPES = {
    "PERSON": "人物/角色",
    "CONCEPT": "概念/理论",
    "SYSTEM": "系统/服务",
    "PROTOCOL": "协议/规则",
    "ASSET": "资产/产物",
    "TECH": "技术/算法",
    "DIMENSION": "维度/指标",
    "AXIOM": "公理/定理",
}

# 关系类型定义
RELATION_TYPES = {
    "CAUSE": "因果关系",
    "PART_OF": "从属/包含",
    "TEMPORAL": "时序关系",
    "SIMILAR": "相似关系",
    "OPPOSE": "对立关系",
    "DEPENDS": "依赖关系",
    "IMPLEMENTS": "实现关系",
    "ANCHORS": "锚定/确权",
    "EVOLVES": "进化/升级",
    "GOVERNS": "治理/约束",
}

# 预定义核心实体库
CORE_ENTITIES = {
    "ZONGYUAN-ROOT": {"type": "SYSTEM", "name": "元极恒一自治体系", "aliases": ["ZONGYUAN", "元极恒一"]},
    "OMEGA_BRAIN": {"type": "SYSTEM", "name": "Ω-Brainμ真值引擎", "aliases": ["omega_brain", "Omega Brain", "Ω-Brainμ"]},
    "LOIP": {"type": "SYSTEM", "name": "层叠本体推理系统", "aliases": ["loip"]},
    "CORE-TRUTH-ARCH": {"type": "PROTOCOL", "name": "核心真值架构", "aliases": ["核心真值", "truth architecture"]},
    "SM-BS": {"type": "CONCEPT", "name": "语义-黎曼流形双向稳态映射", "aliases": ["SM-BS映射"]},
    "DID-BR-000002": {"type": "PROTOCOL", "name": "DID确权标识", "aliases": ["DID"]},
    "TRACE_MARK": {"type": "PROTOCOL", "name": "溯源标识", "aliases": ["溯源符号"]},
    "THREE_STATE": {"type": "AXIOM", "name": "三态秩序化智能最小完备体系", "aliases": ["三态", "逻辑态信息态能量态"]},
    "SYMBOL_EMERGENCE": {"type": "AXIOM", "name": "符号涌现AI认知进化机制", "aliases": ["符号涌现机制"]},
    "HIGH_DENSITY_TRUTH": {"type": "AXIOM", "name": "高密度客观真值层级理论", "aliases": ["真值层级"]},
    "KUNLUN_DONGTIAN": {"type": "ASSET", "name": "昆仑洞天短剧IP", "aliases": ["昆仑洞天短剧", "昆仑洞天"]},
    "JIUTIAN_XUANNV": {"type": "PERSON", "name": "九天玄女", "aliases": ["玄女"]},
    "HUODOU_AIOS": {"type": "SYSTEM", "name": "火斗云智AIOS", "aliases": ["huodouai", "AIOS", "火斗云智"]},
    "META_ORDER_ARCHIVE": {"type": "SYSTEM", "name": "元秩序归档锁档引擎", "aliases": ["元秩序归档", "meta-order-archive"]},
    "EFUSE": {"type": "PROTOCOL", "name": "eFuse硬件熔断固化", "aliases": ["eFuse熔断", "eFuse"]},
    "MERKLE_DAG": {"type": "TECH", "name": "Merkle-DAG哈希链", "aliases": ["哈希链", "Merkle"]},
    "VECTOR_DB": {"type": "SYSTEM", "name": "向量数据库知识库", "aliases": ["vector_db", "向量库", "向量数据库"]},
    "DRIFT_DETECT": {"type": "TECH", "name": "语义漂移检测", "aliases": ["drift", "漂移检测", "漂移"]},
    "FEDERATION": {"type": "TECH", "name": "多实例联邦合并引擎", "aliases": ["federation", "联邦合并"]},
    "SELF_HEAL": {"type": "SYSTEM", "name": "自我修复引擎", "aliases": ["self_heal", "自愈", "自愈引擎"]},
}

class EntityRelationExtractor:
    def __init__(self):
        self.entities = {}
        self.triples = []
        self.entity_counter = 0
        self._init_core_entities()

    def _init_core_entities(self):
        for eid, edata in CORE_ENTITIES.items():
            self.entities[eid] = {
                "id": eid,
                "name": edata["name"],
                "type": edata["type"],
                "type_name": ENTITY_TYPES.get(edata["type"], "未知"),
                "aliases": edata.get("aliases", []),
                "source": "core_library",
                "confidence": 1.0,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.entity_counter += 1

    def _normalize_entity_id(self, name):
        clean = re.sub(r'[^\w\u4e00-\u9fff]', '_', name)
        clean = re.sub(r'_+', '_', clean).strip('_')
        return "ENT-" + clean[:32].upper()

    def extract_entities_from_text(self, text, source="unknown"):
        extracted = []
        # 匹配核心实体别名
        for eid, edata in self.entities.items():
            for alias in [edata["name"]] + edata.get("aliases", []):
                if alias in text:
                    extracted.append(eid)
                    break
        # 服务名
        services = re.findall(r'([a-z]+-[a-z]+(?:-[a-z]+)?)\.service', text)
        for svc in services:
            eid = "ENT-SVC-" + svc.upper().replace('-', '_')
            if eid not in self.entities:
                self.entities[eid] = {
                    "id": eid, "name": svc + "服务", "type": "SYSTEM",
                    "type_name": "系统/服务", "aliases": [svc],
                    "source": source, "confidence": 0.9,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                self.entity_counter += 1
            extracted.append(eid)
        # 资产ID
        assets = re.findall(r'KD-[A-Z]+-\d{4}', text)
        for asset in assets:
            eid = "ENT-" + asset
            if eid not in self.entities:
                self.entities[eid] = {
                    "id": eid, "name": "资产" + asset, "type": "ASSET",
                    "type_name": "资产/产物", "aliases": [asset],
                    "source": source, "confidence": 0.95,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                self.entity_counter += 1
            extracted.append(eid)
        return list(set(extracted))

    def add_relation(self, subject_id, relation_type, object_id, confidence=0.8, evidence=""):
        if subject_id not in self.entities or object_id not in self.entities:
            return None
        rid = "REL-" + hashlib.sha256((subject_id + ":" + relation_type + ":" + object_id).encode()).hexdigest()[:12].upper()
        triple = {
            "id": rid,
            "subject": subject_id,
            "subject_name": self.entities[subject_id]["name"],
            "relation": relation_type,
            "relation_name": RELATION_TYPES.get(relation_type, relation_type),
            "object": object_id,
            "object_name": self.entities[object_id]["name"],
            "confidence": confidence,
            "evidence": evidence,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.triples.append(triple)
        return triple

    def build_core_relations(self):
        # 公理体系
        self.add_relation("ZONGYUAN-ROOT", "PART_OF", "CORE-TRUTH-ARCH", 1.0, "核心真值架构是ZONGYUAN-ROOT核心组成")
        self.add_relation("CORE-TRUTH-ARCH", "PART_OF", "THREE_STATE", 1.0, "三态秩序化是第一公理")
        self.add_relation("CORE-TRUTH-ARCH", "PART_OF", "SYMBOL_EMERGENCE", 1.0, "符号涌现是第二公理")
        self.add_relation("CORE-TRUTH-ARCH", "PART_OF", "HIGH_DENSITY_TRUTH", 1.0, "高密度真值是第三公理")
        # 系统依赖
        self.add_relation("OMEGA_BRAIN", "DEPENDS", "VECTOR_DB", 0.95, "Ω-Brainμ依赖向量数据库")
        self.add_relation("LOIP", "DEPENDS", "OMEGA_BRAIN", 0.9, "LOIP依赖Ω-Brainμ")
        self.add_relation("HUODOU_AIOS", "IMPLEMENTS", "ZONGYUAN-ROOT", 0.95, "火斗云智是云端实现")
        # 锚定确权
        self.add_relation("ZONGYUAN-ROOT", "ANCHORS", "DID-BR-000002", 1.0, "所有资产确权至DID")
        self.add_relation("ZONGYUAN-ROOT", "ANCHORS", "TRACE_MARK", 1.0, "所有资产使用溯源标识")
        # 技术实现
        self.add_relation("META_ORDER_ARCHIVE", "IMPLEMENTS", "MERKLE_DAG", 0.95, "使用Merkle-DAG哈希链")
        self.add_relation("META_ORDER_ARCHIVE", "IMPLEMENTS", "EFUSE", 0.95, "使用eFuse熔断固化")
        self.add_relation("SM-BS", "IMPLEMENTS", "DRIFT_DETECT", 0.9, "实现语义漂移检测")
        # 进化
        self.add_relation("ZONGYUAN-ROOT", "EVOLVES", "SELF_HEAL", 0.9, "通过自愈引擎自进化")
        self.add_relation("ZONGYUAN-ROOT", "EVOLVES", "FEDERATION", 0.85, "通过联邦合并多实例进化")
        # 治理
        self.add_relation("CORE-TRUTH-ARCH", "GOVERNS", "OMEGA_BRAIN", 0.95, "治理Ω-Brainμ真值输出")
        self.add_relation("CORE-TRUTH-ARCH", "GOVERNS", "LOIP", 0.9, "治理LOIP推理过程")
        # 产品
        self.add_relation("KUNLUN_DONGTIAN", "PART_OF", "JIUTIAN_XUANNV", 0.8, "九天玄女是核心角色")
        self.add_relation("KUNLUN_DONGTIAN", "DEPENDS", "ZONGYUAN-ROOT", 0.9, "依赖自治体系")

    def save(self):
        os.makedirs(os.path.dirname(OUTPUT_TRIPLES), exist_ok=True)
        os.makedirs(os.path.dirname(OUTPUT_ENTITIES), exist_ok=True)
        os.makedirs(os.path.dirname(OUTPUT_RELATIONS), exist_ok=True)
        with open(OUTPUT_TRIPLES, "w", encoding="utf-8") as f:
            for triple in self.triples:
                f.write(json.dumps(triple, ensure_ascii=False) + "\n")
        with open(OUTPUT_ENTITIES, "w", encoding="utf-8") as f:
            json.dump({"total_entities": len(self.entities), "entities": list(self.entities.values()),
                       "generated_at": datetime.now(timezone.utc).isoformat()}, f, ensure_ascii=False, indent=2)
        with open(OUTPUT_RELATIONS, "w", encoding="utf-8") as f:
            json.dump({"total_relations": len(self.triples), "relation_types": RELATION_TYPES,
                       "entity_types": ENTITY_TYPES, "generated_at": datetime.now(timezone.utc).isoformat()},
                      f, ensure_ascii=False, indent=2)
        kg_content = json.dumps({"entities": len(self.entities), "triples": len(self.triples)}, sort_keys=True)
        kg_hash = hashlib.sha256(kg_content.encode()).hexdigest().upper()
        return {"total_entities": len(self.entities), "total_triples": len(self.triples), "kg_hash": kg_hash}

def main():
    print("=" * 60)
    print("ZONGYUAN-ROOT 实体关系抽取算子 v1.0")
    print("=" * 60)
    extractor = EntityRelationExtractor()
    print("初始化核心实体:", extractor.entity_counter, "个")
    extractor.build_core_relations()
    print("构建核心关系:", len(extractor.triples), "条三元组")
    arch_file = "/opt/ZONGYUAN-ROOT/core_truth_architecture.json"
    if os.path.exists(arch_file):
        with open(arch_file, "r", encoding="utf-8") as f:
            content = f.read()
        entities = extractor.extract_entities_from_text(content, "core_truth_architecture")
        print("从核心真值架构抽取实体:", len(entities), "个")
    result = extractor.save()
    print("\n知识图谱构建完成:")
    print("  实体总数:", result["total_entities"])
    print("  三元组总数:", result["total_triples"])
    print("  图谱哈希:", result["kg_hash"][:16], "...")

if __name__ == "__main__":
    main()
