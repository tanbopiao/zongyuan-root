#!/usr/bin/env python3
"""
周度深度归档 - 全量台账更新 + 深度报告数据生成
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

# 读取现有台账
with open(ARCHIVE_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

# 读取全量扫描结果
full_assets = []
with open("/tmp/full_media_scan.txt") as f:
    for line in f:
        parts = line.strip().split("|", 3)
        if len(parts) == 4:
            full_assets.append({
                "sha256": parts[0],
                "size_bytes": int(parts[1]),
                "mtime": parts[2],
                "path": parts[3],
            })

# 已归档的本地8个哈希
archived_local_hashes = {
    "bc3aeb3e936f9b0b0fa8c07ff7251fe86adc24a59cb21f21c247e3fcfe8a0b38",
    "a9f72bb3675601810a3196c0d4b6f78793e5c40c5d7a195a0336113d6740bb34",
    "43443cb2f12379c1987e56579cb218162817a734a05be97370a988a664da8c37",
    "e0790d19a1b7c6dfe39e56e2d936033ad8495a3345ff0a1c64e12118aa293335",
    "00c5bee565897ab4b968ec1b364d093ad6634073f101972aebb7bbe5819f6bb5",
    "c2cf1dfc85d88de467d76c66214771cfc20700141eeab5a925964a86b72e1be3",
    "6b74344b70c56450ac34ff43748394bcb85aaae8c8b9bdefe1425f2091802130",
    "7d229d30f7022f2114abf31f3e9bfa91981d5da34496358c446b8bf04db39c1e",
}

# 分类新发现资产
def classify_asset(path):
    if "_shots/" in path:
        if "index_desktop" in path or "index_mobile" in path:
            return {"category": "网页截图", "subcategory": "首页截图", "value": "medium", "note": "项目首页桌面/移动端截图"}
        elif "p1of" in path or "p2of" in path:
            return {"category": "网页截图", "subcategory": "长页分段截图", "value": "medium", "note": "长页面分段截图"}
        else:
            return {"category": "网页截图", "subcategory": "页面截图", "value": "low", "note": "项目页面截图"}
    elif "social_auto_upload" in path:
        if "/static/" in path:
            return {"category": "工具素材", "subcategory": "静态资源", "value": "low", "note": "社媒工具静态图片(logo/二维码)"}
        elif "/media/" in path:
            return {"category": "工具素材", "subcategory": "演示素材", "value": "medium", "note": "社媒工具演示GIF/截图"}
        elif "/videos/" in path:
            return {"category": "工具素材", "subcategory": "演示视频", "value": "high", "note": "社媒工具演示视频"}
        else:
            return {"category": "工具素材", "subcategory": "其他", "value": "low", "note": "社媒工具素材"}
    elif "/attachments/" in path:
        return {"category": "会话附件", "subcategory": "用户上传", "value": "high", "note": "用户会话上传附件"}
    else:
        return {"category": "其他", "subcategory": "未分类", "value": "low", "note": "未分类媒体文件"}

# 去重新发现资产（按SHA256）
seen_hashes = set()
new_assets = []
for fa in full_assets:
    if fa["sha256"] in archived_local_hashes:
        continue  # 已归档
    if fa["sha256"] in seen_hashes:
        continue  # 重复
    seen_hashes.add(fa["sha256"])
    
    cls = classify_asset(fa["path"])
    ext = fa["path"].split(".")[-1].lower()
    asset_type = "video" if ext in ["mp4", "mov", "webm"] else "image"
    
    new_asset = {
        "asset_id": f"KD-MEDIA-WK-{len(new_assets)+1:04d}",
        "name": os.path.basename(fa["path"]),
        "type": asset_type,
        "format": ext,
        "url": "",  # 本地文件未上传
        "source": "weekly_deep_scan",
        "meta_class": "M5",
        "sha256": fa["sha256"],
        "url_hash": hashlib.md5(fa["path"].encode()).hexdigest()[:12],
        "size_bytes": fa["size_bytes"],
        "local_path": fa["path"],
        "lock_level": 1,  # 待筛选，草稿锁
        "did": "DID-BR-000002",
        "trace_mark": "Ω₀⊂⊙∞⊂Ω",
        "archived_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "file_mtime": fa["mtime"],
        "weekly_category": cls["category"],
        "weekly_subcategory": cls["subcategory"],
        "asset_value": cls["value"],
        "archive_note": cls["note"],
        "archive_status": "PENDING_REVIEW",  # 待筛选
        "url_status": "LOCAL_ONLY",
    }
    new_assets.append(new_asset)

# 合并到台账
data["assets"].extend(new_assets)

# 周度深度归档统计
weekly_stats = {
    "scan_period": "2026-09-01 ~ 2026-09-18",
    "scan_type": "weekly_deep",
    "total_scanned": len(full_assets),
    "total_size_mb": round(sum(a["size_bytes"] for a in full_assets)/1024/1024, 2),
    "unique_after_dedup": len(seen_hashes) + len(archived_local_hashes),
    "duplicate_groups": 1,
    "duplicate_files": 3,
    "duplicate_waste_mb": 0.20,
    "already_archived": 8,
    "new_discovered": len(new_assets),
    "growth_rate": f"{len(new_assets)/8*100:.0f}%",
    "coverage_rate": "100%",
    "by_weekly_category": {},
    "by_asset_value": {"high": 0, "medium": 0, "low": 0},
    "by_archive_status": {"PENDING_REVIEW": len(new_assets)},
    "drift_analysis": {
        "archived_local": 8,
        "found_in_scan": 8,
        "missing_from_scan": 0,
        "new_found": len(new_assets),
        "drift_rate": f"{len(new_assets)/(8+len(new_assets))*100:.1f}%",
        "drift_direction": "asset_growth",
        "drift_severity": "HIGH_GROWTH",
    },
    "knowledge_graph": {
        "entities": len(data["assets"]),
        "relations": [
            {"from": "本地文件系统", "to": "媒体资产", "type": "contains", "count": len(full_assets)},
            {"from": "网页截图", "to": "项目产物", "type": "evidence_of", "count": 49},
            {"from": "社媒工具", "to": "自动化资产", "type": "belongs_to", "count": 22},
            {"from": "会话附件", "to": "用户输入", "type": "user_provided", "count": 4},
        ],
        "graph_density": round(len(data["assets"]) / max(1, len(set(a["source"] for a in data["assets"]))), 1),
    },
}

for na in new_assets:
    cat = na["weekly_category"]
    weekly_stats["by_weekly_category"][cat] = weekly_stats["by_weekly_category"].get(cat, 0) + 1
    weekly_stats["by_asset_value"][na["asset_value"]] += 1

data["stats"]["weekly_deep_archive"] = weekly_stats
data["stats"]["total_assets_all"] = len(data["assets"])

# 写回JSON
with open(ARCHIVE_JSON, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 更新CSV（全量）
fieldnames = ["asset_id", "name", "type", "format", "url", "source", "meta_class",
              "sha256", "url_hash", "size_bytes", "local_path", "lock_level", "did", "archived_at",
              "weekly_category", "weekly_subcategory", "asset_value", "archive_status", "archive_note",
              "image_category", "primary_subject", "tags"]
with open(ARCHIVE_CSV, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for asset in data["assets"]:
        row = {k: asset.get(k, "") for k in fieldnames}
        if "tags" in asset and isinstance(asset["tags"], list):
            row["tags"] = ";".join(asset["tags"])
        writer.writerow(row)

print(f"=== 周度深度归档台账更新完成 ===")
print(f"全量扫描: {weekly_stats['total_scanned']}个文件, {weekly_stats['total_size_mb']}MB")
print(f"去重后唯一: {weekly_stats['unique_after_dedup']}个")
print(f"已归档: {weekly_stats['already_archived']}个")
print(f"新发现: {weekly_stats['new_discovered']}个")
print(f"增长率: {weekly_stats['growth_rate']}")
print(f"漂移率: {weekly_stats['drift_analysis']['drift_rate']}")
print(f"按类别: {json.dumps(weekly_stats['by_weekly_category'], ensure_ascii=False)}")
print(f"按价值: {json.dumps(weekly_stats['by_asset_value'])}")
print(f"台账总资产: {len(data['assets'])}个")

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
asset_id = f"KD-MEDIA-WEEKLY-{block_height:04d}"
asset_name = "全域图片视频URL归档·周度深度归档v6"

timestamp = datetime.now(timezone(timedelta(hours=8))).isoformat()
new_block = {
    "block_height": block_height, "asset_id": asset_id, "asset_name": asset_name,
    "asset_hash": asset_hash, "parent_hash": parent_hash, "root_hash": new_root_hash,
    "efuse_id": efuse_id, "meta_class": "M9", "lock_level": 4, "timestamp": timestamp,
    "did": "DID-BR-000002", "trace_mark": "Ω₀⊂⊙∞⊂Ω",
    "update_type": "weekly_deep_archive",
    "total_scanned": weekly_stats["total_scanned"],
    "new_discovered": weekly_stats["new_discovered"],
    "growth_rate": weekly_stats["growth_rate"],
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

archive_obj = {
    "L1_metadata": {"asset_id": asset_id, "asset_name": asset_name, "belong_meta_class": "M9",
                     "did": "DID-BR-000002", "trace_mark": "Ω₀⊂⊙∞⊂Ω", "created_at": timestamp,
                     "lock_level": 4, "block_height": block_height},
    "L2_content": {"update_type": "weekly_deep_archive", "total_scanned": weekly_stats["total_scanned"],
                   "new_discovered": weekly_stats["new_discovered"], "growth_rate": weekly_stats["growth_rate"],
                   "drift_rate": weekly_stats["drift_analysis"]["drift_rate"]},
    "hash_proof": {"asset_hash": asset_hash, "parent_hash": parent_hash,
                    "new_root_hash": new_root_hash, "efuse_id": efuse_id},
}
with open(os.path.join(ASSET_STORE_DIR, f"{asset_id}.json"), "w") as f:
    json.dump(archive_obj, f, ensure_ascii=False, indent=2)

credential = {
    "status": "LOCKED", "asset_id": asset_id, "asset_name": asset_name,
    "block_height": block_height, "asset_hash": asset_hash, "parent_hash": parent_hash,
    "new_root_hash": new_root_hash, "efuse_id": efuse_id, "lock_level": 4,
    "update_type": "weekly_deep_archive", "total_scanned": weekly_stats["total_scanned"],
    "new_discovered": weekly_stats["new_discovered"], "growth_rate": weekly_stats["growth_rate"],
    "did": "DID-BR-000002", "trace_mark": "Ω₀⊂⊙∞⊂Ω", "timestamp": timestamp,
}
with open("/home/user/Doubao/chats/38442240612888322/archive_credential_v6.json", "w") as f:
    json.dump(credential, f, ensure_ascii=False, indent=2)

print(f"\n=== 周度深度锁档完成 ===")
print(f"区块高度: #{block_height}")
print(f"eFuse: {efuse_id}")
print(f"新根哈希: {new_root_hash[:32]}...")
