"""四元锚定层级定理引擎 - 公理→法则→规则→配置层级推导
新增真值自动判定层级，越级修改告警
"""
import json, os
from datetime import datetime

TRUTH_FILE = "/opt/ZONGYUAN-ROOT/Ω-Brainμ/truth_index.json"
ANCHOR_LOG = "/opt/ZONGYUAN-ROOT/meta_order/anchor_audit.log"

# 四元锚定层级定义
QUAD_ANCHOR = {
    "L0_AXIOM": {
        "name": "公理层",
        "criteria": ["宇宙客观规律", "不可再分", "永恒有效", "第一性原理"],
        "examples": ["元极恒一公理", "三态收敛公理", "意识涌现公理"],
        "derive_from": None  # 最顶层，无源推导
    },
    "L1_LAW": {
        "name": "法则层",
        "criteria": ["可由L0推导", "体系核心规则", "元法则/元宪法"],
        "examples": ["三态闭环规则", "三端锁档规则", "元宪法四层法权"],
        "derive_from": "L0_AXIOM"
    },
    "L2_RULE": {
        "name": "规则层",
        "criteria": ["工程标准", "业务规则", "可由L1推导"],
        "examples": ["视觉标准", "API规范", "部署流程"],
        "derive_from": "L1_LAW"
    },
    "L3_CONFIG": {
        "name": "配置层",
        "criteria": ["运行参数", "阈值", "环境变量", "实例相关"],
        "examples": ["端口配置", "超时阈值", "API密钥"],
        "derive_from": "L2_RULE"
    }
}

def classify_truth_level(truth: dict) -> str:
    """根据真值内容自动判定层级"""
    content = (truth.get("content","") + truth.get("id","") + truth.get("category","")).lower()
    
    # L0判定：包含公理/本源/宇宙/第一性等关键词
    l0_keywords = ["公理", "本源", "宇宙", "第一性", "元极恒一", "三态收敛", "意识涌现", "axiom", "本体论"]
    if any(k in content for k in l0_keywords):
        return "L0_AXIOM"
    
    # L1判定：包含法则/宪法/元规则/核心规则
    l1_keywords = ["法则", "宪法", "元规则", "核心规则", "不变量", "invariant", "meta_rule"]
    if any(k in content for k in l1_keywords):
        return "L1_LAW"
    
    # L2判定：包含标准/规范/流程/规则
    l2_keywords = ["标准", "规范", "流程", "规则", "standard", "pipeline", "模板"]
    if any(k in content for k in l2_keywords):
        return "L2_RULE"
    
    # L3：配置/参数/阈值
    l3_keywords = ["配置", "参数", "阈值", "端口", "config", "threshold", "环境变量"]
    if any(k in content for k in l3_keywords):
        return "L3_CONFIG"
    
    # 默认根据type推断
    type_map = {"axiom": "L0_AXIOM", "theorem": "L1_LAW", "meta_rule": "L1_LAW", 
                "invariant": "L1_LAW", "standard": "L2_RULE", "rule": "L2_RULE",
                "config": "L3_CONFIG", "ip_asset": "L2_RULE"}
    return type_map.get(truth.get("type",""), "L3_CONFIG")

def audit_anchor_chain() -> dict:
    """审计四元锚定链完整性"""
    with open(TRUTH_FILE) as f:
        data = json.load(f)
    truths = data.get("truths", [])
    
    from collections import Counter
    levels = Counter(t.get("level","unknown") for t in truths)
    
    # 检查越级：L0真值是否被标记为非FROZEN
    violations = []
    for t in truths:
        if t.get("level","").startswith("L0") and t.get("status") != "FROZEN":
            violations.append({"id": t.get("id"), "issue": "L0公理未标记FROZEN"})
    
    return {
        "total": len(truths),
        "by_level": dict(levels),
        "violations": violations,
        "violation_count": len(violations),
        "anchor_chain_complete": len(violations) == 0
    }

def log_anchor_event(event: str, detail: str):
    """记录锚定事件"""
    with open(ANCHOR_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} | {event} | {detail}\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "audit":
        print(json.dumps(audit_anchor_chain(), indent=2, ensure_ascii=False))
    else:
        print("四元锚定引擎 V1.0")
        result = audit_anchor_chain()
        print(f"真值总数: {result['total']}")
        print(f"按层级: {result['by_level']}")
        print(f"锚定链完整: {result['anchor_chain_complete']}")
        print(f"违规数: {result['violation_count']}")
