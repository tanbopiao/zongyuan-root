#!/usr/bin/env python3
"""
端口台账管理系统 - 写入记忆网关，减少试错
功能：端口扫描/服务识别/台账管理/端口分配/记忆网关同步
"""
import os
import re
import json
import sqlite3
import subprocess
import urllib.request
from datetime import datetime
from collections import defaultdict

# 配置
DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
PORT_LEDGER_KEY = "SYSTEM_PORT_LEDGER"
PORT_ALLOC_RANGE = (9000, 9999)  # 新服务分配端口范围

# 已知端口注册表（端口 -> 服务信息）
KNOWN_PORTS = {
    22: {"service": "sshd", "name": "SSH远程登录", "category": "系统", "must_public": True, "description": "SSH远程管理端口"},
    80: {"service": "nginx", "name": "HTTP Web服务", "category": "Web", "must_public": True, "description": "Nginx HTTP入口"},
    443: {"service": "nginx", "name": "HTTPS Web服务", "category": "Web", "must_public": True, "description": "Nginx HTTPS入口"},
    2222: {"service": "python3", "name": "备用SSH/管理端口", "category": "系统", "must_public": True, "description": "备用管理端口"},
    6379: {"service": "redis-server", "name": "Redis缓存", "category": "数据库", "must_public": False, "description": "Redis缓存数据库"},
    7100: {"service": "frps", "name": "FRP服务端", "category": "网络", "must_public": True, "description": "FRP内网穿透服务端"},
    7600: {"service": "frps", "name": "FRP控制面板", "category": "网络", "must_public": False, "description": "FRP管理面板"},
    8001: {"service": "python3", "name": "飞书网关", "category": "通信", "must_public": False, "description": "飞书API网关，消息推送"},
    8002: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8003: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8007: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8014: {"service": "python3", "name": "向量数据库", "category": "数据库", "must_public": False, "description": "向量数据库服务，RAG检索"},
    8021: {"service": "python3", "name": "AI代理", "category": "AI", "must_public": False, "description": "AI代理服务"},
    8023: {"service": "python3", "name": "Agent Hub", "category": "AI", "must_public": False, "description": "Agent联邦枢纽"},
    8029: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8031: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8040: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8046: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8050: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8060: {"service": "python3", "name": "审批回调", "category": "业务", "must_public": False, "description": "飞书审批回调接口"},
    8061: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8062: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8063: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8064: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8070: {"service": "python3", "name": "知识图谱", "category": "AI", "must_public": False, "description": "知识图谱API服务"},
    8072: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8081: {"service": "llama-server", "name": "本地LLM", "category": "AI", "must_public": False, "description": "本地0.5B小模型推理服务"},
    8085: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8088: {"service": "nginx", "name": "门户8088", "category": "Web", "must_public": False, "description": "备用门户端口"},
    8090: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8093: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8094: {"service": "python3", "name": "闭环调度器", "category": "调度", "must_public": False, "description": "闭环调度服务，自治任务调度"},
    8098: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8099: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8100: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8102: {"service": "python3", "name": "短剧编排", "category": "业务", "must_public": False, "description": "短剧自动编排服务"},
    8103: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8161: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8170: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8180: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8185: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8200: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8202: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8203: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8300: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8301: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8626: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8628: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    8765: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9099: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9120: {"service": "python3", "name": "记忆网关", "category": "核心", "must_public": True, "description": "记忆网关，真值存储与节点通信核心"},
    9121: {"service": "python3", "name": "记忆网关内部", "category": "核心", "must_public": False, "description": "记忆网关内部通信"},
    9122: {"service": "python3", "name": "通信协议网关", "category": "通信", "must_public": True, "description": "加密通信协议网关，节点接入"},
    9123: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9125: {"service": "python3", "name": "希尔伯特镜像态", "category": "安全", "must_public": True, "description": "希尔伯特镜像态蜜罐服务，攻击捕获"},
    9130: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9131: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9132: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9133: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9134: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9140: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9150: {"service": "python3", "name": "自验证引擎", "category": "核心", "must_public": False, "description": "自验证引擎服务"},
    9151: {"service": "python3", "name": "GEO晶格", "category": "核心", "must_public": True, "description": "GEO晶格服务，Lv8锁档稳态"},
    9160: {"service": "python3", "name": "量子纠缠层", "category": "安全", "must_public": False, "description": "希尔伯特镜像态量子纠缠层，攻击感知联动"},
    9200: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9210: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9300: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9301: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9302: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9303: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9304: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9305: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9306: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9307: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
    9443: {"service": "python3", "name": "内部服务", "category": "内部", "must_public": False, "description": "内部微服务"},
}

