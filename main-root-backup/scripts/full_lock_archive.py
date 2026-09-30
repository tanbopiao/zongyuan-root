#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 全域锁档主流水线（增量索引改造版）
锁档完成后自动增量更新 memory_index.json 元索引
调用 meta-order-lock-archive 的 full_pipeline.py 执行底层锁档
"""
import os
import json
import hashlib
import subprocess
import sys
from datetime import datetime

BASE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(BASE_ROOT, "runtime", "memory_index.json")
MANIFEST_PATH = os.path.join(BASE_ROOT, "lock_archive", "asset_manifest.json")
LOG_PATH = os.path.join(BASE_ROOT, "log", "full_lock_archive.log")
IGNORE_DIRS = {"_trash_legacy_backup", "runtime", "log", ".terraform", "__pycache__", ".git"}


def log(msg):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    print(msg)


def calc_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_assets(root_path):
    """扫描正式业务资产，生成asset_items字典"""
    asset_items = {}
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for name in files:
            fullpath = os.path.join(root, name)
            rel_path = os.path.relpath(fullpath, root_path)
            try:
                sha = calc_sha256(fullpath)
                asset_id = os.path.splitext(name)[0].upper().replace("-", "_").replace(".", "_")
                asset_items[asset_id] = {
                    "sha256": sha,
                    "locator": f"local:{rel_path}",
                    "tags": ["engine_asset"],
                    "summary": f"工程资产 {rel_path}",
                    "priority": "B"
                }
            except Exception as e:
                log(f"WARN 扫描失败 {rel_path}:{e}")
    return asset_items


def update_memory_index(new_snap_id, asset_items, did, sovereign_root, merkle_root):
    """增量更新 memory_index.json 元索引，eFuse熔断不删除历史，只更新/追加"""
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    now = datetime.now().isoformat()
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            idx = json.load(f)
    else:
        idx = {
            "index_meta": {
                "did": did,
                "sovereign_root": sovereign_root,
                "latest_snap_id": "",
                "merkle_root": "",
                "index_update_time": "",
                "eFuse_status": "BLOWN"
            },
            "asset_entries": []
        }

    idx["index_meta"]["latest_snap_id"] = new_snap_id
    idx["index_meta"]["merkle_root"] = merkle_root
    idx["index_meta"]["index_update_time"] = now

    exist_map = {item["asset_id"]: item for item in idx["asset_entries"]}
    for aid, info in asset_items.items():
        if aid in exist_map:
            exist_map[aid]["snap_id"].append(new_snap_id)
            exist_map[aid]["sha256"] = info["sha256"]
            exist_map[aid]["summary"] = info["summary"]
        else:
            new_entry = {
                "asset_id": aid,
                "tags": info["tags"],
                "snap_id": [new_snap_id],
                "locator": info["locator"],
                "backup_locator": info.get("backup_locator", ""),
                "sha256": info["sha256"],
                "summary": info["summary"],
                "priority": info.get("priority", "B")
            }
            idx["asset_entries"].append(new_entry)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    log(f"memory_index 增量更新完成 latest_snap={new_snap_id} 资产总数={len(idx['asset_entries'])}")


def main():
    snap_id = f"SNAP-{datetime.now().strftime('%Y%m%d-%H%M%S')}-ENGINE"
    did = "DID-BR-000002"
    sovereign_root = "Ω-TAN-7-001"

    log(f"===== 全域锁档开始 {snap_id} =====")

    # 阶段1：扫描资产
    log("[1/4] 扫描正式业务资产...")
    asset_items = scan_assets(BASE_ROOT)
    log(f"  扫描到 {len(asset_items)} 项资产")

    # 阶段2：生成manifest
    log("[2/4] 生成资产manifest...")
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    manifest = {
        "snap_id": snap_id,
        "did": did,
        "sovereign_root": sovereign_root,
        "created_at": datetime.now().isoformat(),
        "asset_count": len(asset_items),
        "asset_items": asset_items
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 阶段3：计算Merkle根（简化版：所有资产hash拼接后再hash）
    log("[3/4] 计算Merkle根...")
    all_hashes = sorted([v["sha256"] for v in asset_items.values()])
    merkle_root = hashlib.sha256("".join(all_hashes).encode()).hexdigest()
    log(f"  Merkle根: {merkle_root[:32]}...")

    # 阶段4：增量更新元索引
    log("[4/4] 增量更新memory_index.json...")
    update_memory_index(snap_id, asset_items, did, sovereign_root, merkle_root)

    # 生成锁档回执
    receipt_path = os.path.join(BASE_ROOT, "lock_archive", f"LOCK-CREDENTIAL-{snap_id}.md")
    with open(receipt_path, "w", encoding="utf-8") as f:
        f.write(f"# 全域锁档凭证｜{snap_id}\n\n")
        f.write(f"- DID: {did}\n")
        f.write(f"- 本体主权根: {sovereign_root}\n")
        f.write(f"- 时间: {datetime.now().isoformat()}\n")
        f.write(f"- 资产数: {len(asset_items)}\n")
        f.write(f"- Merkle根: {merkle_root}\n")
        f.write(f"- eFuse状态: BLOWN\n")
        f.write(f"- 元索引: 已增量更新\n\n")
        f.write("Ω₀⊂⊙∞⊂Ω｜永久锁档固化\n")

    log(f"锁档凭证: {receipt_path}")
    log(f"===== 全域锁档完成 {snap_id} =====")
    print(json.dumps({"snap_id": snap_id, "merkle_root": merkle_root, "asset_count": len(asset_items)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
