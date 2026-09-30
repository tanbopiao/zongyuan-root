#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 多媒体资产自动归档守护进程
功能：监控图片/视频目录，自动上传到COS对象存储，本地保留索引
部署：/opt/ZONGYUAN-ROOT/services/asset_archiver/
systemd：zr-asset-archiver.service
"""
import os, json, time, hashlib, sqlite3, urllib.request, shutil
from datetime import datetime, timezone
from pathlib import Path

# ===== 配置 =====
WATCH_DIRS = [
    "/opt/ZONGYUAN-ROOT/drama_output",
    "/opt/ZONGYUAN-ROOT/assets",
    "/www/wwwroot/drama.huodouai.com/assets",
]
ARCHIVE_DB = "/opt/ZONGYUAN-ROOT/data/asset_archive.db"
LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/asset_archiver.log"
SCAN_INTERVAL = 120  # 秒
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".gif"}
# COS配置（从环境变量读取，不硬编码）
COS_BUCKET = os.environ.get("COS_BUCKET", "")
COS_REGION = os.environ.get("COS_REGION", "ap-shanghai")
COS_SECRET_ID = os.environ.get("COS_SECRET_ID", "")
COS_SECRET_KEY = os.environ.get("COS_SECRET_KEY", "")
# 本地归档目录（COS未配置时先归档到本地）
LOCAL_ARCHIVE = "/opt/ZONGYUAN-ROOT/archive/media"

def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] {msg}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)

def init_db():
    os.makedirs(os.path.dirname(ARCHIVE_DB), exist_ok=True)
    conn = sqlite3.connect(ARCHIVE_DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS assets (
        file_path TEXT PRIMARY KEY,
        file_hash TEXT,
        file_size INTEGER,
        file_type TEXT,
        archived_at TEXT,
        cos_key TEXT,
        status TEXT
    )""")
    conn.commit()
    conn.close()

def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def scan_once():
    conn = sqlite3.connect(ARCHIVE_DB)
    existing = set(row[0] for row in conn.execute("SELECT file_path FROM assets"))
    found = 0
    archived = 0

    for watch_dir in WATCH_DIRS:
        if not os.path.isdir(watch_dir):
            continue
        for root, dirs, files in os.walk(watch_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                ext = os.path.splitext(fname)[1].lower()
                if ext not in ALLOWED_EXT:
                    continue
                if fpath in existing:
                    continue
                found += 1
                try:
                    fsize = os.path.getsize(fpath)
                    fhash = file_hash(fpath)
                    now = datetime.now(timezone.utc).isoformat()
                    ftype = "video" if ext in (".mp4", ".mov") else "image"

                    # 本地归档
                    os.makedirs(LOCAL_ARCHIVE, exist_ok=True)
                    cos_key = f"{ftype}/{now[:10]}/{fhash[:16]}{ext}"
                    dest = os.path.join(LOCAL_ARCHIVE, cos_key)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(fpath, dest)

                    conn.execute(
                        "INSERT OR REPLACE INTO assets VALUES (?,?,?,?,?,?,?)",
                        (fpath, fhash, fsize, ftype, now, cos_key, "local_archived")
                    )
                    archived += 1
                    log(f"归档: {fname} ({fsize//1024}KB) → {cos_key}")
                except Exception as e:
                    log(f"错误: {fname} - {e}")

    conn.commit()
    conn.close()
    if found:
        log(f"扫描完成: 发现{found}个新文件，归档{archived}个")
    return found, archived

def main():
    init_db()
    log("资产归档守护进程启动")
    while True:
        try:
            scan_once()
        except Exception as e:
            log(f"主循环异常: {e}")
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()
