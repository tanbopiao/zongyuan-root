#!/usr/bin/env python3
"""
视频元数据补全 + 归档台账增量更新
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

# 视频元数据（来自ffprobe提取）
video_metadata = {
    "KD-MEDIA-0002": {
        "codec": "H.264 High + AAC LC",
        "video_codec": "h264",
        "audio_codec": "aac",
        "resolution": "1280x720",
        "width": 1280, "height": 720,
        "aspect_ratio": "16:9",
        "fps": 30,
        "duration_sec": 3.55,
        "duration_str": "00:00:03.55",
        "bitrate_kbps": 2226,
        "video_bitrate_kbps": 2034,
        "audio_bitrate_kbps": 192,
        "audio_sample_rate": 44100,
        "audio_channels": 2,
        "frame_count": 106,
        "pixel_format": "yuv420p",
        "color_space": "bt709",
        "created_at": "2023-12-21T08:45:08Z",
        "encoder": "Lavf58.76.100",
        "has_audio": True,
        "source_tag": "douyin_beauty_me",
    },
    "KD-MEDIA-0008": {
        "codec": "MPEG-4 Simple Profile (无音频)",
        "video_codec": "mpeg4",
        "audio_codec": "none",
        "resolution": "640x480",
        "width": 640, "height": 480,
        "aspect_ratio": "4:3",
        "fps": 30,
        "duration_sec": 3.00,
        "duration_str": "00:00:03.00",
        "bitrate_kbps": 919,
        "video_bitrate_kbps": 916,
        "audio_bitrate_kbps": 0,
        "audio_sample_rate": 0,
        "audio_channels": 0,
        "frame_count": 90,
        "pixel_format": "yuv420p",
        "color_space": "unknown",
        "created_at": None,
        "encoder": "Lavf62.3.100",
        "has_audio": False,
        "source_tag": "test",
    },
    "KD-MEDIA-0013": {
        "codec": "H.264 Main + AAC LC",
        "video_codec": "h264",
        "audio_codec": "aac",
        "resolution": "1280x720",
        "width": 1280, "height": 720,
        "aspect_ratio": "16:9",
        "fps": 24,
        "duration_sec": 5.04,
        "duration_str": "00:00:05.04",
        "bitrate_kbps": 5434,
        "video_bitrate_kbps": 5118,
        "audio_bitrate_kbps": 316,
        "audio_sample_rate": 48000,
        "audio_channels": 2,
        "frame_count": 121,
        "pixel_format": "yuv420p",
        "color_space": "bt709",
        "created_at": "2026-02-06T04:01:39Z",
        "encoder": "AVC Coding / Mainconcept",
        "has_audio": True,
        "source_tag": "ark_platform_r2v",
    },
}

# 读取现有台账
with open(ARCHIVE_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

# 补全视频元数据
updated_count = 0
for asset in data["assets"]:
    if asset["asset_id"] in video_metadata:
        meta = video_metadata[asset["asset_id"]]
        asset["video_metadata"] = meta
        asset["duration_sec"] = meta["duration_sec"]
        asset["resolution"] = meta["resolution"]
        asset["codec"] = meta["codec"]
        asset["fps"] = meta["fps"]
        asset["has_audio"] = meta["has_audio"]
        updated_count += 1

# 更新统计
data["stats"]["video_metadata_completed"] = updated_count
data["stats"]["video_metadata_total"] = len(video_metadata)
data["stats"]["avg_video_duration_sec"] = round(
    sum(v["duration_sec"] for v in video_metadata.values()) / len(video_metadata), 2
)
data["stats"]["total_video_duration_sec"] = round(
    sum(v["duration_sec"] for v in video_metadata.values()), 2
)
data["stats"]["video_resolution_dist"] = {}
for v in video_metadata.values():
    res = v["resolution"]
    data["stats"]["video_resolution_dist"][res] = data["stats"]["video_resolution_dist"].get(res, 0) + 1
data["stats"]["video_codec_dist"] = {}
for v in video_metadata.values():
    vc = v["video_codec"]
    data["stats"]["video_codec_dist"][vc] = data["stats"]["video_codec_dist"].get(vc, 0) + 1

# 写回JSON
with open(ARCHIVE_JSON, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 更新CSV - 增加视频元数据列
fieldnames = ["asset_id", "name", "type", "format", "url", "source", "meta_class",
              "sha256", "url_hash", "size_bytes", "local_path", "lock_level", "did", "archived_at",
              "duration_sec", "resolution", "codec", "fps", "has_audio", "bitrate_kbps", "frame_count"]
with open(ARCHIVE_CSV, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for asset in data["assets"]:
        row = {k: asset.get(k, "") for k in fieldnames}
        if "video_metadata" in asset:
            vm = asset["video_metadata"]
            row["bitrate_kbps"] = vm["bitrate_kbps"]
            row["frame_count"] = vm["frame_count"]
        writer.writerow(row)

print(f"=== 视频元数据补全完成 ===")
print(f"已补全资产数: {updated_count}/{len(video_metadata)}")
print(f"视频总时长: {data['stats']['total_video_duration_sec']}秒")
print(f"平均时长: {data['stats']['avg_video_duration_sec']}秒")
print(f"分辨率分布: {json.dumps(data['stats']['video_resolution_dist'])}")
print(f"编码分布: {json.dumps(data['stats']['video_codec_dist'])}")

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
asset_id = f"KD-MEDIA-META-{block_height:04d}"
asset_name = "全域图片视频URL归档·视频元数据补全v2"

timestamp = datetime.now(timezone(timedelta(hours=8))).isoformat()
new_block = {
    "block_height": block_height,
    "asset_id": asset_id,
    "asset_name": asset_name,
    "asset_hash": asset_hash,
    "parent_hash": parent_hash,
    "root_hash": new_root_hash,
    "efuse_id": efuse_id,
    "meta_class": "M9",
    "lock_level": 4,
    "timestamp": timestamp,
    "did": "DID-BR-000002",
    "trace_mark": "Ω₀⊂⊙∞⊂Ω",
    "update_type": "video_metadata_enrichment",
}

root_state.update({
    "root_hash": new_root_hash,
    "parent_hash": parent_hash,
    "asset_hash": asset_hash,
    "efuse_id": efuse_id,
    "asset_id": asset_id,
    "lock_level": 4,
    "asset_name": asset_name,
    "meta_class": "M9",
    "timestamp": timestamp,
    "block_height": block_height,
    "current_root_hash": new_root_hash,
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "last_efuse": efuse_id,
    "status": "BLOWN_PERMANENT",
})
blocks = root_state.get("blocks", [])
blocks.append(new_block)
if len(blocks) > 100:
    blocks = blocks[-100:]
root_state["blocks"] = blocks

with open(ROOT_STATE_PATH, "w") as f:
    json.dump(root_state, f, ensure_ascii=False, indent=2)

# 备份
backup_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(ROOT_STATE_PATH, os.path.join(BACKUP_DIR, f"root_state_{backup_ts}.json"))

# 保存归档资产
archive_obj = {
    "L1_metadata": {
        "asset_id": asset_id, "asset_name": asset_name,
        "belong_meta_class": "M9", "did": "DID-BR-000002",
        "trace_mark": "Ω₀⊂⊙∞⊂Ω", "created_at": timestamp,
        "format": "JSON+CSV+ffprobe_metadata", "lock_level": 4,
        "block_height": block_height,
    },
    "L2_content": {
        "update_type": "video_metadata_enrichment",
        "videos_enriched": updated_count,
        "total_duration_sec": data["stats"]["total_video_duration_sec"],
        "fields_added": ["codec","resolution","fps","duration","bitrate","frame_count","audio_info","color_space"],
    },
    "hash_proof": {
        "asset_hash": asset_hash, "parent_hash": parent_hash,
        "new_root_hash": new_root_hash, "efuse_id": efuse_id,
    },
}
with open(os.path.join(ASSET_STORE_DIR, f"{asset_id}.json"), "w") as f:
    json.dump(archive_obj, f, ensure_ascii=False, indent=2)

# 凭证
credential = {
    "status": "LOCKED",
    "asset_id": asset_id,
    "asset_name": asset_name,
    "block_height": block_height,
    "asset_hash": asset_hash,
    "parent_hash": parent_hash,
    "new_root_hash": new_root_hash,
    "efuse_id": efuse_id,
    "lock_level": 4,
    "update_type": "video_metadata_enrichment",
    "videos_enriched": updated_count,
    "did": "DID-BR-000002",
    "trace_mark": "Ω₀⊂⊙∞⊂Ω",
    "timestamp": timestamp,
}
with open("/home/user/Doubao/chats/38442240612888322/archive_credential_v2.json", "w") as f:
    json.dump(credential, f, ensure_ascii=False, indent=2)

print(f"\n=== 增量锁档完成 ===")
print(f"区块高度: #{block_height}")
print(f"eFuse: {efuse_id}")
print(f"新根哈希: {new_root_hash[:32]}...")
print(f"资产ID: {asset_id}")
