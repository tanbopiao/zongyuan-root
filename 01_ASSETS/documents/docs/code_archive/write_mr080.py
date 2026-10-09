#!/usr/bin/env python3
"""写入MR-080全域变更管控元法则"""
import json
import subprocess
from datetime import datetime

meta_rule_path = "/opt/ZONGYUAN-ROOT/meta_rule_set.json"

# 移除chattr保护
subprocess.run(["chattr", "-i", meta_rule_path], capture_output=True)

with open(meta_rule_path) as f:
    data = json.load(f)

# 检查是否已存在
exists = any(mr.get("rule_id") == "MR-080" for mr in data.get("meta_rules", []))

if not exists:
    new_mr = {
        "rule_id": "MR-080",
        "rule_name": "全域变更管控元法则",
        "content": {
            "principle": "迭代阶段全域变更管控，核心修改必须审批，低风险优化自动通过",
            "change_levels": {
                "P0": {"name": "核心架构变更", "risk": "critical", "must_manual": True, "auto_threshold": 100},
                "P1": {"name": "核心服务变更", "risk": "high", "must_manual": True, "auto_threshold": 95},
                "P2": {"name": "功能开发与部署", "risk": "medium_high", "must_manual": False, "auto_threshold": 90},
                "P3": {"name": "优化与维护", "risk": "medium", "must_manual": False, "auto_threshold": 80},
                "P4": {"name": "低风险操作", "risk": "low", "must_manual": False, "auto_threshold": 70}
            },
            "approval_workflow": {
                "tool": "change_manager.py",
                "steps": [
                    "提交变更: change_manager.py submit --type 类型 --desc 描述",
                    "自动分级: P0-P4智能识别",
                    "五方仲裁: 安全/稳定/成本/价值/合规评分",
                    "P0/P1必须人工审批（飞书卡片）",
                    "P2/P3/P4评分达标自动通过",
                    "执行+备份+审计+飞书通知"
                ]
            },
            "lockdown": {
                "core_files": "chattr +i全域锁定",
                "whitelist": "chattr_whitelist.json管理",
                "never_lock": ["merkle_chain_state.json", "memory_gateway.db"]
            },
            "emergency": "P0紧急修复可先执行，24小时内补审批"
        },
        "category": "protocol",
        "priority": "L1",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "efuse": True,
        "enforcement": "mandatory"
    }
    data.setdefault("meta_rules", []).append(new_mr)
    print("MR-080已写入")
else:
    print("MR-080已存在，跳过")

data["version"] = data.get("version", "v15.4") + ".2"
data["updated_at"] = datetime.now().isoformat()

with open(meta_rule_path, "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 恢复chattr保护
subprocess.run(["chattr", "+i", meta_rule_path], capture_output=True)

total = len(data.get("meta_rules", []))
print(f"元法则总数: {total}")
print("已锁定")
