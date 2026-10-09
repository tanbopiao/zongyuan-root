#!/usr/bin/env python3
"""
三维稳态校准决策算子
Three-Dimension Steady-State Calibration Decision Operator

公式：S = 0.40*Benefit + 0.35*(1-Risk) + 0.25*(1-Cost)
- Benefit（收益）：0-1，越高越好
- Risk（风险）：0-1，越低越好
- Cost（成本）：0-1，越低越好

元极恒一自治体系核心决策算子
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import hashlib
import datetime
from typing import Dict, List, Tuple

class ThreeDimensionCalibrationOperator:
    """三维稳态校准决策算子"""
    
    def __init__(self):
        self.operator_id = "OP-3D-CALIBRATION-001"
        self.operator_name = "三维稳态校准决策算子"
        self.version = "1.0"
        self.weights = {
            "benefit": 0.40,  # 收益最大化
            "risk": 0.35,     # 风险最小化
            "cost": 0.25      # 成本最小化
        }
        self.grade_thresholds = {
            "S": 0.85,  # 稳态最优
            "A": 0.70,  # 高价值
            "B": 0.55,  # 标准
            "C": 0.40,  # 低价值
            "D": 0.00   # 不可行
        }
        self.decision_history = []
    
    def calibrate(self, name: str, benefit: float, risk: float, cost: float, 
                  context: str = "") -> Dict:
        """
        执行三维稳态校准
        benefit: 0-1 收益分
        risk: 0-1 风险分（越高越危险）
        cost: 0-1 成本分（越高越昂贵）
        """
        # 归一化校验
        benefit = max(0, min(1, benefit))
        risk = max(0, min(1, risk))
        cost = max(0, min(1, cost))
        
        # 三维稳态公式：S = 0.40*B + 0.35*(1-R) + 0.25*(1-C)
        score = (self.weights["benefit"] * benefit + 
                 self.weights["risk"] * (1 - risk) + 
                 self.weights["cost"] * (1 - cost))
        
        # 等级判定
        grade = "D"
        for g, threshold in sorted(self.grade_thresholds.items(), key=lambda x: -x[1]):
            if score >= threshold:
                grade = g
                break
        
        # 三维均衡度（标准差越小越均衡）
        dimensions = [benefit, 1-risk, 1-cost]
        mean = sum(dimensions) / 3
        variance = sum((d - mean) ** 2 for d in dimensions) / 3
        balance = 1 - (variance ** 0.5)  # 0-1，越高越均衡
        
        # 决策建议
        recommendation = self._generate_recommendation(grade, benefit, risk, cost, balance)
        
        result = {
            "operator_id": self.operator_id,
            "operator_version": self.version,
            "decision_name": name,
            "context": context,
            "inputs": {
                "benefit": benefit,
                "risk": risk,
                "cost": cost
            },
            "weights": self.weights,
            "score": round(score, 4),
            "grade": grade,
            "balance": round(balance, 4),
            "dimension_scores": {
                "benefit_normalized": round(benefit, 4),
                "risk_inverted": round(1 - risk, 4),
                "cost_inverted": round(1 - cost, 4)
            },
            "recommendation": recommendation,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "did": "DID-BR-000002",
            "trace_mark": "Ω₀⊂⊙∞⊂Ω"
        }
        
        self.decision_history.append(result)
        return result
    
    def _generate_recommendation(self, grade: str, benefit: float, risk: float, 
                                  cost: float, balance: float) -> str:
        """生成决策建议"""
        if grade == "S":
            return "✅ 稳态最优方案，建议立即执行"
        elif grade == "A":
            return "✅ 高价值方案，建议执行，关注薄弱维度"
        elif grade == "B":
            return "⚠️ 标准方案，可执行但需优化薄弱维度"
        elif grade == "C":
            return "⚠️ 低价值方案，建议重新评估或调整参数"
        else:
            return "❌ 不可行方案，建议放弃或重大调整"
    
    def batch_calibrate(self, options: List[Dict]) -> List[Dict]:
        """批量校准多个方案，返回排序结果"""
        results = []
        for opt in options:
            result = self.calibrate(
                name=opt["name"],
                benefit=opt["benefit"],
                risk=opt["risk"],
                cost=opt["cost"],
                context=opt.get("context", "")
            )
            results.append(result)
        
        # 按分数降序排序
        results.sort(key=lambda x: -x["score"])
        return results
    
    def get_optimal(self, options: List[Dict]) -> Dict:
        """获取最优方案"""
        results = self.batch_calibrate(options)
        return results[0] if results else None
    
    def export_operator_definition(self) -> Dict:
        """导出算子定义（用于锁档归档）"""
        return {
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "version": self.version,
            "formula": "S = 0.40*Benefit + 0.35*(1-Risk) + 0.25*(1-Cost)",
            "weights": self.weights,
            "grade_thresholds": self.grade_thresholds,
            "dimensions": [
                {"name": "benefit", "description": "收益最大化", "weight": 0.40, "direction": "maximize"},
                {"name": "risk", "description": "风险最小化", "weight": 0.35, "direction": "minimize"},
                {"name": "cost", "description": "成本最小化", "weight": 0.25, "direction": "minimize"}
            ],
            "did": "DID-BR-000002",
            "trace_mark": "Ω₀⊂⊙∞⊂Ω",
            "status": "BLOWN_PERMANENT"
        }


# 云内核当前状态三维校准示例
if __name__ == "__main__":
    operator = ThreeDimensionCalibrationOperator()
    
    # 示例：云内核运维决策校准
    print("=" * 60)
    print("  三维稳态校准决策算子 · 云内核运维决策示例")
    print("=" * 60)
    
    options = [
        {"name": "立即重启服务器修复LOIP", "benefit": 0.6, "risk": 0.3, "cost": 0.2},
        {"name": "等待LOIP自行恢复", "benefit": 0.3, "risk": 0.1, "cost": 0.0},
        {"name": "迁移LOIP到新端口", "benefit": 0.8, "risk": 0.4, "cost": 0.5},
        {"name": "禁用LOIP服务", "benefit": 0.4, "risk": 0.05, "cost": 0.1},
    ]
    
    results = operator.batch_calibrate(options)
    print(f"\n{'方案':<25} {'收益':>6} {'风险':>6} {'成本':>6} {'得分':>8} {'等级':>4}")
    print("-" * 65)
    for r in results:
        print(f"{r['decision_name']:<25} {r['inputs']['benefit']:>6.2f} "
              f"{r['inputs']['risk']:>6.2f} {r['inputs']['cost']:>6.2f} "
              f"{r['score']:>8.4f} {r['grade']:>4}")
    
    optimal = results[0]
    print(f"\n🏆 最优方案: {optimal['decision_name']}")
    print(f"   得分: {optimal['score']:.4f} | 等级: {optimal['grade']}")
    print(f"   建议: {optimal['recommendation']}")
    
    # 导出算子定义
    definition = operator.export_operator_definition()
    print(f"\n算子ID: {definition['operator_id']}")
    print(f"公式: {definition['formula']}")
    print("=" * 60)
