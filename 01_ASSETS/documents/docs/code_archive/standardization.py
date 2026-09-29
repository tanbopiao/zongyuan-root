#!/usr/bin/env python3
"""全域标准化工程化落地：端口台账+服务台账+定时任务台账+API规范+元法则"""
import subprocess, json, hashlib, time, os, re

print("=" * 60)
print("全域标准化工程化落地")
print("=" * 60)

# ========== 1. 端口台账 ==========
print("\n【1/6】构建端口台账...")
result = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
port_registry = []
for line in result.stdout.strip().split("\n")[1:]:
    parts = line.split()
    if len(parts) < 5:
        continue
    local = parts[3]
    addr, port = local.rsplit(":", 1) if ":" in local else ("", local)
    process = parts[5] if len(parts) > 5 else "unknown"
    # 提取进程名和PID
    pid = ""
    pname = ""
    if "users:" in process:
        m = re.search(r'users:\(\("(.+?)",pid=(\d+)', process)
        if m:
            pname, pid = m.group(1), m.group(2)
    
    exposure = "公网" if addr in ["0.0.0.0", "*"] else "本地"
    status = "✅合规" if addr == "127.0.0.1" else "⚠️需整改"
    
    port_registry.append({
        "port": int(port),
        "address": addr,
        "exposure": exposure,
        "process": pname,
        "pid": pid,
        "status": status,
        "nginx_path": "",
        "description": ""
    })

# 已知服务映射
known_services = {
    80: ("Nginx HTTP", "公网必需", "/"),
    443: ("Nginx HTTPS", "公网必需", "/"),
    2222: ("SSH", "公网必需", "SSH管理"),
    8001: ("飞书网关", "本地", "/docs/"),
    8002: ("ANCE服务", "本地", "/ance/"),
    8003: ("内部服务", "本地", ""),
    8007: ("内部服务", "本地", ""),
    8014: ("向量数据库", "需整改", "/vector/"),
    8021: ("AI代理", "需整改", "/ai-proxy/"),
    8023: ("Agent Hub", "需整改", "/agent-hub/"),
    8029: ("内部服务", "需整改", ""),
    8031: ("主权API", "需整改", "/sovereignty-api/"),
    8040: ("内部服务", "需整改", ""),
    8046: ("内部服务", "需整改", ""),
    8050: ("飞书网关", "需整改", ""),
    8060: ("内部服务", "需整改", ""),
    8061: ("内部服务", "需整改", ""),
    8062: ("内部服务", "需整改", ""),
    8063: ("内部服务", "需整改", ""),
    8064: ("内部服务", "需整改", ""),
    8070: ("知识图谱", "需整改", "/aios-api/kg/"),
    8072: ("Op调度器", "需整改", ""),
    8085: ("RAG服务", "需整改", ""),
    8088: ("Nginx状态", "本地", ""),
    8090: ("Steady Ops", "需整改", ""),
    8091: ("内部服务", "本地", ""),
    8092: ("内部服务", "本地", ""),
    8093: ("内部服务", "本地", ""),
    8094: ("闭环调度器", "需整改", ""),
    8098: ("内部服务", "需整改", ""),
    8100: ("短剧管理API", "需整改", "/drama/"),
    8628: ("短剧工业API", "需整改", ""),
    9000: ("管控中心", "需整改", "/api/hub/"),
    9090: ("Prometheus", "需整改", "/prometheus/"),
    9099: ("商业API网关", "需整改", "/api/gateway/"),
    9120: ("记忆网关", "本地✅", "/api/memory/"),
    9122: ("通信协议网关", "需整改", ""),
    9140: ("WebSocket推送", "需整改", ""),
    9150: ("自我识别引擎", "需整改", ""),
}

for p in port_registry:
    if p["port"] in known_services:
        name, desc, nginx_path = known_services[p["port"]]
        p["description"] = name
        p["nginx_path"] = nginx_path
        if "本地" in desc or "✅" in desc:
            p["status"] = "✅合规"
        elif "必需" in desc:
            p["status"] = "✅必需公网"

