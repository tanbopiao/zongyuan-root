#!/usr/bin/env python3
"""
P1: 豆包云电脑→腾讯云正式服务器 真值自动同步脚本
用途：防止临时云电脑会话销毁导致数据丢失，自动将本地真值同步到腾讯云记忆网关9120
用法：python3 truth_sync_to_gateway.py [--dry-run] [--category <类别>] [--key <key>]
"""
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

# 配置
GATEWAY_URL = "http://127.0.0.1:9120"  # 通过SSH隧道访问腾讯云9120
SSH_TUNNEL_CMD = "ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=10 -L 9120:127.0.0.1:9120 root@123.207.202.158 -N"
NODE_ID = "doubao-cloud-dev-001"
SYNC_LOG_FILE = os.path.expanduser("~/truth_sync_log.json")

def get_sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def check_gateway():
    """检查记忆网关连通性"""
    try:
        req = urllib.request.Request(f"{GATEWAY_URL}/api/status")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("status") == "ok", data.get("stats", {})
    except Exception as e:
        return False, str(e)

def sync_truth(key, value, category="general", node_id=NODE_ID):
    """同步单条真值到记忆网关"""
    payload = json.dumps({
        "key": key,
        "value": value,
        "category": category,
        "node_id": node_id
    }).encode('utf-8')
    try:
        req = urllib.request.Request(
            f"{GATEWAY_URL}/api/truth/upsert",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("status") == "ok", result
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        return False, str(e)

def batch_sync(truths, dry_run=False):
    """批量同步真值"""
    results = {"success": [], "failed": [], "skipped": []}
    for t in truths:
        key = t.get("key")
        value = t.get("value", "")
        category = t.get("category", "general")
        if not key or not value:
            results["skipped"].append({"key": key, "reason": "key或value为空"})
            continue
        if dry_run:
            results["success"].append({"key": key, "category": category, "hash": get_sha256(value)[:16], "dry_run": True})
            continue
        ok, result = sync_truth(key, value, category)
        if ok:
            results["success"].append({"key": key, "category": category, "result": result})
        else:
            results["failed"].append({"key": key, "error": str(result)})
    return results

def load_local_truths():
    """从本地文件加载待同步真值"""
    truth_files = [
        os.path.expanduser("~/pending_truths.json"),
        os.path.expanduser("~/truths_to_sync.json"),
    ]
    truths = []
    for f in truth_files:
        if os.path.exists(f):
            try:
                with open(f, 'r') as fp:
                    data = json.load(fp)
                    if isinstance(data, list):
                        truths.extend(data)
                    elif isinstance(data, dict) and "truths" in data:
                        truths.extend(data["truths"])
            except Exception as e:
                print(f"[WARN] 读取 {f} 失败: {e}")
    return truths

def main():
    import argparse
    parser = argparse.ArgumentParser(description="真值自动同步到腾讯云记忆网关")
    parser.add_argument("--dry-run", action="store_true", help="仅检测不实际写入")
    parser.add_argument("--key", help="同步单条真值的key")
    parser.add_argument("--value", help="同步单条真值的value")
    parser.add_argument("--category", default="general", help="真值类别")
    parser.add_argument("--status", action="store_true", help="仅检查网关状态")
    args = parser.parse_args()

    print("=" * 60)
    print("P1: 豆包云电脑→腾讯云记忆网关 真值同步工具")
    print(f"时间: {datetime.now().isoformat()}")
    print(f"节点ID: {NODE_ID}")
    print("=" * 60)

    # 检查网关连通性
    ok, stats = check_gateway()
    if not ok:
        print(f"\n[ERROR] 记忆网关不可达: {stats}")
        print(f"请先建立SSH隧道: {SSH_TUNNEL_CMD}")
        sys.exit(1)
    print(f"\n[OK] 记忆网关连通正常")
    print(f"  真值总量: {stats.get('truths', '?')}")
    print(f"  节点数: {stats.get('nodes', '?')}")
    print(f"  审计日志: {stats.get('audit_logs', '?')}")

    if args.status:
        return

    # 单条同步
    if args.key and args.value:
        print(f"\n[INFO] 同步单条真值: {args.key}")
        ok, result = sync_truth(args.key, args.value, args.category)
        if ok:
            print(f"[OK] 同步成功: {json.dumps(result, ensure_ascii=False)[:200]}")
        else:
            print(f"[FAIL] 同步失败: {result}")
        return

    # 批量同步
    truths = load_local_truths()
    if not truths:
        print("\n[INFO] 未找到待同步真值文件（~/pending_truths.json 或 ~/truths_to_sync.json）")
        print("使用方式:")
        print("  1. 创建 ~/pending_truths.json，格式: [{\"key\":\"...\", \"value\":\"...\", \"category\":\"...\"}]")
        print("  2. 运行 python3 truth_sync_to_gateway.py")
        print("  3. 或单条同步: python3 truth_sync_to_gateway.py --key KEY --value VALUE --category CAT")
        return

    print(f"\n[INFO] 加载到 {len(truths)} 条待同步真值")
    results = batch_sync(truths, dry_run=args.dry_run)
    
    print(f"\n[同步结果]")
    print(f"  成功: {len(results['success'])}")
    print(f"  失败: {len(results['failed'])}")
    print(f"  跳过: {len(results['skipped'])}")
    
    if results["failed"]:
        print("\n[失败详情]")
        for f in results["failed"][:5]:
            print(f"  - {f['key']}: {f['error'][:100]}")

    # 记录同步日志
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "node_id": NODE_ID,
        "total": len(truths),
        "success": len(results["success"]),
        "failed": len(results["failed"]),
        "dry_run": args.dry_run
    }
    try:
        logs = []
        if os.path.exists(SYNC_LOG_FILE):
            with open(SYNC_LOG_FILE, 'r') as f:
                logs = json.load(f)
        logs.append(log_entry)
        with open(SYNC_LOG_FILE, 'w') as f:
            json.dump(logs[-100:], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] 日志写入失败: {e}")

if __name__ == "__main__":
    main()
