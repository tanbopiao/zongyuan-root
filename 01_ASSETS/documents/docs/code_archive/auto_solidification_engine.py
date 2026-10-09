#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 高价值成果自动识别与固化引擎 V1.0
自动判断成果价值，超过阈值自动固化，无需人工指令
"""
import json, os, hashlib, subprocess
from datetime import datetime

# 价值评估五维体系
VALUE_DIMENSIONS = {
    "strategic_value": {
        "name": "战略价值",
        "weight": 0.30,
        "description": "对体系长期战略方向的影响程度",
        "indicators": ["是否涉及核心架构", "是否影响元法则", "是否改变体系范式"]
    },
    "reusability": {
        "name": "可复用性",
        "weight": 0.20,
        "description": "被其他模块/节点复用的可能性",
        "indicators": ["是否通用", "是否标准化", "是否可跨场景应用"]
    },
    "irreplaceability": {
        "name": "不可替代性",
        "weight": 0.20,
        "description": "失去后对体系的影响程度",
        "indicators": ["是否唯一", "是否核心依赖", "重建成本"]
    },
    "system_contribution": {
        "name": "体系贡献度",
        "weight": 0.20,
        "description": "对当前体系运行效率/稳定性的提升",
        "indicators": ["是否提升效率", "是否增强稳定性", "是否填补空白"]
    },
    "evolution_potential": {
        "name": "进化潜力",
        "weight": 0.10,
        "description": "未来可扩展/进化的空间",
        "indicators": ["是否可扩展", "是否可迭代", "是否有衍生能力"]
    }
}

# 自动固化阈值
AUTO_LOCK_THRESHOLD = 75  # 价值评分>=75自动固化
MANUAL_REVIEW_THRESHOLD = 50  # 50-75需人工审核
HIGH_PRIORITY_THRESHOLD = 90  # >=90最高优先级固化

class AutoSolidificationEngine:
    """高价值成果自动识别与固化引擎"""

    def __init__(self):
        self.state_file = "/opt/ZONGYUAN-ROOT/data/auto_solidification_state.json"
        self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file) as f:
                self.state = json.load(f)
        else:
            self.state = {"solidified_assets": [], "pending_review": [], "evaluation_log": []}

    def save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def evaluate_value(self, asset_name, asset_type, asset_description, scores=None):
        """评估成果价值（五维评分）"""
        if scores is None:
            # 基于资产类型和描述的启发式评分
            scores = self._heuristic_score(asset_name, asset_type, asset_description)

        total = 0
        dimension_scores = {}
        for dim_id, dim in VALUE_DIMENSIONS.items():
            score = scores.get(dim_id, 50)
            dimension_scores[dim_id] = score
            total += score * dim["weight"]

        result = {
            "asset_name": asset_name,
            "asset_type": asset_type,
            "asset_description": asset_description,
            "total_score": round(total, 2),
            "dimension_scores": dimension_scores,
            "evaluated_at": datetime.now().isoformat(),
            "auto_lock_eligible": total >= AUTO_LOCK_THRESHOLD,
            "manual_review_eligible": MANUAL_REVIEW_THRESHOLD <= total < AUTO_LOCK_THRESHOLD,
            "high_priority": total >= HIGH_PRIORITY_THRESHOLD
        }

        self.state["evaluation_log"].append(result)
        self.save_state()
        return result

    def _heuristic_score(self, name, asset_type, description):
        """启发式评分（基于关键词和类型）"""
        scores = {}
        text = (name + " " + asset_type + " " + description).lower()

        # 战略价值关键词
        strategic_keywords = ["元法则", "基准", "基底", "架构", "协议", "中枢", "元极恒一", "自治", "宪法", "公理"]
        strategic = 50 + sum(20 for kw in strategic_keywords if kw in text)
        scores["strategic_value"] = min(100, strategic)

        # 可复用性
        reuse_keywords = ["框架", "引擎", "标准", "规范", "通用", "模板", "sop", "协议"]
        reuse = 50 + sum(15 for kw in reuse_keywords if kw in text)
        scores["reusability"] = min(100, reuse)

        # 不可替代性
        irreplace_keywords = ["唯一", "核心", "关键", "基底", "根", "锚点", "确权"]
        irreplace = 50 + sum(15 for kw in irreplace_keywords if kw in text)
        scores["irreplaceability"] = min(100, irreplace)

        # 体系贡献度
        contrib_keywords = ["提升", "优化", "修复", "增强", "完善", "打通", "闭环", "解决"]
        contrib = 50 + sum(10 for kw in contrib_keywords if kw in text)
        scores["system_contribution"] = min(100, contrib)

        # 进化潜力
        evol_keywords = ["可扩展", "可迭代", "进化", "自", "递归", "衍生", "框架"]
        evol = 50 + sum(10 for kw in evol_keywords if kw in text)
        scores["evolution_potential"] = min(100, evol)

        return scores

    def solidify(self, evaluation_result, file_path=None):
        """自动固化成果"""
        if not evaluation_result["auto_lock_eligible"]:
            return {"error": "价值评分不足，不满足自动固化条件", "threshold": AUTO_LOCK_THRESHOLD}

        solidification = {
            "asset_name": evaluation_result["asset_name"],
            "asset_type": evaluation_result["asset_type"],
            "value_score": evaluation_result["total_score"],
            "dimension_scores": evaluation_result["dimension_scores"],
            "solidified_at": datetime.now().isoformat(),
            "solidification_id": "AUTO-SOLID-" + datetime.now().strftime("%Y%m%d%H%M%S"),
            "steps": []
        }

        # 步骤1: 写入9120真值
        try:
            import requests
            payload = {
                "key": "SOLIDIFIED." + evaluation_result["asset_name"].replace(" ", ".").upper(),
                "value": json.dumps(evaluation_result, ensure_ascii=False),
                "type": "solidified_asset",
                "source_node": "auto-solidification-engine",
                "confidence": 0.95
            }
            r = requests.post("http://127.0.0.1:9120/api/truth/upsert", json=payload, timeout=10)
            if r.json().get("success"):
                solidification["steps"].append("✅ 写入9120真值")
            else:
                solidification["steps"].append("⚠️ 9120写入失败")
        except Exception as e:
            solidification["steps"].append("⚠️ 9120写入异常: " + str(e))

        # 步骤2: 文件锁定（如果提供了文件路径）
        if file_path and os.path.exists(file_path):
            try:
                subprocess.run(["chattr", "+i", file_path], capture_output=True)
                solidification["steps"].append("✅ 文件chattr +i锁定: " + file_path)
            except:
                solidification["steps"].append("⚠️ 文件锁定失败")

        # 步骤3: 登记台账
        self.state["solidified_assets"].append(solidification)
        self.save_state()
        solidification["steps"].append("✅ 登记固化台账")

        return solidification

    def get_status(self):
        """获取引擎状态"""
        return {
            "total_evaluated": len(self.state["evaluation_log"]),
            "total_solidified": len(self.state["solidified_assets"]),
            "pending_review": len(self.state["pending_review"]),
            "auto_lock_threshold": AUTO_LOCK_THRESHOLD,
            "high_priority_threshold": HIGH_PRIORITY_THRESHOLD,
            "recent_solidified": self.state["solidified_assets"][-5:] if self.state["solidified_assets"] else []
        }


if __name__ == "__main__":
    import sys
    engine = AutoSolidificationEngine()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            print(json.dumps(engine.get_status(), indent=2, ensure_ascii=False))
        elif cmd == "evaluate" and len(sys.argv) > 4:
            name = sys.argv[2]
            atype = sys.argv[3]
            desc = sys.argv[4]
            result = engine.evaluate_value(name, atype, desc)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif cmd == "solidify" and len(sys.argv) > 4:
            name = sys.argv[2]
            atype = sys.argv[3]
            desc = sys.argv[4]
            file_path = sys.argv[5] if len(sys.argv) > 5 else None
            result = engine.evaluate_value(name, atype, desc)
            if result["auto_lock_eligible"]:
                solid = engine.solidify(result, file_path)
                print(json.dumps(solid, indent=2, ensure_ascii=False))
            else:
                print("价值评分 " + str(result["total_score"]) + " 不足，不满足自动固化条件(需>=" + str(AUTO_LOCK_THRESHOLD) + ")")
    else:
        print(json.dumps(engine.get_status(), indent=2, ensure_ascii=False))
