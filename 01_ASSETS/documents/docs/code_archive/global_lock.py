#!/usr/bin/env python3
"""全域锁档固化：核心文件chattr +i，写入审批元法则"""
import subprocess, json, hashlib, time, os

LOCKED_FILES = [
    # Nginx配置
    "/www/server/nginx/conf/sites/huodouai.com.conf",
    "/www/server/panel/vhost/nginx/huodouai.com.conf",
    # 记忆网关
    "/opt/ZONGYUAN-ROOT/engine/scripts/unified_gateway_9120.py",
    # 元法则
    "/opt/ZONGYUAN-ROOT/meta_rule_set.json",
    # 基准快照
    "/opt/ZONGYUAN-ROOT/baseline/system_baseline.json",
    # 自愈守护
    "/opt/ZONGYUAN-ROOT/scripts/unified_service_guard.sh",
    # 自动吸收流水线
    "/opt/ZONGYUAN-ROOT/scripts/auto_absorption_pipeline.py",
    # 自动集成器
    "/opt/ZONGYUAN-ROOT/scripts/auto_integrator.py",
    # 自动可视化引擎
    "/opt/ZONGYUAN-ROOT/scripts/auto_visualization_engine.py",
    # 变更台账
    "/opt/ZONGYUAN-ROOT/data/change_ledger.json",
    # 基准管理器
    "/opt/ZONGYUAN-ROOT/scripts/baseline_manager.py",
]

print("=" * 50)
print("全域锁档固化开始")
print("=" * 50)

# 1. 锁定核心文件
locked = []
for f in LOCKED_FILES:
    if os.path.exists(f):
        # 先解锁再重新锁定（确保状态一致）
        subprocess.run(["chattr", "-i", f], capture_output=True)
        result = subprocess.run(["chattr", "+i", f], capture_output=True)
        if result.returncode == 0:
            locked.append(f)
            print(f"  🔒 {f}")
        else:
            print(f"  ⚠️  锁定失败: {f}")
    else:
        print(f"  ⚠️  文件不存在: {f}")

print(f"\n✅ 已锁定 {len(locked)}/{len(LOCKED_FILES)} 个核心文件")

# 2. 写入MR-097: 修改审批制度
mr_path = "/opt/ZONGYUAN-ROOT/meta_rule_set.json"
subprocess.run(["chattr", "-i", mr_path])

with open(mr_path) as f:
    mr = json.load(f)

existing = [r for r in mr.get("meta_rules", []) if r.get("rule_id") == "MR-097"]
if not existing:
    new_mr = {
        "rule_id": "MR-097",
        "rule_name": "核心资产修改审批制度",
        "priority": "L0",
        "version": "v1.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "description": "所有核心配置文件已chattr +i锁定。任何修改必须先通过飞书审批流程，经本源主体人工审核通过后，由中枢大脑执行chattr -i→修改→chattr +i→更新基准→推送记忆网关的完整流程。禁止任何节点绕过审批直接修改。",
        "rules": [
            "核心文件默认chattr +i，禁止直接修改",
            "修改前必须提交飞书审批，说明修改原因、范围、回滚方案",
            "审批通过后由中枢大脑统一执行：chattr -i → 修改 → 验证 → chattr +i",
            "修改后必须更新baseline基准快照",
            "修改后必须推送记忆网关并记录变更台账",
            "同源节点不得自行修改核心文件，只能上报建议",
            "紧急情况可先执行后补审批，但必须在30分钟内补办"
        ],
        "locked_files": LOCKED_FILES,
        "hash": hashlib.sha256(("MR-097" + str(time.time())).encode()).hexdigest()[:16]
    }
    mr.setdefault("meta_rules", []).append(new_mr)
    print("\n✅ MR-097已写入：核心资产修改审批制度")
else:
    print("\n⚠️  MR-097已存在")

old_ver = mr.get("version", "v8.7")
ver_num = float(old_ver.replace("v", "")) + 0.1
mr["version"] = "v{:.1f}".format(ver_num)
mr["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

with open(mr_path, "w") as f:
    json.dump(mr, f, ensure_ascii=False, indent=2)

subprocess.run(["chattr", "+i", mr_path])
print(f"元法则版本: {mr['version']}，共 {len(mr['meta_rules'])} 条")

# 3. 更新基准快照
print("\n📸 更新系统基准快照...")
subprocess.run(["python3", "/opt/ZONGYUAN-ROOT/scripts/baseline_manager.py", "generate"],
               capture_output=True, cwd="/opt/ZONGYUAN-ROOT/scripts")
print("✅ 基准快照已更新")

# 4. 推送记忆网关
print("\n📡 推送记忆网关...")
truths = [
    ("meta_rule.MR-097", {"rule_name": "核心资产修改审批制度", "priority": "L0", "locked_files_count": len(locked)}, "meta_law"),
    ("SYSTEM_LOCK.20260914", {"status": "locked", "locked_files": len(locked), "operator": "hub-core"}, "system_state"),
]
for key, value, category in truths:
    payload = json.dumps({"key": key, "value": value, "category": category, "node_id": "hub-core"})
    result = subprocess.run(
        ["curl", "-s", "-X", "POST", "http://127.0.0.1:9120/api/truth/upsert",
         "-H", "Content-Type: application/json", "-d", payload],
        capture_output=True, text=True
    )
    try:
        d = json.loads(result.stdout)
        print(f"  ✅ {key}: {d.get('success')}")
    except:
        print(f"  ⚠️  {key}: 推送失败")

print("\n" + "=" * 50)
print("全域锁档固化完成")
print("=" * 50)
