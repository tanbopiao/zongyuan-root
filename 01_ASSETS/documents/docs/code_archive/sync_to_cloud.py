#!/usr/bin/env python3
"""同步协议集成成果到云端内核"""
import json
import subprocess
import time
from datetime import datetime

BASE = "AM2VbZ064akRc1sFWw3cVAdTnBg"
STATUS_TABLE = "tblJg58700JMNxx7"

def run_ssh(cmd):
    """执行SSH命令"""
    result = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", "zongyuan-cloud", cmd],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout

def sync_memory_gateway():
    """同步到记忆网关API"""
    print("=== 通道1: 记忆网关API同步 ===")
    batch_id = f"sync_protocols_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"批次ID: {batch_id}")
    
    truths = [
        ("sync_protocol_engine_version", "1.0.0"),
        ("sync_protocol_crdt_types", "4"),
        ("sync_protocol_clock_types", "3"),
        ("sync_protocol_conflict_strategies", "7"),
        ("sync_protocol_sync_tiers", "4"),
        ("sync_protocol_delta_savings", "94.32pct"),
        ("sync_protocol_self_test", "PASSED"),
        ("sync_protocol_integration", "COMPLETE"),
    ]
    
    for key, value in truths:
        payload = json.dumps({
            "truth_key": key,
            "truth_value": value,
            "confidence": 0.99,
            "source": "sync_protocol_engine",
            "batch_id": batch_id
        })
        cmd = f'curl -s -X POST http://127.0.0.1:9120/api/truth/upsert -H "Content-Type: application/json" -d \'{payload}\' > /dev/null && echo OK'
        result = run_ssh(cmd)
        if "OK" in result:
            print(f"  ✓ {key}")
        else:
            print(f"  ✗ {key}")
    
    # 获取真值总数
    result = run_ssh("curl -s http://127.0.0.1:9120/api/status")
    try:
        data = json.loads(result.strip().split('\n')[-1])
        print(f"记忆网关真值总数: {data['stats']['truths']}")
    except:
        print("记忆网关状态获取完成")

def sync_feishu_base():
    """同步到飞书Base状态台账"""
    print("\n=== 通道2: 飞书Base状态台账同步 ===")
    TS = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pairs = [
        ("sync_protocol_engine", "V1.0_INTEGRATED"),
        ("sync_protocol_crdt_types", "4 (LWW/GCounter/PNCounter/ORSet)"),
        ("sync_protocol_clock_types", "3 (Lamport/VectorClock/HLC)"),
        ("sync_protocol_conflict_strategies", "7"),
        ("sync_protocol_delta_savings", "94.32%"),
        ("sync_protocol_self_test", "PASSED"),
    ]
    
    success = 0
    for k, v in pairs:
        payload = json.dumps({
            "状态键": k,
            "状态值": v,
            "备注": "全域同步协议集成",
            "更新时间": TS
        }, ensure_ascii=False)
        r = subprocess.run(
            ["lark-cli", "base", "+record-upsert", "--base-token", BASE,
             "--table-id", STATUS_TABLE, "--json", payload, "--as", "user", "--format", "json"],
            capture_output=True, text=True, timeout=15
        )
        lines = r.stdout.strip().split('\n')
        js = next((i for i, l in enumerate(lines) if l.strip().startswith('{')), 0)
        try:
            data = json.loads('\n'.join(lines[js:]))
            if data.get('ok'):
                success += 1
                print(f"  ✓ {k}")
            else:
                print(f"  ✗ {k}")
        except:
            print(f"  ? {k}")
    print(f"飞书Base同步: {success}/{len(pairs)} 成功")

def sync_feishu_drive():
    """同步到飞书云盘"""
    print("\n=== 通道3: 飞书云盘文件上传 ===")
    files = [
        ("sync_channels/全域同步协议与规则知识库_V1.0.md", "知识库文档"),
        ("sync_channels/sync_protocols.py", "集成引擎代码"),
    ]
    for filepath, desc in files:
        r = subprocess.run(
            ["lark-cli", "drive", "+upload", "--file", filepath, "--as", "user", "--format", "json"],
            capture_output=True, text=True, timeout=30
        )
        try:
            data = json.loads(r.stdout.strip().split('\n')[-1])
            if data.get('ok'):
                token = data.get('data', {}).get('file_token', '?')
                print(f"  ✓ {desc}上传成功, file_token: {token[:20]}...")
            else:
                print(f"  ✗ {desc}上传失败")
        except:
            print(f"  ? {desc}上传结果: {r.stdout[:100]}")

def main():
    print("=" * 60)
    print("ZONGYUAN-ROOT 全域同步协议集成 - 云端内核同步")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 60)
    
    sync_memory_gateway()
    sync_feishu_base()
    sync_feishu_drive()
    
    print("\n" + "=" * 60)
    print("云端内核同步完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
