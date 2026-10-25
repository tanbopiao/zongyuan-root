"""
LOIP 认知漂移检测模块 v0.2
实时比对AI输出与本体基线的一致性，检测偏移并自动校准。
支持关键词匹配（默认）和语义级检测（可选sentence-transformers）。
"""
import re
from typing import Any, Dict, List, Optional, Tuple
from .baseline import OntologyBaseline
from .semantic import get_detector, BaseDetector


class DriftDetector:
    """认知漂移检测器"""

    def __init__(self, baseline: OntologyBaseline, backend: str = "auto"):
        self.baseline = baseline
        self.detector: BaseDetector = get_detector(backend)
        self.drift_history: List[Dict[str, Any]] = []
        self.consecutive_drifts: Dict[str, int] = {}

    def check(self, user_input: str, ai_output: str) -> Dict[str, Any]:
        """
        执行漂移检测
        返回: {drift_detected, conflicts, corrections, severity, drift_level}
        """
        conflicts = []
        corrections = []

        # 1. 规则冲突检测
        rule_conflicts = self._check_rule_conflicts(ai_output)
        conflicts.extend(rule_conflicts)

        # 2. 事实矛盾检测
        fact_conflicts = self._check_fact_conflicts(ai_output)
        conflicts.extend(fact_conflicts)

        # 3. 约束违反检测
        constraint_violations = self._check_constraints(user_input, ai_output)
        conflicts.extend(constraint_violations)

        # 4. 前后一致性检测（基于历史）
        consistency_issues = self._check_consistency(user_input, ai_output)
        conflicts.extend(consistency_issues)

        # 生成修正建议
        for c in conflicts:
            corrections.append(self._generate_correction(c))

        # 严重度评估
        severity = self._assess_severity(conflicts)
        drift_level = self._calculate_drift_level(conflicts)

        # 记录漂移历史
        if conflicts:
            self._record_drift(user_input, ai_output, conflicts, drift_level)

        return {
            "drift_detected": len(conflicts) > 0,
            "conflicts": conflicts,
            "corrections": corrections,
            "severity": severity,
            "drift_level": drift_level,
            "conflict_count": len(conflicts)
        }

    def _check_rule_conflicts(self, output: str) -> List[Dict[str, Any]]:
        """检测输出是否违反核心规则"""
        conflicts = []
        rules = self.baseline.get_all_rules()
        for key, rule in rules.items():
            rule_content = rule["content"]
            # 简化检测：关键词匹配 + 否定模式
            # 实际生产环境应使用语义相似度模型
            if self._contains_violation(output, rule_content):
                conflicts.append({
                    "type": "rule_violation",
                    "rule_key": key,
                    "rule": rule_content,
                    "severity": "high" if rule["weight"] >= 0.8 else "medium"
                })
        return conflicts

    def _check_fact_conflicts(self, output: str) -> List[Dict[str, Any]]:
        """检测输出是否与事实标准矛盾"""
        conflicts = []
        facts = self.baseline.data.get("facts", {})
        for key, fact in facts.items():
            # 简化矛盾检测：提取事实中的关键实体，检查输出中是否有相反表述
            if self._contains_contradiction(output, fact["content"]):
                conflicts.append({
                    "type": "fact_contradiction",
                    "fact_key": key,
                    "fact": fact["content"],
                    "confidence": fact["confidence"],
                    "severity": "high" if fact["confidence"] >= 0.9 else "medium"
                })
        return conflicts

    def _check_constraints(self, user_input: str, output: str) -> List[Dict[str, Any]]:
        """检测是否违反逻辑底线约束"""
        violations = []
        constraints = self.baseline.get_constraints(level="hard")
        for c in constraints:
            if self._violates_constraint(user_input, output, c["content"]):
                violations.append({
                    "type": "constraint_violation",
                    "constraint": c["content"],
                    "level": c["level"],
                    "severity": "critical"
                })
        return violations

    def _check_consistency(self, user_input: str, output: str) -> List[Dict[str, Any]]:
        """检测与历史输出的前后一致性"""
        issues = []
        # 简化实现：检查本次输出与最近漂移记录的关联
        # 实际应维护对话历史并做语义比对
        return issues

    def _contains_violation(self, output: str, rule: str) -> bool:
        """规则违反检测（支持关键词和语义级检测）"""
        is_violation, confidence = self.detector.check_violation(output, rule)
        return is_violation and confidence > 0.5

    def _contains_contradiction(self, output: str, fact: str) -> bool:
        """事实矛盾检测（支持关键词和NLI语义检测）"""
        is_contradiction, confidence = self.detector.check_contradiction(output, fact)
        return is_contradiction and confidence > 0.5

    def _violates_constraint(self, user_input: str, output: str, constraint: str) -> bool:
        """简化的约束违反检测"""
        return False

    def _generate_correction(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """生成修正建议"""
        correction_map = {
            "rule_violation": f"输出违反规则 '{conflict.get('rule_key')}'，应遵循：{conflict.get('rule')}",
            "fact_contradiction": f"输出与事实 '{conflict.get('fact_key')}' 矛盾，正确事实为：{conflict.get('fact')}",
            "constraint_violation": f"输出违反底线约束：{conflict.get('constraint')}，必须修正"
        }
        return {
            "conflict_type": conflict["type"],
            "suggestion": correction_map.get(conflict["type"], "需要修正"),
            "action": "auto_calibrate" if conflict["severity"] != "critical" else "block_output"
        }

    def _assess_severity(self, conflicts: List[Dict[str, Any]]) -> str:
        """评估整体严重度"""
        if not conflicts:
            return "none"
        severities = [c["severity"] for c in conflicts]
        if "critical" in severities:
            return "critical"
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        return "low"

    def _calculate_drift_level(self, conflicts: List[Dict[str, Any]]) -> float:
        """计算漂移等级（0-1）"""
        if not conflicts:
            return 0.0
        severity_weights = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.2}
        total = sum(severity_weights.get(c["severity"], 0.3) for c in conflicts)
        return min(total / 5.0, 1.0)  # 归一化到0-1

    def _record_drift(self, user_input: str, ai_output: str,
                      conflicts: List[Dict[str, Any]], drift_level: float):
        """记录漂移事件"""
        entry = {
            "timestamp": self.baseline._now(),
            "user_input": user_input[:200],
            "ai_output": ai_output[:200],
            "conflict_count": len(conflicts),
            "drift_level": drift_level,
            "conflict_types": [c["type"] for c in conflicts]
        }
        self.drift_history.append(entry)
        # 连续漂移计数
        for c in conflicts:
            key = c["type"]
            self.consecutive_drifts[key] = self.consecutive_drifts.get(key, 0) + 1
            if self.consecutive_drifts[key] >= 3:
                entry["alert"] = f"连续3次{key}漂移，触发告警"

    def get_drift_stats(self) -> Dict[str, Any]:
        """获取漂移统计"""
        total = len(self.drift_history)
        by_type = {}
        for d in self.drift_history:
            for t in d["conflict_types"]:
                by_type[t] = by_type.get(t, 0) + 1
        return {
            "total_drifts": total,
            "drifts_by_type": by_type,
            "consecutive_alerts": {k: v for k, v in self.consecutive_drifts.items() if v >= 3},
            "recent_drifts": self.drift_history[-10:]
        }

    def reset_consecutive_counter(self, drift_type: str):
        """重置某类漂移的连续计数（校准成功后调用）"""
        self.consecutive_drifts[drift_type] = 0
