#!/usr/bin/env python3
"""
FRAME-SNAPSHOT-AUTOSAVE-001 帧快照自动保存钩子
=================================================
META-RULE-017 落地 · 昆仑洞天视觉资产自治流水线 V1.7 增量项

在图像生成完成后自动调用：
  1. 复制帧快照到持久层目录（本地+魔搭双备份）
  2. 生成四维元数据 JSON（空间/时序/属性/因果）
  3. >5MB 自动转 WebP 压缩
  4. 计算 SHA256 哈希作为 Merkle 叶子凭证
  5. 零成本标记 memory_retrieval=true

用法（命令行）:
  python3 frame_snapshot_autosave.py \
    --source /path/to/generated.webp \
    --character "真武大帝" \
    --scene "昆仑绝壁" \
    --version "V1.6" \
    --shot-id "KUNLUN-SHOT-0042" \
    --pipeline "KUNLUN-RUN-002"

用法（Python 导入）:
  from frame_snapshot_autosave import save_frame_snapshot
  result = save_frame_snapshot(
      source_path="...", character="真武大帝",
      scene="昆仑绝壁", version="V1.6",
      shot_id="KUNLUN-SHOT-0042", pipeline="KUNLUN-RUN-002"
  )
"""
import os, sys, json, shutil, hashlib, time, argparse
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

# 帧快照根目录（本地持久层）
SNAPSHOT_ROOT = os.path.expanduser("~/ZONGYUAN-ROOT/03_文档资产/帧快照")
# 魔搭数据湖备份目录（GPU实例侧路径）
DATA_LAKE_ROOT = "/mnt/workspace/ZONGYUAN-SHARED-DATALAKE/frame-snapshots"

# WebP 压缩阈值（字节）
WEBP_THRESHOLD = 5 * 1024 * 1024  # 5MB


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dirs():
    os.makedirs(SNAPSHOT_ROOT, exist_ok=True)
    os.makedirs(DATA_LAKE_ROOT, exist_ok=True)


def convert_to_webp(src_path, quality=85):
    """>5MB 时转 WebP 压缩。需要 Pillow。失败则保留原图。"""
    try:
        from PIL import Image
        img = Image.open(src_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        dst = os.path.splitext(src_path)[0] + ".webp"
        img.save(dst, "WEBP", quality=quality)
        os.remove(src_path)
        return dst
    except ImportError:
        # 无 Pillow，跳过压缩，保留原文件
        return src_path
    except Exception:
        return src_path


def save_frame_snapshot(source_path, character="", scene="", version="V1.0",
                        shot_id="", pipeline="", extra_meta=None):
    """
    保存帧快照 + 四维元数据。
    返回 dict: {status, snapshot_path, meta_path, hash, size_kb, webp_converted}
    """
    ensure_dirs()

    if not os.path.exists(source_path):
        return {"status": "error", "msg": f"源文件不存在: {source_path}"}

    # 生成快照文件名：日期_角色_场景_shotid.ext
    today = datetime.now(CST).strftime("%Y%m%d")
    safe_char = character.replace(" ", "_") if character else "unknown"
    base_name = f"{today}_{safe_char}_{shot_id or 'shot'}"
    ext = os.path.splitext(source_path)[1] or ".png"
    snapshot_filename = base_name + ext
    snapshot_path = os.path.join(SNAPSHOT_ROOT, snapshot_filename)

    # 复制到本地持久层
    shutil.copy2(source_path, snapshot_path)

    # >5MB 转 WebP
    file_size = os.path.getsize(snapshot_path)
    webp_converted = False
    if file_size > WEBP_THRESHOLD:
        new_path = convert_to_webp(snapshot_path)
        if new_path != snapshot_path:
            snapshot_path = new_path
            webp_converted = True
            file_size = os.path.getsize(snapshot_path)

    # 计算哈希
    file_hash = sha256_file(snapshot_path)

    # 四维元数据
    now_iso = datetime.now(CST).isoformat()
    meta = {
        "frame_id": f"FRAME-{today}-{safe_char}-{shot_id or 'auto'}",
        "timestamp": now_iso,
        # D1 空间存在维
        "D1_space": {
            "character": character,
            "scene": scene,
            "composition": "9:16竖屏",
            "lighting": "UE5.7电影级朦胧柔光",
            "snapshot_path": snapshot_path,
        },
        # D2 时间时序维
        "D2_time": {
            "version": version,
            "pipeline": pipeline,
            "shot_id": shot_id,
            "create_ts": now_iso,
        },
        # D3 属性规则维
        "D3_attribute": {
            "format": os.path.splitext(snapshot_path)[1].lstrip("."),
            "size_kb": round(file_size / 1024, 1),
            "webp_converted": webp_converted,
            "style": "暗色奇幻国风，仙雾弥散",
        },
        # D4 因果真值维
        "D4_causal": {
            "hash_sha256": file_hash,
            "merkle_leaf": True,
            "memory_retrieval": True,
            "trace_sign": "Ω₀⊂⊙∞⊂Ω",
            "did": "DID-BR-000002",
        },
    }
    if extra_meta:
        meta.update(extra_meta)

    # 写元数据 JSON
    meta_path = os.path.splitext(snapshot_path)[0] + ".json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 同步到魔搭数据湖备份（如果目录可写）
    backup_status = "local_only"
    try:
        lake_path = os.path.join(DATA_LAKE_ROOT, os.path.basename(snapshot_path))
        shutil.copy2(snapshot_path, lake_path)
        shutil.copy2(meta_path, os.path.splitext(lake_path)[0] + ".json")
        backup_status = "double_backup"
    except Exception:
        pass  # GPU实例不可达时仅本地保存

    return {
        "status": "ok",
        "snapshot_path": snapshot_path,
        "meta_path": meta_path,
        "frame_id": meta["frame_id"],
        "hash_sha256": file_hash,
        "size_kb": round(file_size / 1024, 1),
        "webp_converted": webp_converted,
        "backup": backup_status,
        "memory_retrieval": True,
        "cost": {"token": 0, "quota": "free"},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="帧快照自动保存钩子 V1.0")
    parser.add_argument("--source", required=True, help="生成的图像文件路径")
    parser.add_argument("--character", default="", help="角色名")
    parser.add_argument("--scene", default="", help="场景描述")
    parser.add_argument("--version", default="V1.6", help="流水线版本")
    parser.add_argument("--shot-id", default="", help="分镜ID")
    parser.add_argument("--pipeline", default="", help="流水线批次号")
    args = parser.parse_args()

    result = save_frame_snapshot(
        source_path=args.source,
        character=args.character,
        scene=args.scene,
        version=args.version,
        shot_id=args.shot_id,
        pipeline=args.pipeline,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
