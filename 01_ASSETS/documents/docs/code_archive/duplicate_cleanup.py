#!/usr/bin/env python3
"""
重复资产清理建议 - 台账标记 + 清理方案生成（不实际删除）
"""
import json
import csv
import hashlib
import os
import shutil
from datetime import datetime, timezone, timedelta

ARCHIVE_JSON = "/home/user/Doubao/chats/38442240612888322/media_url_archive.json"
ARCHIVE_CSV = "/home/user/Doubao/chats/38442240612888322/media_url_archive.csv"
ROOT_STATE_PATH = os.path.expanduser("~/.meta_order/root_state.json")
BACKUP_DIR = "/home/user/.doubao/agent_mode/workspace/.meta_order_backup"
ASSET_STORE_DIR = "/home/user/.doubao/agent_mode/workspace/meta_order_assets"

# 重复组定义
duplicate_group = {
    "group_id": "DUP-GROUP-001",
    "sha256": "32b89c876b0cde4fae2cde20f2accbebc8f08c262cca2d8c971a0cc57f0f6512",
    "size_bytes": 105813,
    "size_kb": 103.3,
    "file_count": 3,
    "redundant_copies": 2,
    "wasted_space_bytes": 211626,
    "wasted_space_kb": 206.7,
    "keep_canonical": {
        "asset_id": None,  # 运行时查找
        "path": "./zongyuan_tools/social_auto_upload/repo/videos/demo.png",
        "reason": "文件名最简洁，作为规范命名保留",
    },
    "remove_candidates": [
        {"path": "./zongyuan_tools/social_auto_upload/repo/videos/demo1.png", "reason": "demo1.png为冗余副本，内容与demo.png完全一致"},
        {"path": "./zongyuan_tools/social_auto_upload/repo/videos/demo2.png", "reason": "demo2.png为冗余副本，内容与demo.png完全一致"},
    ],
    "all_files": [
        "./zongyuan_tools/social_auto_upload/repo/videos/demo.png",
        "./zongyuan_tools/social_auto_upload/repo/videos/demo1.png",
        "./zongyuan_tools/social_auto_upload/repo/videos/demo2.png",
    ],
    "action": "PENDING_USER_CONFIRM",
    "risk_level": "LOW",
    "reversibility": "可恢复（删除前建议备份）",
}

