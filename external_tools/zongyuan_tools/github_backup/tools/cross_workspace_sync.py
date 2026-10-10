#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 跨工作区资产自动同步脚本
机制编号: CROSS-WS-SYNC-001
功能: 双向同步两个工作区间的locked目录资产,以内容SHA256为唯一标识
用法: python3 cross_workspace_sync.py [--ws-a <path>] [--ws-b <path>] [--dry-run]
"""
import json, os, hashlib, datetime, argparse, sys, shutil

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

DEFAULT_WS_A = "/home/user/.doubao/agent_mode/workspace/.user_skills/meta-order-archive/locked"
DEFAULT_WS_B = "/home/user/.super_doubao/super-doubao-runtime/workspace/.user_skills/meta-order-archive/locked"

def scan_workspace(locked_dir):
    """扫描工作区,返回 {asset_hash: {cred_path, content_path, cred}}"""
    assets = {}
    if not os.path.isdir(locked_dir):
        return assets
    for fn in os.listdir(locked_dir):
        if fn.endswith("_credential.json"):
            try:
                cred_path = os.path.join(locked_dir, fn)
                with open(cred_path, encoding="utf-8") as f:
                    cred = json.load(f)
                ah = cred.get("asset_hash", "")
                if ah:
                    content_fn = fn.replace("_credential.json", "_content.txt")
                    content_path = os.path.join(locked_dir, content_fn)
                    assets[ah] = {
                        "cred_path": cred_path,
                        "content_path": content_path if os.path.exists(content_path) else None,
                        "cred": cred,
                        "asset_id": cred.get("asset_id", ""),
                        "asset_name": cred.get("asset_name", ""),
                    }
            except:
                pass
    return assets

def copy_asset(asset, target_dir):
    """复制资产到目标工作区"""
    cred = asset["cred"]
    aid = cred["asset_id"]
    # 复制凭证
    target_cred = os.path.join(target_dir, f"{aid}_credential.json")
    with open(target_cred, "w", encoding="utf-8") as f:
        json.dump(cred, f, ensure_ascii=False, indent=2)
    # 复制内容
    if asset["content_path"] and os.path.exists(asset["content_path"]):
        target_content = os.path.join(target_dir, f"{aid}_content.txt")
        shutil.copy2(asset["content_path"], target_content)
    return True

def main():
    parser = argparse.ArgumentParser(description="跨工作区资产自动同步")
    parser.add_argument("--ws-a", default=DEFAULT_WS_A, help="工作区A locked目录")
    parser.add_argument("--ws-b", default=DEFAULT_WS_B, help="工作区B locked目录")
    parser.add_argument("--dry-run", action="store_true", help="仅检测不复制")
    args = parser.parse_args()

    now = datetime.datetime.now(datetime.timezone.utc)
    print(f"=== ZONGYUAN-ROOT 跨工作区资产同步 ===")
    print(f"时间: {now.isoformat()[:19]} UTC")
    print(f"WS-A: {args.ws_a}")
    print(f"WS-B: {args.ws_b}")

    # 扫描两个工作区
    assets_a = scan_workspace(args.ws_a)
    assets_b = scan_workspace(args.ws_b)
    print(f"\nWS-A资产数: {len(assets_a)}")
    print(f"WS-B资产数: {len(assets_b)}")

    # 找出差异
    only_a = set(assets_a.keys()) - set(assets_b.keys())
    only_b = set(assets_b.keys()) - set(assets_a.keys())
    common = set(assets_a.keys()) & set(assets_b.keys())

    print(f"\n共有资产: {len(common)}")
    print(f"仅WS-A有(需同步到B): {len(only_a)}")
    print(f"仅WS-B有(需同步到A): {len(only_b)}")

    if only_a:
        print(f"\n--- 仅WS-A有的资产 ---")
        for h in list(only_a)[:10]:
            a = assets_a[h]
            print(f"  {a['asset_id']} | {h[:10]} | {a['asset_name'][:40]}")
        if len(only_a) > 10:
            print(f"  ...共{len(only_a)}项")

    if only_b:
        print(f"\n--- 仅WS-B有的资产 ---")
        for h in list(only_b)[:10]:
            b = assets_b[h]
            print(f"  {b['asset_id']} | {h[:10]} | {b['asset_name'][:40]}")
        if len(only_b) > 10:
            print(f"  ...共{len(only_b)}项")

    if args.dry_run:
        print(f"\n(dry-run模式,不执行复制)")
        return {"status": "DRY_RUN", "only_a": len(only_a), "only_b": len(only_b)}

    # 执行同步
    copied_a_to_b = 0
    copied_b_to_a = 0

    for h in only_a:
        try:
            if copy_asset(assets_a[h], args.ws_b):
                copied_a_to_b += 1
        except Exception as e:
            print(f"  ❌ 复制失败 {assets_a[h]['asset_id']}: {e}")

    for h in only_b:
        try:
            if copy_asset(assets_b[h], args.ws_a):
                copied_b_to_a += 1
        except Exception as e:
            print(f"  ❌ 复制失败 {assets_b[h]['asset_id']}: {e}")

    print(f"\n✅ 同步完成:")
    print(f"  WS-A → WS-B: {copied_a_to_b}项")
    print(f"  WS-B → WS-A: {copied_b_to_a}项")
    print(f"  DID: {DID} | 溯源: {TRACE}")

    # 验证
    assets_a2 = scan_workspace(args.ws_a)
    assets_b2 = scan_workspace(args.ws_b)
    print(f"\n同步后: WS-A={len(assets_a2)} WS-B={len(assets_b2)}")
    remaining_diff = len(set(assets_a2.keys()) ^ set(assets_b2.keys()))
    print(f"剩余差异: {remaining_diff}")

    return {"status": "SYNCED", "copied_a_to_b": copied_a_to_b, "copied_b_to_a": copied_b_to_a, "remaining_diff": remaining_diff}

if __name__ == "__main__":
    result = main()
    print(f"\n结果: {json.dumps(result, ensure_ascii=False)}")
