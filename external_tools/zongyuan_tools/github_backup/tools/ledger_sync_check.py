#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 凭证文件→M9台账汇总字段自动同步巡检脚本
机制编号: AUTO-SYNC-001
功能: 比对凭证文件数与台账total_assets, 不一致时以真实链尾为准同步刷新台账
用法: python3 ledger_sync_check.py [--locked-dir <path>] [--dry-run]
"""
import json, os, hashlib, datetime, argparse, sys
from collections import Counter

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

def sha256_string(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest().upper()

def main():
    parser = argparse.ArgumentParser(description="凭证→台账自动同步巡检")
    parser.add_argument("--locked-dir", default=None, help="locked目录路径")
    parser.add_argument("--dry-run", action="store_true", help="仅检测不修改")
    args = parser.parse_args()

    # 自动探测locked目录
    if args.locked_dir:
        locked = args.locked_dir
    else:
        candidates = [
            "/home/user/.doubao/agent_mode/workspace/.user_skills/meta-order-archive/locked",
            "/home/user/.super_doubao/super-doubao-runtime/workspace/.user_skills/meta-order-archive/locked",
        ]
        locked = None
        for c in candidates:
            if os.path.isfile(os.path.join(c, "M9_global_ledger.json")):
                locked = c
                break
        if not locked:
            print("❌ 未找到locked目录,请使用--locked-dir指定")
            sys.exit(1)

    now = datetime.datetime.now(datetime.timezone.utc)
    ledger_path = os.path.join(locked, "M9_global_ledger.json")

    # 步骤1: 统计凭证文件
    cred_files = [f for f in os.listdir(locked) if f.endswith("_credential.json")]
    actual_count = len(cred_files)

    # 步骤2: 读取台账
    with open(ledger_path, encoding="utf-8") as f:
        ledger = json.load(f)
    ledger_count = ledger.get("total_assets", 0)
    ledger_root = ledger.get("current_root_hash", "")

    print(f"=== ZONGYUAN-ROOT 台账同步巡检 ===")
    print(f"时间: {now.isoformat()[:19]} UTC")
    print(f"目录: {locked}")
    print(f"凭证文件数: {actual_count}")
    print(f"台账total_assets: {ledger_count}")
    print(f"差异: {actual_count - ledger_count}")

    # 步骤3: 找真实链尾
    latest = None
    latest_time = ""
    for fn in cred_files:
        try:
            with open(os.path.join(locked, fn), encoding="utf-8") as f:
                c = json.load(f)
            ct = c.get("created_at", "")
            if ct > latest_time:
                latest_time = ct
                latest = c
        except:
            pass

    if not latest:
        print("❌ 未找到任何凭证文件")
        sys.exit(1)

    real_root = latest["new_root_hash"]
    print(f"真实链尾: {latest['asset_id']} | {real_root[:16]}... | {latest_time[:16]}")
    print(f"台账根哈希: {ledger_root[:16]}...")
    print(f"根哈希匹配: {'✅' if ledger_root.upper() == real_root.upper() else '❌ 不一致'}")

    # 步骤4: 比对
    if actual_count == ledger_count and ledger_root.upper() == real_root.upper():
        print("\n✅ 台账已同步,无需操作")
        return {"status": "SYNCED", "actual": actual_count, "ledger": ledger_count, "diff": 0}

    diff = actual_count - ledger_count
    print(f"\n⚠️  检测到差异: {diff}项,执行同步...")

    if args.dry_run:
        print("(dry-run模式,不修改台账)")
        return {"status": "DRY_RUN", "actual": actual_count, "ledger": ledger_count, "diff": diff}

    # 步骤5: 重新统计元类
    meta_counter = Counter()
    for fn in cred_files:
        try:
            with open(os.path.join(locked, fn), encoding="utf-8") as f:
                c = json.load(f)
            mc = c.get("meta_class")
            if isinstance(mc, str):
                meta_counter[mc] += 1
        except:
            pass

    # 步骤6: 更新台账
    ledger["total_assets"] = actual_count
    ledger["current_root_hash"] = real_root
    ledger["last_updated"] = now.isoformat()
    ledger["meta_class_stats"] = dict(meta_counter)
    ledger["sync_note"] = f"自动同步巡检触发,差异{diff}项已修复,链尾{latest['asset_id']}"

    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 台账已同步:")
    print(f"  total_assets: {ledger_count} → {actual_count}")
    print(f"  current_root_hash: {ledger_root[:16]}... → {real_root[:16]}...")
    print(f"  meta_class_stats: {json.dumps(dict(meta_counter), ensure_ascii=False)}")
    print(f"  last_updated: {now.isoformat()[:19]}")
    print(f"  DID: {DID} | 溯源: {TRACE}")

    return {"status": "SYNCED", "actual": actual_count, "ledger": ledger_count, "diff": diff, "real_root": real_root}

if __name__ == "__main__":
    result = main()
    print(f"\n结果: {json.dumps(result, ensure_ascii=False)}")
