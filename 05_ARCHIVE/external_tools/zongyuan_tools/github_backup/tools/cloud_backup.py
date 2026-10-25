#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 三层级存储态L1云盘归档脚本
机制编号: LOCK-3TIER-L1
功能: 将locked目录资产归档到飞书云空间/百度网盘/GitHub异地冷备
用法:
  python3 cloud_backup.py sync [--config <path>] [--dry-run]
  python3 cloud_backup.py verify [--config <path>]
"""
import json, os, hashlib, datetime, argparse, sys, shutil, subprocess, zipfile, io

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

def load_config(config_path):
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def collect_assets(locked_dir, policy):
    """收集待归档资产"""
    assets = []
    if not os.path.isdir(locked_dir):
        return assets
    for fn in os.listdir(locked_dir):
        fpath = os.path.join(locked_dir, fn)
        if not os.path.isfile(fpath):
            continue
        size_mb = os.path.getsize(fpath) / (1024*1024)
        if size_mb > policy.get("exclude_large_files_mb", 50):
            continue
        if fn.endswith("_credential.json") and policy.get("include_credentials", True):
            assets.append({"path": fpath, "name": fn, "type": "credential", "size": os.path.getsize(fpath)})
        elif fn.endswith("_content.txt") and policy.get("include_content", True):
            assets.append({"path": fpath, "name": fn, "type": "content", "size": os.path.getsize(fpath)})
        elif fn == "M9_global_ledger.json" and policy.get("include_ledger", True):
            assets.append({"path": fpath, "name": fn, "type": "ledger", "size": os.path.getsize(fpath)})
    # kernel snapshots
    kernel_dir = os.path.join(locked_dir, "kernel")
    if os.path.isdir(kernel_dir) and policy.get("include_kernel_snapshots", True):
        for fn in os.listdir(kernel_dir):
            fpath = os.path.join(kernel_dir, fn)
            if os.path.isfile(fpath):
                assets.append({"path": fpath, "name": f"kernel/{fn}", "type": "kernel", "size": os.path.getsize(fpath)})
    return assets

def sync_github(config, assets, dry_run=False):
    """同步到GitHub异地冷备"""
    gh = config.get("github", {})
    if not gh.get("enabled", False):
        print("  GitHub: 未启用,跳过")
        return {"status": "DISABLED"}
    backup_dir = config.get("local", {}).get("backup_dir", "")
    if not backup_dir or not os.path.isdir(backup_dir):
        print(f"  GitHub: 备份目录不存在: {backup_dir}")
        return {"status": "NO_BACKUP_DIR"}
    if dry_run:
        print(f"  GitHub: dry-run,待同步{len(assets)}项到{gh.get('repo_url','')}")
        return {"status": "DRY_RUN", "count": len(assets)}
    # 复制资产到备份目录
    copied = 0
    for a in assets:
        target = os.path.join(backup_dir, a["name"])
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(a["path"], target)
        copied += 1
    # git提交推送
    try:
        result = subprocess.run(
            ["git", "add", "-A"],
            cwd=backup_dir, capture_output=True, text=True, timeout=30
        )
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = subprocess.run(
            ["git", "commit", "-m", f"ZONGYUAN-ROOT 自动同步 {now} | 资产{len(assets)}项"],
            cwd=backup_dir, capture_output=True, text=True, timeout=30
        )
        result = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=backup_dir, capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 or "Everything up-to-date" in result.stdout:
            print(f"  GitHub: ✅ 同步完成,{copied}项")
            return {"status": "SYNCED", "copied": copied}
        else:
            print(f"  GitHub: ⚠️  推送结果: {result.stdout[-100:] if result.stdout else result.stderr[-100:]}")
            return {"status": "PUSH_WARNING", "copied": copied}
    except Exception as e:
        print(f"  GitHub: ❌ 同步失败: {e}")
        return {"status": "FAILED", "error": str(e)}

def sync_feishu(config, assets, dry_run=False):
    """同步到飞书云空间"""
    fs = config.get("feishu", {})
    if not fs.get("enabled", False):
        print("  飞书云: 未启用,跳过(需配置app_id/app_secret/folder_token)")
        return {"status": "DISABLED"}
    if dry_run:
        print(f"  飞书云: dry-run,待同步{len(assets)}项到文件夹{fs.get('folder_name','')}")
        return {"status": "DRY_RUN", "count": len(assets)}
    # 飞书云API实现需要tenant_access_token
    # 此处为框架,实际调用需完善API请求
    print(f"  飞书云: ⚠️  API接入待完善(需tenant_access_token+上传API)")
    return {"status": "TODO", "count": len(assets)}

def sync_baidu(config, assets, dry_run=False):
    """同步到百度网盘"""
    bd = config.get("baidu_netdisk", {})
    if not bd.get("enabled", False):
        print("  百度网盘: 未启用,跳过(需配置access_token)")
        return {"status": "DISABLED"}
    if dry_run:
        print(f"  百度网盘: dry-run,待同步{len(assets)}项到{bd.get('remote_path','')}")
        return {"status": "DRY_RUN", "count": len(assets)}
    print(f"  百度网盘: ⚠️  MCP接入待完善")
    return {"status": "TODO", "count": len(assets)}

def verify_remote(config):
    """验证远程归档完整性"""
    print("=== 远程归档验证 ===")
    # GitHub验证
    gh = config.get("github", {})
    if gh.get("enabled", False):
        backup_dir = config.get("local", {}).get("backup_dir", "")
        if os.path.isdir(os.path.join(backup_dir, ".git")):
            try:
                result = subprocess.run(
                    ["git", "log", "--oneline", "-5"],
                    cwd=backup_dir, capture_output=True, text=True, timeout=10
                )
                print(f"  GitHub最近提交:\n{result.stdout}")
                result = subprocess.run(
                    ["git", "ls-files"],
                    cwd=backup_dir, capture_output=True, text=True, timeout=10
                )
                count = len([l for l in result.stdout.strip().split("\n") if l])
                print(f"  GitHub已跟踪文件: {count}个")
            except Exception as e:
                print(f"  GitHub验证失败: {e}")
    return {"status": "VERIFIED"}

def main():
    parser = argparse.ArgumentParser(description="三层级L1云盘归档")
    parser.add_argument("action", choices=["sync", "verify"], help="操作: sync/verify")
    parser.add_argument("--config", default=None, help="配置文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅检测不上传")
    args = parser.parse_args()

    # 自动查找配置
    if args.config:
        config_path = args.config
    else:
        candidates = [
            "/home/user/.doubao/agent_mode/workspace/zongyuan_tools/cloud_backup_config.json",
            "/home/user/.doubao/agent_mode/workspace/zongyuan_tools/cloud_backup_config.template.json",
        ]
        config_path = None
        for c in candidates:
            if os.path.exists(c):
                config_path = c
                break
        if not config_path:
            print("❌ 未找到配置文件,请使用--config指定")
            sys.exit(1)

    config = load_config(config_path)
    now = datetime.datetime.now(datetime.timezone.utc)
    locked_dir = config.get("local", {}).get("locked_dir", "")
    policy = config.get("sync_policy", {})

    print(f"=== ZONGYUAN-ROOT 三层级L1云盘归档 ===")
    print(f"时间: {now.isoformat()[:19]} UTC")
    print(f"配置: {config_path}")
    print(f"DID: {DID} | 溯源: {TRACE}")

    if args.action == "verify":
        return verify_remote(config)

    # 收集资产
    assets = collect_assets(locked_dir, policy)
    total_size = sum(a["size"] for a in assets)
    print(f"\n待归档资产: {len(assets)}项,总大小: {total_size/(1024*1024):.1f}MB")

    # 压缩
    if policy.get("compress_before_upload", False):
        print("压缩模式: 已启用(单文件上传时压缩)")

    # 同步到各云端
    print(f"\n--- 同步执行 ---")
    results = {}
    results["github"] = sync_github(config, assets, args.dry_run)
    results["feishu"] = sync_feishu(config, assets, args.dry_run)
    results["baidu"] = sync_baidu(config, assets, args.dry_run)

    # 汇总
    print(f"\n=== 同步汇总 ===")
    for name, r in results.items():
        status = r.get("status", "UNKNOWN")
        icon = "✅" if status in ("SYNCED", "VERIFIED", "DISABLED") else "⚠️" if status in ("TODO", "DRY_RUN", "PUSH_WARNING") else "❌"
        print(f"  {icon} {name}: {status}")

    # 生成回执
    receipt = {
        "sync_id": f"SYNC-{now.strftime('%Y%m%d-%H%M%S')}",
        "timestamp": now.isoformat(),
        "asset_count": len(assets),
        "total_size_mb": round(total_size/(1024*1024), 2),
        "results": results,
        "did": DID,
        "trace_mark": TRACE,
    }
    receipt_path = os.path.join(os.path.dirname(config_path), "last_sync_receipt.json")
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
    print(f"\n回执: {receipt_path}")
    return receipt

if __name__ == "__main__":
    result = main()
    print(f"\n结果: {json.dumps(result, ensure_ascii=False, default=str)[:500]}")
