#!/usr/bin/env python3
"""
自主决策引擎 V1.0
基于三维稳态决策公式（利益40%/风险35%/成本25%）自动决策
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json, os, time, hashlib
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

@dataclass
class DecisionOption:
    name: str
    benefit: float      # 利益 0-1
    risk: float         # 风险 0-1 (越低越好)
    cost: float         # 成本 0-1 (越低越好)
    description: str = ""

@dataclass
class DecisionResult:
    decision_id: str
    question: str
    options: List[Dict]
    scores: Dict[str, float]
    recommended: str
    auto_approved: bool
    threshold: float
    timestamp: int
    did: str = "DID-BR-000002"

class AutonomousDecisionEngine:
    def __init__(self, db_path=None):
        self.benefit_weight = 0.40
        self.risk_weight = 0.35
        self.cost_weight = 0.25
        self.auto_approve_threshold = 0.75
        self.human_review_threshold = 0.50
        self.history_path = os.path.expanduser("~/.zongyuan_root/decisions/decision_history.json")
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
        self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_path):
            with open(self.history_path) as f:
                self.history = json.load(f)
        else:
            self.history = {"decisions": [], "stats": {"total": 0, "auto_approved": 0, "human_review": 0}}

    def _save_history(self):
        with open(self.history_path, 'w') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def score_option(self, option: DecisionOption) -> float:
        """三维稳态评分：利益*0.4 + (1-风险)*0.35 + (1-成本)*0.25"""
        score = (option.benefit * self.benefit_weight +
                 (1 - option.risk) * self.risk_weight +
                 (1 - option.cost) * self.cost_weight)
        return round(score, 4)

    def decide(self, question: str, options: List[DecisionOption]) -> DecisionResult:
        """执行自主决策"""
        scores = {}
        for opt in options:
            scores[opt.name] = self.score_option(opt)

        recommended = max(scores, key=scores.get)
        best_score = scores[recommended]
        auto_approved = best_score >= self.auto_approve_threshold

        decision_id = f"DEC-{int(time.time())}-{hashlib.md5(question.encode()).hexdigest()[:6]}"

        result = DecisionResult(
            decision_id=decision_id,
            question=question,
            options=[asdict(o) for o in options],
            scores=scores,
            recommended=recommended,
            auto_approved=auto_approved,
            threshold=self.auto_approve_threshold,
            timestamp=int(time.time())
        )

        # 记录历史
        self.history["decisions"].append(asdict(result))
        self.history["stats"]["total"] += 1
        if auto_approved:
            self.history["stats"]["auto_approved"] += 1
        elif best_score < self.human_review_threshold:
            self.history["stats"]["human_review"] += 1
        self._save_history()

        return result

    def batch_decide(self, tasks: List[Dict]) -> List[DecisionResult]:
        """批量决策"""
        results = []
        for task in tasks:
            options = [DecisionOption(**o) for o in task["options"]]
            results.append(self.decide(task["question"], options))
        return results

    def get_stats(self) -> Dict:
        return self.history["stats"]

    def get_recent_decisions(self, n=10) -> List[Dict]:
        return self.history["decisions"][-n:]


if __name__ == "__main__":
    engine = AutonomousDecisionEngine()

    # 测试：破局作战任务优先级决策
    print("=== 自主决策引擎 V1.0 测试 ===")
    print(f"公式: 利益40% + 风险35% + 成本25%")
    print(f"自动通过阈值: {engine.auto_approve_threshold}")
    print()

    tasks = [
        {
            "question": "破局作战P0任务优先级排序",
            "options": [
                {"name": "T0短剧视频合成", "benefit": 0.85, "risk": 0.6, "cost": 0.7, "description": "需付费额度"},
                {"name": "T1平台API后端部署", "benefit": 0.9, "risk": 0.3, "cost": 0.4, "description": "中枢执行"},
                {"name": "T2短视频素材包", "benefit": 0.6, "risk": 0.2, "cost": 0.3, "description": "本地可做"},
                {"name": "T3教育课程生产", "benefit": 0.7, "risk": 0.1, "cost": 0.2, "description": "静默生产"},
            ]
        },
        {
            "question": "知识图谱进化方向选择",
            "options": [
                {"name": "图谱降噪+关系推理", "benefit": 0.8, "risk": 0.15, "cost": 0.2},
                {"name": "社区发现+子图识别", "benefit": 0.65, "risk": 0.2, "cost": 0.3},
                {"name": "可视化网页开发", "benefit": 0.55, "risk": 0.1, "cost": 0.25},
            ]
        },
    ]

    for task in tasks:
        options = [DecisionOption(**o) for o in task["options"]]
        result = engine.decide(task["question"], options)
        print(f"【{result.question}】")
        for name, score in sorted(result.scores.items(), key=lambda x: -x[1]):
            marker = " ← 推荐" if name == result.recommended else ""
            auto = " [自动通过]" if result.auto_approved and name == result.recommended else ""
            print(f"  {name}: {score}{marker}{auto}")
        print()

    print(f"=== 决策统计 ===")
    stats = engine.get_stats()
    print(f"总决策数: {stats['total']}")
    print(f"自动通过: {stats['auto_approved']}")
    print(f"人工审核: {stats['human_review']}")
    print(f"自动通过率: {stats['auto_approved']/max(stats['total'],1)*100:.1f}%")
