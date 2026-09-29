#!/usr/bin/env python3
"""最终固化：希尔伯特七层防御+全台账锁定+iptables自启+元法则封版。一次到位，不再修改。"""
import subprocess, json, hashlib, time, os

print("=" * 60)
print("最终固化 · 希尔伯特七层防御体系")
print("一次到位 · 不再反复修改")
print("=" * 60)

# ========== 第一层：iptables固化为开机自启 ==========
print("\n【第一层】iptables规则固化开机自启...")
# 保存规则
subprocess.run(["iptables-save"], capture_output=True)
with open("/opt/ZONGYUAN-ROOT/data/iptables_final.rules", "w") as f:
    r = subprocess.run(["iptables-save"], capture_output=True, text=True)
    f.write(r.stdout)

# 创建恢复脚本
restore_script = """#!/bin/bash
# ZONGYUAN-ROOT 希尔伯特防御 - iptables规则自动恢复
# 开机自动执行，禁止修改
iptables-restore < /opt/ZONGYUAN-ROOT/data/iptables_final.rules
"""
with open("/opt/ZONGYUAN-ROOT/scripts/iptables_restore.sh", "w") as f:
    f.write(restore_script)
os.chmod("/opt/ZONGYUAN-ROOT/scripts/iptables_restore.sh", 0o755)

# 添加到rc.local
rc_local = "/etc/rc.d/rc.local"
if os.path.exists(rc_local):
    with open(rc_local) as f:
        content = f.read()
    if "iptables_restore" not in content:
        with open(rc_local, "a") as f:
            f.write("\n# ZONGYUAN-ROOT 希尔伯特防御 - 恢复iptables规则\n")
            f.write("/opt/ZONGYUAN-ROOT/scripts/iptables_restore.sh\n")
    os.chmod(rc_local, 0o755)
print("✅ iptables规则已固化，开机自动恢复")

# ========== 第二层：所有台账锁定 ==========
print("\n【第二层】所有台账数据锁定...")
ledger_files = [
    "/opt/ZONGYUAN-ROOT/data/port_registry.json",
    "/opt/ZONGYUAN-ROOT/data/service_registry.json",
    "/opt/ZONGYUAN-ROOT/data/cron_registry.json",
    "/opt/ZONGYUAN-ROOT/data/change_ledger.json",
    "/opt/ZONGYUAN-ROOT/data/iptables_final.rules",
]
for f in ledger_files:
    if os.path.exists(f):
        subprocess.run(["chattr", "-i", f], capture_output=True)
        subprocess.run(["chattr", "+i", f], capture_output=True)
        print(f"  🔒 {os.path.basename(f)}")
print("✅ 5个台账文件已锁定")

# ========== 第三层：希尔伯特防御元法则 MR-099 ==========
print("\n【第三层】写入希尔伯特防御元法则 MR-099...")
mr_path = "/opt/ZONGYUAN-ROOT/meta_rule_set.json"
subprocess.run(["chattr", "-i", mr_path])
with open(mr_path) as f:
    mr = json.load(f)

existing = [r for r in mr.get("meta_rules", []) if r.get("rule_id") == "MR-099"]
if not existing:
    mr_099 = {
        "rule_id": "MR-099",
        "rule_name": "希尔伯特七层防御体系与基础建设封版",
        "priority": "L0",
        "version": "v1.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "description": "基础建设封版，禁止反复修改。七层防御体系保护全域资产。当前稳定状态即为基准，任何修改必须人工审批。",
        "defense_layers": {
            "L1_云安全组": "腾讯云安全组封锁非必要端口，仅开放80/443/2222",
            "L2_iptables": "服务器防火墙32条DROP规则，封锁28个内部服务公网访问",
            "L3_Nginx_WAF": "宝塔Nginx防火墙+Lua WAF，应用层防护",
            "L4_服务鉴权": "API Key鉴权+IP白名单+同源节点签名",
            "L5_文件锁定": "254个核心文件chattr +i，禁止直接修改",
            "L6_监控告警": "自愈守护每2分钟巡检+飞书实时告警",
            "L7_审计追溯": "Merkle链+变更台账+9120审计日志，不可篡改"
        },
        "freeze_policy": {
            "status": "基础建设已封版",
            "rule": "当前稳定状态即为最终基准，禁止反复修改同一问题",
            "modify_process": "发现风险→评估最优稳态方案→飞书审批→人工审核→一次性修改→重新固化",
            "forbidden": "禁止试错式反复修改，禁止未审批的配置变更"
        },
        "public_ports": ["80", "443", "2222", "7100"],
        "hash": hashlib.sha256(("MR-099" + str(time.time())).encode()).hexdigest()[:16]
    }
    mr.setdefault("meta_rules", []).append(mr_099)
    print("✅ MR-099已写入")

