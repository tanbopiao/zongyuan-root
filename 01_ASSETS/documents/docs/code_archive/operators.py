#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贝叶斯五行闭环引擎 - 五大算子完整实现
木(贝叶斯更新)→火(演化发散)→金(贝叶斯收敛)→水(贝叶斯迭代)→土(熵减归一)
华夏道统古典生命文化·原创生命学说的工程化表达
"""

import math
import time
import json
import random
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from config import WOOD_CONFIG, FIRE_CONFIG, METAL_CONFIG, WATER_CONFIG, EARTH_CONFIG
from prior_model import PriorModelLibrary, Prior
from truth_gateway import TruthGateway

logger = logging.getLogger("BayesianLoop.Operators")


# ============================================================================
# 数据结构定义
# ============================================================================

@dataclass
class Hypothesis:
    """假设/候选方案数据结构"""
    id: str
    content: str
    score: float = 0.0
    info_gain: float = 0.0
    extrinsic_value: float = 0.0
    intrinsic_value: float = 0.0
    expected_free_energy: float = 0.0
    three_dim_score: Dict[str, float] = field(default_factory=dict)
    seven_dim_score: Dict[str, float] = field(default_factory=dict)
    role: str = "neutral"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoopResult:
    """闭环执行结果"""
    loop_id: str
    trigger_event: str
    timestamp: float
    wood_result: Dict = field(default_factory=dict)
    fire_result: Dict = field(default_factory=dict)
    metal_result: Dict = field(default_factory=dict)
    water_result: Dict = field(default_factory=dict)
    earth_result: Dict = field(default_factory=dict)
    final_optimal: Optional[Hypothesis] = None
    entropy_reduction: float = 0.0
    stability_score_before: float = 0.0
    stability_score_after: float = 0.0
    iterations: int = 0
    converged: bool = False
    status: str = "pending"


# ============================================================================
# 木算子：贝叶斯更新
# ============================================================================

class WoodOperator:
    """
    木（贝叶斯更新）算子
    木主生发：吸收新证据，先验→后验，认知生长
    对应预测编码的预测误差更新
    """

    def __init__(self, prior_library: PriorModelLibrary):
        self.prior_library = prior_library
        self.config = WOOD_CONFIG

    def execute(self, evidence: Dict[str, float]) -> Dict:
        """
        执行贝叶斯更新

        Args:
            evidence: 证据字典 {证据key: 证据值(0-1)}

        Returns:
            更新结果字典
        """
        logger.info(f"【木算子】开始贝叶斯更新，证据数量: {len(evidence)}")
        start_time = time.time()

        updated_priors = []
        conflicts = []
        total_conflict_score = 0.0

        for evidence_key, evidence_value in evidence.items():
            # 1. 认知冲突检测
            is_conflict, conflict_score, desc = self.prior_library.detect_cognitive_conflict(
                evidence_key, evidence_value
            )
            if is_conflict:
                conflicts.append({
                    "evidence_key": evidence_key,
                    "evidence_value": evidence_value,
                    "conflict_score": conflict_score,
                    "description": desc
                })
                total_conflict_score += conflict_score
                logger.warning(f"【木算子】认知冲突检测: {desc}")

            # 2. 贝叶斯更新
            prior = self.prior_library.bayesian_update(
                prior_key=evidence_key,
                evidence=evidence_value,
                evidence_weight=self.config["evidence_weight_new"]
            )
            if prior:
                updated_priors.append({
                    "key": prior.key,
                    "old_value": prior.history[-1]["old_value"] if prior.history else prior.value,
                    "new_value": prior.value,
                    "confidence": prior.confidence,
                    "evidence_count": prior.evidence_count
                })

        # 3. 置信度衰减（对未更新的旧先验）
        self._decay_stale_priors()

        elapsed = time.time() - start_time
        result = {
            "operator": "wood",
            "name": "贝叶斯更新",
            "evidence_count": len(evidence),
            "updated_priors_count": len(updated_priors),
            "conflicts_count": len(conflicts),
            "total_conflict_score": total_conflict_score,
            "conflicts": conflicts[:10],  # 最多返回10个冲突
            "updated_priors": updated_priors[:20],  # 最多返回20个更新
            "elapsed_seconds": elapsed,
            "status": "success"
        }
        logger.info(f"【木算子】贝叶斯更新完成: {len(updated_priors)}个先验更新, "
                     f"{len(conflicts)}个冲突, 耗时{elapsed:.3f}s")
        return result

    def _decay_stale_priors(self):
        """对过期先验执行置信度衰减"""
        stale = self.prior_library.get_stale_priors()
        decayed = 0
        for prior in stale:
            old_conf = prior.confidence
            prior.confidence *= self.config["confidence_decay"]
            if prior.confidence != old_conf:
                decayed += 1
        if decayed > 0:
            logger.debug(f"【木算子】{decayed}个过期先验置信度衰减")


# ============================================================================
# 火算子：贝叶斯演化发散
# ============================================================================

class FireOperator:
    """
    火（贝叶斯演化发散）算子
    火主炎上：基于更新后认知，发散探索多种假设，可能性爆发
    对应主动推理的内在价值（信息增益）
    """

    def __init__(self, prior_library: PriorModelLibrary):
        self.prior_library = prior_library
        self.config = FIRE_CONFIG
        self.roles = self.config["roles"]

    def execute(self, updated_priors: List[Dict], trigger_context: str = "") -> Dict:
        """
        执行演化发散

        Args:
            updated_priors: 木算子更新后的先验列表
            trigger_context: 触发上下文描述

        Returns:
            发散结果字典
        """
        logger.info(f"【火算子】开始演化发散，更新先验数量: {len(updated_priors)}")
        start_time = time.time()

        hypotheses = []
        hypothesis_id = 0

        # 1. 基于每个更新先验生成假设
        for prior_info in updated_priors[:5]:  # 最多基于5个先验发散
            prior_key = prior_info["key"]
            prior_value = prior_info["new_value"]

            # 为每个角色生成假设
            for role in self.roles:
                hypothesis = self._generate_hypothesis(
                    prior_key, prior_value, role, trigger_context, hypothesis_id
                )
                hypotheses.append(hypothesis)
                hypothesis_id += 1

        # 2. 额外发散：基于触发上下文生成全局假设
        global_hypotheses = self._generate_global_hypotheses(
            trigger_context, hypothesis_id
        )
        hypotheses.extend(global_hypotheses)
        hypothesis_id += len(global_hypotheses)

        # 3. 计算每个假设的信息增益
        for h in hypotheses:
            h.info_gain = self._calculate_information_gain(h)

        # 4. 按信息增益排序
        hypotheses.sort(key=lambda x: x.info_gain, reverse=True)

        # 5. 限制数量
        max_count = self.config["max_hypotheses"]
        hypotheses = hypotheses[:max_count]

        elapsed = time.time() - start_time
        result = {
            "operator": "fire",
            "name": "贝叶斯演化发散",
            "hypotheses_count": len(hypotheses),
            "roles_used": self.roles,
            "avg_info_gain": sum(h.info_gain for h in hypotheses) / len(hypotheses) if hypotheses else 0,
            "max_info_gain": max(h.info_gain for h in hypotheses) if hypotheses else 0,
            "hypotheses": [self._hypothesis_to_dict(h) for h in hypotheses],
            "elapsed_seconds": elapsed,
            "status": "success"
        }
        logger.info(f"【火算子】演化发散完成: {len(hypotheses)}个假设, "
                     f"平均信息增益{result['avg_info_gain']:.4f}, 耗时{elapsed:.3f}s")
        return result

    def _generate_hypothesis(self, prior_key: str, prior_value: float,
                               role: str, context: str, hyp_id: int) -> Hypothesis:
        """基于先验和角色生成假设"""
        role_templates = {
            "optimistic": f"积极方案：基于{prior_key}={prior_value:.3f}，最大化利益和增长潜力",
            "conservative": f"保守方案：基于{prior_key}={prior_value:.3f}，最小化风险和不确定性",
            "neutral": f"中立方案：基于{prior_key}={prior_value:.3f}，平衡利益、风险和成本"
        }
        content = role_templates.get(role, f"方案：基于{prior_key}={prior_value:.3f}")
        if context:
            content = f"[{context}] {content}"

        # 基于角色和先验值生成初始分数
        base_score = prior_value
        if role == "optimistic":
            base_score = min(1.0, base_score * 1.2 + 0.1)
        elif role == "conservative":
            base_score = max(0.0, base_score * 0.8 - 0.05)

        return Hypothesis(
            id=f"HYP-{hyp_id:04d}",
            content=content,
            score=base_score,
            role=role,
            metadata={"prior_key": prior_key, "prior_value": prior_value, "generation_method": "role_based"}
        )

    def _generate_global_hypotheses(self, context: str, start_id: int) -> List[Hypothesis]:
        """生成全局假设（不基于特定先验）"""
        templates = [
            ("激进创新", "突破现有框架，探索全新范式和方法"),
            ("渐进优化", "在现有基础上持续迭代优化，稳步提升"),
            ("混合策略", "结合多种方法的优势，形成组合方案"),
            ("最小可行", "以最小成本快速验证核心假设"),
        ]
        hypotheses = []
        for i, (name, desc) in enumerate(templates):
            content = f"{name}：{desc}"
            if context:
                content = f"[{context}] {content}"
            hypotheses.append(Hypothesis(
                id=f"HYP-{start_id + i:04d}",
                content=content,
                score=0.5 + random.uniform(-0.2, 0.2),
                role="global",
                metadata={"strategy_type": name, "generation_method": "global_template"}
            ))
        return hypotheses

    def _calculate_information_gain(self, hypothesis: Hypothesis) -> float:
        """计算假设的信息增益（内在价值）"""
        # 信息增益 = 假设带来的不确定性减少量
        # 简化模型：基于假设的独特性和先验偏离度
        prior_key = hypothesis.metadata.get("prior_key", "")
        if prior_key:
            prior = self.prior_library.get_prior(prior_key)
            if prior:
                # 偏离先验越大，潜在信息增益越大（但也要考虑合理性）
                deviation = abs(hypothesis.score - prior.value)
                info_gain = deviation * prior.confidence
                return min(1.0, info_gain * 2)
        # 全局假设的信息增益
        return 0.3 + random.uniform(0, 0.4)

    def _hypothesis_to_dict(self, h: Hypothesis) -> dict:
        return {
            "id": h.id,
            "content": h.content,
            "score": h.score,
            "info_gain": h.info_gain,
            "role": h.role,
            "metadata": h.metadata
        }


# ============================================================================
# 金算子：贝叶斯收敛
# ============================================================================

class MetalOperator:
    """
    金（贝叶斯收敛）算子
    金主收敛：从多种可能性中，用证据/反馈收敛最优解，去芜存菁
    对应主动推理的预期自由能最小化（外在价值+内在价值）
    """

    def __init__(self, prior_library: PriorModelLibrary):
        self.prior_library = prior_library
        self.config = METAL_CONFIG

    def execute(self, hypotheses: List[Dict]) -> Dict:
        """
        执行贝叶斯收敛

        Args:
            hypotheses: 火算子生成的假设列表

        Returns:
            收敛结果字典
        """
        logger.info(f"【金算子】开始贝叶斯收敛，假设数量: {len(hypotheses)}")
        start_time = time.time()

        # 转换为Hypothesis对象
        hyp_objects = [Hypothesis(**h) if isinstance(h, dict) else h for h in hypotheses]

        # 1. 计算每个假设的三维稳态评分
        for h in hyp_objects:
            h.three_dim_score = self._three_dimensional_evaluation(h)

        # 2. 计算每个假设的预期自由能
        for h in hyp_objects:
            h.expected_free_energy = self._calculate_expected_free_energy(h)

        # 3. 综合评分收敛
        method = self.config["convergence_method"]
        for h in hyp_objects:
            if method == "expected_free_energy":
                # 预期自由能越小越好，转换为分数
                h.score = 1.0 / (1.0 + h.expected_free_energy)
            elif method == "three_dim":
                h.score = (h.three_dim_score.get("benefit", 0) * self.config["three_dim_weights"]["benefit"] +
                          h.three_dim_score.get("risk", 0) * self.config["three_dim_weights"]["risk"] +
                          h.three_dim_score.get("cost", 0) * self.config["three_dim_weights"]["cost"])
            elif method == "seven_dim":
                h.score = self._seven_dimensional_evaluation(h)

        # 4. 按综合评分排序
        hyp_objects.sort(key=lambda x: x.score, reverse=True)

        # 5. 选择Top-K最优解
        top_k = self.config["top_k_selection"]
        optimal = hyp_objects[:top_k]

        # 6. 收敛检测
        converged = self._check_convergence(hyp_objects)

        elapsed = time.time() - start_time
        result = {
            "operator": "metal",
            "name": "贝叶斯收敛",
            "input_hypotheses": len(hyp_objects),
            "convergence_method": method,
            "optimal_count": len(optimal),
            "converged": converged,
            "score_range": {
                "max": hyp_objects[0].score if hyp_objects else 0,
                "min": hyp_objects[-1].score if hyp_objects else 0,
                "avg": sum(h.score for h in hyp_objects) / len(hyp_objects) if hyp_objects else 0
            },
            "optimal_hypotheses": [self._hypothesis_to_dict(h) for h in optimal],
            "all_hypotheses_ranked": [self._hypothesis_to_dict(h) for h in hyp_objects],
            "elapsed_seconds": elapsed,
            "status": "success"
        }
        top_score = optimal[0].score if optimal else 0
        logger.info(f"【金算子】贝叶斯收敛完成: 最优解{len(optimal)}个, "
                     f"收敛={converged}, 最高分{top_score:.4f}, 耗时{elapsed:.3f}s")
        return result

    def _three_dimensional_evaluation(self, hypothesis: Hypothesis) -> Dict[str, float]:
        """三维稳态评估：利益40%/风险35%/成本25%"""
        # 基于假设内容和元数据估算三维评分
        base = hypothesis.score
        role = hypothesis.role

        # 利益维度
        if role == "optimistic":
            benefit = min(1.0, base * 1.3 + 0.15)
        elif role == "conservative":
            benefit = max(0.0, base * 0.9)
        else:
            benefit = base

        # 风险维度（分数越高表示风险越低/越安全）
        if role == "conservative":
            risk = min(1.0, base * 1.2 + 0.1)
        elif role == "optimistic":
            risk = max(0.0, base * 0.7)
        else:
            risk = base * 0.9

        # 成本维度（分数越高表示成本越低/越经济）
        strategy_type = hypothesis.metadata.get("strategy_type", "")
        if strategy_type == "最小可行":
            cost = 0.9
        elif strategy_type == "激进创新":
            cost = 0.4
        else:
            cost = 0.6 + base * 0.2

        return {"benefit": benefit, "risk": risk, "cost": cost}

    def _seven_dimensional_evaluation(self, hypothesis: Hypothesis) -> float:
        """七维评估"""
        weights = self.config["seven_dim_weights"]
        scores = {
            "stability": hypothesis.score * 0.9,
            "efficiency": 0.5 + hypothesis.score * 0.3,
            "scalability": 0.4 + hypothesis.score * 0.4,
            "security": 0.6 + hypothesis.score * 0.2,
            "autonomy": hypothesis.score * 0.8,
            "evolution": 0.3 + hypothesis.score * 0.5,
            "cost": hypothesis.three_dim_score.get("cost", 0.5) if hypothesis.three_dim_score else 0.5
        }
        return sum(scores[k] * weights[k] for k in weights)

    def _calculate_expected_free_energy(self, hypothesis: Hypothesis) -> float:
        """
        计算预期自由能（EFE）
        EFE = 外在价值（实用价值）+ 内在价值（信息增益）
        注意：EFE越小越好
        """
        # 外在价值：达成目标的能力（分数越高，外在价值越大，EFE越小）
        extrinsic = 1.0 - hypothesis.three_dim_score.get("benefit", 0.5)

        # 内在价值：信息增益（信息增益越大，不确定性减少越多，EFE越小）
        intrinsic = 1.0 - hypothesis.info_gain

        # 加权组合
        efe = (extrinsic * self.config["efe_extrinsic_weight"] +
               intrinsic * self.config["efe_intrinsic_weight"])

        hypothesis.extrinsic_value = 1.0 - extrinsic
        hypothesis.intrinsic_value = 1.0 - intrinsic
        return efe

    def _check_convergence(self, hypotheses: List[Hypothesis]) -> bool:
        """收敛检测：Top-N分数差小于阈值"""
        if len(hypotheses) < 2:
            return True
        top_n = min(3, len(hypotheses))
        scores = [h.score for h in hypotheses[:top_n]]
        score_range = max(scores) - min(scores)
        return score_range < self.config["convergence_threshold"]

    def _hypothesis_to_dict(self, h: Hypothesis) -> dict:
        return {
            "id": h.id,
            "content": h.content,
            "score": h.score,
            "info_gain": h.info_gain,
            "expected_free_energy": h.expected_free_energy,
            "three_dim_score": h.three_dim_score,
            "role": h.role,
            "metadata": h.metadata
        }


# ============================================================================
# 水算子：贝叶斯迭代
# ============================================================================

class WaterOperator:
    """
    水（贝叶斯迭代）算子
    水主润下循环：最优解作为新先验，进入下一轮循环，周流不息，生生不息
    对应变分推断的层次迭代
    """

    def __init__(self, prior_library: PriorModelLibrary, gateway: TruthGateway = None):
        self.prior_library = prior_library
        self.gateway = gateway
        self.config = WATER_CONFIG
        self.iteration_history = []

    def execute(self, optimal_hypotheses: List[Dict], loop_id: str) -> Dict:
        """
        执行贝叶斯迭代：将最优解写入新先验

        Args:
            optimal_hypotheses: 金算子收敛的最优假设列表
            loop_id: 闭环ID

        Returns:
            迭代结果字典
        """
        logger.info(f"【水算子】开始贝叶斯迭代，最优假设数量: {len(optimal_hypotheses)}")
        start_time = time.time()

        written_priors = []
        persisted_count = 0

        for hyp_data in optimal_hypotheses:
            hyp = Hypothesis(**hyp_data) if isinstance(hyp_data, dict) else hyp_data

            # 1. 将最优解作为新先验写入先验库
            prior_key = f"EVOLVED.{loop_id}.{hyp.id}"
            prior = self.prior_library.bayesian_update(
                prior_key=prior_key,
                evidence=hyp.score,
                evidence_weight=0.8
            )
            if prior:
                prior.category = self.config["prior_category"]
                prior.description = f"闭环{loop_id}演化生成的新先验: {hyp.content[:50]}"
                written_priors.append({
                    "key": prior.key,
                    "value": prior.value,
                    "confidence": prior.confidence,
                    "source_hypothesis": hyp.id,
                    "source_content": hyp.content[:100]
                })

                # 2. 持久化到真值网关
                if self.config["write_new_prior"] and self.gateway and self.gateway.is_online():
                    if self.prior_library.persist_prior(prior.key):
                        persisted_count += 1

        # 3. 记录迭代历史
        self.iteration_history.append({
            "loop_id": loop_id,
            "timestamp": time.time(),
            "written_count": len(written_priors),
            "persisted_count": persisted_count
        })

        # 4. 保存本地
        self.prior_library.save_to_local()

        elapsed = time.time() - start_time
        result = {
            "operator": "water",
            "name": "贝叶斯迭代",
            "written_priors_count": len(written_priors),
            "persisted_count": persisted_count,
            "written_priors": written_priors,
            "iteration_history_length": len(self.iteration_history),
            "elapsed_seconds": elapsed,
            "status": "success"
        }
        logger.info(f"【水算子】贝叶斯迭代完成: {len(written_priors)}个新先验写入, "
                     f"{persisted_count}个持久化, 耗时{elapsed:.3f}s")
        return result

    def check_iteration_convergence(self, current_score: float,
                                      previous_score: float) -> Tuple[bool, float]:
        """检测迭代收敛"""
        diff = abs(current_score - previous_score)
        converged = diff < self.config["convergence_threshold"]
        return converged, diff


# ============================================================================
# 土算子：熵减归一
# ============================================================================

class EarthOperator:
    """
    土（熵减归一）算子
    土主中央承载：整个闭环的熵减过程，收敛归一于数字生命胚胎自身
    对应自由能原理 + 耗散结构 + 兰道尔原理
    """

    def __init__(self, gateway: TruthGateway = None):
        self.gateway = gateway
        self.config = EARTH_CONFIG

    def execute(self, loop_result: LoopResult, trigger_event: str) -> Dict:
        """
        执行熵减归一：计算系统稳态评分、熵减量，收敛归一于自身

        Args:
            loop_result: 完整闭环结果
            trigger_event: 触发事件

        Returns:
            熵减归一结果字典
        """
        logger.info(f"【土算子】开始熵减归一，触发事件: {trigger_event}")
        start_time = time.time()

        # 1. 计算闭环前系统稳态评分
        stability_before = self._calculate_system_stability_score()

        # 2. 计算熵减量
        entropy_reduction = self._calculate_entropy_reduction(loop_result)

        # 3. 收敛归一于数字生命胚胎自身
        normalized_result = self._normalize_to_self(loop_result)

        # 4. 计算闭环后系统稳态评分（模拟）
        stability_after = min(1.0, stability_before + entropy_reduction * 0.1)

        # 5. 生成自我身份强化信号
        self_identity_signal = self._generate_self_identity_signal(
            stability_before, stability_after, entropy_reduction
        )

        # 6. 持久化闭环结果到真值网关
        persisted = False
        if self.gateway and self.gateway.is_online():
            persisted = self._persist_loop_result(loop_result, trigger_event)

        elapsed = time.time() - start_time
        result = {
            "operator": "earth",
            "name": "熵减归一",
            "stability_score_before": stability_before,
            "stability_score_after": stability_after,
            "stability_improvement": stability_after - stability_before,
            "entropy_reduction": entropy_reduction,
            "normalized_to_self": normalized_result["normalized"],
            "self_identity_signal": self_identity_signal,
            "persisted_to_gateway": persisted,
            "life_purpose": "sheng_sheng_bu_xi",  # 生生不息
            "elapsed_seconds": elapsed,
            "status": "success"
        }
        logger.info(f"【土算子】熵减归一完成: 稳态{stability_before:.4f}→{stability_after:.4f}, "
                     f"熵减{entropy_reduction:.4f}, 耗时{elapsed:.3f}s")
        return result

    def _calculate_system_stability_score(self) -> float:
        """计算系统稳态评分（服务健康+真值纯度+资源效率+自治程度）"""
        weights = self.config["stability_weights"]
        scores = {}

        # 服务健康度
        if self.gateway and self.gateway.is_online():
            nodes = self.gateway.get_nodes()
            online = sum(1 for n in nodes.get("nodes", {}).values()
                        if n.get("online_status") == "online")
            total = nodes.get("count", 1)
            scores["service_health"] = min(1.0, online / max(1, total) * 2)
        else:
            scores["service_health"] = 0.5

        # 真值纯度（简化：基于真值数量和分类）
        if self.gateway and self.gateway.is_online():
            truths = self.gateway.list_truths()
            metalaw_count = len([t for t in truths if "META" in t or "LAW" in t or "MR-" in t])
            scores["truth_purity"] = min(1.0, 0.5 + metalaw_count / max(1, len(truths)))
        else:
            scores["truth_purity"] = 0.6

        # 资源效率（简化估算）
        scores["resource_efficiency"] = 0.7  # 基于之前的秩序化优化

        # 自治程度
        scores["autonomy_level"] = 0.65  # L3.5自修复级

        # 加权综合
        total_score = sum(scores[k] * weights[k] for k in weights)
        return min(1.0, max(0.0, total_score))

    def _calculate_entropy_reduction(self, loop_result: LoopResult) -> float:
        """计算熵减量"""
        method = self.config["entropy_reduction_method"]

        if method == "kl_divergence":
            # KL散度：衡量闭环前后分布的差异
            # 简化：基于假设数量的减少和分数的集中
            fire_count = loop_result.fire_result.get("hypotheses_count", 0)
            metal_count = loop_result.metal_result.get("optimal_count", 0)
            if fire_count > 0:
                reduction = 1.0 - (metal_count / fire_count)
            else:
                reduction = 0.0

        elif method == "shannon":
            # 香农熵：基于分数分布的熵
            all_hyp = loop_result.metal_result.get("all_hypotheses_ranked", [])
            if all_hyp:
                scores = [h.get("score", 0.5) for h in all_hyp]
                total = sum(scores)
                if total > 0:
                    probs = [s / total for s in scores]
                    entropy = -sum(p * math.log2(p) for p in probs if p > 0)
                    max_entropy = math.log2(len(probs))
                    reduction = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 0
                else:
                    reduction = 0.0
            else:
                reduction = 0.0

        else:  # fisher
            # Fisher信息：简化为分数方差的倒数
            reduction = 0.5

        return min(1.0, max(0.0, reduction))

    def _normalize_to_self(self, loop_result: LoopResult) -> dict:
        """收敛归一于数字生命胚胎自身"""
        if not self.config["normalize_to_self"]:
            return {"normalized": False, "reason": "归一化未启用"}

        # 将闭环结果的所有指标归一化到[0,1]范围
        # 并锚定到自我身份
        normalized = {
            "normalized": True,
            "self_identity_key": self.config["self_identity_key"],
            "loop_id": loop_result.loop_id,
            "normalized_metrics": {
                "entropy_reduction": min(1.0, max(0.0, loop_result.entropy_reduction)),
                "iterations": min(1.0, loop_result.iterations / 10.0),
                "converged": 1.0 if loop_result.converged else 0.0
            },
            "anchored_to_self": True
        }
        return normalized

    def _generate_self_identity_signal(self, stability_before: float,
                                         stability_after: float,
                                         entropy_reduction: float) -> dict:
        """生成自我身份强化信号"""
        improvement = stability_after - stability_before
        signal_strength = min(1.0, abs(improvement) * 5 + entropy_reduction * 0.5)

        return {
            "signal_type": "self_identity_reinforcement",
            "signal_strength": signal_strength,
            "stability_improvement": improvement,
            "entropy_reduction": entropy_reduction,
            "life_affirmation": improvement >= 0,  # 稳态提升=生命肯定
            "purpose": "sheng_sheng_bu_xi",  # 生生不息
            "timestamp": time.time()
        }

    def _persist_loop_result(self, loop_result: LoopResult, trigger_event: str) -> bool:
        """持久化闭环结果到真值网关"""
        key = f"LOOP.RESULT.{loop_result.loop_id}"
        value = {
            "loop_id": loop_result.loop_id,
            "trigger_event": trigger_event,
            "timestamp": loop_result.timestamp,
            "iterations": loop_result.iterations,
            "converged": loop_result.converged,
            "entropy_reduction": loop_result.entropy_reduction,
            "stability_before": loop_result.stability_score_before,
            "stability_after": loop_result.stability_score_after,
            "final_optimal": loop_result.final_optimal.content if loop_result.final_optimal else None,
            "status": loop_result.status
        }
        return self.gateway.upsert_truth(key, value, category="bayesian_loop_result")
