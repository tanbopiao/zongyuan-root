#!/usr/bin/env python3
"""
真值自动转化知识图谱引擎 V1.0
ZONGYUAN-ROOT元极恒一自治体系
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

功能：
1. 从态元数据库/内核/本地资产提取真值
2. 实体关系自动抽取（基于规则+语义模式）
3. 构建知识图谱三元组（主体-关系-客体）
4. 图谱去重、合并、置信度评分
5. 输出JSON/GraphML/可视化HTML
6. 增量更新（只处理新增真值）
"""
import hashlib
import json
import os
import re
import sqlite3
import time
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict

# ==================== 配置 ====================
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
STATE_ATOMS_DB = os.path.expanduser("~/.zongyuan_root/state_atoms.db")
KERNEL_PATH = os.path.expanduser("~/.zongyuan_root/kernel/kernel_state.json")
GRAPH_OUTPUT_DIR = os.path.expanduser("~/.zongyuan_root/knowledge_graph")
PROCESSED_TRUTHS_FILE = os.path.join(GRAPH_OUTPUT_DIR, "processed_truths.json")

# 实体类型定义
ENTITY_TYPES = {
    "concept": "概念",
    "system": "系统",
    "technology": "技术",
    "protocol": "协议",
    "node": "节点",
    "role": "角色",
    "rule": "规则",
    "dimension": "维度",
    "state": "状态",
    "operator": "算子",
}

# 关系类型定义
RELATION_TYPES = {
    "contains": "包含",
    "depends_on": "依赖",
    "belongs_to": "属于",
    "related_to": "关联",
    "drives": "驱动",
    "constrains": "约束",
    "maps_to": "映射",
    "evolves_to": "演化",
    "consists_of": "由...组成",
    "enables": "使能",
}

# 实体识别关键词模式
ENTITY_PATTERNS = {
    "system": [
        r"ZONGYUAN-ROOT", r"元极恒一", r"火斗云智", r"昆仑洞天",
        r"态元引擎", r"六态生命体", r"记忆网关", r"知识图谱",
        r"Webhook", r"全网搜索", r"真值提炼",
    ],
    "concept": [
        r"三态融合", r"六态融合", r"信息态", r"逻辑态", r"能量态",
        r"法则态", r"智能态", r"生命态", r"本源节点", r"太初寂态",
        r"因果链", r"希尔伯特", r"流形", r"黎曼", r"真值",
        r"自治", r"稳态", r"fitness", r"能量竞价",
    ],
    "protocol": [
        r"同源协议", r"A2A", r"MCP", r"Ω-OP-SCHED",
        r"CTE", r"SM-BS", r"Merkle-DAG",
    ],
    "technology": [
        r"向量数据库", r"向量检索", r"语义搜索", r"知识图谱",
        r"SQLite", r"Flask", r"Chromadb",
    ],
    "node": [
        r"太初寂态", r"宇宙首次自震荡", r"本源九维框架", r"1080基准网格",
        r"希尔伯特基座", r"希尔伯特场态", r"天地人三盘", r"因果链第一链",
        r"先天基准态", r"本源六态层级",
    ],
    "dimension": [
        r"信息维度", r"逻辑维度", r"能量维度", r"时间维度", r"空间维度",
        r"因果维度", r"语义维度",
    ],
    "operator": [
        r"P4真值对账", r"P7外部锚定", r"真值提炼", r"漂移巡检",
        r"实体关系抽取", r"因果链溯源", r"奇点预测", r"因果干预",
    ],
    "rule": [
        r"元宪法", r"元公理", r"元法则", r"熔断", r"eFuse",
        r"二八分配", r"用进废退",
    ],
}

