#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 体系状态快照
每日全量记录体系状态，用于回退检测和恢复参考
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import subprocess
import sqlite3
from datetime import datetime

BASE = "/opt/ZONGYUAN-ROOT"
SNAPSHOT_DIR = os.path.join(BASE, "archive/system_snapshots")

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except:
        return ""

def snapshot():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    data = {
        "timestamp": datetime.now().isoformat(),
        "did": "DID-BR-000002",
        "anchor": "Ω₀⊂⊙∞⊂Ω",
        "system": {
            "hostname": run("hostname"),
            "uptime": run("uptime -p"),
            "kernel": run("uname -r"),
        },
        "resources": {
            "memory": run("free -m | awk 'NR==2{printf \"%d/%dMB (%.1f%%)\", $3,$2,$3/$2*100}'"),
            "disk": run("df -h / | tail -1 | awk '{print $3\"/\"$2\" (\"$5\")\"}'"),
            "load": run("cat /proc/loadavg | awk '{print $1,$2,$3}'"),
        },
        "services": {},
        "ports": {},
        "data": {},
        "security": {},
        "cron": {},
    }
    
    # 核心服务状态
    core_services = [
        "zongyuan-unified-gateway", "zongyuan-vector-server", "zongyuan-local-llm",
        "zongyuan-rag", "self-healing-engine", "zongyuan-healing-bridge",
        "dr-self-healing-monitor", "closed-loop-scheduler", "zongyuan-decision-formula",
        "zongyuan-operator-panel", "nginx", "kg-api", "zongyuan-meta-evolution",
        "zongyuan-honeypot", "dynamic-ip-manager", "dr-resource-monitor",
        "dr-truth-absorber", "zongyuan-meta-evolution",
    ]
    for svc in core_services:
        data["services"][svc] = {
            "active": run("systemctl is-active %s" % svc),
            "enabled": run("systemctl is-enabled %s" % svc),
        }
    
    # 关键端口
    ports = [9120, 8014, 8081, 8085, 8161, 8170, 8180, 8094, 8070, 2222, 80, 443, 22]
    for p in ports:
        data["ports"][p] = "LISTEN" if ":%d " % p in run("ss -tlnp") else "CLOSED"
    
    # 数据状态
    try:
        conn = sqlite3.connect(os.path.join(BASE, "data/memory_gateway.db"))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM truths")
        data["data"]["truth_count"] = c.fetchone()[0]
        c.execute("SELECT category, COUNT(*) FROM truths GROUP BY category")
        data["data"]["truth_by_category"] = dict(c.fetchall())
        conn.close()
    except:
        pass
    
    # 元法则
    try:
        with open(os.path.join(BASE, "meta_rule_set.json")) as f:
            mr = json.load(f)
        data["data"]["meta_law_version"] = mr.get("version")
        data["data"]["meta_law_count"] = mr.get("count")
    except:
        pass
    
    # Merkle链
    try:
        with open(os.path.join(BASE, "kernel/merkle_chain_state.json")) as f:
            mc = json.load(f)
        chain = mc.get("chain", [])
        if chain:
            data["data"]["merkle_blocks"] = len(chain)
            data["data"]["merkle_integrity"] = chain[-1].get("integrity_percent")
    except:
        pass
    
    # 安全
    data["security"]["iptables_input_policy"] = run("iptables -L INPUT -n | head -1 | grep -o 'policy [A-Z]*'")
    data["security"]["iptables_rules"] = run("iptables -L INPUT -n | wc -l")
    data["security"]["ssh_keys"] = run("grep -c '^ssh-' /root/.ssh/authorized_keys")
    
    # cron
    data["cron"]["total_tasks"] = run("crontab -l | grep -v '^#' | grep -v '^$' | wc -l")
    
    # 保存
    filepath = os.path.join(SNAPSHOT_DIR, "snapshot_%s.json" % ts)
    with open(filepath, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 保留最近30个快照
    snapshots = sorted(os.listdir(SNAPSHOT_DIR))
    for old in snapshots[:-30]:
        os.remove(os.path.join(SNAPSHOT_DIR, old))
    
    print("快照已保存: %s" % filepath)
    print("  服务: %d个, 端口: %d个, 真值: %d条, 元法则: %s" % (
        len(data["services"]), len(data["ports"]),
        data["data"].get("truth_count", 0),
        data["data"].get("meta_law_count", "?")
    ))
    return filepath

if __name__ == '__main__':
    snapshot()
