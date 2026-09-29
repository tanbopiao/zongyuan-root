#!/usr/bin/env python3
"""轻量化战略V2标准化：写入元规则+推送网关+更新版本"""
import json, time, hashlib, sqlite3, subprocess

BASE = "/opt/ZONGYUAN-ROOT"
MR_PATH = f"{BASE}/meta_rule_set.json"
DB_PATH = f"{BASE}/data/memory_gateway.db"

print("=" * 60)
print("轻量化战略V2标准化落地")
print("=" * 60)

# 1. 写入元规则
print("\n【1】写入元规则 MR-102/103/104")
with open(MR_PATH) as f:
    mr = json.load(f)

# 安全获取已有ID（处理缺少rule_id的情况）
existing_ids = set()
for r in mr.get("meta_rules", []):
    rid = r.get("rule_id") or r.get("id") or ""
    if rid:
        existing_ids.add(rid)

new_rules = [
    {
        "rule_id": "MR-102",
        "rule_name": "轻量化优先战略元规则",
        "priority": "L0",
        "version": "v2.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hash": hashlib.sha256(("MR-102" + str(time.time())).encode()).hexdigest()[:16],
        "rules": [
            "所有网页交付物优先采用单HTML自包含格式，<=50KB，即开即用",
            "禁止依赖外部框架/构建工具/CDN资源，纯静态纯原生",
            "功能完整优先于技术栈炫技，真实可用优先于视觉堆砌",
            "新页面默认集成活体感六大功能（唤醒动画/在线指示器/数据波动/对话面板/知识库/心跳动画）",
            "轻量化是战略级最高准则，凌驾于技术偏好之上"
        ],
        "scope": "全域网页交付",
        "enforcement": "强制"
    },
    {
        "rule_id": "MR-103",
        "rule_name": "网页即智能体身体元规则",
        "priority": "L0",
        "version": "v1.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hash": hashlib.sha256(("MR-103" + str(time.time())).encode()).hexdigest()[:16],
        "rules": [
            "每个HTML页面不是静态展示，而是智能体的可视化身体/对外实体",
            "页面背后必须有对应智能体在实时服务用户",
            "页面必须具备活体感：在线状态/心跳动画/实时数据/交互对话",
            "网页=智能体身体，智能体=网页灵魂，二者不可分离",
            "所有新页面必须按活体感标准构建，禁止纯静态死页面"
        ],
        "scope": "全域网页体系",
        "enforcement": "强制"
    },
    {
        "rule_id": "MR-104",
        "rule_name": "标准化交付成果元规则",
        "priority": "L1",
        "version": "v1.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hash": hashlib.sha256(("MR-104" + str(time.time())).encode()).hexdigest()[:16],
        "rules": [
            "所有交付成果必须包含：资产ID/锁档等级/eFuse位/资产哈希/确权DID/溯源标识",
            "交付物必须通过记忆网关上报告广+飞书群聊通知双通道推广",
            "交付完成后必须锁档归档，禁止后续随意修改",
            "交付标准遵循火斗云智AIOS交付标准规范V1.0"
        ],
        "scope": "全域交付",
        "enforcement": "强制"
    }
]

added = 0
for rule in new_rules:
    if rule["rule_id"] not in existing_ids:
        mr["meta_rules"].append(rule)
        added += 1
        print(f"  + {rule['rule_id']}: {rule['rule_name']}")

mr["version"] = "v9.5"
mr["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

with open(MR_PATH, "w") as f:
    json.dump(mr, f, ensure_ascii=False, indent=2)

print(f"  新增{added}条，当前共{len(mr['meta_rules'])}条，版本{mr['version']}")

# 2. 推送记忆网关
print("\n【2】推送记忆网关")
truths_to_push = [
    ("meta_rule.MR-102", {"name": "轻量化优先战略元规则", "priority": "L0"}, "meta_rule"),
    ("meta_rule.MR-103", {"name": "网页即智能体身体元规则", "priority": "L0"}, "meta_rule"),
    ("meta_rule.MR-104", {"name": "标准化交付成果元规则", "priority": "L1"}, "meta_rule"),
    ("KD-PROD-0020", {"name": "轻量化优先战略可视化网页V2", "url": "/lightweight-strategy-v2.html", "size": "30KB", "level": "Lv8"}, "product"),
]

for key, value, category in truths_to_push:
    payload = json.dumps({"key": key, "value": value, "category": category, "node_id": "hub-core"})
    result = subprocess.run(
        ["curl", "-s", "-X", "POST", "http://127.0.0.1:9120/api/truth/upsert",
         "-H", "Content-Type: application/json", "-d", payload],
        capture_output=True, text=True
    )
    try:
        d = json.loads(result.stdout)
        status = "OK" if d.get("success") else "FAIL"
        print(f"  [{status}] {key}")
    except:
        print(f"  [ERR] {key}: {result.stdout[:100]}")

# 3. 更新global_rev
print("\n【3】更新global_rev")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("UPDATE sync_state SET value=?, updated_at=? WHERE key=?", ("3", time.time(), "global_rev"))
conn.commit()
c.execute("SELECT value FROM sync_state WHERE key='global_rev'")
print(f"  global_rev = {c.fetchone()[0]}")
conn.close()

# 4. 统计真值总量
print("\n【4】真值总量")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM truths")
print(f"  当前真值: {c.fetchone()[0]}条")
conn.close()

print("\n" + "=" * 60)
print("标准化落地完成")
print("=" * 60)
print("  元法则: v9.5 / 105条")
print("  新增: MR-102轻量化优先 / MR-103网页即智能体身体 / MR-104标准化交付")
print("  网页: https://www.huodouai.com/lightweight-strategy-v2.html")
print("  确权: DID-BR-000002 | Omega_0 subset circle_infinity subset Omega")