# 关系抽取模式（正则）
RELATION_PATTERNS = [
    # "A包含B" / "A由B组成"
    (r"(.+?)包含(.+?)(?:[，。、；]|$)", "contains"),
    (r"(.+?)由(.+?)组成", "consists_of"),
    # "A依赖B" / "A基于B"
    (r"(.+?)(?:依赖|基于|依托)(.+?)(?:[，。、；]|$)", "depends_on"),
    # "A属于B" / "A是B的"
    (r"(.+?)(?:属于|是)(.+?)(?:的|层|类|体系)(?:[，。、；]|$)", "belongs_to"),
    # "A驱动B" / "A使能B"
    (r"(.+?)(?:驱动|使能|触发|激活)(.+?)(?:[，。、；]|$)", "drives"),
    # "A约束B" / "A限制B"
    (r"(.+?)(?:约束|限制|规范|管控)(.+?)(?:[，。、；]|$)", "constrains"),
    # "A映射到B" / "A对应B"
    (r"(.+?)(?:映射|对应|转换为)(.+?)(?:[，。、；]|$)", "maps_to"),
    # "A演化到B" / "A进化为B"
    (r"(.+?)(?:演化|进化|跃迁)(?:到|为)(.+?)(?:[，。、；]|$)", "evolves_to"),
    # "A与B关联" / "A和B协同"
    (r"(.+?)(?:与|和)(.+?)(?:关联|协同|联动|配合)(?:[，。、；]|$)", "related_to"),
]


# ==================== 实体类 ====================
class Entity:
    def __init__(self, name: str, entity_type: str = "concept"):
        self.id = hashlib.md5(name.encode()).hexdigest()[:12]
        self.name = name
        self.type = entity_type
        self.confidence = 0.5
        self.source_count = 0
        self.related_entities = set()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "type_label": ENTITY_TYPES.get(self.type, self.type),
            "confidence": round(self.confidence, 4),
            "source_count": self.source_count,
            "degree": len(self.related_entities),
        }


# ==================== 关系类 ====================
class Relation:
    def __init__(self, source: str, target: str, rel_type: str,
                 confidence: float = 0.5, source_truth: str = ""):
        self.id = hashlib.md5(f"{source}{rel_type}{target}".encode()).hexdigest()[:12]
        self.source = source
        self.target = target
        self.type = rel_type
        self.type_label = RELATION_TYPES.get(rel_type, rel_type)
        self.confidence = confidence
        self.source_truth = source_truth
        self.evidence_count = 1

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "type_label": self.type_label,
            "confidence": round(self.confidence, 4),
            "evidence_count": self.evidence_count,
        }


# ==================== 实体抽取器 ====================
class EntityExtractor:
    """从真值文本中抽取实体"""

    def extract(self, text: str) -> List[Tuple[str, str]]:
        """返回 [(实体名, 实体类型), ...]"""
        entities = []
        seen = set()

        for entity_type, patterns in ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    name = match if isinstance(match, str) else match[0]
                    name = name.strip().strip("，。、；：")
                    if len(name) >= 2 and name not in seen:
                        seen.add(name)
                        entities.append((name, entity_type))

        return entities


# ==================== 关系抽取器 ====================
class RelationExtractor:
    """从真值文本中抽取实体间关系"""

    def __init__(self):
        self.entity_extractor = EntityExtractor()

    def extract(self, text: str, truth_id: str = "") -> List[Relation]:
        """从文本中抽取关系三元组"""
        relations = []
        entities = self.entity_extractor.extract(text)
        entity_names = [e[0] for e in entities]

        if len(entity_names) < 2:
            return relations

        # 基于模式匹配抽取关系
        for pattern, rel_type in RELATION_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    source_raw, target_raw = match[0], match[1]
                else:
                    continue

                # 匹配到的文本中是否包含已知实体
                source_entity = self._find_best_entity(source_raw, entity_names)
                target_entity = self._find_best_entity(target_raw, entity_names)

                if source_entity and target_entity and source_entity != target_entity:
                    rel = Relation(
                        source=source_entity,
                        target=target_entity,
                        rel_type=rel_type,
                        confidence=0.6,
                        source_truth=truth_id,
                    )
                    relations.append(rel)

        # 基于共现的弱关系（同一真值中出现的实体互相关联）
        if len(entity_names) >= 2:
            for i in range(len(entity_names)):
                for j in range(i + 1, len(entity_names)):
                    # 检查是否已有更强的关系
                    has_strong = any(
                        r.source == entity_names[i] and r.target == entity_names[j]
                        or r.source == entity_names[j] and r.target == entity_names[i]
                        for r in relations
                    )
                    if not has_strong:
                        rel = Relation(
                            source=entity_names[i],
                            target=entity_names[j],
                            rel_type="related_to",
                            confidence=0.3,
                            source_truth=truth_id,
                        )
                        relations.append(rel)

        return relations

    def _find_best_entity(self, text: str, entity_names: List[str]) -> Optional[str]:
        """在文本中找到最匹配的已知实体"""
        best = None
        best_len = 0
        for name in entity_names:
            if name in text and len(name) > best_len:
                best = name
                best_len = len(name)
        return best


