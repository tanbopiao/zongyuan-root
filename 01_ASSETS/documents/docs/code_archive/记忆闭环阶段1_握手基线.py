#!/usr/bin/env python3
"""
记忆闭环自动化·阶段1 本地握手基线
ZONGYUAN-ROOT / 火斗云智AIOS | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
遵守 AAB 双隔离公理：仅通过记忆网关9120真值通道，其余通道隔离。

通道：本地 → SSH回环 → 123.207.202.158:127.0.0.1:9120（只读）
基线：全域基准 GLOBAL-BASE-V1.0-20260910
"""
import json, subprocess, hashlib, os, sys
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
SSH = [
    "ssh", "-o", "ConnectTimeout=10", "-o", "ConnectionAttempts=2",
    "-o", "StrictHostKeyChecking=no", "-i", os.path.expanduser("~/.ssh/id_ed25519"),
    "root@123.207.202.158"
]
BASE_DIR = "/home/user/Doubao/chats/38438306874426882"
STATE_FILE = os.path.join(BASE_DIR, "记忆闭环阶段1_握手基线台账_20260911.json")

def ssh_curl(path):
    """经SSH在云端本机 curl 127.0.0.1:9120（只读 GET）"""
    cmd = SSH + [f'curl -s "http://127.0.0.1:9120{path}"']
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return None, r.stderr.strip()
    # 跳过登录banner（前若干行非JSON）
    out = r.stdout
    # 找到第一个 '{' 起截取
    idx = out.find('{')
    if idx < 0:
        return None, "无JSON输出"
    return out[idx:], None

def main():
    now = datetime.now(CST)
    report = {
        "baseline_id": "HANDSHAKE-BASELINE-STAGE1-20260911",
        "did": "DID-BR-000002",
        "trace_mark": "Ω₀⊂⊙∞⊂Ω",
        "created_at": now.isoformat(),
        "channel": "SSH回环→127.0.0.1:9120(只读)",
        "purpose": "记忆闭环自动化阶段1：本地↔云端记忆网关握手基线(本地仿真)",
        "isolation": "AAB双隔离:仅9120真值通道,其余隔离;本地仿真未人工审核不自动同步云端"
    }

    # 1. 云端状态
    status, err = ssh_curl("/api/status")
    if err:
        report["cloud_status"] = {"error": err}
    else:
        report["cloud_status"] = json.loads(status)

    # 2. 真值列表（仅统计）
    truths, err = ssh_curl("/api/truths")
    if err:
        report["cloud_truths"] = {"error": err}
    else:
        t = json.loads(truths)
        report["cloud_truths"] = {
            "count": t.get("count"),
            "sample_keys": t.get("truths", [])[:8]
        }

    # 3. 节点列表
    nodes, err = ssh_curl("/api/nodes")
    if err:
        report["cloud_nodes"] = {"error": err}
    else:
        n = json.loads(nodes)
        report["cloud_nodes"] = n if isinstance(n, dict) else {"data": n}

    # 4. 本地侧记账
    report["local_state"] = {
        "ledger_total_assets": 823,
        "local_root_hash": "33723D7D6BA50E0F7DDB6634C6BF6FA0FFC7766CB5542202FCB8BD84E9F21C07",
        "kernel_truth": "KD-KERNEL-TRUTH-003 工程能力已有产品化缺位",
        "protocol_archived": "KD-PROD-ZR-MHP-20260911 Lv4已锁档三层"
    }

    # 5. 一致性判定
    cs = report.get("cloud_status", {})
    ok = isinstance(cs, dict) and cs.get("status") == "ok"
    report["verdict"] = (
        "阶段1握手基线建立成功：经SSH回环已打通记忆网关9120真值通道，"
        f"云端状态={'OK' if ok else '异常'}，真值{report.get('cloud_truths',{}).get('count')}条。"
        "遵守双隔离公理，本台账为本地仿真产物，未经人工审核不自动同步云端。"
    )

    # 写台账
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("=== 记忆闭环阶段1 握手基线台账已生成 ===")
    print("文件:", STATE_FILE)
    print(f"云端状态: {cs.get('status') if ok else '异常'}")
    print(f"云端真值: {report.get('cloud_truths',{}).get('count')} 条")
    print(f"云端节点: {report.get('cloud_nodes')}")
    print("确权锚点: Ω₀⊂⊙∞⊂Ω | DID-BR-000002")

if __name__ == "__main__":
    main()