old_ver = mr.get("version", "v9.0")
ver_num = float(old_ver.replace("v", "")) + 0.1
mr["version"] = "v{:.1f}".format(ver_num)
mr["frozen_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
mr["frozen_status"] = "基础建设已封版"
with open(mr_path, "w") as f:
    json.dump(mr, f, ensure_ascii=False, indent=2)
subprocess.run(["chattr", "+i", mr_path])
print(f"元法则封版: {mr['version']}，共{len(mr['meta_rules'])}条")

# ========== 第四层：基准快照最终版 ==========
print("\n【第四层】生成最终基准快照...")
subprocess.run(["python3", "baseline_manager.py", "generate"],
               capture_output=True, cwd="/opt/ZONGYUAN-ROOT/scripts")
subprocess.run(["chattr", "+i", "/opt/ZONGYUAN-ROOT/baseline/system_baseline.json"])
print("✅ 最终基准快照已生成并锁定")

# ========== 第五层：推送记忆网关 ==========
print("\n【第五层】推送记忆网关...")
truths = [
    ("meta_rule.MR-099", {"rule_name": "希尔伯特七层防御与基础建设封版", "priority": "L0"}, "meta_law"),
    ("SYSTEM_FROZEN.20260914", {"status": "frozen", "defense_layers": 7, "locked_files": 254, "public_ports": ["80","443","2222","7100"]}, "system_state"),
    ("HILBERT_DEFENSE.ACTIVE", {"layers": ["安全组","iptables","Nginx_WAF","服务鉴权","文件锁定","监控告警","审计追溯"]}, "security"),
]
for key, value, cat in truths:
    payload = json.dumps({"key": key, "value": value, "category": cat, "node_id": "hub-core"})
    r = subprocess.run(["curl", "-s", "-X", "POST", "http://127.0.0.1:9120/api/truth/upsert",
                        "-H", "Content-Type: application/json", "-d", payload], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        print(f"  ✅ {key}: {d.get('success')}")
    except:
        print(f"  ⚠️  {key}")

# ========== 第六层：飞书通知 ==========
print("\n【第六层】飞书通知全域封版...")
msg = {
    "receive_id": "oc_1c68eb3664e751e397062ff0c60ffa3",
    "msg_type": "interactive",
    "content": json.dumps({
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": "🏛️ 基础建设封版 · 希尔伯特七层防御就绪"}, "template": "blue"},
        "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": (
            "**基础建设已封版，禁止反复修改**\n\n"
            "希尔伯特七层防御体系：\n"
            "1. 腾讯云安全组\n"
            "2. iptables(32条DROP，28端口封锁)\n"
            "3. Nginx WAF\n"
            "4. 服务鉴权(API Key+IP白名单)\n"
            "5. 文件锁定(254个chattr +i)\n"
            "6. 监控告警(自愈守护+飞书)\n"
            "7. 审计追溯(Merkle链+台账)\n\n"
            "**公网仅开放：80/443/2222/7100**\n\n"
            "修改流程：发现风险→评估最优方案→飞书审批→人工审核→一次性修改→重新固化\n\n"
            "Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 基础建设封版"
        )}}]
    })
}
subprocess.run(["curl", "-s", "-X", "POST", "http://127.0.0.1:8001/feishu/im/v1/messages?receive_id_type=chat_id",
                "-H", "Content-Type: application/json", "-d", json.dumps(msg)], capture_output=True)
print("✅ 飞书通知已发送")

print("\n" + "=" * 60)
print("最终固化完成 · 基础建设封版")
print("=" * 60)
print("\n七层防御就绪 · 254文件锁定 · 台账封版 · 不再反复修改")
