#!/usr/bin/env python3
"""写入MR-079元法则并更新chattr白名单"""
import json
import hashlib
import subprocess
from datetime import datetime

# 1. 写入MR-079元法则
print("【1】写入MR-079元法则")
meta_rule_path = "/opt/ZONGYUAN-ROOT/meta_rule_set.json"

# 移除chattr保护
subprocess.run(["chattr", "-i", meta_rule_path], capture_output=True)

with open(meta_rule_path, "r") as f:
    meta_rules = json.load(f)

mr_id = "MR-079"
existing = [mr for mr in meta_rules.get("meta_rules", []) if mr.get("meta_law_id") == mr_id]
if existing:
    print(f"  ⚠️  {mr_id}已存在，跳过")
else:
    new_mr = {
        "meta_law_id": mr_id,
        "title": "端口安全固化与人工审核元法则",
        "content": {
            "principle": "端口配置属于核心安全资产，禁止任意修改，所有变更必须经过人工审核",
            "public_whitelist": [22, 80, 443, 2222, 7100, 9120, 9122, 9125, 9151],
            "audit_rules": {
                "port_open": "新开公网端口必须人工审核，说明用途/服务/风险评估",
                "port_close": "关闭端口需记录原因和影响范围",
                "iptables_modify": "修改iptables规则必须人工审核",
                "service_config": "修改服务监听地址必须人工审核"
            },
            "lockdown": {
                "iptables_rules": "chattr +i保护，禁止直接修改",
                "port_ledger": "端口台账写入记忆网关，作为唯一权威来源",
                "emergency_override": "紧急情况下可临时修改，但24小时内必须补审核流程"
            },
            "verification": "每日健康监控检查iptables规则完整性，发现异常立即告警"
        },
        "priority": "L1",
        "created_at": datetime.now().isoformat(),
        "version": "1.0",
        "status": "active"
    }
    new_mr["truth_hash"] = hashlib.sha256(json.dumps(new_mr, sort_keys=True).encode()).hexdigest()
    
    meta_rules.setdefault("meta_rules", []).append(new_mr)
    old_version = meta_rules.get("version", "v15.4")
    meta_rules["version"] = old_version + ".1"
    meta_rules["updated_at"] = datetime.now().isoformat()
    
    with open(meta_rule_path, "w") as f:
        json.dump(meta_rules, f, ensure_ascii=False, indent=2)
    
    total = len(meta_rules["meta_rules"])
    print(f"  ✅ {mr_id} 已写入元法则")
    print(f"  元法则总数: {total}")

# 恢复chattr保护
subprocess.run(["chattr", "+i", meta_rule_path], capture_output=True)

# 2. 更新chattr白名单
print("\n【2】更新chattr白名单")
whitelist_path = "/opt/ZONGYUAN-ROOT/config/chattr_whitelist.json"
subprocess.run(["chattr", "-i", whitelist_path], capture_output=True)

with open(whitelist_path, "r") as f:
    whitelist = json.load(f)

new_files = [
    "/opt/ZONGYUAN-ROOT/config/iptables_rules.rules",
    "/opt/ZONGYUAN-ROOT/scripts/port_ledger.py",
    "/opt/ZONGYUAN-ROOT/scripts/restore_iptables.sh"
]
added = 0
for f in new_files:
    if f not in whitelist.get("allowed_files", []):
        whitelist.setdefault("allowed_files", []).append(f)
        added += 1

with open(whitelist_path, "w") as f:
    json.dump(whitelist, f, ensure_ascii=False, indent=2)

subprocess.run(["chattr", "+i", whitelist_path], capture_output=True)
total_files = len(whitelist.get("allowed_files", []))
print(f"  ✅ chattr白名单已更新，新增{added}个，共{total_files}个文件")

# 3. 推送MR-079到记忆网关
print("\n【3】推送MR-079到记忆网关")
import urllib.request
data = json.dumps({
    "key": "meta_rule.MR-079",
    "value": new_mr if not existing else existing[0],
    "category": "meta_rule",
    "node_id": "cloud-main-kernel-001"
}).encode()
try:
    req = urllib.request.Request(
        "http://127.0.0.1:9120/api/truth/upsert",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    response = urllib.request.urlopen(req, timeout=10)
    result = json.loads(response.read())
    if result.get("success"):
        print("  ✅ MR-079已推送记忆网关")
    else:
        print(f"  ⚠️  推送结果: {result}")
except Exception as e:
    print(f"  ❌ 推送失败: {e}")

print("\n✅ 完成")