# 读取台账
with open(ARCHIVE_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

# 在台账中标记重复资产
marked_count = 0
canonical_asset_id = None
for asset in data["assets"]:
    ap = asset.get("local_path", "")
    # 匹配路径（台账中路径可能是绝对路径）
    for dup_path in duplicate_group["all_files"]:
        if dup_path.replace("./", "") in ap or ap.endswith(dup_path.split("/")[-1]):
            asset["duplicate_group"] = duplicate_group["group_id"]
            asset["duplicate_sha256"] = duplicate_group["sha256"]
            if "demo.png" in ap and "demo1" not in ap and "demo2" not in ap:
                asset["duplicate_role"] = "CANONICAL_KEEP"
                asset["cleanup_action"] = "KEEP"
                canonical_asset_id = asset["asset_id"]
            else:
                asset["duplicate_role"] = "REDUNDANT_COPY"
                asset["cleanup_action"] = "PENDING_DELETE"
            marked_count += 1
            break

duplicate_group["keep_canonical"]["asset_id"] = canonical_asset_id

# 清理建议统计
cleanup_stats = {
    "scan_total": 75,
    "duplicate_groups": 1,
    "duplicate_files": 3,
    "redundant_copies": 2,
    "wasted_space_kb": 206.7,
    "wasted_space_mb": 0.20,
    "marked_in_ledger": marked_count,
    "groups": [duplicate_group],
    "summary": {
        "action_required": "用户确认后可删除2个冗余副本（demo1.png + demo2.png），释放206.7KB空间",
        "keep_file": "demo.png（规范命名，保留）",
        "delete_files": ["demo1.png", "demo2.png"],
        "safety_note": "删除前建议备份至回收站或临时目录，确认无引用后再永久删除",
        "reference_check": "需确认这3个文件是否被代码/文档/HTML引用，避免删除后出现断链",
    },
}

data["stats"]["duplicate_cleanup"] = cleanup_stats

# 写回JSON
with open(ARCHIVE_JSON, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 更新CSV
fieldnames = ["asset_id", "name", "type", "format", "url", "source", "meta_class",
              "sha256", "url_hash", "size_bytes", "local_path", "lock_level", "did", "archived_at",
              "weekly_category", "asset_value", "archive_status",
              "duplicate_group", "duplicate_role", "cleanup_action",
              "image_category", "tags"]
with open(ARCHIVE_CSV, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for asset in data["assets"]:
        row = {k: asset.get(k, "") for k in fieldnames}
        if "tags" in asset and isinstance(asset["tags"], list):
            row["tags"] = ";".join(asset["tags"])
        writer.writerow(row)

print(f"=== 重复资产清理建议标记完成 ===")
print(f"标记资产数: {marked_count}")
print(f"保留规范文件: demo.png ({canonical_asset_id})")
print(f"待删除副本: demo1.png, demo2.png")
print(f"可释放空间: 206.7 KB (0.20 MB)")
print(f"操作状态: PENDING_USER_CONFIRM（待用户确认，不自动删除）")

# === 增量锁档 ===
with open(ROOT_STATE_PATH, "r") as f:
    root_state = json.load(f)

parent_hash = root_state.get("current_root_hash", "")
block_height = root_state.get("block_height", 0) + 1
last_efuse_num = int(root_state.get("last_efuse", "EFUSE-0").split("-")[1]) if root_state.get("last_efuse", "").startswith("EFUSE-") else 0

with open(ARCHIVE_JSON, "r", encoding="utf-8") as f:
    content = f.read()
with open(ARCHIVE_CSV, "r", encoding="utf-8") as f:
    csv_content = f.read()

asset_hash = hashlib.sha256((content + csv_content).encode("utf-8")).hexdigest().upper()
new_root_hash = hashlib.sha256((parent_hash + asset_hash).encode("utf-8")).hexdigest().upper()
efuse_num = last_efuse_num + 1
efuse_id = f"EFUSE-{efuse_num:04d}-{asset_hash[:8].upper()}"
asset_id = f"KD-MEDIA-DEDUP-{block_height:04d}"
asset_name = "全域图片视频URL归档·重复资产清理建议v7"

timestamp = datetime.now(timezone(timedelta(hours=8))).isoformat()
new_block = {
    "block_height": block_height, "asset_id": asset_id, "asset_name": asset_name,
    "asset_hash": asset_hash, "parent_hash": parent_hash, "root_hash": new_root_hash,
    "efuse_id": efuse_id, "meta_class": "M9", "lock_level": 4, "timestamp": timestamp,
    "did": "DID-BR-000002", "trace_mark": "Ω₀⊂⊙∞⊂Ω",
    "update_type": "duplicate_cleanup_advisory",
    "duplicate_groups": 1,
    "redundant_copies": 2,
    "action": "PENDING_USER_CONFIRM",
}

root_state.update({
    "root_hash": new_root_hash, "parent_hash": parent_hash, "asset_hash": asset_hash,
    "efuse_id": efuse_id, "asset_id": asset_id, "lock_level": 4,
    "asset_name": asset_name, "meta_class": "M9", "timestamp": timestamp,
    "block_height": block_height, "current_root_hash": new_root_hash,
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "last_efuse": efuse_id, "status": "BLOWN_PERMANENT",
})
blocks = root_state.get("blocks", [])
blocks.append(new_block)
if len(blocks) > 100:
    blocks = blocks[-100:]
root_state["blocks"] = blocks

with open(ROOT_STATE_PATH, "w") as f:
    json.dump(root_state, f, ensure_ascii=False, indent=2)

backup_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(ROOT_STATE_PATH, os.path.join(BACKUP_DIR, f"root_state_{backup_ts}.json"))

credential = {
    "status": "LOCKED", "asset_id": asset_id, "asset_name": asset_name,
    "block_height": block_height, "asset_hash": asset_hash, "parent_hash": parent_hash,
    "new_root_hash": new_root_hash, "efuse_id": efuse_id, "lock_level": 4,
    "update_type": "duplicate_cleanup_advisory", "duplicate_groups": 1,
    "redundant_copies": 2, "action": "PENDING_USER_CONFIRM",
    "did": "DID-BR-000002", "trace_mark": "Ω₀⊂⊙∞⊂Ω", "timestamp": timestamp,
}
with open("/home/user/Doubao/chats/38442240612888322/archive_credential_v7.json", "w") as f:
    json.dump(credential, f, ensure_ascii=False, indent=2)

print(f"\n=== 增量锁档完成 ===")
print(f"区块高度: #{block_height}")
print(f"eFuse: {efuse_id}")
print(f"新根哈希: {new_root_hash[:32]}...")
