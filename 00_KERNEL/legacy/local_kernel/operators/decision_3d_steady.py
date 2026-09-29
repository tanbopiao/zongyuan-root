"""
三维稳态校准决策算子 - ZONGYUAN-ROOT 算子化架构

基于元极恒一三维稳态决策公式：
    收益最大化(40%) + 风险最小化(35%) + 成本最小化(25%)

核心公式：
    score = 0.4 × benefit - 0.35 × risk - 0.25 × cost

功能：
    1. 多方案三维评分
    2. 综合排序
    3. 最优方案推荐
    4. 权重敏感性分析
    5. 决策凭证生成（可锁档Merkle-DAG）

溯源标识：Ω₀⊂⊙∞⊂Ω
确权编码：DID-BR-000002
根挂载：ZONGYUAN-ROOT V1.7
算子ID：OP-DECISION-3D-STEADY-001
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from operator_base import BaseOperator, OperatorMetadata


class Decision3DSteadyOperator(BaseOperator):
    """
    三维稳态校准决策算子

    输入格式：
        {
            "question": "决策问题描述",
            "options": [
                {
                    "name": "方案名称",
                    "description": "方案描述",
                    "benefit": 0.8,   # 收益 0-1，越高越好
                    "risk": 0.2,      # 风险 0-1，越低越好
                    "cost": 0.3       # 成本 0-1，越低越好
                },
                ...
            ],
            "weights": {          # 可选，自定义权重
                "benefit": 0.4,
                "risk": 0.35,
                "cost": 0.25
            }
        }

    输出格式：
        {
            "question": "...",
            "weights": {"benefit": 0.4, "risk": 0.35, "cost": 0.25},
            "scored_options": [
                {"name": "...", "benefit": 0.8, "risk": 0.2, "cost": 0.3,
                 "score": 0.265, "rank": 1},
                ...
            ],
            "recommended": {...},
            "sensitivity": {...},
            "decision_record": {...}
        }
    """

    DEFAULT_WEIGHTS = {"benefit": 0.4, "risk": 0.35, "cost": 0.25}

    def __init__(self):
        metadata = OperatorMetadata(
            operator_id="OP-DECISION-3D-STEADY-001",
            operator_name="三维稳态校准决策算子",
            version="1.0.0",
            description="基于收益最大化(40%)、风险最小化(35%)、成本最小化(25%)三维稳态公式，对多方案进行评分、排序、推荐和敏感性分析",
            category="decision",
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            inputs_schema={
                "question": "string - 决策问题描述",
                "options": "array - 方案列表，每个方案含name/benefit/risk/cost(0-1)",
                "weights": "object - 可选，自定义权重"
            },
            outputs_schema={
                "scored_options": "array - 评分排序后的方案列表",
                "recommended": "object - 推荐方案",
                "sensitivity": "object - 权重敏感性分析",
                "decision_record": "object - 决策凭证（可锁档）"
            }
        )
        super().__init__(metadata)

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """输入校验"""
        if "options" not in inputs or not isinstance(inputs["options"], list):
            return False
        if len(inputs["options"]) == 0:
            return False
        for opt in inputs["options"]:
            if not all(k in opt for k in ["name", "benefit", "risk", "cost"]):
                return False
            for k in ["benefit", "risk", "cost"]:
                if not isinstance(opt[k], (int, float)) or not (0 <= opt[k] <= 1):
                    return False
        return True

    def _compute_score(self, benefit: float, risk: float, cost: float,
                       weights: Dict[str, float]) -> float:
        """计算三维稳态综合评分"""
        return round(
            weights["benefit"] * benefit
            - weights["risk"] * risk
            - weights["cost"] * cost,
            6
        )

    def _sensitivity_analysis(self, options: List[Dict],
                               base_weights: Dict[str, float]) -> Dict[str, Any]:
        """
        权重敏感性分析
        在±20%范围内调整每个权重，观察排名变化
        """
        sensitivity = {"base_weights": base_weights, "scenarios": [], "rank_stability": {}}

        # 基准排名
        base_scores = [(opt["name"], self._compute_score(
            opt["benefit"], opt["risk"], opt["cost"], base_weights)) for opt in options]
        base_ranking = [name for name, _ in sorted(base_scores, key=lambda x: -x[1])]

        for opt in options:
            sensitivity["rank_stability"][opt["name"]] = {
                "base_rank": base_ranking.index(opt["name"]) + 1,
                "rank_changes": 0,
                "best_rank": len(options),
                "worst_rank": 1
            }

        # 生成权重变化场景（每个维度±20%，共7个场景）
        scenarios = []
        for dim in ["benefit", "risk", "cost"]:
            for delta in [-0.2, 0.2]:
                w = dict(base_weights)
                w[dim] = round(base_weights[dim] * (1 + delta), 4)
                # 归一化
                total = sum(w.values())
                w = {k: round(v / total, 4) for k, v in w.items()}
                scenarios.append({"name": f"{dim}_{'+' if delta > 0 else ''}{int(delta*100)}%", "weights": w})

        for scenario in scenarios:
            scores = [(opt["name"], self._compute_score(
                opt["benefit"], opt["risk"], opt["cost"], scenario["weights"])) for opt in options]
            ranking = [name for name, _ in sorted(scores, key=lambda x: -x[1])]
            scenario["ranking"] = ranking
            scenario["top"] = ranking[0]
            sensitivity["scenarios"].append(scenario)

            # 统计排名变化
            for opt in options:
                new_rank = ranking.index(opt["name"]) + 1
                stability = sensitivity["rank_stability"][opt["name"]]
                if new_rank != stability["base_rank"]:
                    stability["rank_changes"] += 1
                stability["best_rank"] = min(stability["best_rank"], new_rank)
                stability["worst_rank"] = max(stability["worst_rank"], new_rank)

        # 推荐方案稳定性
        top_counts = {}
        for scenario in sensitivity["scenarios"]:
            top = scenario["top"]
            top_counts[top] = top_counts.get(top, 0) + 1
        sensitivity["recommendation_stability"] = {
            "most_stable": max(top_counts, key=top_counts.get) if top_counts else None,
            "scenario_count": len(scenarios),
            "top_counts": top_counts
        }

        return sensitivity

    def _generate_decision_record(self, question: str, weights: Dict[str, float],
                                   scored_options: List[Dict],
                                   recommended: Dict) -> Dict[str, Any]:
        """生成决策凭证（可锁档Merkle-DAG）"""
        record = {
            "decision_id": f"DEC-{time.strftime('%Y%m%d%H%M%S')}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "formula": "score = 0.4×benefit - 0.35×risk - 0.25×cost",
            "weights": weights,
            "options_count": len(scored_options),
            "recommended": {
                "name": recommended["name"],
                "score": recommended["score"],
                "benefit": recommended["benefit"],
                "risk": recommended["risk"],
                "cost": recommended["cost"]
            },
            "all_ranking": [{"rank": o["rank"], "name": o["name"], "score": o["score"]}
                            for o in scored_options],
            "trace_symbol": "Ω₀⊂⊙∞⊂Ω",
            "did": "DID-BR-000002",
            "operator": "OP-DECISION-3D-STEADY-001"
        }
        # 计算凭证哈希
        record["hash"] = hashlib.sha256(
            json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return record

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """算子核心执行逻辑"""
        question = inputs.get("question", "未命名决策问题")
        options = inputs["options"]
        weights = inputs.get("weights", dict(self.DEFAULT_WEIGHTS))

        # 校验权重和为1
        weight_sum = sum(weights.values())
        if abs(weight_sum - 1.0) > 0.01:
            # 归一化
            weights = {k: round(v / weight_sum, 4) for k, v in weights.items()}

        # 1. 计算每个方案的三维评分
        scored = []
        for opt in options:
            score = self._compute_score(opt["benefit"], opt["risk"], opt["cost"], weights)
            scored.append({
                "name": opt["name"],
                "description": opt.get("description", ""),
                "benefit": opt["benefit"],
                "risk": opt["risk"],
                "cost": opt["cost"],
                "score": score,
                "benefit_contribution": round(weights["benefit"] * opt["benefit"], 4),
                "risk_penalty": round(weights["risk"] * opt["risk"], 4),
                "cost_penalty": round(weights["cost"] * opt["cost"], 4)
            })

        # 2. 排序
        scored.sort(key=lambda x: -x["score"])
        for i, opt in enumerate(scored):
            opt["rank"] = i + 1

        # 3. 推荐最优方案
        recommended = scored[0]

        # 4. 敏感性分析
        sensitivity = self._sensitivity_analysis(options, weights)

        # 5. 生成决策凭证
        decision_record = self._generate_decision_record(question, weights, scored, recommended)

        return {
            "question": question,
            "weights": weights,
            "formula": "score = benefit×Wb - risk×Wr - cost×Wc",
            "scored_options": scored,
            "recommended": recommended,
            "sensitivity": sensitivity,
            "decision_record": decision_record
        }


# 算子注册实例
decision_3d_steady = Decision3DSteadyOperator()


if __name__ == "__main__":
    # 自测：本地内核优化方案决策
    test_inputs = {
        "question": "本地内核内存优化方案选择",
        "options": [
            {"name": "升级内存到16GB", "description": "硬件升级，根本解决",
             "benefit": 0.95, "risk": 0.1, "cost": 0.8},
            {"name": "Ollama模型按需加载", "description": "不常驻内存，用时加载",
             "benefit": 0.7, "risk": 0.2, "cost": 0.2},
            {"name": "关闭非必要后台进程", "description": "释放DoubaoWork等进程内存",
             "benefit": 0.5, "risk": 0.4, "cost": 0.1},
            {"name": "增加虚拟内存页面文件", "description": "用磁盘空间扩展内存",
             "benefit": 0.3, "risk": 0.15, "cost": 0.05}
        ]
    }

    result = decision_3d_steady(test_inputs)
    print(f"决策问题: {result.data['question']}")
    print(f"权重: {result.data['weights']}")
    print(f"\n方案排名:")
    for opt in result.data["scored_options"]:
        print(f"  #{opt['rank']} {opt['name']}: score={opt['score']:.4f} "
              f"(收益{opt['benefit']}/风险{opt['risk']}/成本{opt['cost']})")
    print(f"\n推荐方案: {result.data['recommended']['name']} "
          f"(score={result.data['recommended']['score']:.4f})")
    print(f"\n敏感性分析:")
    print(f"  推荐稳定性: {result.data['sensitivity']['recommendation_stability']}")
    print(f"\n决策凭证: {result.data['decision_record']['decision_id']}")
    print(f"凭证哈希: {result.data['decision_record']['hash'][:16]}...")
    print(f"\n算子状态: {decision_3d_steady.get_stats()}")