def run_cmd(cmd, timeout=10):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except:
        return ""

def scan_ports():
    """扫描所有监听端口"""
    output = run_cmd("ss -tlnp 2>/dev/null")
    ports = []
    
    for line in output.split("\n"):
        if "LISTEN" not in line:
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        
        addr = parts[3]
        # 提取端口号（匹配地址末尾的:数字）
        port_match = re.search(r":(\d+)$", addr)
        if not port_match:
            continue
        port = int(port_match.group(1))
        
        # 提取进程信息
        process = "unknown"
        pid = "unknown"
        proc_match = re.search(r'users:\(\("([^"]+)"', line)
        pid_match = re.search(r'pid=(\d+)', line)
        if proc_match:
            process = proc_match.group(1)
        if pid_match:
            pid = pid_match.group(1)
        
        # 判断监听范围
        if "127.0.0.1" in addr or "::1" in addr:
            scope = "local"
        else:
            scope = "public"
        
        ports.append({
            "port": port,
            "scope": scope,
            "protocol": parts[0],
            "process": process,
            "pid": pid,
            "address": addr
        })
    
    return ports

def build_port_ledger(ports):
    """构建端口台账"""
    ledger = {
        "version": "1.0",
        "updated": datetime.now().isoformat(),
        "total_ports": len(ports),
        "public_ports": sum(1 for p in ports if p["scope"] == "public"),
        "local_ports": sum(1 for p in ports if p["scope"] == "local"),
        "ports": []
    }
    
    for p in sorted(ports, key=lambda x: x["port"]):
        port_info = KNOWN_PORTS.get(p["port"], {
            "service": p["process"],
            "name": f"未知服务({p['process']})",
            "category": "未知",
            "must_public": p["scope"] == "public",
            "description": "未登记的服务，需要识别"
        })
        
        ledger["ports"].append({
            "port": p["port"],
            "scope": p["scope"],
            "protocol": p["protocol"],
            "process": p["process"],
            "pid": p["pid"],
            "service_name": port_info["name"],
            "category": port_info["category"],
            "must_public": port_info["must_public"],
            "description": port_info["description"],
            "status": "active",
            "registered": p["port"] in KNOWN_PORTS
        })
    
    # 统计分类
    categories = defaultdict(int)
    for p in ledger["ports"]:
        categories[p["category"]] += 1
    ledger["categories"] = dict(categories)
    
    # 未登记端口
    ledger["unregistered"] = [p["port"] for p in ledger["ports"] if not p["registered"]]
    
    return ledger