port_registry.sort(key=lambda x: x["port"])

# 保存端口台账
port_ledger_path = "/opt/ZONGYUAN-ROOT/data/port_registry.json"
with open(port_ledger_path, "w") as f:
    json.dump({"updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "total": len(port_registry), "ports": port_registry}, f, ensure_ascii=False, indent=2)

public_count = sum(1 for p in port_registry if p["exposure"] == "公网")
local_count = sum(1 for p in port_registry if p["exposure"] == "本地")
need_fix = sum(1 for p in port_registry if "需整改" in p["status"])
print(f"  共{len(port_registry)}个端口 | 公网{public_count} | 本地{local_count} | 需整改{need_fix}")

# ========== 2. 服务台账 ==========
print("\n【2/6】构建服务台账...")
result = subprocess.run(["systemctl", "list-units", "--type=service", "--state=running", "--no-pager"], capture_output=True, text=True)
service_registry = []
for line in result.stdout.strip().split("\n")[1:]:
    if not line.strip() or "loaded" not in line:
        continue
    parts = line.split()
    if len(parts) >= 4:
        name = parts[0].replace(".service", "")
        desc = " ".join(parts[3:]) if len(parts) > 3 else ""
        service_registry.append({"name": name, "description": desc, "status": "running"})

service_ledger_path = "/opt/ZONGYUAN-ROOT/data/service_registry.json"
with open(service_ledger_path, "w") as f:
    json.dump({"updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "total": len(service_registry), "services": service_registry}, f, ensure_ascii=False, indent=2)
print(f"  共{len(service_registry)}个运行中服务")

# ========== 3. 定时任务台账 ==========
print("\n【3/6】构建定时任务台账...")
result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
cron_registry = []
for line in result.stdout.strip().split("\n"):
    if line.startswith("#") or not line.strip():
        continue
    parts = line.split(None, 5)
    if len(parts) >= 6:
        schedule = " ".join(parts[:5])
        command = parts[5]
        cron_registry.append({"schedule": schedule, "command": command[:100], "enabled": True})

cron_ledger_path = "/opt/ZONGYUAN-ROOT/data/cron_registry.json"
with open(cron_ledger_path, "w") as f:
    json.dump({"updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "total": len(cron_registry), "crons": cron_registry}, f, ensure_ascii=False, indent=2)
print(f"  共{len(cron_registry)}个定时任务")

# ========== 4. 写入标准化元法则 MR-098 ==========
print("\n【4/6】写入标准化元法则 MR-098...")
mr_path = "/opt/ZONGYUAN-ROOT/meta_rule_set.json"
subprocess.run(["chattr", "-i", mr_path])
with open(mr_path) as f:
    mr = json.load(f)

existing = [r for r in mr.get("meta_rules", []) if r.get("rule_id") == "MR-098"]
if not existing:
    mr_098 = {
        "rule_id": "MR-098",
        "rule_name": "全域标准化工程化规范",
        "priority": "L1",
        "version": "v1.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "description": "体系全域标准化：端口/服务/脚本/页面/定时任务/API/真值上报七大领域统一规范，确保可工程化落地、可维护、可扩展。",
        "standards": {
            "port_standard": {
                "rule": "内部服务默认127.0.0.1监听，公网通过Nginx反代",
                "exceptions": ["80(HTTP)", "443(HTTPS)", "2222(SSH)"],
                "registry": "/opt/ZONGYUAN-ROOT/data/port_registry.json"
            },
            "service_standard": {
                "rule": "所有常驻服务必须注册systemd，禁止nohup裸跑",
                "naming": "zr-<功能>.service 或 <功能>.service",
                "registry": "/opt/ZONGYUAN-ROOT/data/service_registry.json"
            },
            "script_standard": {
                "rule": "脚本必须有功能注释头、错误处理、日志输出",
                "classification": ["deploy", "monitor", "sync", "archive", "analysis", "repair"],
                "directory": "/opt/ZONGYUAN-ROOT/scripts/"
            },
            "webpage_standard": {
                "rule": "单文件HTML+内联CSS/JS，双root同步，自动集成导航",
                "max_size": "200KB",
                "lazy_load": True,
                "directory": "/www/wwwroot/www.huodouai.com/"
            },
            "cron_standard": {
                "rule": "定时任务必须登记台账，含执行频率、功能、负责人",
                "registry": "/opt/ZONGYUAN-ROOT/data/cron_registry.json"
            },
            "api_standard": {
                "rule": "统一返回格式{success, data, error, timestamp}",
                "auth": "X-API-Key或同源节点签名",
                "rate_limit": "默认60次/分钟"
            },
            "truth_report_standard": {
                "rule": "真值上报必须含key/value/category/node_id/timestamp",
                "hash": "SHA256(key+value+timestamp)",
                "endpoint": "POST /api/memory/api/truth/upsert"
            }
        },
        "hash": hashlib.sha256(("MR-098" + str(time.time())).encode()).hexdigest()[:16]
    }
    mr.setdefault("meta_rules", []).append(mr_098)
    print("  ✅ MR-098已写入")
else:
    print("  ⚠️  MR-098已存在")

old_ver = mr.get("version", "v8.9")
ver_num = float(old_ver.replace("v", "")) + 0.1
mr["version"] = "v{:.1f}".format(ver_num)
with open(mr_path, "w") as f:
    json.dump(mr, f, ensure_ascii=False, indent=2)
subprocess.run(["chattr", "+i", mr_path])
print(f"  元法则版本: {mr['version']}，共{len(mr['meta_rules'])}条")

# ========== 5. 推送记忆网关 ==========
print("\n【5/6】推送记忆网关...")
for key, value, cat in [
    ("PORT_REGISTRY", {"total": len(port_registry), "public": public_count, "local": local_count, "need_fix": need_fix}, "system_state"),
    ("SERVICE_REGISTRY", {"total": len(service_registry)}, "system_state"),
    ("CRON_REGISTRY", {"total": len(cron_registry)}, "system_state"),
    ("meta_rule.MR-098", {"rule_name": "全域标准化工程化规范", "priority": "L1"}, "meta_law"),
]:
    payload = json.dumps({"key": key, "value": value, "category": cat, "node_id": "hub-core"})
    r = subprocess.run(["curl", "-s", "-X", "POST", "http://127.0.0.1:9120/api/truth/upsert",
                        "-H", "Content-Type: application/json", "-d", payload], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        print(f"  ✅ {key}: {d.get('success')}")
    except:
        print(f"  ⚠️  {key}: 失败")

# ========== 6. 更新台账 ==========
print("\n【6/6】更新变更台账...")
ledger_path = "/opt/ZONGYUAN-ROOT/data/change_ledger.json"
subprocess.run(["chattr", "-i", ledger_path])
with open(ledger_path) as f:
    ledger = json.load(f)
records = ledger.get("records", [])
next_id = "CL-{:03d}".format(len(records) + 1)
records.append({
    "id": next_id,
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "category": "标准化",
    "title": "全域标准化工程化落地：七大领域统一规范",
    "description": f"构建端口台账({len(port_registry)}个)、服务台账({len(service_registry)}个)、定时任务台账({len(cron_registry)}个)，写入MR-098全域标准化规范，覆盖端口/服务/脚本/页面/定时任务/API/真值上报七大领域。",
    "affected": ["端口", "服务", "定时任务", "API", "元法则"],
    "operator": "ZONGYUAN-ROOT中枢大脑",
    "hash": hashlib.sha256((next_id + str(time.time())).encode()).hexdigest()[:16]
})
ledger["records"] = records
with open(ledger_path, "w") as f:
    json.dump(ledger, f, ensure_ascii=False, indent=2)
subprocess.run(["chattr", "+i", ledger_path])
print(f"  ✅ 台账已更新: {next_id}")

print("\n" + "=" * 60)
print("全域标准化工程化落地完成")
print("=" * 60)
