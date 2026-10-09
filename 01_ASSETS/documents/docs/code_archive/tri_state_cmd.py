#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜三态指令发送工具
功能：构造并下发三态驱动指令（逻辑态+信息态+能量态），验证完整裁决-执行-反馈链路
用法：python3 tri_state_cmd.py <action> [--priority high] [--target node-01]
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""

import sys
import json
import time
import hashlib
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()
CONFIG_DIR = BASE_DIR / "config"
PENDING_CMD = CONFIG_DIR / "pending_cmd.json"

# 允许的动作
ALLOWED_ACTIONS = [
    "SCAN_ASSET", "RUN_PIPELINE", "CROSS_VERIFY",
    "SYNC_LEDGER", "RELOAD_META_RULE", "STOP_WORKER",
    "TRUTH_REPORT", "BACKUP_NOW", "RESTORE_NOW"
]

# 优先级
PRIORITIES = ["critical", "high", "normal", "low"]


def build_tri_state_command(action, priority="normal", target="ALL", payload=None):
    """构造完整的三态指令包"""
    cmd_id = f"CMD-{int(time.time())}-{hashlib.md5(f'{action}{time.time()}'.encode()).hexdigest()[:8]}"

    # 逻辑态：裁决与决策
    logic_state = {
        "allow_execute": True,
        "source": "manual",
        "priority": priority,
        "target_node": target,
        "requires_approval": False,
        "rule_version": "v1.0",
    }

    # 信息态：数据与真值载荷
    info_state = {
        "action": action,
        "payload": payload or {},
        "confidence": 0.95,
        "timestamp": time.time(),
        "content_hash": hashlib.sha256(json.dumps({"action": action, "payload": payload or {}}, sort_keys=True).encode()).hexdigest(),
    }

    # 能量态：资源配额
    energy_state = {
        "priority_level": PRIORITIES.index(priority),
        "base_quota": {
            "cpu_budget_percent": 20 if priority != "critical" else 50,
            "mem_budget_mb": 512 if priority != "critical" else 1024,
            "timeout_seconds": 300 if priority != "critical" else 600,
            "max_retries": 3,
        },
        "fuse_override": priority == "critical",  # 紧急优先级可覆盖熔断
    }

    return {
        "cmd_id": cmd_id,
        "logic_state": logic_state,
        "info_state": info_state,
        "energy_state": energy_state,
        "created_at": time.time(),
        "did": "DID-BR-000002",
        "trace": "Ω₀⊂⊙∞⊂Ω",
    }


def send_command(cmd):
    """下发指令到Worker的待执行队列"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(PENDING_CMD, "w", encoding="utf-8") as f:
        json.dump(cmd, f, ensure_ascii=False, indent=2)
    return PENDING_CMD.exists()


def main():
    parser = argparse.ArgumentParser(description="元极恒一三态指令发送工具")
    parser.add_argument("action", choices=ALLOWED_ACTIONS, help="指令动作")
    parser.add_argument("--priority", choices=PRIORITIES, default="normal", help="优先级")
    parser.add_argument("--target", default="ALL", help="目标节点")
    parser.add_argument("--payload", default="{}", help="载荷JSON")
    parser.add_argument("--dry-run", action="store_true", help="仅打印指令不下发")
    args = parser.parse_args()

    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError:
        print("❌ payload JSON格式错误")
        sys.exit(1)

    # 构造指令
    cmd = build_tri_state_command(args.action, args.priority, args.target, payload)

    print("=" * 60)
    print("元极恒一｜三态指令发送工具")
    print("=" * 60)
    print(f"指令ID: {cmd['cmd_id']}")
    print(f"动作: {args.action}")
    print(f"优先级: {args.priority}")
    print(f"目标: {args.target}")
    print()

    print("--- 逻辑态 (Logic State) ---")
    print(json.dumps(cmd["logic_state"], indent=2, ensure_ascii=False))
    print()

    print("--- 信息态 (Info State) ---")
    print(f"  动作: {cmd['info_state']['action']}")
    print(f"  置信度: {cmd['info_state']['confidence']}")
    print(f"  内容哈希: {cmd['info_state']['content_hash'][:32]}...")
    print(f"  载荷: {json.dumps(cmd['info_state']['payload'], ensure_ascii=False)}")
    print()

    print("--- 能量态 (Energy State) ---")
    print(f"  优先级级别: {cmd['energy_state']['priority_level']}")
    print(f"  CPU预算: {cmd['energy_state']['base_quota']['cpu_budget_percent']}%")
    print(f"  内存预算: {cmd['energy_state']['base_quota']['mem_budget_mb']}MB")
    print(f"  超时: {cmd['energy_state']['base_quota']['timeout_seconds']}s")
    print(f"  熔断覆盖: {cmd['energy_state']['fuse_override']}")
    print()

    if args.dry_run:
        print("⚠️  Dry-run模式，指令未下发")
        print("=" * 60)
        return

    # 下发指令
    if send_command(cmd):
        print(f"✅ 指令已下发到: {PENDING_CMD}")
        print(f"   Worker将在下一个主循环（约30秒内）消费此指令")
        print(f"   可通过仪表盘 /api/audit 查看执行结果")
    else:
        print("❌ 指令下发失败")
        sys.exit(1)

    print("=" * 60)


if __name__ == "__main__":
    main()
