"""
节点晋升机制
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

信任等级晋升规则：
UNTRUSTED → OBSERVER → TRUSTED → HOMOGENEOUS
"""
from datetime import datetime, timedelta
from enum import Enum


class TrustLevel(Enum):
    UNTRUSTED = 0
    OBSERVER = 1
    TRUSTED = 2
    HOMOGENEOUS = 3


# 晋升条件
PROMOTION_RULES = {
    TrustLevel.UNTRUSTED: {
        "min_days": 7,           # 最少观察天数
        "min_heartbeat": 50,     # 最少心跳次数
        "min_credit_score": 80,  # 最低信用分
        "max_anomalies": 3,      # 最多异常次数
        "target_level": TrustLevel.OBSERVER
    },
    TrustLevel.OBSERVER: {
        "min_days": 14,
        "min_heartbeat": 200,
        "min_credit_score": 85,
        "max_anomalies": 2,
        "target_level": TrustLevel.TRUSTED
    },
    TrustLevel.TRUSTED: {
        "min_days": 30,
        "min_heartbeat": 500,
        "min_credit_score": 90,
        "max_anomalies": 1,
        "target_level": TrustLevel.HOMOGENEOUS
    }
}


class NodePromotion:
    """节点晋升评估器"""

    def __init__(self):
        self.rules = PROMOTION_RULES

    def evaluate(self, node_info: dict) -> dict:
        """
        评估节点是否满足晋升条件

        Args:
            node_info: 节点信息，包含：
                - trust_level: 当前信任等级
                - registered_at: 注册时间
                - heartbeat_count: 心跳次数
                - credit_score: 信用分
                - anomaly_count: 异常次数

        Returns:
            评估结果
        """
        current_level = TrustLevel(node_info.get("trust_level", 0))

        if current_level == TrustLevel.HOMOGENEOUS:
            return {
                "eligible": False,
                "reason": "已达到最高信任等级",
                "current_level": current_level.name
            }

        rule = self.rules.get(current_level)
        if not rule:
            return {"eligible": False, "reason": "无晋升规则"}

        # 计算已运行天数
        registered_at = datetime.fromisoformat(node_info.get("registered_at", datetime.now().isoformat()))
        days = (datetime.now() - registered_at).days

        checks = {
            "days_ok": days >= rule["min_days"],
            "heartbeat_ok": node_info.get("heartbeat_count", 0) >= rule["min_heartbeat"],
            "credit_ok": node_info.get("credit_score", 0) >= rule["min_credit_score"],
            "anomaly_ok": node_info.get("anomaly_count", 0) <= rule["max_anomalies"]
        }

        eligible = all(checks.values())

        return {
            "eligible": eligible,
            "current_level": current_level.name,
            "target_level": rule["target_level"].name,
            "checks": checks,
            "details": {
                "current_days": days,
                "required_days": rule["min_days"],
                "current_heartbeats": node_info.get("heartbeat_count", 0),
                "required_heartbeats": rule["min_heartbeat"],
                "current_credit": node_info.get("credit_score", 0),
                "required_credit": rule["min_credit_score"]
            }
        }

    def auto_promote(self, node_info: dict) -> dict:
        """自动晋升"""
        result = self.evaluate(node_info)
        if result["eligible"]:
            node_info["trust_level"] = result["target_level"]
            node_info["promoted_at"] = datetime.now().isoformat()
            node_info["promoted_from"] = result["current_level"]
            return {
                "promoted": True,
                "from": result["current_level"],
                "to": result["target_level"],
                "node": node_info
            }
        return {"promoted": False, "reason": result.get("reason", "不满足条件")}


# 使用示例
if __name__ == "__main__":
    evaluator = NodePromotion()

    # 测试一个UNTRUSTED节点
    test_node = {
        "trust_level": 0,  # UNTRUSTED
        "registered_at": (datetime.now() - timedelta(days=10)).isoformat(),
        "heartbeat_count": 80,
        "credit_score": 85,
        "anomaly_count": 1
    }

    result = evaluator.evaluate(test_node)
    print(f"评估结果: {result}")
