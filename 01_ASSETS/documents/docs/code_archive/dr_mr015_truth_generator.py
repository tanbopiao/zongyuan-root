#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT MR-015 主动真值生成引擎
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | Ω-TAN-7-001

定位：从"被动吸收真值"升级为"主动探索和生成知识"。

核心功能：
  1. 知识缺口识别器 - 分析真值库，识别知识空白领域和未解答问题
  2. 探索任务生成器 - 针对知识缺口，自动生成探索任务
  3. 新知识生成器   - 通过本地LLM+外部API生成新的高质量真值
  4. 质量验证器     - 多轮交叉验证（自评→交叉验证→置信度评估）
  5. 优先级排序器   - 根据知识缺口的重要性和紧迫性排序
  6. 预算控制器     - 控制每天生成数量，防止算力过载

技术设计：
  - 知识缺口识别：基于分类分布+内容质量+实体覆盖度
  - 探索任务队列：优先级队列，高价值缺口优先
  - 质量验证流程：生成→自评→交叉验证→置信度评估→入库
  - 双轮算力：简单知识→本地LLM，复杂知识→外部API
  - 常驻服务：每6小时执行一轮探索
"""

import os
import sys
import json
import time
import sqlite3
import logging
import hashlib
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter

# ============================================================
# 配置
# ============================================================
CONFIG = {
    "db_path": "/opt/ZONGYUAN-ROOT/data/memory_gateway.db",
    "log_file": "/opt/ZONGYUAN-ROOT/ops/mr015_truth_generator/mr015.log",
    "audit_log": "/opt/ZONGYUAN-ROOT/ops/mr015_truth_generator/audit.jsonl",
    "state_file": "/opt/ZONGYUAN-ROOT/ops/mr015_truth_generator/state.json",
    "exploration_log": "/opt/ZONGYUAN-ROOT/kernel/exploration/exploration_log.jsonl",
    "local_llm_url": "http://127.0.0.1:8081/v1/chat/completions",
    "external_llm_url": "http://127.0.0.1:8021/v1/chat/completions",
    "exploration_interval": 21600,  # 探索间隔（6小时）
    "max_truths_per_day": 20,        # 每天最多生成的真值数
    "min_confidence": 0.7,            # 最低置信度阈值
    "node_id": "mr015-truth-generator",
}

# ============================================================
# 知识缺口领域定义
# ============================================================
KNOWLEDGE_DOMAINS = {
    "risk": {
        "name": "风险管理",
        "name_en": "Risk Management",
        "description": "风险识别、风险评估、风险缓解、应急预案",
        "target_count": 50,
        "exploration_topics": [
            "ZONGYUAN-ROOT体系运行风险识别与评估框架",
            "云服务器OOM风险预警与缓解机制",
            "服务故障应急预案与恢复流程",
            "数据丢失风险与备份策略",
            "算力资源耗尽风险与降级方案",
            "外部API依赖风险与替代方案",
            "安全漏洞风险与防护措施",
            "真值污染风险与质量控制",
        ],
    },
    "decision": {
        "name": "决策管理",
        "name_en": "Decision Management",
        "description": "决策记录、决策框架、决策评估、决策复盘",
        "target_count": 50,
        "exploration_topics": [
            "ZONGYUAN-ROOT体系三维稳态决策框架（利益40%/风险35%/成本25%）",
            "算力资源分配决策模型与优先级",
            "组件部署决策的评估标准与流程",
            "进化策略选择的决策树与权衡分析",
            "真值质量阈值决策与置信度校准",
            "资源熔断决策的触发条件与恢复机制",
            "多节点负载均衡决策算法",
            "模型选择决策的性能/成本/质量权衡",
        ],
    },
    "axiom": {
        "name": "公理体系",
        "name_en": "Axiom System",
        "description": "体系基础假设、根本原则、第一性原理",
        "target_count": 50,
        "exploration_topics": [
            "元极恒一公理：体系统一性的根本假设",
            "超认知公理：元认知能力的基础假设",
            "永恒自治公理：长期自我维持的前提条件",
            "耗散结构公理：开放系统维持有序的必要条件",
            "真值优先公理：决策和行动以真值为基础",
            "稳态优先公理：进化不能破坏系统稳态",
            "唯一握手点公理：9120作为唯一权威数据源",
            "可验证公理：所有声明必须可验证可追溯",
        ],
    },
    "protocol": {
        "name": "协议规范",
        "name_en": "Protocol Specification",
        "description": "接口规范、通信协议、数据格式、标准",
        "target_count": 50,
        "exploration_topics": [
            "9120记忆网关API协议规范",
            "MR-012内核总线组件注册协议",
            "真值上报协议（单条upsert/批量sync）",
            "节点心跳协议与超时判定标准",
            "事件发布订阅协议格式",
            "指令分发与执行反馈协议",
            "真值四层结构标准（元数据/内容/关系/真值层）",
            "九大元类分类标准与判定规则",
        ],
    },
    "method": {
        "name": "方法论",
        "name_en": "Methodology",
        "description": "操作方法、流程、算法、SOP",
        "target_count": 100,
        "exploration_topics": [
            "真值质量评估方法论（四维评分法）",
            "认知偏差识别方法论（规则+LLM混合）",
            "知识缺口识别方法论（分类分布+内容质量+实体覆盖）",
            "主动真值生成方法论（缺口识别→探索→生成→验证→入库）",
            "稳态进化方法论（度量→决策→执行→验证→回滚）",
            "双轮算力调度方法论（简单→本地，复杂→外部，失败→降级）",
            "分类迁移方法论（备份→映射→迁移→验证）",
            "自愈机制方法论（监控→检测→诊断→修复→验证）",
        ],
    },
    "case": {
        "name": "案例库",
        "name_en": "Case Library",
        "description": "具体案例、实例、事件记录、经验教训",
        "target_count": 80,
        "exploration_topics": [
            "MR-007内存熔断实战案例与效果评估",
            "MR-008全链路自愈实战案例（grafana 502异常）",
            "llama.cpp编译OOM故障案例与解决方案",
            "Nginx配置错误导致网站无法访问案例",
            "Basic Auth取消的精确操作案例",
            "内存从1.9Gi升级到3.6Gi的决策与效果",
            "Qwen2.5-0.5B模型选型与性能测试案例",
            "129个分类统一为12个的迁移案例",
        ],
    },
}

# ============================================================
# 日志
# ============================================================
def setup_logging():
    os.makedirs(os.path.dirname(CONFIG["log_file"]), exist_ok=True)
    os.makedirs(os.path.dirname(CONFIG["exploration_log"]), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(CONFIG["log_file"]),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("mr015")

logger = setup_logging()

# ============================================================
# 工具函数
# ============================================================
def append_jsonl(filepath: str, data: Any):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "a") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def call_llm(prompt: str, system_prompt: str = "你是一个知识生成专家，擅长生成高质量、结构化、可验证的知识内容。",
              use_external: bool = False, max_tokens: int = 800) -> Optional[str]:
    """调用LLM"""
    url = CONFIG["external_llm_url"] if use_external else CONFIG["local_llm_url"]
    model = "doubao" if use_external else "qwen"
    try:
        resp = requests.post(
            url,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.4,
            },
            timeout=90 if use_external else 45,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"LLM调用失败: {e}")
        return None

# ============================================================
# 组件一：知识缺口识别器
# ============================================================
class KnowledgeGapDetector:
    """知识缺口识别器"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def detect(self) -> Dict:
        """识别知识缺口"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. 分类分布分析
        cursor.execute("SELECT category, COUNT(*) FROM truths GROUP BY category")
        category_counts = {row[0] or "unclassified": row[1] for row in cursor.fetchall()}
        total = sum(category_counts.values())

        # 2. 内容质量分析
        cursor.execute("SELECT length(truth_value) FROM truths WHERE truth_value IS NOT NULL")
        lengths = [row[0] for row in cursor.fetchall() if row[0]]
        avg_length = sum(lengths) / len(lengths) if lengths else 0
        short_count = sum(1 for l in lengths if l < 100)
        long_count = sum(1 for l in lengths if l > 500)

        # 3. 各领域缺口分析
        gaps = []
        for domain_id, domain in KNOWLEDGE_DOMAINS.items():
            current = category_counts.get(domain_id, 0)
            target = domain["target_count"]
            gap = max(0, target - current)
            gap_ratio = gap / target if target > 0 else 0
            gaps.append({
                "domain_id": domain_id,
                "domain_name": domain["name"],
                "current_count": current,
                "target_count": target,
                "gap_count": gap,
                "gap_ratio": round(gap_ratio, 2),
                "priority": "high" if gap_ratio > 0.7 else ("medium" if gap_ratio > 0.4 else "low"),
            })

        # 按缺口比例排序
        gaps.sort(key=lambda x: x["gap_ratio"], reverse=True)

        # 4. 未分类真值
        unclassified = category_counts.get("unclassified", 0)

        conn.close()

        result = {
            "timestamp": datetime.now().isoformat(),
            "total_truths": total,
            "category_distribution": category_counts,
            "content_quality": {
                "avg_length": round(avg_length, 0),
                "short_count": short_count,
                "short_ratio": round(short_count / len(lengths) * 100, 1) if lengths else 0,
                "long_count": long_count,
                "long_ratio": round(long_count / len(lengths) * 100, 1) if lengths else 0,
            },
            "knowledge_gaps": gaps,
            "unclassified_count": unclassified,
            "summary": {
                "high_priority_gaps": [g["domain_name"] for g in gaps if g["priority"] == "high"],
                "medium_priority_gaps": [g["domain_name"] for g in gaps if g["priority"] == "medium"],
                "total_gap": sum(g["gap_count"] for g in gaps),
            },
        }

        logger.info(f"知识缺口识别完成: {len(gaps)}个领域, 高优先级{len(result['summary']['high_priority_gaps'])}个")
        return result


# ============================================================
# 组件二：探索任务生成器
# ============================================================
class ExplorationTaskGenerator:
    """探索任务生成器"""

    def __init__(self):
        self.domains = KNOWLEDGE_DOMAINS

    def generate_tasks(self, gaps: List[Dict], max_tasks: int = 10) -> List[Dict]:
        """生成探索任务"""
        tasks = []
        for gap in gaps:
            if gap["gap_count"] <= 0:
                continue
            domain_id = gap["domain_id"]
            domain = self.domains.get(domain_id)
            if not domain:
                continue

            # 根据缺口数量决定生成多少任务
            num_tasks = min(3, max(1, gap["gap_count"] // 10))
            topics = domain["exploration_topics"]

            for i in range(num_tasks):
                topic = topics[i % len(topics)]
                task = {
                    "task_id": f"EXPLORE-{int(time.time())}-{hashlib.md5(f'{domain_id}{topic}{time.time()}'.encode()).hexdigest()[:8]}",
                    "domain_id": domain_id,
                    "domain_name": domain["name"],
                    "topic": topic,
                    "priority": gap["priority"],
                    "target_category": domain_id,
                    "status": "pending",
                    "created_at": datetime.now().isoformat(),
                }
                tasks.append(task)

        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        tasks.sort(key=lambda x: priority_order.get(x["priority"], 3))

        return tasks[:max_tasks]


# ============================================================
# 组件三：新知识生成器
# ============================================================
class TruthGenerator:
    """新知识生成器"""

    def generate(self, task: Dict) -> Optional[Dict]:
        """生成新知识"""
        domain_name = task["domain_name"]
        topic = task["topic"]

        prompt = f"""请围绕以下主题生成一段高质量的知识内容，作为ZONGYUAN-ROOT元极恒一自治体系的真值条目。

