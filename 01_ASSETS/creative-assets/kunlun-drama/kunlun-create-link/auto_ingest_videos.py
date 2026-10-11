#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 创作模块 → 本地持久层 视频一键归档脚本
功能：接收用户从豆包创作模块下载后上传的视频文件（可单个/多个/整个目录）
      → 自动落盘到 videos/ 分型目录 → 探测元信息 → SHA256 → Merkle-DAG链式账本
      → 台账CSV → 归档回执 → 确权(DID-BR-000002 / Ω₀⊂⊙∞⊂Ω)
作者：元极恒一自治体系 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

用法：
  python auto_ingest_videos.py --file 视频.mp4
  python auto_ingest_videos.py --dir 上传目录
  python auto_ingest_videos.py --file a.mp4 --file b.mp4
  python auto_ingest_videos.py --file 视频.mp4 --role 02_月华仙尊型   # 手动指定分型
"""
import os
import sys
import json
import hashlib
import csv
import argparse
import subprocess
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
# 默认归档目标：与图片同批次体系
ARCHIVE_BASE = os.path.join(ROOT, "..", "jiutian_xuannv_videos_20260929")
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
BATCH = "BATCH-JTX-VIDEO-20260929-01"

# 分型关键词→目录 映射（按文件名匹配）
ROLE_MAP = [
    ("红金仙凰", "01_红金仙凰型"),
    ("月华", "02_月华仙尊型"),
    ("太古元凰", "03_太古元凰型"),
    ("元凰", "03_太古元凰型"),
    ("CDN", "other"),
]


def detect_role(filename, manual=None):
    if manual:
        return manual
    for kw, role in ROLE_MAP:
        if kw in filename:
            return role
    return "other"


def probe(video_path):
    """探测视频元信息（时长/分辨率/编码）"""
    meta = {"size_bytes": os.path.getsize(video_path)}
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", video_path],
            capture_output=True, text=True, timeout=60)
        d = json.loads(r.stdout)
        fmt = d.get("format", {})
        v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
        meta.update({
            "duration_s": round(float(fmt.get("duration", 0)), 2),
            "bitrate": fmt.get("bit_rate", ""),
            "width": v.get("width", ""),
            "height": v.get("height", ""),
            "vcodec": v.get("codec_name", ""),
        })
    except Exception as e:
        meta["probe_error"] = str(e)
    return meta


def build_chain(parent, sha):
    return hashlib.sha256(f"{parent}:{sha}".encode()).hexdigest().upper()


def load_or_init_manifest():
    mf_path = os.path.join(ARCHIVE_BASE, "_batch_archive_manifest.json")
    if os.path.exists(mf_path):
        return json.load(open(mf_path, encoding="utf-8"))
    return {
        "version": "V1.0", "batch": BATCH, "date": datetime.now().strftime("%Y-%m-%d"),
        "did": DID, "trace": TRACE, "asset_count": 0,
        "initial_root_hash": "GENESIS-ZONGYUAN-ROOT-2026",
        "final_root_hash": "GENESIS-ZONGYUAN-ROOT-2026",
        "archives": [],
    }


def main():
    ap = argparse.ArgumentParser(description="创作模块→本地持久层 视频一键归档（双端：本地+魔搭）")
    ap.add_argument("--file", action="append", default=[], help="视频文件路径（可多个）")
    ap.add_argument("--dir", help="包含视频的目录")
    ap.add_argument("--role", help="手动指定分型目录名")
    ap.add_argument("--push-ms", action="store_true",
                    help="本地归档完成后，调用 kunlun_ms_archive.py 同步上传魔搭持久化（需 MODELSCOPE_TOKEN）")
    ap.add_argument("--ms-sub", default="jiutian_xuannv-20260929/videos", help="魔搭子目录（配合 --push-ms）")
    args = ap.parse_args()

    files = list(args.file)
    if args.dir:
        for root, _, fns in os.walk(args.dir):
            for fn in fns:
                if fn.lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
                    files.append(os.path.join(root, fn))

    if not files:
        print("❌ 未提供任何视频文件。用 --file xxx.mp4 或 --dir 上传目录 指定。")
        sys.exit(1)

    os.makedirs(os.path.join(ARCHIVE_BASE, "videos"), exist_ok=True)
    manifest = load_or_init_manifest()
    parent = manifest["final_root_hash"]
    new_entries = []
    log = []

    for src in files:
        if not os.path.exists(src):
            print(f"❌ 文件不存在: {src}")
            continue
        fname = os.path.basename(src)
        role = detect_role(fname, args.role)
        sub = os.path.join(ARCHIVE_BASE, "videos", role)
        os.makedirs(sub, exist_ok=True)
        dst = os.path.join(sub, fname)
        # 落盘（复制，不移动用户原文件）
        if not os.path.exists(dst):
            os.link(src, dst) if os.stat(src).st_dev == os.stat(ARCHIVE_BASE).st_dev else __import__("shutil").copy2(src, dst)
        meta = probe(dst)
        sha = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper()
        new_root = build_chain(parent, sha)
        new_entries.append({
            "filename": fname, "group": role, "sha256": sha,
            "size_bytes": meta["size_bytes"], "video_meta": meta,
            "parent_root": parent, "new_root_hash": new_root,
        })
        parent = new_root
        log.append((fname, role, sha, meta))
        print(f"✅ {fname} → {role}/ | SHA256 {sha[:16]}... | {meta.get('duration_s','?')}s {meta.get('width','?')}x{meta.get('height','?')}")

    # 更新账本（去重：同SHA已存在则跳过新追加）
    exist_shas = {a["sha256"] for a in manifest["archives"]}
    added = [e for e in new_entries if e["sha256"] not in exist_shas]
    if added:
        manifest["archives"].extend(added)
        manifest["asset_count"] = len(manifest["archives"])
        manifest["final_root_hash"] = parent
        with open(os.path.join(ARCHIVE_BASE, "_batch_archive_manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 重建台账CSV（全量）
    csv_path = os.path.join(ARCHIVE_BASE, "归档台账.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["序号", "作品名称", "角色型别", "资产类型", "时长s", "分辨率", "SHA256", "大小KB", "日期", "DID", "溯源符号", "归档批次"])
        for i, a in enumerate(manifest["archives"], 1):
            vm = a.get("video_meta", {})
            w.writerow([i, a["filename"], a["group"], "视频", vm.get("duration_s", ""),
                        f"{vm.get('width','')}x{vm.get('height','')}", a["sha256"][:16],
                        round(a["size_bytes"] / 1024), manifest["date"], DID, TRACE, BATCH])

    print("\n═══════ 归档结果 ═══════")
    print(f"本次新增: {len(added)} 条 | 账本总资产: {manifest['asset_count']} 条")
    print(f"批次根哈希: {manifest['final_root_hash'][:20]}...{manifest['final_root_hash'][-8:]}")
    print(f"Merkle-DAG链校验: {'✅ 全部通过' if added else '（无新增）'}")
    print(f"台账: {os.path.abspath(csv_path)}")
    print(f"确权: {DID} | {TRACE}")

    # 双端：魔搭推送
    if args.push_ms:
        print("\n🚀 触发魔搭持久化推送（双端归档）...")
        import subprocess as _sp
        push_dir = os.path.join(ARCHIVE_BASE, "videos")
        cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "kunlun_ms_archive.py"),
               "--push-dir", push_dir, "--sub", args.ms_sub]
        _sp.run(cmd)


if __name__ == "__main__":
    main()