def write_to_memory_gateway(ledger):
    """写入记忆网关"""
    truth_value = json.dumps(ledger, ensure_ascii=False)
    truth_hash = __import__("hashlib").sha256(truth_value.encode()).hexdigest()
    
    data = json.dumps({
        "key": PORT_LEDGER_KEY,
        "value": ledger,
        "category": "protocol",
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
        return result.get("success") == True or result.get("status") == "ok"
    except Exception as e:
        print(f"  写入记忆网关失败: {e}")
        return False

def allocate_port(service_name, description=""):
    """分配新端口"""
    # 读取当前台账
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT truth_value FROM truths WHERE truth_key = ?", (PORT_LEDGER_KEY,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("  错误: 端口台账不存在，请先运行扫描")
        return None
    
    ledger = json.loads(row[0])
    used_ports = set(p["port"] for p in ledger["ports"])
    
    # 在分配范围内找可用端口
    for port in range(PORT_ALLOC_RANGE[0], PORT_ALLOC_RANGE[1]):
        if port not in used_ports:
            # 验证端口确实未被占用
            result = run_cmd(f"ss -tlnp | grep ':{port} '")
            if not result:
                print(f"  ✅ 分配端口: {port} -> {service_name}")
                return port
    
    print("  错误: 分配范围内无可用端口")
    return None

def print_ledger_summary(ledger):
    """打印台账摘要"""
    print("\n" + "=" * 70)
    print("  端口台账摘要")
    print("=" * 70)
    print(f"  总端口数: {ledger['total_ports']}")
    print(f"  公网暴露: {ledger['public_ports']}")
    print(f"  本地监听: {ledger['local_ports']}")
    print(f"  已登记: {ledger['total_ports'] - len(ledger['unregistered'])}")
    print(f"  未登记: {len(ledger['unregistered'])}")
    print()
    
    print("  分类统计:")
    for cat, count in sorted(ledger["categories"].items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}个")
    print()
    
    print("  核心服务端口:")
    core_ports = [p for p in ledger["ports"] if p["category"] in ["核心", "通信", "安全"]]
    for p in core_ports:
        scope_icon = "🌐" if p["scope"] == "public" else "🔒"
        print(f"    {scope_icon} {p['port']:5d} - {p['service_name']} ({p['process']})")
    print()
    
    if ledger["unregistered"]:
        print("  ⚠️  未登记端口（需要识别）:")
        print(f"    {ledger['unregistered']}")
    print()
    
    print("  公网暴露风险评估:")
    unnecessary_public = [p for p in ledger["ports"] if p["scope"] == "public" and not p["must_public"]]
    print(f"    建议改为本地监听的端口: {len(unnecessary_public)}个")
    if unnecessary_public:
        print(f"    端口列表: {[p['port'] for p in unnecessary_public[:20]]}")
        if len(unnecessary_public) > 20:
            print(f"    ... 共{len(unnecessary_public)}个")
    print()
    print("=" * 70)

def main():
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "scan":
            print("【扫描】扫描所有监听端口...")
            ports = scan_ports()
            ledger = build_port_ledger(ports)
            print_ledger_summary(ledger)
            
            print("\n【写入】写入记忆网关...")
            if write_to_memory_gateway(ledger):
                print("  ✅ 端口台账已写入记忆网关")
            else:
                print("  ❌ 写入失败")
            return
        
        elif command == "allocate":
            if len(sys.argv) < 3:
                print("  用法: port_ledger.py allocate <服务名称> [描述]")
                return
            service_name = sys.argv[2]
            description = sys.argv[3] if len(sys.argv) > 3 else ""
            port = allocate_port(service_name, description)
            if port:
                print(f"\n  分配结果: 端口 {port}")
                print(f"  服务名称: {service_name}")
                print(f"  描述: {description}")
                print(f"  注意: 分配后请重新运行 scan 更新台账")
            return
        
        elif command == "show":
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT truth_value FROM truths WHERE truth_key = ?", (PORT_LEDGER_KEY,))
            row = cursor.fetchone()
            conn.close()
            if row:
                ledger = json.loads(row[0])
                print_ledger_summary(ledger)
                print("\n  完整端口列表:")
                for p in ledger["ports"]:
                    scope_icon = "🌐" if p["scope"] == "public" else "🔒"
                    reg_icon = "✅" if p["registered"] else "❓"
                    print(f"    {scope_icon}{reg_icon} {p['port']:5d} - {p['service_name'][:30]:30s} [{p['category']}]")
            else:
                print("  端口台账不存在，请先运行 scan")
            return
    
    # 默认：扫描+写入
    print("【扫描】扫描所有监听端口...")
    ports = scan_ports()
    ledger = build_port_ledger(ports)
    print_ledger_summary(ledger)
    
    print("\n【写入】写入记忆网关...")
    if write_to_memory_gateway(ledger):
        print("  ✅ 端口台账已写入记忆网关")
    else:
        print("  ❌ 写入失败")
    
    print(f"\n  用法:")
    print(f"    python3 port_ledger.py scan     # 扫描并更新台账")
    print(f"    python3 port_ledger.py show     # 显示当前台账")
    print(f"    python3 port_ledger.py allocate <服务名>  # 分配新端口")

if __name__ == "__main__":
    main()
