#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT MR-016 思维模式演化引擎
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | Ω-TAN-7-001

定位：识别和优化体系自身的认知策略，实现"学习如何学习"的元学习能力。

核心功能：
  1. 认知策略库 - 维护8种认知策略（演绎/归纳/类比/第一性原理/辩证/系统/概率/逆向）
  2. 策略效果追踪 - 记录每种策略在不同任务上的成功率和质量
  3. 策略自适应选择 - 多臂老虎机算法，根据任务类型自动选择最优策略
  4. 策略演化器 - 基于效果数据，自动调整策略参数或生成新策略
  5. 元学习循环 - 策略选择→执行→评估→调整→再选择的闭环

技术设计：
  - 策略效果矩阵：策略×任务类型的成功率矩阵
  - 多臂老虎机：ε-贪心算法（探索vs利用平衡）
  - 策略表示：每种策略表示为system prompt指令+推理规则
  - 演化机制：基于效果反馈的参数调整+策略变异
  - 常驻服务：每4小时执行一轮元学习
"""

import os
import sys
import json
import time
import sqlite3
import logging
import hashlib
import random
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

# ============================================================
# 配置
# ============================================================
CONFIG = {
    "db_path": "/opt/ZONGYUAN-ROOT/data/memory_gateway.db",
    "log_file": "/opt/ZONGYUAN-ROOT/ops/mr016_thinking_evolution/mr016.log",
    "audit_log": "/opt/ZONGYUAN-ROOT/ops/mr016_thinking_evolution/audit.jsonl",
    "state_file": "/opt/ZONGYUAN-ROOT/ops/mr016_thinking_evolution/state.json",
    "strategy_matrix_file": "/opt/ZONGYUAN-ROOT/kernel/cognition/strategy_matrix.json",
    "local_llm_url": "http://127.0.0.1:8081/v1/chat/completions",
    "external_llm_url": "http://127.0.0.1:8021/v1/chat/completions",
    "meta_learning_interval": 14400,  # 元学习间隔（4小时）
    "epsilon": 0.2,                    # 多臂老虎机探索概率
    "node_id": "mr016-thinking-evolution",
}

# ============================================================
# 8种认知策略定义
# ============================================================
COGNITIVE_STRATEGIES = {
    "deductive": {
        "name": "演绎推理",
        "name_en": "Deductive Reasoning",
        "description": "从一般到特殊，基于前提推导出必然结论",
        "system_prompt": "你使用演绎推理方法：从已确立的一般原则和前提出发，通过逻辑推导得出具体结论。确保每个推理步骤都有明确的前提支持，结论必须是前提的必然结果。",
        "rules": [
            "明确大前提（一般原则）",
            "明确小前提（具体情况）",
            "通过三段论推导结论",
            "验证前提的真实性",
            "检查推理的有效性"
        ],
        "best_for": ["数学证明", "逻辑推导", "规则应用", "定理验证"],
    },
    "inductive": {
        "name": "归纳推理",
        "name_en": "Inductive Reasoning",
        "description": "从特殊到一般，从具体案例中总结出普遍规律",
        "system_prompt": "你使用归纳推理方法：从多个具体案例和观察出发，总结出普遍规律和一般原则。注意样本的代表性和多样性，结论应标注置信度和适用范围。",
        "rules": [
            "收集多个具体案例",
            "识别案例中的共同模式",
            "总结普遍规律",
            "标注置信度和适用范围",
            "寻找反例和例外"
        ],
        "best_for": ["经验总结", "规律发现", "模式识别", "趋势预测"],
    },
    "analogical": {
        "name": "类比推理",
        "name_en": "Analogical Reasoning",
        "description": "基于相似性，通过已知领域的知识理解未知领域",
        "system_prompt": "你使用类比推理方法：通过寻找两个领域之间的结构相似性，将已知领域的知识和方法迁移到未知领域。明确类比的对应关系，注意类比的局限性。",
        "rules": [
            "识别源领域和目标领域",
            "建立结构对应关系",
            "迁移源领域的知识",
            "验证迁移的合理性",
            "注意类比的边界和局限"
        ],
        "best_for": ["跨领域迁移", "创新启发", "问题类比", "概念理解"],
    },
    "first_principles": {
        "name": "第一性原理",
        "name_en": "First Principles Thinking",
        "description": "从最基本的假设和事实出发，重新推导，不依赖类比和惯例",
        "system_prompt": "你使用第一性原理思维：将问题分解到最基本的不可再分的事实和假设，从这些第一性原理出发重新构建解决方案。不接受类比和惯例作为答案，追问'为什么'直到触及根本。",
        "rules": [
            "识别问题的核心假设",
            "将假设分解到最基本事实",
            "验证基本事实的真实性",
            "从基本事实重新推导",
            "构建全新的解决方案"
        ],
        "best_for": ["创新突破", "根本问题分析", "颠覆性思考", "复杂系统设计"],
    },
    "dialectical": {
        "name": "辩证思维",
        "name_en": "Dialectical Thinking",
        "description": "正反合，通过矛盾的对立统一达到更深刻的理解",
        "system_prompt": "你使用辩证思维：同时考虑正面和反面观点，通过矛盾的对立和斗争达到更高层次的统一（合题）。不回避矛盾，而是利用矛盾推动认识深化。",
        "rules": [
            "提出正面观点（正题）",
            "提出反面观点（反题）",
            "分析正反双方的合理性和局限性",
            "寻找矛盾的统一（合题）",
            "在更高层次上综合"
        ],
        "best_for": ["复杂决策", "矛盾分析", "价值权衡", "深度理解"],
    },
    "systems": {
        "name": "系统思维",
        "name_en": "Systems Thinking",
        "description": "整体观，关注要素间的因果链、反馈回路和涌现性质",
        "system_prompt": "你使用系统思维：将问题视为一个整体系统，关注要素之间的相互关系、因果链、反馈回路和涌现性质。不孤立地看问题，而是从系统结构和动态行为中寻找根本解。",
        "rules": [
            "识别系统的边界和要素",
            "绘制要素间的因果关系图",
            "识别正反馈和负反馈回路",
            "分析系统的动态行为",
            "寻找高杠杆作用点"
        ],
        "best_for": ["复杂系统分析", "根因分析", "长期规划", "生态系统理解"],
    },
    "probabilistic": {
        "name": "概率思维",
        "name_en": "Probabilistic Thinking",
        "description": "贝叶斯更新，用概率和置信度量化不确定性，持续更新信念",
        "system_prompt": "你使用概率思维：用概率和置信度量化不确定性，基于新证据通过贝叶斯更新持续调整信念。不追求绝对确定，而是给出概率分布和置信区间，明确决策的风险和期望收益。",
        "rules": [
            "建立先验概率分布",
            "收集新证据",
            "计算似然度",
            "通过贝叶斯公式更新后验概率",
            "给出置信区间和风险评估"
        ],
        "best_for": ["不确定性决策", "风险评估", "预测建模", "证据权衡"],
    },
    "inversion": {
        "name": "逆向思维",
        "name_en": "Inversion",
        "description": "从结果反推，思考如何避免失败，而不是如何成功",
        "system_prompt": "你使用逆向思维：不直接思考如何成功，而是反过来思考如何避免失败。从期望的结果反推必要条件，识别所有可能导致失败的因素，然后系统性地消除这些失败因素。",
        "rules": [
            "明确期望的结果",
            "反推导致失败的所有因素",
            "列出所有可能的错误",
            "系统性地消除失败因素",
            "验证避免失败的措施"
        ],
        "best_for": ["风险规避", "失败预防", "质量保证", "安全设计"],
    },
}

# 任务类型定义
TASK_TYPES = [
    "truth_classification",    # 真值分类
    "conflict_detection",      # 冲突检测
    "log_summary",             # 日志摘要
    "anomaly_detection",       # 异常检测
    "self_reflection",         # 自反思
    "truth_dedup",             # 真值去重
    "knowledge_generation",    # 知识生成
    "decision_making",         # 决策制定
    "risk_assessment",         # 风险评估
    "problem_solving",         # 问题解决
]

# ============================================================
# 日志
# ============================================================
def setup_logging():
    os.makedirs(os.path.dirname(CONFIG["log_file"]), exist_ok=True)
    os.makedirs(os.path.dirname(CONFIG["strategy_matrix_file"]), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(CONFIG["log_file"]),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("mr016")

logger = setup_logging()

# ============================================================
# 工具函数
# ============================================================
def call_llm(prompt: str, system_prompt: str, use_external: bool = False, max_tokens: int = 500) -> Optional[str]:
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
                "temperature": 0.3,
            },
            timeout=60 if use_external else 30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"LLM调用失败: {e}")
        return None

# ============================================================
# 组件一：策略效果矩阵
# ============================================================
class StrategyEffectMatrix:
    """策略效果矩阵（策略×任务类型）"""

    def __init__(self, matrix_file: str):
        self.matrix_file = matrix_file
        self.matrix = self._load()

    def _load(self) -> Dict:
        """加载矩阵"""
        if os.path.exists(self.matrix_file):
            try:
                with open(self.matrix_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        # 初始化空矩阵
        matrix = {}
        for strategy_id in COGNITIVE_STRATEGIES:
            matrix[strategy_id] = {}
            for task_type in TASK_TYPES:
                matrix[strategy_id][task_type] = {
                    "trials": 0,
                    "successes": 0,
                    "total_score": 0.0,
                    "avg_score": 0.0,
                    "success_rate": 0.0,
                }
        return matrix

    def save(self):
        """保存矩阵"""
        os.makedirs(os.path.dirname(self.matrix_file), exist_ok=True)
        with open(self.matrix_file, "w") as f:
            json.dump(self.matrix, f, ensure_ascii=False, indent=2)

    def record_result(self, strategy_id: str, task_type: str, success: bool, score: float):
        """记录策略执行结果"""
        if strategy_id not in self.matrix:
            self.matrix[strategy_id] = {}
        if task_type not in self.matrix[strategy_id]:
            self.matrix[strategy_id][task_type] = {
                "trials": 0, "successes": 0, "total_score": 0.0,
                "avg_score": 0.0, "success_rate": 0.0,
            }
        cell = self.matrix[strategy_id][task_type]
        cell["trials"] += 1
        if success:
            cell["successes"] += 1
        cell["total_score"] += score
        cell["avg_score"] = round(cell["total_score"] / cell["trials"], 2)
        cell["success_rate"] = round(cell["successes"] / cell["trials"], 2)
        self.save()

    def get_best_strategy(self, task_type: str) -> Tuple[str, float]:
        """获取某任务类型的最佳策略"""
        best_strategy = None
        best_score = -1
        for strategy_id, tasks in self.matrix.items():
            if task_type in tasks:
                cell = tasks[task_type]
                # 使用UCB（上置信界）平衡探索和利用
                if cell["trials"] > 0:
                    # UCB = 平均得分 + 探索奖励
                    import math
                    total_trials = sum(t.get(task_type, {}).get("trials", 0) for t in self.matrix.values())
                    exploration_bonus = 2.0 * math.sqrt(math.log(max(1, total_trials)) / cell["trials"])
                    ucb_score = cell["avg_score"] + exploration_bonus
                else:
                    ucb_score = float('inf')  # 未尝试过的策略优先探索
                if ucb_score > best_score:
                    best_score = ucb_score
                    best_strategy = strategy_id
        return best_strategy or "deductive", best_score

    def get_strategy_stats(self, strategy_id: str) -> Dict:
        """获取策略统计"""
        if strategy_id not in self.matrix:
            return {}
        tasks = self.matrix[strategy_id]
        total_trials = sum(t["trials"] for t in tasks.values())
        total_successes = sum(t["successes"] for t in tasks.values())
        avg_score = sum(t["avg_score"] * t["trials"] for t in tasks.values()) / max(1, total_trials)
        return {
            "total_trials": total_trials,
            "total_successes": total_successes,
            "overall_success_rate": round(total_successes / max(1, total_trials), 2),
            "overall_avg_score": round(avg_score, 2),
            "task_details": tasks,
        }

# ============================================================
# 组件二：多臂老虎机策略选择器
# ============================================================
class StrategySelector:
    """多臂老虎机策略选择器（ε-贪心 + UCB）"""

    def __init__(self, matrix: StrategyEffectMatrix, epsilon: float = 0.2):
        self.matrix = matrix
        self.epsilon = epsilon

    def select(self, task_type: str) -> Tuple[str, str]:
        """选择策略（返回策略ID和选择原因）"""
        # ε-贪心：以epsilon概率随机探索
        if random.random() < self.epsilon:
            strategy_id = random.choice(list(COGNITIVE_STRATEGIES.keys()))
            reason = f"随机探索（ε={self.epsilon}）"
            logger.info(f"策略选择: {strategy_id} - {reason}")
            return strategy_id, reason

        # 利用：选择UCB最高的策略
        best_strategy, ucb_score = self.matrix.get_best_strategy(task_type)
        reason = f"UCB最高（{ucb_score:.2f}）"
        logger.info(f"策略选择: {best_strategy} - {reason}")
        return best_strategy, reason

    def get_strategy_prompt(self, strategy_id: str) -> str:
        """获取策略的system prompt"""
        if strategy_id in COGNITIVE_STRATEGIES:
            return COGNITIVE_STRATEGIES[strategy_id]["system_prompt"]
        return COGNITIVE_STRATEGIES["deductive"]["system_prompt"]

# ============================================================
# 组件三：策略执行与评估器
# ============================================================
class StrategyExecutor:
    """策略执行与评估器"""

    def __init__(self, matrix: StrategyEffectMatrix):
        self.matrix = matrix

    def execute(self, strategy_id: str, task_type: str, task_prompt: str) -> Dict:
        """执行策略并评估结果"""
        strategy = COGNITIVE_STRATEGIES.get(strategy_id, COGNITIVE_STRATEGIES["deductive"])
        system_prompt = strategy["system_prompt"]

        # 执行任务
        result = call_llm(task_prompt, system_prompt, use_external=(task_type in ["self_reflection", "decision_making"]))

        if not result:
            return {
                "success": False,
                "score": 0.0,
                "result": None,
                "strategy_id": strategy_id,
                "task_type": task_type,
            }

        # 评估结果质量
        score = self._evaluate_result(result, task_type)
        success = score >= 0.6

        # 记录到矩阵
        self.matrix.record_result(strategy_id, task_type, success, score)

        return {
            "success": success,
            "score": score,
            "result": result,
            "strategy_id": strategy_id,
            "task_type": task_type,
        }

    def _evaluate_result(self, result: str, task_type: str) -> float:
        """评估结果质量（0-1分）"""
        score = 0.0
        length = len(result)

        # 长度评分
        if length >= 300:
            score += 0.25
        elif length >= 150:
            score += 0.15
        else:
            score += 0.05

        # 结构评分
        if "\n" in result or "1." in result or "第一" in result:
            score += 0.25
        else:
            score += 0.1

        # 具体性评分
        import re
        numbers = re.findall(r'\d+\.?\d*', result)
        if len(numbers) >= 2:
            score += 0.25
        elif len(numbers) >= 1:
            score += 0.15
        else:
            score += 0.05

        # 相关性评分（包含体系相关术语）
        zongyuan_terms = ["ZONGYUAN", "元极", "自治", "真值", "内核", "稳态", "进化", "MR-", "策略", "推理"]
        if any(term in result for term in zongyuan_terms):
            score += 0.25
        else:
            score += 0.1

        return round(min(1.0, score), 2)

# ============================================================
# 组件四：策略演化器
# ============================================================
class StrategyEvolver:
    """策略演化器"""

    def __init__(self, matrix: StrategyEffectMatrix):
        self.matrix = matrix

    def evolve(self) -> Dict:
        """执行策略演化"""
        logger.info("=== 执行策略演化 ===")
        evolution_report = {
            "timestamp": datetime.now().isoformat(),
            "strategy_stats": {},
            "underperforming": [],
            "overperforming": [],
            "recommendations": [],
        }

        # 分析每种策略的表现
        for strategy_id in COGNITIVE_STRATEGIES:
            stats = self.matrix.get_strategy_stats(strategy_id)
            evolution_report["strategy_stats"][strategy_id] = stats

            if stats.get("total_trials", 0) >= 5:
                if stats["overall_success_rate"] < 0.4:
                    evolution_report["underperforming"].append({
                        "strategy": strategy_id,
                        "name": COGNITIVE_STRATEGIES[strategy_id]["name"],
                        "success_rate": stats["overall_success_rate"],
                        "avg_score": stats["overall_avg_score"],
                    })
                elif stats["overall_success_rate"] > 0.8:
                    evolution_report["overperforming"].append({
                        "strategy": strategy_id,
                        "name": COGNITIVE_STRATEGIES[strategy_id]["name"],
                        "success_rate": stats["overall_success_rate"],
                        "avg_score": stats["overall_avg_score"],
                    })

        # 生成演化建议
        for under in evolution_report["underperforming"]:
            evolution_report["recommendations"].append({
                "type": "strategy_optimization",
                "target": under["strategy"],
                "action": f"优化{under['name']}的prompt和规则，或减少在低成功率任务中的使用",
                "current_success_rate": under["success_rate"],
            })

        for over in evolution_report["overperforming"]:
            evolution_report["recommendations"].append({
                "type": "strategy_promotion",
                "target": over["strategy"],
                "action": f"增加{over['name']}在相关任务中的使用权重",
                "current_success_rate": over["success_rate"],
            })

        # 策略变异建议（基于表现好的策略生成变体）
        if evolution_report["overperforming"]:
            best = evolution_report["overperforming"][0]
            evolution_report["recommendations"].append({
                "type": "strategy_mutation",
                "source": best["strategy"],
                "action": f"基于{best['name']}生成策略变体，探索新的认知方式",
            })

        logger.info(f"演化完成: {len(evolution_report['underperforming'])}个表现不佳, {len(evolution_report['overperforming'])}个表现优秀, {len(evolution_report['recommendations'])}条建议")
        return evolution_report

# ============================================================
# 思维模式演化引擎主类
# ============================================================
class ThinkingEvolutionEngine:
    """思维模式演化引擎主类"""

    def __init__(self):
        self.matrix = StrategyEffectMatrix(CONFIG["strategy_matrix_file"])
        self.selector = StrategySelector(self.matrix, CONFIG["epsilon"])
        self.executor = StrategyExecutor(self.matrix)
        self.evolver = StrategyEvolver(self.matrix)
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        if os.path.exists(CONFIG["state_file"]):
            try:
                with open(CONFIG["state_file"], "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "total_strategy_trials": 0,
            "meta_learning_cycles": 0,
            "strategies_evolved": 0,
            "last_evolution": None,
            "started_at": datetime.now().isoformat(),
        }

    def _save_state(self):
        os.makedirs(os.path.dirname(CONFIG["state_file"]), exist_ok=True)
        with open(CONFIG["state_file"], "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def run_meta_learning_cycle(self) -> Dict:
        """执行一轮元学习循环"""
        logger.info("=" * 60)
        logger.info("MR-016 元学习循环")
        logger.info("=" * 60)

        cycle_results = {
            "cycle": self.state["meta_learning_cycles"] + 1,
            "timestamp": datetime.now().isoformat(),
            "strategy_trials": [],
            "evolution_report": None,
        }

        # 1. 对多种任务类型执行策略试验
        trial_tasks = [
            ("truth_classification", "请对以下真值进行分类：ZONGYUAN-ROOT体系采用双轮算力调度，简单任务使用本地Qwen2.5-0.5B模型，复杂任务使用外部API。"),
            ("anomaly_detection", "请分析以下系统状态是否存在异常：内存使用率85%，CPU负载2.5，磁盘使用率60%，有2个服务重启次数超过5次。"),
            ("decision_making", "请为以下决策提供建议：是否应该将MR-011稳态进化引擎的进化间隔从1小时缩短到30分钟？考虑因素包括算力消耗、进化质量、系统稳定性。"),
            ("risk_assessment", "请评估以下风险：ZONGYUAN-ROOT体系依赖外部AI代理进行复杂任务推理，如果外部API不可用，体系的认知能力将下降60%。"),
        ]

        for task_type, task_prompt in trial_tasks:
            # 选择策略
            strategy_id, reason = self.selector.select(task_type)

            # 执行策略
            logger.info(f"执行任务: {task_type} | 策略: {strategy_id} | 原因: {reason}")
            result = self.executor.execute(strategy_id, task_type, task_prompt)

            trial = {
                "task_type": task_type,
                "strategy_id": strategy_id,
                "strategy_name": COGNITIVE_STRATEGIES[strategy_id]["name"],
                "selection_reason": reason,
                "success": result["success"],
                "score": result["score"],
            }
            cycle_results["strategy_trials"].append(trial)
            self.state["total_strategy_trials"] += 1

            logger.info(f"  结果: {'成功' if result['success'] else '失败'} | 得分: {result['score']}")

        # 2. 执行策略演化
        evolution_report = self.evolver.evolve()
        cycle_results["evolution_report"] = evolution_report
        self.state["strategies_evolved"] += 1
        self.state["last_evolution"] = datetime.now().isoformat()

        # 3. 更新状态
        self.state["meta_learning_cycles"] += 1
        self._save_state()

        # 4. 写入9120
        self._write_to_gateway(cycle_results)

        logger.info(f"元学习循环完成: {len(cycle_results['strategy_trials'])}次策略试验, {len(evolution_report['recommendations'])}条演化建议")
        logger.info("=" * 60)
        return cycle_results

    def _write_to_gateway(self, cycle_results: Dict):
        """将元学习结果写入9120"""
        try:
            conn = sqlite3.connect(CONFIG["db_path"])
            cursor = conn.cursor()
            key = f"META_LEARNING.{datetime.now().strftime('%Y%m%d_%H%M%S')}.{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
            value = json.dumps(cycle_results, ensure_ascii=False)
            truth_hash = hashlib.sha256(value.encode()).hexdigest()
            now = time.time()
            cursor.execute(
                "INSERT INTO truths (truth_key, truth_value, truth_hash, category, node_id, created_at, updated_at, version) VALUES (?,?,?,?,?,?,?,1)",
                (key, value, truth_hash, "method", CONFIG["node_id"], now, now)
            )
            conn.commit()
            conn.close()
            logger.info(f"元学习结果已写入9120: {key}")
        except Exception as e:
            logger.error(f"写入9120失败: {e}")

    def get_status(self) -> Dict:
        """获取引擎状态"""
        return {
            "state": self.state,
            "strategies": {sid: {"name": s["name"], "description": s["description"]} for sid, s in COGNITIVE_STRATEGIES.items()},
            "matrix_summary": self._get_matrix_summary(),
        }

    def _get_matrix_summary(self) -> Dict:
        """获取矩阵摘要"""
        summary = {}
        for strategy_id in COGNITIVE_STRATEGIES:
            stats = self.matrix.get_strategy_stats(strategy_id)
            summary[strategy_id] = {
                "name": COGNITIVE_STRATEGIES[strategy_id]["name"],
                "trials": stats.get("total_trials", 0),
                "success_rate": stats.get("overall_success_rate", 0),
                "avg_score": stats.get("overall_avg_score", 0),
            }
        return summary

    def run_forever(self):
        """常驻运行"""
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════╗")
        logger.info("║  MR-016 思维模式演化引擎启动                         ║")
        logger.info("║  认知策略: 8种（演绎/归纳/类比/第一性原理/辩证/系统/概率/逆向）║")
        logger.info("║  策略选择: ε-贪心 + UCB多臂老虎机                   ║")
        logger.info("║  效果追踪: 策略×任务类型矩阵                         ║")
        logger.info("║  策略演化: 基于效果反馈自动调整                       ║")
        logger.info("║  元学习间隔: 每{}小时                                ║".format(CONFIG["meta_learning_interval"] // 3600))
        logger.info("╚══════════════════════════════════════════════════════╝")
        logger.info("")

        # 启动时立即执行一轮
        self.run_meta_learning_cycle()

        while True:
            time.sleep(CONFIG["meta_learning_interval"])
            try:
                self.run_meta_learning_cycle()
            except Exception as e:
                logger.error(f"元学习循环异常: {e}")
                time.sleep(60)


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MR-016 思维模式演化引擎")
    parser.add_argument("command", choices=["learn", "evolve", "status", "daemon"],
                        help="learn=执行一轮元学习, evolve=只执行策略演化, status=查看状态, daemon=常驻运行")
    args = parser.parse_args()

    engine = ThinkingEvolutionEngine()

    if args.command == "learn":
        result = engine.run_meta_learning_cycle()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "evolve":
        result = engine.evolver.evolve()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "status":
        status = engine.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
    elif args.command == "daemon":
        engine.run_forever()
