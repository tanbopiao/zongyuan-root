#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 媒体归档引擎 v2.0
核心原则：生成即归档，文件直接上传，不重新生成
- 节点生成图片/视频后直接上传文件到 /api/media/upload
- 引擎自动：SHA256校验 → 去重 → 分类存储 → 写9120 → 返回访问URL
- 同时保留 /api/media/report（元数据+URL，用于外部URL场景）
"""
import json
import time
import hashlib
import sqlite3
import os
import threading
import requests
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# ========== 配置 ==========
PORT = 9133
DB_PATH = "/opt/ZONGYUAN-ROOT/data/media_archive.db"
STORAGE_ROOT = "/opt/storage"
GATEWAY_API = "http://127.0.0.1:9120/api/truth/upsert"
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
DOWNLOAD_TIMEOUT = 120

# 分类目录映射
CATEGORY_DIRS = {
    "image": {
        "drama": "images/drama", "character": "images/character",
        "keyframe": "images/keyframe", "poster": "images/poster",
        "ui": "images/ui", "other": "images/other",
    },
    "video": {
        "drama": "videos/drama", "clip": "videos/clip",
        "trailer": "videos/trailer", "other": "videos/other",
    }
}

ALLOWED_EXTENSIONS = {
    "image": [".jpg", ".jpeg", ".png", ".webp", ".gif"],
    "video": [".mp4", ".webm", ".mov", ".mkv"]
}

# ========== 数据库 ==========
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS media_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id TEXT UNIQUE,
        asset_name TEXT,
        media_type TEXT,
        category TEXT,
        file_format TEXT,
        file_size INTEGER,
        file_hash TEXT,
        source_url TEXT,
        local_path TEXT,
        access_url TEXT,
        style TEXT,
        ip_owner TEXT,
        project TEXT,
        node_id TEXT,
        status TEXT DEFAULT 'pending',
        error_message TEXT,
        reported_at REAL,
        archived_at REAL,
        did TEXT,
        anchor TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS download_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id TEXT, source_url TEXT,
        retries INTEGER DEFAULT 0, max_retries INTEGER DEFAULT 3,
        added_at REAL, locked INTEGER DEFAULT 0
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_hash ON media_assets(file_hash)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_status ON media_assets(status)")
    conn.commit()
    conn.close()

init_db()

# ========== 工具函数 ==========
def generate_asset_id(media_type, category, node_id):
    ts = time.strftime("%Y%m%d%H%M%S")
    return f"MEDIA-{media_type.upper()}-{category.upper()}-{node_id[:8]}-{ts}"

def detect_media_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ALLOWED_EXTENSIONS["image"]: return "image"
    elif ext in ALLOWED_EXTENSIONS["video"]: return "video"
    return None

def get_storage_path(media_type, category, filename):
    cat_dirs = CATEGORY_DIRS.get(media_type, CATEGORY_DIRS["image"])
    subdir = cat_dirs.get(category, cat_dirs.get("other", "images/other"))
    date_dir = time.strftime("%Y-%m-%d")
    full_dir = os.path.join(STORAGE_ROOT, subdir, date_dir)
    os.makedirs(full_dir, exist_ok=True)
    return os.path.join(full_dir, filename)

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def check_duplicate(file_hash):
    if not file_hash: return None
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT asset_id, asset_name, local_path, access_url FROM media_assets WHERE file_hash=? AND status='archived'", (file_hash,))
    result = c.fetchone()
    conn.close()
    if result:
        return {"asset_id": result[0], "asset_name": result[1], "local_path": result[2], "access_url": result[3]}
    return None

def archive_file(filepath, asset_name, media_type, category, file_format, node_id, style="", ip_owner="", project="", source_url=""):
    """归档一个已存在的文件：校验→去重→存储→写9120→返回结果"""
    # 校验哈希
    file_hash = sha256_file(filepath)

    # 检查重复
    dup = check_duplicate(file_hash)
    if dup:
        return {"status": "duplicate", "asset_id": dup["asset_id"], "access_url": dup["access_url"],
                "message": "文件已存在，无需重复归档"}

    # 生成资产ID
    asset_id = generate_asset_id(media_type, category, node_id)
    filename = f"{asset_id}{file_format}"

    # 移动到归档目录
    local_path = get_storage_path(media_type, category, filename)
    shutil.move(filepath, local_path)
    file_size = os.path.getsize(local_path)

    # 生成访问URL
    rel_path = os.path.relpath(local_path, STORAGE_ROOT)
    access_url = f"https://www.huodouai.com/cos/{rel_path}"

    # 写入数据库
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO media_assets
        (asset_id, asset_name, media_type, category, file_format, file_size, file_hash,
         source_url, local_path, access_url, style, ip_owner, project, node_id,
         status, reported_at, archived_at, did, anchor)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'archived',?,?,?,?)""",
        (asset_id, asset_name, media_type, category, file_format, file_size, file_hash,
         source_url, local_path, access_url, style, ip_owner, project, node_id,
         time.time(), time.time(), "DID-BR-000002", "Ω₀⊂⊙∞⊂Ω"))
    conn.commit()
    conn.close()

    # 写入9120
    try:
        requests.post(GATEWAY_API, json={
            "key": f"MEDIA.ARCHIVE.{asset_id}",
            "value": json.dumps({
                "asset_id": asset_id, "asset_name": asset_name,
                "media_type": media_type, "category": category,
                "format": file_format, "size": file_size, "hash": file_hash,
                "access_url": access_url, "style": style, "ip_owner": ip_owner,
                "archived_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }, ensure_ascii=False),
            "category": "drama" if media_type == "video" else "other",
            "node_id": "media-archive-engine",
            "truth_type": "activation", "confidence": 1.0
        }, timeout=10, headers={"X-From-Governance": "true"})
    except:
        pass

    return {"status": "archived", "asset_id": asset_id, "access_url": access_url,
            "file_size": file_size, "file_hash": file_hash, "local_path": local_path}

# ========== 下载Worker（用于URL上报模式） ==========
def download_worker():
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, asset_id, source_url, retries, max_retries FROM download_queue WHERE locked=0 AND retries<max_retries ORDER BY added_at LIMIT 1")
            task = c.fetchone()
            if not task:
                conn.close()
                time.sleep(5)
                continue
            task_id, asset_id, source_url, retries, max_retries = task
            c.execute("UPDATE download_queue SET locked=1 WHERE id=?", (task_id,))
            conn.commit()
            conn.close()

            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT asset_name, media_type, category, file_format FROM media_assets WHERE asset_id=?", (asset_id,))
                asset = c.fetchone()
                conn.close()
                if not asset: continue
                asset_name, media_type, category, file_format = asset

                # 检查本地COS快捷路径
                local_cos_path = None
                if "/cos/" in source_url:
                    cos_idx = source_url.find("/cos/")
                    rel_path = source_url[cos_idx + 5:]
                    candidate = os.path.join(STORAGE_ROOT, rel_path)
                    if os.path.exists(candidate):
                        local_cos_path = candidate

                temp_path = f"/tmp/{asset_id}{file_format}"
                if local_cos_path:
                    shutil.copy2(local_cos_path, temp_path)
                else:
                    resp = requests.get(source_url, timeout=DOWNLOAD_TIMEOUT, stream=True)
                    resp.raise_for_status()
                    with open(temp_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)

                result = archive_file(temp_path, asset_name, media_type, category, file_format,
                                      "url-import", source_url=source_url)

                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("DELETE FROM download_queue WHERE id=?", (task_id,))
                conn.commit()
                conn.close()
                print(f"[URL归档] {asset_id}: {result['status']}")

            except Exception as e:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("UPDATE download_queue SET retries=retries+1, locked=0 WHERE id=?", (task_id,))
                if retries + 1 >= max_retries:
                    c.execute("UPDATE media_assets SET status='failed', error_message=? WHERE asset_id=?", (str(e), asset_id))
                    c.execute("DELETE FROM download_queue WHERE id=?", (task_id,))
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"[Worker错误] {e}")
            time.sleep(5)

threading.Thread(target=download_worker, daemon=True).start()

# ========== HTTP服务 ==========
class MediaArchiveHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok", "service": "media-archive-engine", "port": PORT, "mode": "direct-upload", "did": "DID-BR-000002"})
        elif self.path == "/api/media/stats":
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            stats = {}
            for s in ["pending", "archived", "duplicate", "failed"]:
                c.execute("SELECT COUNT(*) FROM media_assets WHERE status=?", (s,))
                stats[s] = c.fetchone()[0]
            c.execute("SELECT COALESCE(SUM(file_size),0) FROM media_assets WHERE status='archived'")
            stats["total_size_bytes"] = c.fetchone()[0]
            conn.close()
            self._send_json(stats)
        elif self.path.startswith("/api/media/asset/"):
            asset_id = self.path.split("/")[-1]
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT asset_id,asset_name,media_type,category,file_format,file_size,file_hash,access_url,status,node_id,archived_at FROM media_assets WHERE asset_id=?", (asset_id,))
            row = c.fetchone()
            conn.close()
            if row:
                self._send_json({
                    "asset_id": row[0], "asset_name": row[1], "media_type": row[2],
                    "category": row[3], "format": row[4], "size": row[5],
                    "hash": row[6], "access_url": row[7], "status": row[8],
                    "node_id": row[9], "archived_at": row[10]
                })
            else:
                self._send_json({"error": "not found"}, 404)
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/api/media/upload":
            # 直接文件上传（multipart/form-data）
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self._send_json({"status": "rejected", "reason": "需要multipart/form-data格式"}, 400)
                return

            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > MAX_FILE_SIZE:
                self._send_json({"status": "rejected", "reason": f"文件超过{MAX_FILE_SIZE//1024//1024}MB限制"}, 413)
                return

            body = self.rfile.read(content_length)

            # 解析multipart
            boundary = content_type.split("boundary=")[1].encode()
            parts = body.split(b"--" + boundary)

            file_data = None
            filename = ""
            fields = {}

            for part in parts:
                if b"Content-Disposition" not in part:
                    continue
                # 提取字段名和文件名
                header_end = part.find(b"\r\n\r\n")
                if header_end == -1: continue
                headers = part[:header_end].decode("utf-8", errors="ignore")
                content = part[header_end+4:]
                # 去掉结尾的\r\n
                if content.endswith(b"\r\n"): content = content[:-2]

                name = ""
                fname = ""
                for line in headers.split("\r\n"):
                    if "name=" in line:
                        name = line.split('name="')[1].split('"')[0]
                    if "filename=" in line:
                        fname = line.split('filename="')[1].split('"')[0]

                if fname:
                    file_data = content
                    filename = fname
                else:
                    fields[name] = content.decode("utf-8", errors="ignore")

            if not file_data or not filename:
                self._send_json({"status": "rejected", "reason": "未找到文件"}, 400)
                return

            # 获取元数据字段
            asset_name = fields.get("asset_name", filename)
            category = fields.get("category", "other")
            node_id = fields.get("node_id", "unknown")
            style = fields.get("style", "")
            ip_owner = fields.get("ip_owner", "")
            project = fields.get("project", "")

            # 检测媒体类型
            file_format = os.path.splitext(filename)[1].lower()
            media_type = detect_media_type(filename)
            if not media_type:
                self._send_json({"status": "rejected", "reason": f"不支持的文件格式: {file_format}"}, 400)
                return

            # 保存临时文件
            temp_path = f"/tmp/media_upload_{int(time.time()*1000)}{file_format}"
            with open(temp_path, "wb") as f:
                f.write(file_data)

            # 归档
            result = archive_file(temp_path, asset_name, media_type, category, file_format,
                                  node_id, style, ip_owner, project)
            self._send_json(result)

        elif self.path == "/api/media/report":
            # URL上报模式（备选）
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length))
            asset_name = body.get("asset_name", "")
            source_url = body.get("source_url", "")
            media_type = body.get("media_type", "")
            category = body.get("category", "other")
            node_id = body.get("node_id", "unknown")
            file_format = body.get("file_format", "")
            style = body.get("style", "")
            ip_owner = body.get("ip_owner", "")

            if not asset_name or not source_url:
                self._send_json({"status": "rejected", "reason": "缺少asset_name或source_url"}, 400)
                return

            if not media_type:
                parsed = urlparse(source_url)
                media_type = detect_media_type(parsed.path) or "image"
            if not file_format:
                parsed = urlparse(source_url)
                file_format = os.path.splitext(parsed.path)[1].lower() or ".jpg"

            asset_id = generate_asset_id(media_type, category, node_id)
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""INSERT INTO media_assets
                (asset_id, asset_name, media_type, category, file_format, source_url,
                 style, ip_owner, node_id, status, reported_at, did, anchor)
                VALUES (?,?,?,?,?,?,?,?,?, 'pending', ?, 'DID-BR-000002', 'Ω₀⊂⊙∞⊂Ω')""",
                (asset_id, asset_name, media_type, category, file_format, source_url,
                 style, ip_owner, node_id, time.time()))
            c.execute("INSERT INTO download_queue (asset_id, source_url, added_at) VALUES (?,?,?)",
                      (asset_id, source_url, time.time()))
            conn.commit()
            conn.close()

            self._send_json({
                "status": "queued", "asset_id": asset_id,
                "message": "已加入下载队列（推荐使用/api/media/upload直接上传文件）"
            })
        else:
            self._send_json({"error": "not found"}, 404)

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), MediaArchiveHandler)
    print(f"媒体归档引擎v2.0启动: 端口{PORT} (直传模式)")
    server.serve_forever()
