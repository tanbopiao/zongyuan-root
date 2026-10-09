#!/usr/bin/env python3
"""更新台账+写入MR-096元法则"""
import json, hashlib, time, subprocess

# 1. 更新台账
ledger_path = "/opt/ZONGYUAN-ROOT/data/change_ledger.json"
with open(ledger_path) as f:
    ledger = json.load(f)

records = ledger.get("records", [])
next_id = "CL-{:03d}".format(len(records) + 1)

new_entry = {
    "id": next_id,
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "category": "网络架构",
    "title": "域名/端口分离：记忆网关9120关闭公网，统一Nginx反代",
    "description": "9120从0.0.0.0改为127.0.0.1监听，关闭公网直接暴露。公网统一通过Nginx反代：/api/memory/(需API Key，读写)、/aios-api/memory/(只读GET)、/api/v1/gateway/status(只读状态)。与短剧API /drama/、/api/v1/* 完全分离。修复/aios-api/memory/路径bug。",
    "affected_services": ["zr-memory-gateway(9120)", "Nginx", "drama-admin-api(8100)"],
    "verification": "curl https://www.huodouai.com/api/v1/gateway/status 返回5648真值；ss -tlnp显示9120仅127.0.0.1监听",
    "rollback": "恢复unified_gateway_9120.py.bak_localonly，改回0.0.0.0监听",
    "operator": "ZONGYUAN-ROOT中枢大脑",
    "hash": hashlib.sha256((next_id + str(time.time())).encode()).hexdigest()[:16]
}

records.append(new_entry)
ledger["records"] = records
with open(ledger_path, "w") as f:
    json.dump(ledger, f, ensure_ascii=False, indent=2)
print("台账已更新:", next_id)

# 2. 写入MR-096
mr_path = "/opt/ZONGYUAN-ROOT/meta_rule_set.json"
subprocess.run(["chattr", "-i", mr_path])

with open(mr_path) as f:
    mr = json.load(f)

# 检查是否已存在MR-096
existing = [r for r in mr.get("meta_rules", []) if r.get("rule_id") == "MR-096"]
if not existing:
    new_mr = {
        "rule_id": "MR-096",
        "rule_name": "域名端口分离与Nginx反代规范",
        "priority": "L1",
        "version": "v1.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "description": "所有内部服务禁止直接监听0.0.0.0公网端口，必须改为127.0.0.1监听，通过Nginx反代对外暴露。",
        "rules": [
            "内部服务默认监听127.0.0.1，禁止0.0.0.0",
            "公网访问必须通过Nginx反代",
            "记忆网关路径前缀：/api/memory/ 或 /api/v1/gateway/",
            "短剧API路径前缀：/drama/ 或 /api/v1/*",
            "Nginx配置必须同时修改sites和vhost两个目录保持同步",
            "修改Nginx配置前必须备份，nginx -t通过后才能reload"
        ],
        "hash": hashlib.sha256(("MR-096" + str(time.time())).encode()).hexdigest()[:16]
    }
    mr.setdefault("meta_rules", []).append(new_mr)
    print("MR-096已写入")
else:
    print("MR-096已存在，跳过")

old_ver = mr.get("version", "v7.4")
ver_num = float(old_ver.replace("v", "")) + 0.1
mr["version"] = "v{:.1f}".format(ver_num)
mr["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

with open(mr_path, "w") as f:
    json.dump(mr, f, ensure_ascii=False, indent=2)

subprocess.run(["chattr", "+i", mr_path])
print("元法则版本:", mr["version"], "共", len(mr["meta_rules"]), "条")