领域：{domain_name}
主题：{topic}

要求：
1. 内容必须具体、可验证、有实际价值
2. 结构清晰，包含核心观点、关键要素、实施要点
3. 长度在300-800字之间
4. 避免空泛的套话，要有具体的方法、数据或案例
5. 与ZONGYUAN-ROOT体系的实际运行相关

请直接输出知识内容，不要输出标题或额外说明。
"""

        # 复杂/重要主题用外部API，简单主题用本地LLM
        use_external = task["priority"] == "high"
        content = call_llm(prompt, use_external=use_external, max_tokens=800)

        if not content or len(content) < 50:
            logger.warning(f"生成内容过短或失败: {topic}")
            return None

        # 生成真值key
        key = f"GENERATED.{task['domain_id'].upper()}.{hashlib.md5(topic.encode()).hexdigest()[:8]}.{int(time.time())}"

        truth = {
            "truth_key": key,
            "truth_value": content,
            "category": task["target_category"],
            "node_id": CONFIG["node_id"],
            "metadata": {
                "source": "mr015_active_generation",
                "task_id": task["task_id"],
                "domain": domain_name,
                "topic": topic,
                "priority": task["priority"],
                "generated_by": "external_api" if use_external else "local_llm",
                "generated_at": datetime.now().isoformat(),
            },
        }

        logger.info(f"新知识生成成功: {key} ({len(content)}字符)")
        return truth


# ============================================================
# 组件四：质量验证器
# ============================================================
class QualityValidator:
    """质量验证器（多轮交叉验证）"""

    def validate(self, truth: Dict) -> Dict:
        """验证真值质量"""
        content = truth["truth_value"]
        results = {}

        # 1. 基础质量检查
        basic_score = self._basic_check(content)
        results["basic_check"] = basic_score

        # 2. 自评估（LLM自评）
        self_eval = self._self_evaluation(content, truth["metadata"]["topic"])
        results["self_evaluation"] = self_eval

        # 3. 交叉验证（用另一个prompt重新评估）
        cross_eval = self._cross_evaluation(content, truth["metadata"]["domain"])
        results["cross_evaluation"] = cross_eval

        # 综合置信度（三个维度都是0-1分，取平均）
        confidence = (basic_score["score"] / 100 + self_eval["score"] + cross_eval["score"]) / 3
        confidence = round(min(1.0, max(0.0, confidence)), 2)

        result = {
            "passed": confidence >= CONFIG["min_confidence"],
            "confidence": confidence,
            "checks": results,
            "validated_at": datetime.now().isoformat(),
        }

        logger.info(f"质量验证: 置信度{confidence}, {'通过' if result['passed'] else '未通过'}")
        return result

    def _basic_check(self, content: str) -> Dict:
        """基础质量检查"""
        score = 0
        issues = []

        # 长度检查
        length = len(content)
        if length >= 300:
            score += 25
        elif length >= 150:
            score += 15
        else:
            score += 5
            issues.append("内容过短")

        # 结构检查（有分段或编号）
        if "\n" in content or "1." in content or "第一" in content:
            score += 25
        else:
            score += 10
            issues.append("结构不清晰")

        # 具体性检查（有数字或具体术语）
        import re
        numbers = re.findall(r'\d+\.?\d*', content)
        if len(numbers) >= 2:
            score += 25
        elif len(numbers) >= 1:
            score += 15
        else:
            score += 5
            issues.append("缺乏具体数据")

        # 相关性检查（包含体系相关术语）
        zongyuan_terms = ["ZONGYUAN", "元极", "自治", "真值", "内核", "稳态", "进化", "算力", "MR-"]
        if any(term in content for term in zongyuan_terms):
            score += 25
        else:
            score += 10
            issues.append("与体系相关性不足")

        return {"score": score, "issues": issues, "length": length}

    def _self_evaluation(self, content: str, topic: str) -> Dict:
        """自评估"""
        prompt = f"""请对以下知识内容进行质量评估，从0-1分给出置信度。

