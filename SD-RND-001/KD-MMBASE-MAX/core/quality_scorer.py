"""MM-QUALITY 质量评分引擎 · M2单调收敛联动"""
from typing import Dict, Any

class QualityScorer:
    def __init__(self, config: Dict):
        self.min_score = config.get("quality_min", 4.5)

    def score(self, result: Dict, drift: Dict) -> Dict[str, Any]:
        base = 4.8 if result.get("status", "success") == "success" else 3.0
        drift_penalty = 0.5 if not drift.get("all_pass", True) else 0.0
        final = max(1.0, min(5.0, base - drift_penalty))
        return {
            "score": round(final, 2),
            "pass": final >= self.min_score,
            "m2_convergence": "converging" if final >= self.min_score else "diverging",
            "min_threshold": self.min_score,
        }
