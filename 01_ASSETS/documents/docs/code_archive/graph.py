"""
知识图谱底座模块：实体抽取、关系构建、图谱补全、自动更新
"""
import os
import json
import random
from datetime import datetime
from config.settings import KNOWLEDGE_DOMAINS, EDUCATION_STAGES, DATA_DIR
from src.common.utils import setup_logger, compute_hash, generate_asset_id

logger = setup_logger("knowledge_graph", "knowledge_graph.log")


class KnowledgeGraph:
    """AI全领域知识图谱"""

    def __init__(self):
        self.entities = {}  # entity_id -> entity
        self.relations = []  # list of (head_id, relation, tail_id, weight)
        self.domain_index = {d: [] for d in KNOWLEDGE_DOMAINS}
        self.stage_index = {s: [] for s in EDUCATION_STAGES}
        self.graph_hash = None
        self._init_base_knowledge()

    def _init_base_knowledge(self):
        """初始化十大知识域基础知识点"""
        logger.info("初始化AI全领域知识图谱...")
        base_knowledge = {
            "AI基础理论": [
                ("人工智能定义", "了解", ["小学", "初中", "高中", "中职"]),
                ("AI发展历程", "了解", ["初中", "高中", "中职"]),
                ("AI分类（弱/强/超）", "理解", ["初中", "高中", "中职"]),
                ("AI应用场景", "掌握", ["小学", "初中", "高中", "中职"]),
                ("AI与人类智能区别", "理解", ["初中", "高中", "中职"]),
                ("图灵测试", "了解", ["高中", "中职"]),
                ("AI三大流派", "了解", ["高中"]),
                ("AI优势与局限", "掌握", ["初中", "高中", "中职"]),
            ],
            "机器学习基础": [
                ("机器学习概念", "了解", ["高中", "中职"]),
                ("监督学习", "理解", ["高中"]),
                ("无监督学习", "理解", ["高中"]),
                ("强化学习", "了解", ["高中"]),
                ("训练与推理", "理解", ["高中", "中职"]),
                ("模型与参数", "了解", ["高中"]),
                ("过拟合与欠拟合", "理解", ["高中"]),
                ("特征工程基础", "了解", ["高中"]),
            ],
            "大模型架构": [
                ("大模型概念", "了解", ["高中", "中职"]),
                ("Transformer架构", "理解", ["高中"]),
                ("预训练机制", "理解", ["高中"]),
                ("微调技术", "了解", ["高中"]),
                ("上下文窗口", "掌握", ["高中", "中职"]),
                ("幻觉机制", "理解", ["高中", "中职"]),
                ("提示词工程", "掌握", ["高中", "中职"]),
                ("大模型能力边界", "掌握", ["高中", "中职"]),
            ],
            "智能体理论": [
                ("智能体概念", "了解", ["高中", "中职"]),
                ("单体智能体", "理解", ["高中"]),
                ("多智能体系统", "了解", ["高中"]),
                ("智能体规划能力", "理解", ["高中"]),
                ("工具调用机制", "掌握", ["高中", "中职"]),
                ("智能体记忆系统", "理解", ["高中"]),
                ("角色设定与指令", "掌握", ["高中", "中职"]),
                ("智能体安全边界", "掌握", ["高中", "中职"]),
            ],
            "编程实践": [
                ("编程基本概念", "了解", ["初中", "高中", "中职"]),
                ("图形化编程", "掌握", ["初中", "中职"]),
                ("Python基础语法", "掌握", ["高中", "中职"]),
                ("条件与循环", "掌握", ["初中", "高中", "中职"]),
                ("函数与模块", "理解", ["高中", "中职"]),
                ("AI库调用基础", "掌握", ["高中", "中职"]),
                ("低代码开发", "掌握", ["中职"]),
                ("调试与排错", "掌握", ["高中", "中职"]),
            ],
            "数据科学": [
                ("大数据特征", "了解", ["初中", "高中", "中职"]),
                ("数据采集方法", "理解", ["高中", "中职"]),
                ("数据清洗", "掌握", ["高中", "中职"]),
                ("数据统计分析", "掌握", ["初中", "高中", "中职"]),
                ("数据可视化", "掌握", ["初中", "高中", "中职"]),
                ("规律挖掘基础", "理解", ["高中"]),
                ("趋势预测入门", "了解", ["高中"]),
                ("数据伦理", "掌握", ["初中", "高中", "中职"]),
            ],
            "AI伦理安全": [
                ("AI四大准则", "掌握", ["小学", "初中", "高中", "中职"]),
                ("算法偏见", "理解", ["初中", "高中", "中职"]),
                ("信息茧房", "理解", ["初中", "高中", "中职"]),
                ("隐私保护", "掌握", ["小学", "初中", "高中", "中职"]),
                ("AI幻觉识别", "掌握", ["初中", "高中", "中职"]),
                ("深度伪造辨别", "理解", ["初中", "高中", "中职"]),
                ("AI创作版权", "掌握", ["高中", "中职"]),
                ("学术诚信规范", "掌握", ["初中", "高中", "中职"]),
            ],
            "多模态应用": [
                ("多模态AI概念", "了解", ["初中", "高中", "中职"]),
                ("AI绘画基础", "掌握", ["初中", "高中", "中职"]),
                ("提示词创作", "掌握", ["初中", "高中", "中职"]),
                ("AI音视频生成", "了解", ["高中", "中职"]),
                ("AI数字人", "了解", ["高中", "中职"]),
                ("AI动画制作", "掌握", ["初中", "高中", "中职"]),
                ("文创设计应用", "掌握", ["初中", "高中", "中职"]),
                ("多模态版权规范", "掌握", ["高中", "中职"]),
            ],
            "硬件机器人": [
                ("智能硬件基础", "了解", ["初中", "高中", "中职"]),
                ("传感器原理", "理解", ["初中", "高中", "中职"]),
                ("AI视觉硬件", "掌握", ["高中", "中职"]),
                ("AI语音硬件", "掌握", ["高中", "中职"]),
                ("嵌入式基础", "了解", ["高中", "中职"]),
                ("避障机器人", "掌握", ["初中", "高中", "中职"]),
                ("循迹机器人", "掌握", ["初中", "高中", "中职"]),
                ("智能教室方案", "掌握", ["高中", "中职"]),
            ],
            "跨学科融合": [
                ("AI+语文", "掌握", ["初中", "高中"]),
                ("AI+数学", "掌握", ["初中", "高中"]),
                ("AI+物理", "理解", ["高中"]),
                ("AI+化学", "理解", ["高中"]),
                ("AI+生物", "理解", ["高中"]),
                ("AI+历史", "掌握", ["初中", "高中"]),
                ("AI+地理", "掌握", ["初中", "高中"]),
                ("科创项目方法", "掌握", ["初中", "高中", "中职"]),
            ],
        }

        for domain, points in base_knowledge.items():
            for name, mastery, stages in points:
                eid = self.add_entity(name, domain, mastery, stages)
                # 建立域内前置关系（简化：按顺序前一个是后一个的前置）
                idx = self.domain_index[domain].index(eid)
                if idx > 0:
                    prev_eid = self.domain_index[domain][idx - 1]
                    self.add_relation(prev_eid, "前置知识", eid, 0.8)

        self._rebuild_index()
        self.graph_hash = compute_hash({"entities": len(self.entities), "relations": len(self.relations)})
        logger.info(f"知识图谱初始化完成：{len(self.entities)}个实体，{len(self.relations)}条关系，哈希={self.graph_hash[:16]}...")

    def add_entity(self, name, domain, mastery_level="了解", stages=None):
        """添加知识实体"""
        eid = generate_asset_id("KP")
        entity = {
            "id": eid,
            "name": name,
            "domain": domain,
            "mastery_level": mastery_level,
            "stages": stages or ["高中"],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": 1,
            "confidence": 0.95
        }
        self.entities[eid] = entity
        self.domain_index[domain].append(eid)
        for s in entity["stages"]:
            if s in self.stage_index:
                self.stage_index[s].append(eid)
        return eid

    def add_relation(self, head_id, relation, tail_id, weight=0.5):
        """添加实体关系"""
        if head_id in self.entities and tail_id in self.entities:
            rel = {
                "head": head_id,
                "relation": relation,
                "tail": tail_id,
                "weight": weight,
                "created_at": datetime.now().isoformat()
            }
            self.relations.append(rel)
            return True
        return False

    def _rebuild_index(self):
        """重建索引"""
        self.domain_index = {d: [] for d in KNOWLEDGE_DOMAINS}
        self.stage_index = {s: [] for s in EDUCATION_STAGES}
        for eid, ent in self.entities.items():
            if ent["domain"] in self.domain_index:
                self.domain_index[ent["domain"]].append(eid)
            for s in ent["stages"]:
                if s in self.stage_index:
                    self.stage_index[s].append(eid)

    def get_knowledge_by_stage(self, stage):
        """按学段获取知识点列表"""
        eids = self.stage_index.get(stage, [])
        return [self.entities[eid] for eid in eids if eid in self.entities]

    def get_knowledge_by_domain(self, domain):
        """按知识域获取知识点"""
        eids = self.domain_index.get(domain, [])
        return [self.entities[eid] for eid in eids if eid in self.entities]

    def get_prerequisites(self, entity_id):
        """获取某知识点的前置知识"""
        prereqs = []
        for rel in self.relations:
            if rel["tail"] == entity_id and rel["relation"] == "前置知识":
                if rel["head"] in self.entities:
                    prereqs.append(self.entities[rel["head"]])
        return prereqs

    def get_graph_stats(self):
        """获取图谱统计信息"""
        domain_counts = {d: len(eids) for d, eids in self.domain_index.items()}
        stage_counts = {s: len(eids) for s, eids in self.stage_index.items()}
        relation_types = {}
        for rel in self.relations:
            relation_types[rel["relation"]] = relation_types.get(rel["relation"], 0) + 1
        return {
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
            "domain_distribution": domain_counts,
            "stage_distribution": stage_counts,
            "relation_types": relation_types,
            "graph_hash": self.graph_hash
        }

    def auto_update(self, new_knowledge=None):
        """自动更新知识图谱（模拟每日巡检更新）"""
        updated = 0
        # 模拟：随机提升部分实体版本号
        for eid in list(self.entities.keys()):
            if random.random() < 0.05:  # 5%概率更新
                self.entities[eid]["version"] += 1
                self.entities[eid]["updated_at"] = datetime.now().isoformat()
                self.entities[eid]["confidence"] = min(1.0, self.entities[eid]["confidence"] + 0.01)
                updated += 1
        # 添加新知识（模拟）
        if new_knowledge:
            for item in new_knowledge:
                self.add_entity(item["name"], item["domain"], item.get("mastery", "了解"), item.get("stages", ["高中"]))
                updated += 1
        self.graph_hash = compute_hash({"entities": len(self.entities), "relations": len(self.relations), "ts": datetime.now().isoformat()})
        logger.info(f"知识图谱自动更新完成：更新{updated}个实体，当前总计{len(self.entities)}实体")
        return updated

    def link_prediction(self):
        """知识图谱补全：链接预测（简化版）"""
        new_relations = 0
        entity_ids = list(self.entities.keys())
        # 同域实体建立相似关系
        for domain, eids in self.domain_index.items():
            for i in range(len(eids)):
                for j in range(i + 1, min(i + 3, len(eids))):
                    # 检查是否已存在关系
                    exists = any(
                        (r["head"] == eids[i] and r["tail"] == eids[j]) or
                        (r["head"] == eids[j] and r["tail"] == eids[i])
                        for r in self.relations
                    )
                    if not exists and random.random() < 0.3:
                        self.add_relation(eids[i], "相关知识", eids[j], 0.4)
                        new_relations += 1
        logger.info(f"知识图谱补全完成：新增{new_relations}条关系")
        return new_relations

    def get_entity_by_id(self, entity_id):
        """按ID查询实体详情"""
        return self.entities.get(entity_id)

    def get_entity_by_name(self, name):
        """按名称查询实体"""
        for eid, entity in self.entities.items():
            if entity["name"] == name:
                return entity
        return None

    def update_entity(self, entity_id, **kwargs):
        """更新实体属性"""
        if entity_id not in self.entities:
            return False
        entity = self.entities[entity_id]
        for key, value in kwargs.items():
            if key in entity and key not in ("id", "created_at"):
                entity[key] = value
        entity["updated_at"] = datetime.now().isoformat()
        entity["version"] = entity.get("version", 1) + 1
        self._rebuild_index()
        logger.info(f"实体已更新：{entity_id} v{entity['version']}")
        return True

    def delete_entity(self, entity_id):
        """删除实体及相关关系"""
        if entity_id not in self.entities:
            return False
        del self.entities[entity_id]
        # 删除相关关系
        self.relations = [r for r in self.relations
                          if r["head"] != entity_id and r["tail"] != entity_id]
        self._rebuild_index()
        logger.info(f"实体已删除：{entity_id}（含相关关系）")
        return True

    def delete_relation(self, relation_id):
        """按ID删除关系"""
        original_len = len(self.relations)
        self.relations = [r for r in self.relations if r.get("id") != relation_id]
        deleted = original_len - len(self.relations)
        if deleted:
            logger.info(f"关系已删除：{relation_id}")
        return deleted > 0

    def get_relations_for_entity(self, entity_id, direction="all"):
        """查询实体的关系（all/outgoing/incoming）"""
        if direction == "outgoing":
            return [r for r in self.relations if r["head"] == entity_id]
        elif direction == "incoming":
            return [r for r in self.relations if r["tail"] == entity_id]
        return [r for r in self.relations if r["head"] == entity_id or r["tail"] == entity_id]

    def search_entities(self, keyword, domain=None, stage=None, limit=20):
        """实体搜索（关键词+领域+学段过滤）"""
        results = []
        keyword_lower = keyword.lower()
        for eid, entity in self.entities.items():
            if keyword_lower in entity["name"].lower() or keyword_lower in entity.get("description", "").lower():
                if domain and entity["domain"] != domain:
                    continue
                if stage and stage not in entity.get("stages", []):
                    continue
                results.append(entity)
                if len(results) >= limit:
                    break
        return results

    def get_domains(self):
        """获取所有知识域及实体数"""
        domain_stats = {}
        for entity in self.entities.values():
            d = entity["domain"]
            domain_stats[d] = domain_stats.get(d, 0) + 1
        return [{"domain": d, "entity_count": c} for d, c in sorted(domain_stats.items())]

    def export_graph(self, format="json"):
        """导出图谱（json格式，含节点和边，可用于可视化）"""
        nodes = [{"id": eid, "label": e["name"], "domain": e["domain"],
                  "mastery_level": e["mastery_level"]}
                 for eid, e in self.entities.items()]
        edges = [{"source": r["head"], "target": r["tail"],
                  "relation": r["relation"], "weight": r["weight"]}
                 for r in self.relations]
        return {
            "format": "graph-json",
            "nodes": nodes,
            "edges": edges,
            "stats": self.get_graph_stats(),
            "exported_at": datetime.now().isoformat()
        }

    def get_entity_count_by_stage(self):
        """按学段统计实体数"""
        stage_stats = {}
        for entity in self.entities.values():
            for stage in entity.get("stages", []):
                stage_stats[stage] = stage_stats.get(stage, 0) + 1
        return stage_stats

    def save(self, filepath=None):
        """保存知识图谱到文件"""
        filepath = filepath or os.path.join(DATA_DIR, "knowledge_graph.json")
        data = {
            "entities": self.entities,
            "relations": self.relations,
            "graph_hash": self.graph_hash,
            "saved_at": datetime.now().isoformat()
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"知识图谱已保存至 {filepath}")
        return filepath

    def load(self, filepath=None):
        """从文件加载知识图谱"""
        filepath = filepath or os.path.join(DATA_DIR, "knowledge_graph.json")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.entities = data["entities"]
            self.relations = data["relations"]
            self.graph_hash = data.get("graph_hash")
            self._rebuild_index()
            logger.info(f"知识图谱已从 {filepath} 加载：{len(self.entities)}实体")
            return True
        return False
