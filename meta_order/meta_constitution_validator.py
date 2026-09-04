"""元宪法四层法权校验器 - 立法权落地
每次真值写入前自动校验，L0公理修改自动拒绝
"""
import json, hashlib, os
from datetime import datetime

META_CONSTITUTION = {
    "L0_AXIOM": {
        "modifiable": False,
        "approver": "元极恒一",
        "description": "宇宙客观规律/本源公理，禁止任何修改",
        "violation_penalty": "P0_BLOCK"
    },
    "L1_LAW": {
        "modifiable": "incremental_patch_only",
        "approver": "元宪法审批",
        "description": "元法则/元宪法/核心规则，仅允许增量补丁",
        "violation_penalty": "P1_REJECT"
    },
    "L2_RULE": {
        "modifiable": True,
        "approver": "admin",
        "description": "工程标准/业务规则，管理员可修改",
        "violation_penalty": "P2_WARN"
    },
    "L3_CONFIG": {
        "modifiable": True,
        "approver": "operator",
        "description": "服务配置/参数/阈值，操作员可编辑",
        "violation_penalty": "P3_LOG"
    }
}

CONSTITUTION_HASH_FILE = "/opt/ZONGYUAN-ROOT/meta_order/constitution_hash"

def get_constitution_hash():
    """计算元宪法哈希，用于篡改检测"""
    content = json.dumps(META_CONSTITUTION, sort_keys=True).encode()
    return hashlib.sha256(content).hexdigest()[:16]

def validate_write(truth: dict, actor: str = "unknown") -> tuple:
    """校验写入操作是否符合元宪法
    Returns: (allowed: bool, reason: str, penalty: str)
    """
    level = truth.get("level", "L3_CONFIG")
    
    # 级别映射
    level_map = {
        "L0_AXIOM": "L0_AXIOM", "L0": "L0_AXIOM",
        "L1_LAW": "L1_LAW", "L1": "L1_LAW", "L1_AXIOM": "L1_LAW",
        "L2_RULE": "L2_RULE", "L2": "L2_RULE", "L2_STANDARD": "L2_RULE",
        "L3_CONFIG": "L3_CONFIG", "L3": "L3_CONFIG"
    }
    normalized = level_map.get(level, "L3_CONFIG")
    rule = META_CONSTITUTION[normalized]
    
    if not rule["modifiable"]:
        return False, f"{normalized}禁止修改（{rule['description']}）", rule["violation_penalty"]
    
    if rule["modifiable"] == "incremental_patch_only":
        if actor != "meta_approval" and actor != "元极恒一":
            return False, f"{normalized}仅允许增量补丁，需{rule['approver']}审批", rule["violation_penalty"]
    
    return True, f"{normalized}允许{actor}写入", "PASS"

def validate_truth_consistency(truth: dict) -> list:
    """校验真值内部一致性"""
    violations = []
    if not truth.get("id"): violations.append("缺少id字段")
    if not truth.get("content"): violations.append("缺少content字段")
    if not truth.get("level"): violations.append("缺少level字段")
    if truth.get("status") == "FROZEN" and truth.get("level","").startswith("L0"):
        pass  # FROZEN+L0是合法组合
    return violations

def check_constitution_integrity() -> dict:
    """检查元宪法完整性（防篡改）"""
    current_hash = get_constitution_hash()
    stored_hash = ""
    if os.path.exists(CONSTITUTION_HASH_FILE):
        with open(CONSTITUTION_HASH_FILE) as f:
            stored_hash = f.read().strip()
    
    if not stored_hash:
        with open(CONSTITUTION_HASH_FILE, "w") as f:
            f.write(current_hash)
        return {"status": "initialized", "hash": current_hash}
    
    return {
        "status": "intact" if current_hash == stored_hash else "TAMPERED",
        "current_hash": current_hash,
        "stored_hash": stored_hash,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "integrity":
        print(json.dumps(check_constitution_integrity(), indent=2, ensure_ascii=False))
    elif len(sys.argv) > 3:
        truth = json.loads(sys.argv[1])
        result = validate_write(truth, sys.argv[2])
        print(json.dumps({"allowed": result[0], "reason": result[1], "penalty": result[2]}, ensure_ascii=False))
    else:
        print("元宪法校验器 V1.0")
        print(f"元宪法哈希: {get_constitution_hash()}")
        print(f"完整性: {check_constitution_integrity()['status']}")
        for level, rule in META_CONSTITUTION.items():
            print(f"  {level}: 可修改={rule['modifiable']}, 审批者={rule['approver']}")
