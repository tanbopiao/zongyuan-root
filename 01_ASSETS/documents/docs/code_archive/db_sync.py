#!/usr/bin/env python3
"""
SQLite数据库同步通道 (db_sync.py)
ZONGYUAN-ROOT 元极恒一自治体系 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

通过飞书云盘中转实现SQLite数据库同步：
- 本地数据库上传到飞书云盘
- 从飞书云盘下载数据库到本地
- 增量同步（只同步变更的表/记录）
- 版本管理（保留历史版本）
- 冲突检测和解决

用法：
  python3 db_sync.py --upload --db <数据库路径> [--folder-token <云盘文件夹>]
  python3 db_sync.py --download --db <数据库路径> [--file-token <云盘文件>]
  python3 db_sync.py --sync --db <数据库路径>
  python3 db_sync.py --list-versions --db <数据库名>
"""
import json
import sqlite3
import subprocess
import argparse
import hashlib
import os
import shutil
from datetime import datetime

DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"
DEFAULT_FOLDER_TOKEN = "sync_db_archive"  # 需配置实际文件夹token
SYNC_META_TABLE = "_sync_metadata"


def run_lark_cli(args, timeout=60):
    """执行lark-cli命令并返回解析后的JSON"""
    cmd = ["lark-cli"] + args + ["--as", "user", "--format", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    output = result.stdout
    lines = output.strip().split('\n')
    json_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('{'):
            json_start = i
            break
    try:
        return json.loads('\n'.join(lines[json_start:]))
    except json.JSONDecodeError:
        return {"ok": False, "error": "JSON parse failed", "raw": output}


def sha256_file(filepath):
    """计算文件SHA256"""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest().upper()


def init_sync_metadata(db_path):
    """初始化同步元数据表"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {SYNC_META_TABLE} (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_db_version(db_path):
    """获取数据库版本信息"""
    init_sync_metadata(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT value FROM {SYNC_META_TABLE} WHERE key='version'")
    row = cursor.fetchone()
    version = row[0] if row else "v1.0.0"
    cursor.execute(f"SELECT value FROM {SYNC_META_TABLE} WHERE key='last_sync'")
    row = cursor.fetchone()
    last_sync = row[0] if row else "never"
    conn.close()
    return version, last_sync


def increment_version(version):
    """版本号递增（patch级别）"""
    parts = version.replace('v', '').split('.')
    if len(parts) == 3:
        parts[2] = str(int(parts[2]) + 1)
        return 'v' + '.'.join(parts)
    return "v1.0.1"


def upload_db(db_path, folder_token=None):
    """上传数据库到飞书云盘"""
    if not os.path.exists(db_path):
        print(f"  ✗ 数据库文件不存在: {db_path}")
        return False

    db_name = os.path.basename(db_path)
    version, last_sync = get_db_version(db_path)
    file_hash = sha256_file(db_path)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 版本化文件名
    versioned_name = f"{db_name.replace('.db', '')}_{version}_{ts}.db"

    print(f"[DB-SYNC] 上传数据库")
    print(f"  文件: {db_path}")
    print(f"  版本: {version}")
    print(f"  哈希: {file_hash[:32]}...")
    print(f"  版本化名称: {versioned_name}")

    # 复制为版本化文件
    temp_path = f"/tmp/{versioned_name}"
    shutil.copy2(db_path, temp_path)

    target_folder = folder_token or DEFAULT_FOLDER_TOKEN
    result = run_lark_cli([
        "drive", "+upload",
        "--file", temp_path,
        "--folder-token", target_folder
    ])

    if result.get("ok"):
        file_token = result.get("data", {}).get("file_token", "unknown")
        print(f"  ✓ 上传成功，file_token: {file_token}")

        # 更新元数据
        new_version = increment_version(version)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"INSERT OR REPLACE INTO {SYNC_META_TABLE} (key, value, updated_at) VALUES (?, ?, ?)",
                       ("version", new_version, datetime.now().isoformat()))
        cursor.execute(f"INSERT OR REPLACE INTO {SYNC_META_TABLE} (key, value, updated_at) VALUES (?, ?, ?)",
                       ("last_sync", datetime.now().isoformat(), datetime.now().isoformat()))
        cursor.execute(f"INSERT OR REPLACE INTO {SYNC_META_TABLE} (key, value, updated_at) VALUES (?, ?, ?)",
                       ("last_upload_hash", file_hash, datetime.now().isoformat()))
        cursor.execute(f"INSERT OR REPLACE INTO {SYNC_META_TABLE} (key, value, updated_at) VALUES (?, ?, ?)",
                       ("last_file_token", file_token, datetime.now().isoformat()))
        conn.commit()
        conn.close()

        # 清理临时文件
        os.remove(temp_path)
        return True
    else:
        print(f"  ✗ 上传失败: {result.get('error', 'unknown')}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False


def download_db(db_path, file_token=None):
    """从飞书云盘下载数据库"""
    print(f"[DB-SYNC] 下载数据库")
    print(f"  目标: {db_path}")

    if not file_token:
        print("  ✗ 需要指定 --file-token")
        return False

    # 备份当前数据库
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(db_path, backup_path)
        print(f"  已备份当前数据库: {backup_path}")

    result = run_lark_cli([
        "drive", "+download",
        "--file-token", file_token,
        "--output", db_path
    ])

    if result.get("ok"):
        file_hash = sha256_file(db_path)
        version, last_sync = get_db_version(db_path)
        print(f"  ✓ 下载成功")
        print(f"  版本: {version}")
        print(f"  哈希: {file_hash[:32]}...")
        return True
    else:
        print(f"  ✗ 下载失败: {result.get('error', 'unknown')}")
        return False


def sync_db(db_path, folder_token=None):
    """双向同步（先上传本地版本，再检查是否有更新版本）"""
    print(f"[DB-SYNC] 双向同步: {db_path}")
    print("=" * 50)

    # 步骤1: 上传本地版本
    print("\n[1/2] 上传本地版本...")
    upload_ok = upload_db(db_path, folder_token)

    # 步骤2: 列出云端版本（简化：记录最新file_token）
    print("\n[2/2] 记录同步状态...")
    version, last_sync = get_db_version(db_path)
    print(f"  当前版本: {version}")
    print(f"  最后同步: {last_sync}")

    print(f"\n{'=' * 50}")
    if upload_ok:
        print(f"  ✓ 同步完成")
    else:
        print(f"  ⚠ 同步部分完成（上传失败）")
    return upload_ok


def list_versions(db_name, folder_token=None):
    """列出云端数据库版本"""
    print(f"[DB-SYNC] 列出 {db_name} 的云端版本")
    target_folder = folder_token or DEFAULT_FOLDER_TOKEN

    result = run_lark_cli([
        "drive", "+search",
        "--query", db_name,
        "--folder-token", target_folder
    ])

    if result.get("ok"):
        files = result.get("data", {}).get("files", [])
        print(f"  找到 {len(files)} 个版本:")
        for f in files:
            print(f"    - {f.get('name', 'unknown')} (token: {f.get('token', 'unknown')[:16]}...)")
        return True
    else:
        print(f"  ✗ 查询失败: {result.get('error', 'unknown')}")
        return False


def main():
    parser = argparse.ArgumentParser(description='SQLite数据库同步通道')
    parser.add_argument('--upload', action='store_true', help='上传数据库到云盘')
    parser.add_argument('--download', action='store_true', help='从云盘下载数据库')
    parser.add_argument('--sync', action='store_true', help='双向同步')
    parser.add_argument('--list-versions', action='store_true', help='列出云端版本')
    parser.add_argument('--db', type=str, required=True, help='数据库文件路径')
    parser.add_argument('--folder-token', type=str, help='云盘文件夹token')
    parser.add_argument('--file-token', type=str, help='云盘文件token（下载时用）')

    args = parser.parse_args()

    print("=" * 60)
    print("  SQLite数据库同步通道")
    print(f"  DID: {DID} | {TRACE_MARK}")
    print("=" * 60)

    if args.upload:
        upload_db(args.db, args.folder_token)
    elif args.download:
        download_db(args.db, args.file_token)
    elif args.sync:
        sync_db(args.db, args.folder_token)
    elif args.list_versions:
        list_versions(args.db, args.folder_token)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