主题：{topic}

内容：
{content[:1500]}

评估维度：
1. 准确性：内容是否准确可靠
2. 完整性：是否覆盖了主题的关键方面
3. 实用性：是否有实际应用价值
4. 结构性：结构是否清晰合理

只输出JSON格式：{{"score": 0.0-1.0, "reason": "简要评估理由"}}
"""
        result = call_llm(prompt, use_external=False, max_tokens=200)
        if not result:
            return {"score": 0.5, "reason": "评估失败，默认中等"}
        try:
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(result[json_start:json_end])
                return {"score": float(parsed.get("score", 0.5)), "reason": parsed.get("reason", "")}
        except Exception:
            pass
        return {"score": 0.5, "reason": "解析失败，默认中等"}

    def _cross_evaluation(self, content: str, domain: str) -> Dict:
        """交叉验证"""
        prompt = f"""作为{domain}领域的专家，请批判性地评估以下知识内容的质量。

内容：
{content[:1500]}

请指出：
1. 内容中可能存在的错误或不准确之处
2. 遗漏的重要方面
3. 整体质量评分（0-1分）

只输出JSON格式：{{"score": 0.0-1.0, "issues": ["问题1", "问题2"], "suggestions": ["建议1"]}}
"""
        result = call_llm(prompt, use_external=True, max_tokens=300)
        if not result:
            return {"score": 0.5, "issues": [], "suggestions": []}
        try:
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(result[json_start:json_end])
                return {
                    "score": float(parsed.get("score", 0.5)),
                    "issues": parsed.get("issues", []),
                    "suggestions": parsed.get("suggestions", []),
                }
        except Exception:
            pass
        return {"score": 0.5, "issues": [], "suggestions": []}


# ============================================================
# 组件五：真值入库器
# ============================================================
class TruthWriter:
    """真值入库器"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def write(self, truth: Dict, validation: Dict) -> bool:
        """将验证通过的真值写入数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 在真值内容中附加元数据
            content_with_meta = truth["truth_value"] + "\n\n---\n" + json.dumps({
                "generated_by": "MR-015主动真值生成引擎",
                "task_id": truth["metadata"]["task_id"],
                "domain": truth["metadata"]["domain"],
                "topic": truth["metadata"]["topic"],
                "confidence": validation["confidence"],
                "generated_at": truth["metadata"]["generated_at"],
            }, ensure_ascii=False, indent=2)

            value_str = content_with_meta
            truth_hash = hashlib.sha256(value_str.encode()).hexdigest()
            now = time.time()

            cursor.execute("""
                INSERT INTO truths (truth_key, truth_value, truth_hash, category, node_id, created_at, updated_at, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                truth["truth_key"],
                value_str,
                truth_hash,
                truth["category"],
                truth["node_id"],
                now,
                now,
            ))
            conn.commit()
            conn.close()

            logger.info(f"真值入库成功: {truth['truth_key']} (置信度{validation['confidence']})")
            return True
        except Exception as e:
            logger.error(f"真值入库失败: {e}")
            return False


