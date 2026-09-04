#!/usr/bin/env python3
"""
多写入者并发控制器
文件锁 + 写入者标识 + 版本向量，解决多窗口/定时任务/常驻进程冲突
"""
import json
import fcntl
import hashlib
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
LOCK_DIR = ROOT / ".locks"
WRITER_ID = os.environ.get("ZONGYUAN_WRITER_ID", f"session_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}")


class ConcurrentWriter:
    """并发安全的文件写入器"""

    def __init__(self, writer_id: str = None):
        self.writer_id = writer_id or WRITER_ID
        LOCK_DIR.mkdir(exist_ok=True)

    def _lock_path(self, file_path: Path) -> Path:
        lock_name = hashlib.md5(str(file_path).encode()).hexdigest() + ".lock"
        return LOCK_DIR / lock_name

    def safe_read_json(self, file_path: str) -> Optional[dict]:
        """带锁读取JSON"""
        fp = Path(file_path)
        if not fp.exists():
            return None
        lock_file = self._lock_path(fp)
        with open(lock_file, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_SH)  # 共享锁
            try:
                with open(fp) as f:
                    return json.load(f)
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)

    def safe_write_json(self, file_path: str, data: dict) -> dict:
        """带锁写入JSON，自动添加写入者元数据"""
        fp = Path(file_path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self._lock_path(fp)

        with open(lock_file, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)  # 排他锁
            try:
                # 读取现有版本向量
                existing = {}
                if fp.exists():
                    with open(fp) as f:
                        existing = json.load(f)

                # 更新版本向量
                version_vector = existing.get("_version_vector", {})
                version_vector[self.writer_id] = version_vector.get(self.writer_id, 0) + 1

                # 添加元数据
                data["_metadata"] = {
                    "last_writer": self.writer_id,
                    "last_write_time": datetime.now().isoformat(),
                    "version_vector": version_vector,
                    "write_count": existing.get("_metadata", {}).get("write_count", 0) + 1
                }
                data["_version_vector"] = version_vector

                with open(fp, "w") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())

                return {"status": "written", "writer": self.writer_id, "version": version_vector}
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)

    def check_conflict(self, file_path: str) -> dict:
        """检查文件是否存在写入冲突"""
        fp = Path(file_path)
        if not fp.exists():
            return {"conflict": False, "reason": "file_not_exists"}

        with open(fp) as f:
            data = json.load(f)

        metadata = data.get("_metadata", {})
        version_vector = data.get("_version_vector", {})

        # 检查是否有多个写入者
        writers = list(version_vector.keys())
        has_multiple_writers = len(writers) > 1

        # 检查最后写入时间是否过近（可能并发）
        last_write = metadata.get("last_write_time", "")
        try:
            last_dt = datetime.fromisoformat(last_write)
            seconds_ago = (datetime.now() - last_dt).total_seconds()
            recent_write = seconds_ago < 5
        except:
            recent_write = False

        return {
            "conflict": has_multiple_writers or recent_write,
            "writers": writers,
            "last_writer": metadata.get("last_writer"),
            "last_write_time": last_write,
            "version_vector": version_vector,
            "has_multiple_writers": has_multiple_writers,
            "recent_write": recent_write
        }


def get_writer_id() -> str:
    return WRITER_ID


if __name__ == "__main__":
    import sys
    writer = ConcurrentWriter()
    if len(sys.argv) > 1:
        if sys.argv[1] == "id":
            print(f"Writer ID: {WRITER_ID}")
        elif sys.argv[1] == "check" and len(sys.argv) > 2:
            print(json.dumps(writer.check_conflict(sys.argv[2]), ensure_ascii=False, indent=2))
        elif sys.argv[1] == "write" and len(sys.argv) > 3:
            data = json.loads(sys.argv[3])
            print(json.dumps(writer.safe_write_json(sys.argv[2], data), ensure_ascii=False, indent=2))
    else:
        print(f"Writer ID: {WRITER_ID}")
        print("用法: python3 concurrent_writer.py [id|check|write]")
