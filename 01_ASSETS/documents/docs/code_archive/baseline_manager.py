#!/usr/bin/env python3
"""
系统基准固化管理工具 v1.0
功能: 基准快照生成 / 基准验证 / 偏离报告 / 基准更新审批
用途: 固化成型的系统骨架，防止误改，迭代走审批
"""

import json
import hashlib
import os
import subprocess
import sys
from datetime import datetime

BASELINE_DIR = "/opt/ZONGYUAN-ROOT/baseline"
BASELINE_FILE = os.path.join(BASELINE_DIR, "system_baseline.json")
LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/baseline_verify.log"

# 基准监控的核心文件（骨架文件，修改必须审批）
CORE_FILES = [
    "/opt/ZONGYUAN-ROOT/meta_rule_set.json",
    "/opt/ZONGYUAN-ROOT/config/chattr_whitelist.json",
    "/opt/ZONGYUAN-ROOT/config/iptables_rules.rules",
    "/opt/ZONGYUAN-ROOT/scripts/port_ledger.py",
    "/opt/ZONGYUAN-ROOT/scripts/port_change_approval.py",
    "/opt/ZONGYUAN-ROOT/scripts/change_manager.py",
    "/opt/ZONGYUAN-ROOT/scripts/unified_service_guard.sh",
    "/opt/ZONGYUAN-ROOT/scripts/restore_iptables.sh",
    "/opt/ZONGYUAN-ROOT/scripts/chattr_safe.sh",
    "/opt/ZONGYUAN-ROOT/scripts/kernel_health_monitor.py",
    "/opt/ZONGYUAN-ROOT/scripts/realtime_alert.py",
    "/opt/ZONGYUAN-ROOT/scripts/merkle_chain_maintainer.py",
    "/opt/ZONGYUAN-ROOT/scripts/feishu_approval_callback.py",
    "/opt/ZONGYUAN-ROOT/scripts/approval_bridge.py",
    "/opt/ZONGYUAN-ROOT/scripts/intelligent_approval_engine.py",
    "/opt/ZONGYUAN-ROOT/scripts/intelligent_approval_daemon.py",
    "/etc/ssh/sshd_config",
    "/etc/hosts.allow",
]

# 基准监控的核心服务（端口:名称）
CORE_SERVICES = {
    "9120": "记忆网关",
    "9122": "通信协议网关",
    "9125": "希尔伯特镜像态",
    "9151": "GEO晶格",
    "9160": "量子纠缠层",
    "8001": "飞书网关",
    "8081": "本地LLM",
    "8060": "审批回调",
    "8061": "审批引擎",
    "8014": "向量数据库",
    "8161": "自愈引擎",
    "8085": "RAG服务",
    "8094": "闭环调度器",
    "8100": "短剧管理API",
}


def file_hash(filepath):
    """计算文件SHA256哈希"""
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def get_listening_ports():
    """获取当前监听的端口列表"""
    result = subprocess.run(
        ["ss", "-tlnp"],
        capture_output=True, text=True, timeout=10
    )
    ports = {}
    for line in result.stdout.split("\n")[1:]:
        parts = line.split()
        if len(parts) >= 4:
            addr = parts[3]
            if ":" in addr:
                port = addr.split(":")[-1]
                ports[port] = addr
    return ports


def generate_baseline():
    """生成系统基准快照"""
    os.makedirs(BASELINE_DIR, exist_ok=True)

    baseline = {
        "baseline_version": "v1.0",
        "created_at": datetime.now().isoformat(),
        "created_by": "DID-BR-000002",
        "description": "系统基准快照 - 成型骨架固化，修改需审批",

        # 核心文件哈希
        "core_files": {},
        # 核心服务端口
        "core_services": CORE_SERVICES,
        # 当前监听端口
        "listening_ports": get_listening_ports(),
        # 元法则数量
        "meta_rule_count": 0,
        # 记忆网关真值数
        "truth_count": 0,
    }

    # 计算核心文件哈希
    for f in CORE_FILES:
        baseline["core_files"][f] = file_hash(f)

    # 元法则数量
    try:
        with open("/opt/ZONGYUAN-ROOT/meta_rule_set.json") as f:
            rules = json.load(f)
            if isinstance(rules, list):
                baseline["meta_rule_count"] = len(rules)
            elif isinstance(rules, dict):
                baseline["meta_rule_count"] = len(rules.get("rules", rules.get("meta_rules", [])))
    except Exception:
        pass

    # 记忆网关真值数
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:9120/api/status")
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        baseline["truth_count"] = data.get("stats", {}).get("truths", 0)
    except Exception:
        pass

    # 保存基准
    with open(BASELINE_FILE, "w") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)

    # 计算基准自身的哈希（用于防篡改）
    baseline_hash = file_hash(BASELINE_FILE)
    baseline["baseline_hash"] = baseline_hash

    with open(BASELINE_FILE, "w") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)

    print(f"✅ 基准快照已生成: {BASELINE_FILE}")
    print(f"   基准版本: {baseline['baseline_version']}")
    print(f"   核心文件: {len(baseline['core_files'])}个")
    print(f"   核心服务: {len(baseline['core_services'])}个")
    print(f"   监听端口: {len(baseline['listening_ports'])}个")
    print(f"   元法则: {baseline['meta_rule_count']}条")
    print(f"   真值数: {baseline['truth_count']}条")
    print(f"   基准哈希: {baseline_hash}")

    return baseline