# ============================================================
# 主动真值生成引擎主类
# ============================================================
class ActiveTruthGenerator:
    """主动真值生成引擎主类"""

    def __init__(self):
        self.gap_detector = KnowledgeGapDetector(CONFIG["db_path"])
        self.task_generator = ExplorationTaskGenerator()
        self.truth_generator = TruthGenerator()
        self.validator = QualityValidator()
        self.writer = TruthWriter(CONFIG["db_path"])
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        if os.path.exists(CONFIG["state_file"]):
            try:
                with open(CONFIG["state_file"], "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "total_explorations": 0,
            "truths_generated": 0,
            "truths_passed": 0,
            "truths_rejected": 0,
            "avg_confidence": 0,
            "today_generated": 0,
            "last_exploration_date": None,
            "last_exploration": None,
            "started_at": datetime.now().isoformat(),
        }

    def _save_state(self):
        os.makedirs(os.path.dirname(CONFIG["state_file"]), exist_ok=True)
        with open(CONFIG["state_file"], "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _check_daily_budget(self) -> bool:
        """检查每日预算"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.state.get("last_exploration_date") != today:
            self.state["today_generated"] = 0
            self.state["last_exploration_date"] = today
        return self.state["today_generated"] < CONFIG["max_truths_per_day"]

    def run_exploration_cycle(self) -> Dict:
        """执行一轮探索循环"""
        logger.info("=" * 60)
        logger.info("MR-015 主动真值生成循环")
        logger.info("=" * 60)

        # 1. 检查预算
        if not self._check_daily_budget():
            logger.info(f"今日已达生成上限({CONFIG['max_truths_per_day']}条)，跳过本轮")
            return {"skipped": True, "reason": "daily_budget_exceeded"}

        # 2. 识别知识缺口
        logger.info("步骤1: 识别知识缺口...")
        gaps_result = self.gap_detector.detect()
        gaps = gaps_result["knowledge_gaps"]
        logger.info(f"发现{len(gaps)}个知识领域, 高优先级{len(gaps_result['summary']['high_priority_gaps'])}个")

        # 3. 生成探索任务
        logger.info("步骤2: 生成探索任务...")
        tasks = self.task_generator.generate_tasks(gaps, max_tasks=5)
        logger.info(f"生成{len(tasks)}个探索任务")

        # 4. 执行任务（生成+验证+入库）
        generated = 0
        passed = 0
        rejected = 0
        confidences = []

        for task in tasks:
            if not self._check_daily_budget():
                logger.info("达到每日预算，停止生成")
                break

            logger.info(f"执行任务: [{task['priority']}] {task['topic']}")

            # 生成新知识
            truth = self.truth_generator.generate(task)
            if not truth:
                logger.warning("生成失败，跳过")
                continue

            generated += 1
            self.state["today_generated"] += 1

            # 质量验证
            validation = self.validator.validate(truth)
            confidences.append(validation["confidence"])

            if validation["passed"]:
                # 入库
                if self.writer.write(truth, validation):
                    passed += 1
                    # 记录探索日志
                    append_jsonl(CONFIG["exploration_log"], {
                        "task": task,
                        "truth_key": truth["truth_key"],
                        "confidence": validation["confidence"],
                        "status": "passed",
                        "timestamp": datetime.now().isoformat(),
                    })
            else:
                rejected += 1
                logger.info(f"置信度{validation['confidence']}低于阈值{CONFIG['min_confidence']}，未入库")
                append_jsonl(CONFIG["exploration_log"], {
                    "task": task,
                    "confidence": validation["confidence"],
                    "status": "rejected",
                    "timestamp": datetime.now().isoformat(),
                })

        # 5. 更新状态
        self.state["total_explorations"] += 1
        self.state["truths_generated"] += generated
        self.state["truths_passed"] += passed
        self.state["truths_rejected"] += rejected
        if confidences:
            old_avg = self.state["avg_confidence"]
            total = self.state["truths_passed"]
            if total > 0:
                self.state["avg_confidence"] = round((old_avg * (total - len(confidences)) + sum(confidences)) / total, 2)
        self.state["last_exploration"] = datetime.now().isoformat()
        self._save_state()

        result = {
            "exploration_cycle": self.state["total_explorations"],
            "tasks_generated": len(tasks),
            "truths_generated": generated,
            "truths_passed": passed,
            "truths_rejected": rejected,
            "avg_confidence": round(sum(confidences) / len(confidences), 2) if confidences else 0,
            "today_generated": self.state["today_generated"],
            "daily_budget": CONFIG["max_truths_per_day"],
        }

        logger.info(f"探索循环完成: 生成{generated}条, 通过{passed}条, 拒绝{rejected}条")
        logger.info("=" * 60)
        return result

    def get_status(self) -> Dict:
        """获取引擎状态"""
        return {
            "state": self.state,
            "config": {
                "exploration_interval": CONFIG["exploration_interval"],
                "max_truths_per_day": CONFIG["max_truths_per_day"],
                "min_confidence": CONFIG["min_confidence"],
            },
        }

    def run_forever(self):
        """常驻运行"""
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════╗")
        logger.info("║  MR-015 主动真值生成引擎启动                         ║")
        logger.info("║  知识缺口: 分类分布+内容质量+实体覆盖度分析          ║")
        logger.info("║  生成流程: 缺口识别→任务生成→知识生成→质量验证→入库 ║")
        logger.info("║  质量验证: 基础检查+自评估+交叉验证 三轮验证         ║")
        logger.info("║  算力: 高优先级→外部API, 低优先级→本地LLM           ║")
        logger.info("║  预算: 每天最多{}条真值                              ║".format(CONFIG["max_truths_per_day"]))
        logger.info("║  探索间隔: 每{}小时                                  ║".format(CONFIG["exploration_interval"] // 3600))
        logger.info("╚══════════════════════════════════════════════════════╝")
        logger.info("")

        # 启动时立即执行一轮
        self.run_exploration_cycle()

        while True:
            time.sleep(CONFIG["exploration_interval"])
            try:
                self.run_exploration_cycle()
            except Exception as e:
                logger.error(f"探索循环异常: {e}")
                time.sleep(60)


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MR-015 主动真值生成引擎")
    parser.add_argument("command", choices=["explore", "detect-gaps", "status", "daemon"],
                        help="explore=执行一轮探索, detect-gaps=只识别缺口, status=查看状态, daemon=常驻运行")
    args = parser.parse_args()

    engine = ActiveTruthGenerator()

    if args.command == "detect-gaps":
        gaps = engine.gap_detector.detect()
        print(json.dumps(gaps, ensure_ascii=False, indent=2))
    elif args.command == "explore":
        result = engine.run_exploration_cycle()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "status":
        status = engine.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
    elif args.command == "daemon":
        engine.run_forever()