# ==================== 知识图谱 ====================
class KnowledgeGraph:
    """知识图谱存储与管理"""

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}
        self.truth_sources = set()

    def add_entity(self, name: str, entity_type: str = "concept",
                   confidence: float = 0.5):
        if name not in self.entities:
            self.entities[name] = Entity(name, entity_type)
        entity = self.entities[name]
        entity.source_count += 1
        entity.confidence = min(entity.confidence + 0.1, 0.98)
        if confidence > entity.confidence:
            entity.confidence = confidence

    def add_relation(self, relation: Relation):
        key = f"{relation.source}|{relation.type}|{relation.target}"
        if key not in self.relations:
            self.relations[key] = relation
        else:
            existing = self.relations[key]
            existing.evidence_count += 1
            existing.confidence = min(existing.confidence + 0.05, 0.98)

        # 更新实体关联
        if relation.source in self.entities:
            self.entities[relation.source].related_entities.add(relation.target)
        if relation.target in self.entities:
            self.entities[relation.target].related_entities.add(relation.source)

    def merge(self, other: "KnowledgeGraph"):
        """合并另一个图谱"""
        for name, entity in other.entities.items():
            if name not in self.entities:
                self.entities[name] = entity
            else:
                self.entities[name].source_count += entity.source_count
                self.entities[name].confidence = max(
                    self.entities[name].confidence, entity.confidence
                )
        for key, rel in other.relations.items():
            if key not in self.relations:
                self.relations[key] = rel
            else:
                self.relations[key].evidence_count += rel.evidence_count

    def get_stats(self) -> dict:
        type_dist = defaultdict(int)
        for e in self.entities.values():
            type_dist[e.type] += 1
        rel_dist = defaultdict(int)
        for r in self.relations.values():
            rel_dist[r.type] += 1

        # 计算中心度
        degrees = [(e.name, len(e.related_entities)) for e in self.entities.values()]
        degrees.sort(key=lambda x: x[1], reverse=True)

        return {
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
            "entity_type_distribution": dict(type_dist),
            "relation_type_distribution": dict(rel_dist),
            "top_central_entities": degrees[:10],
            "avg_degree": round(sum(d for _, d in degrees) / max(len(degrees), 1), 2),
            "density": round(
                len(self.relations) / max(len(self.entities) * (len(self.entities) - 1), 1),
                4
            ),
        }

    def to_json(self) -> dict:
        return {
            "meta": {
                "did": DID,
                "trace": TRACE,
                "version": "V1.0",
                "timestamp": int(time.time()),
                "engine": "TruthToKnowledgeGraph V1.0",
            },
            "stats": self.get_stats(),
            "entities": [e.to_dict() for e in self.entities.values()],
            "relations": [r.to_dict() for r in self.relations.values()],
        }

    def to_graphml(self) -> str:
        """导出GraphML格式"""
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')
        lines.append('<key id="d0" for="node" attr.name="type" attr.type="string"/>')
        lines.append('<key id="d1" for="node" attr.name="confidence" attr.type="double"/>')
        lines.append('<key id="d2" for="edge" attr.name="type" attr.type="string"/>')
        lines.append('<graph id="G" edgedefault="directed">')

        for entity in self.entities.values():
            lines.append(f'<node id="{entity.id}">')
            lines.append(f'  <data key="d0">{entity.type}</data>')
            lines.append(f'  <data key="d1">{entity.confidence}</data>')
            lines.append(f'</node>')

        for rel in self.relations.values():
            source_id = self.entities.get(rel.source, Entity(rel.source)).id
            target_id = self.entities.get(rel.target, Entity(rel.target)).id
            lines.append(f'<edge source="{source_id}" target="{target_id}">')
            lines.append(f'  <data key="d2">{rel.type}</data>')
            lines.append(f'</edge>')

        lines.append('</graph>')
        lines.append('</graphml>')
        return "\n".join(lines)


