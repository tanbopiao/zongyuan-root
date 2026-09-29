#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贝叶斯五行闭环引擎 - 先验模型库
管理所有先验概率模型，支持贝叶斯更新、置信度衰减、冲突检测
"""

import json
import time
import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict

from config import PRIOR_MODEL_CONFIG, WOOD_CONFIG
from truth_gateway import TruthGateway

logger = logging.getLogger("BayesianLoop.PriorModel")


@dataclass
class Prior:
    """先验模型数据结构"""
    key: str                           # 先验唯一标识
    value: float                       # 先验值（概率/评分，0-1）
    confidence: float                  # 置信度（0-1）
    evidence_count: int = 0            # 支撑证据数量
    last_update: float = 0.0           # 最后更新时间戳
    created_at: float = 0.0            # 创建时间戳
    category: str = "general"          # 分类
    description: str = ""               # 描述
    history: List[Dict] = field(default_factory=list)  # 更新历史

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Prior":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class PriorModelLibrary:
    """先验模型库 - 木算子的核心数据结构"""

    def __init__(self, gateway: TruthGateway = None):
        self.gateway = gateway
        self.priors: Dict[str, Prior] = {}
        self._loaded = False
        self._storage_path = PRIOR_MODEL_CONFIG["local_storage_path"]

    def load(self) -> int:
        """加载先验模型库（从真值网关或本地文件）"""
        loaded = 0

        # 1. 加载默认先验
        for key, value in PRIOR_MODEL_CONFIG["default_priors"].items():
            if key not in self.priors:
                try:
                    float_value = float(value)
                except (ValueError, TypeError):
                    float_value = 0.5  # 非数值型默认0.5
                self.priors[key] = Prior(
                    key=key, value=float_value, confidence=0.9,
                    evidence_count=1, last_update=time.time(),
                    created_at=time.time(), category="default",
                    description=f"系统默认先验: {key}"
                )
                loaded += 1

        # 2. 从真值网关加载已演化先验
        if self.gateway and self.gateway.is_online():
            evolved_keys = self.gateway.list_truths(prefix="PRIOR.")
            for key in evolved_keys:
                truth = self.gateway.get_truth(key)
                if truth:
                    try:
                        raw_value = truth.get("value", "{}")
                        # value可能是字符串（需要json.loads）或已经是dict
                        if isinstance(raw_value, str):
                            data = json.loads(raw_value)
                        else:
                            data = raw_value
                        prior = Prior.from_dict(data)
                        self.priors[prior.key] = prior
                        loaded += 1
                    except Exception as e:
                        logger.warning(f"解析先验失败 {key}: {e}")

        # 3. 从本地文件加载
        self._load_from_local()

        self._loaded = True
        logger.info(f"先验模型库加载完成: {len(self.priors)} 个先验")
        return loaded

    def _load_from_local(self):
        """从本地JSON文件加载"""
        try:
            import os
            if os.path.exists(self._storage_path):
                with open(self._storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, prior_data in data.items():
                    if key not in self.priors:
                        self.priors[key] = Prior.from_dict(prior_data)
        except Exception as e:
            logger.warning(f"本地先验加载失败: {e}")

    def save_to_local(self):
        """保存到本地JSON文件"""
        try:
            import os
            os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
            data = {k: v.to_dict() for k, v in self.priors.items()}
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"本地先验保存失败: {e}")

    # ============ 核心贝叶斯更新函数 ============

    def bayesian_update(self, prior_key: str, evidence: float,
                         likelihood: float = None, evidence_weight: float = None) -> Optional[Prior]:
        """
        贝叶斯更新核心函数
        P(H|E) = P(E|H) * P(H) / P(E)

        Args:
            prior_key: 先验标识
            evidence: 证据值（0-1，表示证据支持程度）
            likelihood: 似然 P(E|H)，默认根据evidence计算
            evidence_weight: 证据权重，默认使用配置

        Returns:
            更新后的先验
        """
        if prior_key not in self.priors:
            logger.warning(f"先验不存在，创建新先验: {prior_key}")
            self.priors[prior_key] = Prior(
                key=prior_key, value=0.5, confidence=WOOD_CONFIG["default_confidence"],
                evidence_count=0, created_at=time.time(), category="auto_created"
            )

        prior = self.priors[prior_key]
        old_value = prior.value
        old_confidence = prior.confidence

        # 计算似然 P(E|H)
        if likelihood is None:
            # 证据支持程度越高，似然越大
            likelihood = 0.5 + 0.5 * evidence

        # 计算证据概率 P(E) = P(E|H)*P(H) + P(E|¬H)*P(¬H)
        p_not_h = 1 - old_value
        likelihood_not_h = 1 - likelihood  # 简化：非H下的似然
        p_evidence = likelihood * old_value + likelihood_not_h * p_not_h

        if p_evidence == 0:
            logger.warning(f"证据概率为0，跳过更新: {prior_key}")
            return prior

        # 贝叶斯后验 P(H|E)
        posterior = (likelihood * old_value) / p_evidence

        # 证据权重
        weight = evidence_weight or WOOD_CONFIG["evidence_weight_new"]

        # 加权更新（新旧先验的加权平均）
        new_value = old_value * (1 - weight) + posterior * weight

        # 置信度更新：证据越多，置信度越高，但有上限
        new_evidence_count = prior.evidence_count + 1
        new_confidence = min(0.99, old_confidence + (1 - old_confidence) * 0.1 * weight)

        # 记录历史
        prior.history.append({
            "timestamp": time.time(),
            "old_value": old_value,
            "new_value": new_value,
            "evidence": evidence,
            "likelihood": likelihood,
            "posterior": posterior,
            "weight": weight
        })

        # 更新先验
        prior.value = new_value
        prior.confidence = new_confidence
        prior.evidence_count = new_evidence_count
        prior.last_update = time.time()

        logger.debug(f"贝叶斯更新: {prior_key} {old_value:.4f}→{new_value:.4f} "
                     f"(置信度 {old_confidence:.4f}→{new_confidence:.4f})")

        return prior

    def detect_cognitive_conflict(self, new_evidence_key: str,
                                    new_evidence_value: float) -> Tuple[bool, float, str]:
        """
        认知冲突检测
        检测新证据与现有先验是否存在显著冲突

        Returns:
            (is_conflict, conflict_score, description)
        """
        # 查找相关先验
        related_priors = self._find_related_priors(new_evidence_key)
        if not related_priors:
            return False, 0.0, "无相关先验，不构成冲突"

        max_conflict = 0.0
        conflict_prior = None

        for prior in related_priors:
            # 冲突分数 = |新证据值 - 先验值| * 先验置信度
            conflict = abs(new_evidence_value - prior.value) * prior.confidence
            if conflict > max_conflict:
                max_conflict = conflict
                conflict_prior = prior

        threshold = WOOD_CONFIG["conflict_threshold"]
        is_conflict = max_conflict > threshold

        if is_conflict:
            desc = (f"认知冲突: 新证据({new_evidence_value:.4f})与先验"
                    f"{conflict_prior.key}({conflict_prior.value:.4f}, "
                    f"置信度{conflict_prior.confidence:.4f})冲突分数{max_conflict:.4f}")
        else:
            desc = f"无显著冲突(最大冲突分数{max_conflict:.4f}<阈值{threshold})"

        return is_conflict, max_conflict, desc

    def _find_related_priors(self, evidence_key: str) -> List[Prior]:
        """查找与证据相关的先验"""
        related = []
        # 精确匹配
        if evidence_key in self.priors:
            related.append(self.priors[evidence_key])
        # 前缀匹配
        for key, prior in self.priors.items():
            if key != evidence_key and (evidence_key in key or key in evidence_key):
                related.append(prior)
        # 关键词匹配
        evidence_parts = set(evidence_key.lower().split("."))
        for key, prior in self.priors.items():
            if prior not in related:
                key_parts = set(key.lower().split("."))
                if len(evidence_parts & key_parts) >= 2:
                    related.append(prior)
        return related[:10]  # 最多返回10个相关先验

    # ============ 查询函数 ============

    def get_prior(self, key: str) -> Optional[Prior]:
        """获取先验"""
        return self.priors.get(key)

    def get_prior_value(self, key: str, default: float = 0.5) -> float:
        """获取先验值"""
        prior = self.priors.get(key)
        return prior.value if prior else default

    def get_all_priors(self) -> Dict[str, Prior]:
        """获取所有先验"""
        return self.priors.copy()

    def get_priors_by_category(self, category: str) -> List[Prior]:
        """按分类获取先验"""
        return [p for p in self.priors.values() if p.category == category]

    def get_low_confidence_priors(self, threshold: float = 0.5) -> List[Prior]:
        """获取低置信度先验"""
        return [p for p in self.priors.values() if p.confidence < threshold]

    def get_stale_priors(self, max_age_days: int = None) -> List[Prior]:
        """获取过期先验"""
        max_age = max_age_days or WOOD_CONFIG["max_prior_age_days"]
        cutoff = time.time() - max_age * 86400
        return [p for p in self.priors.values() if p.last_update < cutoff and p.category != "default"]

    def get_statistics(self) -> dict:
        """获取先验库统计信息"""
        if not self.priors:
            return {"total": 0}
        values = [p.value for p in self.priors.values()]
        confidences = [p.confidence for p in self.priors.values()]
        categories = {}
        for p in self.priors.values():
            categories[p.category] = categories.get(p.category, 0) + 1
        return {
            "total": len(self.priors),
            "avg_value": sum(values) / len(values),
            "avg_confidence": sum(confidences) / len(confidences),
            "min_confidence": min(confidences),
            "max_confidence": max(confidences),
            "categories": categories,
            "low_confidence_count": len([c for c in confidences if c < 0.5]),
        }

    # ============ 持久化函数 ============

    def persist_prior(self, key: str) -> bool:
        """将单个先验持久化到真值网关
        key已经是完整格式（如PRIOR.EVOLVED.xxx），不再加前缀
        """
        prior = self.priors.get(key)
        if not prior:
            return False
        if self.gateway and self.gateway.is_online():
            return self.gateway.upsert_truth(
                key, prior.to_dict(),
                category="evolved_prior"
            )
        return False

    def persist_all(self) -> int:
        """持久化所有非默认先验"""
        success = 0
        for key, prior in self.priors.items():
            if prior.category != "default" and prior.evidence_count > 0:
                if self.persist_prior(key):
                    success += 1
        self.save_to_local()
        return success
