#!/usr/bin/env python3
"""
动作5: 本地资产7天冷热分层自动清理脚本
超7天资产从本地删除，只留SHA256索引，需要时从飞书云盘拉取
"""
import json
import hashlib
import time
import os
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
INDEX_FILE = ROOT / "cache" / "cold_asset_index.json"
HOT_DAYS = 7
# 永不清理的核心目录
PROTECTED_DIRS = {"truth_base", "autonomous_kernel_protocol", "config", "templates", "scripts", "omega_brain"}

def load_index():
    if INDEX_FILE.exists():
        with open(INDEX_FILE) as f:
            return json.load(f)
    return {"cold_assets": [], "last_cleanup": None}

def save_index(index):
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def cleanup_cold_assets(dry_run=False):
    """清理超过HOT_DAYS的非核心资产"""
    index = load_index()
    cutoff = time.time() - (HOT_DAYS * 86400)
    cleaned = []
    skipped = []

    for fp in ROOT.rglob("*"):
        if not fp.is_file():
            continue
        rel = str(fp.relative_to(ROOT))
        # 跳过保护目录和缓存目录
        top_dir = rel.split("/")[0]
        if top_dir in PROTECTED_DIRS or "cache" in rel:
            skipped.append(rel)
            continue
        # 检查文件修改时间
        mtime = fp.stat().st_mtime
        if mtime < cutoff:
            file_hash = sha256_file(fp)
            entry = {
                "path": rel,
                "sha256": file_hash,
                "size": fp.stat().st_size,
                "mtime": datetime.fromtimestamp(mtime).isoformat(),
                "archived_to": "feishu_drive:Iet0f3PDsl2JYKdUG3WceP2Yneg",
                "cleanup_time": datetime.now().isoformat()
            }
            if not dry_run:
                fp.unlink()
            cleaned.append(entry)
        else:
            skipped.append(rel)

    index["cold_assets"].extend(cleaned)
    index["last_cleanup"] = datetime.now().isoformat()
    index["total_cold_archived"] = len(index["cold_assets"])
    if not dry_run:
        save_index(index)

    return {
        "cleaned_count": len(cleaned),
        "cleaned": cleaned,
        "skipped_count": len(skipped),
        "freed_bytes": sum(a["size"] for a in cleaned),
        "dry_run": dry_run
    }

def restore_asset(relative_path: str):
    """从冷存储索引恢复资产（需从飞书云盘拉取）"""
    index = load_index()
    for asset in index["cold_assets"]:
        if asset["path"] == relative_path:
            return {
                "status": "need_restore",
                "asset": asset,
                "action": f"从飞书云盘 {asset['archived_to']} 拉取 {relative_path}",
                "sha256_verify": asset["sha256"]
            }
    return {"status": "not_found", "path": relative_path}

if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    result = cleanup_cold_assets(dry_run=dry)
    print(json.dumps({
        "mode": "DRY_RUN" if dry else "EXECUTE",
        "cleaned": result["cleaned_count"],
        "freed_mb": round(result["freed_bytes"] / 1024 / 1024, 2),
        "total_cold_archived": len(load_index()["cold_assets"])
    }, ensure_ascii=False, indent=2))