def verify_baseline():
    """验证系统是否偏离基准"""
    if not os.path.exists(BASELINE_FILE):
        print("❌ 基准文件不存在，请先生成基准")
        return False

    with open(BASELINE_FILE) as f:
        baseline = json.load(f)

    deviations = []
    warnings = []

    # 1. 检查核心文件哈希
    print("【1/4】检查核心文件完整性...")
    for filepath, expected_hash in baseline["core_files"].items():
        current_hash = file_hash(filepath)
        if current_hash == "FILE_NOT_FOUND":
            deviations.append(f"文件丢失: {filepath}")
        elif current_hash != expected_hash:
            deviations.append(f"文件被修改: {filepath} (期望{expected_hash[:8]}, 实际{current_hash[:8]})")

    # 2. 检查核心服务端口
    print("【2/4】检查核心服务端口...")
    current_ports = get_listening_ports()
    for port, name in baseline["core_services"].items():
        if port not in current_ports:
            deviations.append(f"服务端口未监听: {name} ({port})")

    # 3. 检查基准文件自身是否被篡改
    print("【3/4】检查基准文件完整性...")
    stored_hash = baseline.get("baseline_hash", "")
    # 重新计算（排除baseline_hash字段）
    baseline_copy = {k: v for k, v in baseline.items() if k != "baseline_hash"}
    temp_file = BASELINE_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(baseline_copy, f, indent=2, ensure_ascii=False)
    current_hash = file_hash(temp_file)
    os.remove(temp_file)
    if stored_hash and current_hash != stored_hash:
        warnings.append(f"基准文件可能被篡改 (期望{stored_hash[:8]}, 实际{current_hash[:8]})")

    # 4. 检查元法则数量
    print("【4/4】检查元法则数量...")
    try:
        with open("/opt/ZONGYUAN-ROOT/meta_rule_set.json") as f:
            rules = json.load(f)
            current_count = len(rules) if isinstance(rules, list) else len(rules.get("rules", []))
        expected_count = baseline["meta_rule_count"]
        if current_count != expected_count:
            warnings.append(f"元法则数量变化: 基准{expected_count}条, 当前{current_count}条")
    except Exception:
        pass

    # 输出报告
    print("\n" + "=" * 60)
    print("基准验证报告")
    print("=" * 60)
    print(f"基准版本: {baseline['baseline_version']}")
    print(f"基准时间: {baseline['created_at']}")
    print(f"验证时间: {datetime.now().isoformat()}")
    print()

    if deviations:
        print(f"❌ 发现 {len(deviations)} 项严重偏离:")
        for d in deviations:
            print(f"   - {d}")
    else:
        print("✅ 核心文件和服务无偏离")

    if warnings:
        print(f"\n⚠️  发现 {len(warnings)} 项警告:")
        for w in warnings:
            print(f"   - {w}")

    if not deviations and not warnings:
        print("\n🎉 系统与基准完全一致，骨架固化完好！")
        result = "PASS"
    elif deviations:
        result = "FAIL"
    else:
        result = "WARN"

    # 记录日志
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} | {result} | deviations={len(deviations)} warnings={len(warnings)}\n")

    return len(deviations) == 0


def show_baseline():
    """显示当前基准信息"""
    if not os.path.exists(BASELINE_FILE):
        print("❌ 基准文件不存在")
        return

    with open(BASELINE_FILE) as f:
        baseline = json.load(f)

    print("=" * 60)
    print("系统基准快照")
    print("=" * 60)
    print(f"版本: {baseline['baseline_version']}")
    print(f"创建时间: {baseline['created_at']}")
    print(f"基准哈希: {baseline.get('baseline_hash', 'N/A')}")
    print()
    print(f"核心文件 ({len(baseline['core_files'])}个):")
    for f, h in baseline["core_files"].items():
        print(f"  {h[:8]}  {os.path.basename(f)}")
    print()
    print(f"核心服务 ({len(baseline['core_services'])}个):")
    for port, name in baseline["core_services"].items():
        print(f"  {port:6}  {name}")
    print()
    print(f"元法则: {baseline['meta_rule_count']}条")
    print(f"真值数: {baseline['truth_count']}条")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 baseline_manager.py generate  - 生成基准快照")
        print("  python3 baseline_manager.py verify    - 验证系统基准")
        print("  python3 baseline_manager.py show      - 显示当前基准")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "generate":
        generate_baseline()
    elif cmd == "verify":
        verify_baseline()
    elif cmd == "show":
        show_baseline()
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)