# ==================== 真值→图谱转化引擎 ====================
class TruthToKnowledgeGraphEngine:
    """真值自动转化知识图谱主引擎"""

    def __init__(self):
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()
        self.graph = KnowledgeGraph()
        self.processed_truths = self._load_processed_truths()
        # V2.0修复：加载已有图谱，增量合并而非覆盖
        self._load_existing_graph()

    def _load_existing_graph(self):
        """加载已有知识图谱，实现增量保护（V2.0修复）"""
        json_path = os.path.join(GRAPH_OUTPUT_DIR, "knowledge_graph.json")
        if not os.path.exists(json_path):
            print("  [增量保护] 无已有图谱，从零构建")
            return
        try:
            with open(json_path) as f:
                data = json.load(f)
            entities = data.get("entities", data.get("nodes", []))
            relations = data.get("relations", data.get("edges", []))
            for e in entities:
                name = e.get("name", e.get("id", ""))
                etype = e.get("type", e.get("entity_type", "concept"))
                conf = e.get("confidence", 0.5)
                if name:
                    self.graph.add_entity(name, etype, conf)
            for r in relations:
                src = r.get("source", r.get("from", ""))
                tgt = r.get("target", r.get("to", ""))
                rtype = r.get("type", r.get("relation", "related_to"))
                if src and tgt:
                    rel = Relation(src, tgt, rtype)
                    self.graph.add_relation(rel)
            print(f"  [增量保护] 已加载已有图谱: {len(entities)}实体/{len(relations)}关系")
        except Exception as ex:
            print(f"  [增量保护] 加载已有图谱失败: {ex}，从零构建")

    def _load_processed_truths(self) -> Set[str]:
        if os.path.exists(PROCESSED_TRUTHS_FILE):
            with open(PROCESSED_TRUTHS_FILE) as f:
                return set(json.load(f))
        return set()

    def _save_processed_truths(self):
        os.makedirs(GRAPH_OUTPUT_DIR, exist_ok=True)
        with open(PROCESSED_TRUTHS_FILE, 'w') as f:
            json.dump(list(self.processed_truths), f)

    def extract_from_state_atoms(self) -> List[Dict]:
        """从态元数据库提取真值"""
        truths = []
        if not os.path.exists(STATE_ATOMS_DB):
            return truths

        conn = sqlite3.connect(STATE_ATOMS_DB)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT atom_id, content, meta_class, truth_type, confidence
            FROM atoms WHERE atom_type = 'truth'
        """)
        for row in cursor.fetchall():
            truth_id, content, meta_class, truth_type, confidence = row
            if truth_id not in self.processed_truths:
                truths.append({
                    "id": truth_id,
                    "content": content or "",
                    "meta_class": meta_class,
                    "truth_type": truth_type,
                    "confidence": confidence,
                    "source": "state_atoms_db",
                })
        conn.close()
        return truths

    def extract_from_kernel(self) -> List[Dict]:
        """从内核状态提取真值"""
        truths = []
        if not os.path.exists(KERNEL_PATH):
            return truths

        with open(KERNEL_PATH) as f:
            kernel = json.load(f)

        # 提取内核模块信息
        for key, value in kernel.items():
            if isinstance(value, dict) and "status" in value:
                truth_id = f"kernel_{key}"
                if truth_id not in self.processed_truths:
                    content = f"{key}: {json.dumps(value, ensure_ascii=False)[:200]}"
                    truths.append({
                        "id": truth_id,
                        "content": content,
                        "meta_class": "M6",
                        "truth_type": "config",
                        "confidence": 0.9,
                        "source": "kernel_state",
                    })
        return truths

    def process_truth(self, truth: Dict) -> Tuple[List[Entity], List[Relation]]:
        """处理单条真值，抽取实体和关系"""
        content = truth.get("content", "")
        truth_id = truth.get("id", "")
        base_confidence = truth.get("confidence", 0.5)

        # 抽取实体
        entity_list = self.entity_extractor.extract(content)
        entities = []
        for name, etype in entity_list:
            entity = Entity(name, etype)
            entity.confidence = base_confidence
            entities.append(entity)

        # 抽取关系
        relations = self.relation_extractor.extract(content, truth_id)
        for rel in relations:
            rel.confidence = min(rel.confidence + base_confidence * 0.3, 0.98)

        return entities, relations

    def run(self, incremental: bool = True) -> Dict:
        """执行完整转化流程"""
        start_time = time.time()
        print(f"{'='*60}")
        print(f"真值自动转化知识图谱引擎 V1.0")
        print(f"DID: {DID} | {TRACE}")
        print(f"{'='*60}")

        # 阶段1：提取真值
        print(f"\n--- 阶段1：真值提取 ---")
        all_truths = []
        atom_truths = self.extract_from_state_atoms()
        kernel_truths = self.extract_from_kernel()
        all_truths.extend(atom_truths)
        all_truths.extend(kernel_truths)
        print(f"  态元数据库: {len(atom_truths)}条新真值")
        print(f"  内核状态: {len(kernel_truths)}条新真值")
        print(f"  总计: {len(all_truths)}条待处理真值")

        if not all_truths:
            print("  无新增真值，图谱已是最新")
            return self.graph.get_stats()

        # 阶段2：实体关系抽取
        print(f"\n--- 阶段2：实体关系抽取 ---")
        total_entities = 0
        total_relations = 0
        for i, truth in enumerate(all_truths):
            entities, relations = self.process_truth(truth)
            for entity in entities:
                self.graph.add_entity(entity.name, entity.type, entity.confidence)
            for rel in relations:
                self.graph.add_relation(rel)
            total_entities += len(entities)
            total_relations += len(relations)
            self.processed_truths.add(truth["id"])

            if (i + 1) % 5 == 0:
                print(f"  处理进度: {i+1}/{len(all_truths)} "
                      f"(实体+{len(entities)}, 关系+{len(relations)})")

        print(f"  抽取实体: {total_entities}个次")
        print(f"  抽取关系: {total_relations}条次")

        # 阶段3：图谱统计
        print(f"\n--- 阶段3：图谱统计 ---")
        stats = self.graph.get_stats()
        print(f"  实体总数: {stats['total_entities']}")
        print(f"  关系总数: {stats['total_relations']}")
        print(f"  平均度: {stats['avg_degree']}")
        print(f"  图谱密度: {stats['density']}")
        print(f"  实体类型分布: {stats['entity_type_distribution']}")
        print(f"  关系类型分布: {stats['relation_type_distribution']}")
        print(f"  Top中心实体:")
        for name, degree in stats['top_central_entities'][:5]:
            print(f"    - {name} (度={degree})")

        # 阶段4：保存输出
        print(f"\n--- 阶段4：保存输出 ---")
        os.makedirs(GRAPH_OUTPUT_DIR, exist_ok=True)

        # V2.0修复：保存前自动备份已有图谱，防止数据丢失
        json_path = os.path.join(GRAPH_OUTPUT_DIR, "knowledge_graph.json")
        if os.path.exists(json_path):
            import shutil
            backup_path = os.path.join(GRAPH_OUTPUT_DIR, f"knowledge_graph.backup_{int(time.time())}.json")
            shutil.copy2(json_path, backup_path)
            # 只保留最近5个备份
            backups = sorted([f for f in os.listdir(GRAPH_OUTPUT_DIR) if f.startswith("knowledge_graph.backup_")])
            for old_backup in backups[:-5]:
                os.remove(os.path.join(GRAPH_OUTPUT_DIR, old_backup))
            print(f"  [备份] 已有图谱已备份: {os.path.basename(backup_path)}")

        # JSON格式
        with open(json_path, 'w') as f:
            json.dump(self.graph.to_json(), f, ensure_ascii=False, indent=2)
        print(f"  JSON: {json_path}")

        # GraphML格式
        graphml_path = os.path.join(GRAPH_OUTPUT_DIR, "knowledge_graph.graphml")
        with open(graphml_path, 'w') as f:
            f.write(self.graph.to_graphml())
        print(f"  GraphML: {graphml_path}")

        # 保存已处理真值记录
        self._save_processed_truths()

        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"转化完成 | 耗时: {elapsed:.1f}s")
        print(f"实体: {stats['total_entities']} | 关系: {stats['total_relations']}")
        print(f"{'='*60}")

        return stats


# ==================== 入口 ====================
if __name__ == "__main__":
    import sys
    engine = TruthToKnowledgeGraphEngine()
    incremental = "--full" not in sys.argv
    if not incremental:
        engine.processed_truths = set()
        if os.path.exists(PROCESSED_TRUTHS_FILE):
            os.remove(PROCESSED_TRUTHS_FILE)
    stats = engine.run(incremental=incremental)
