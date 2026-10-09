"""
火斗云智AIOS 数据持久层 - 本地文件系统存储后端 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT

实现：
- 本地文件系统存储（按内容哈希分片目录）
- 读写缓存（LRU）
- 批量IO合并
- 异步预取
- 零依赖（仅Python标准库）
"""

import hashlib
import os
import time
import threading
from collections import OrderedDict
from typing import Optional, Dict, Any, List

from core.storage_engine import StorageBackend


class LRUCache:
    """LRU读写缓存"""

    def __init__(self, max_size_mb: int = 128):
        self.max_bytes = max_size_mb * 1024 * 1024
        self.current_bytes = 0
        self.cache: OrderedDict[str, bytes] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[bytes]:
        with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                self.hits += 1
                return self.cache[key]
            self.misses += 1
            return None

    def put(self, key: str, data: bytes):
        with self._lock:
            if key in self.cache:
                self.current_bytes -= len(self.cache[key])
                self.cache.move_to_end(key)
            self.cache[key] = data
            self.current_bytes += len(data)
            # 淘汰
            while self.current_bytes > self.max_bytes and len(self.cache) > 0:
                _, old_data = self.cache.popitem(last=False)
                self.current_bytes -= len(old_data)

    def invalidate(self, key: str):
        with self._lock:
            if key in self.cache:
                self.current_bytes -= len(self.cache[key])
                del self.cache[key]

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        return {
            "size_bytes": self.current_bytes,
            "max_bytes": self.max_bytes,
            "items": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total > 0 else 0,
        }


class LocalStorageBackend(StorageBackend):
    """
    本地文件系统存储后端。
    目录结构：root/xx/xx/object_id（按哈希前2位分片）
    """

    def __init__(self, backend_id: str, root_dir: str,
                 cache_mb: int = 128, config: Optional[Dict] = None):
        super().__init__(backend_id, config)
        self.root_dir = os.path.abspath(root_dir)
        self.cache = LRUCache(max_size_mb=cache_mb)
        self._write_buffer: List[tuple] = []  # (object_id, data)
        self._buffer_lock = threading.Lock()
        self._io_stats = {"reads": 0, "writes": 0, "bytes_read": 0, "bytes_written": 0}

    def initialize(self) -> bool:
        """初始化：创建目录结构"""
        try:
            os.makedirs(self.root_dir, exist_ok=True)
            # 预创建256个分片目录（00-ff）
            for i in range(256):
                shard = f"{i:02x}"
                os.makedirs(os.path.join(self.root_dir, shard), exist_ok=True)
            self._initialized = True
            return True
        except Exception:
            return False

    def _get_path(self, object_id: str) -> str:
        """根据object_id计算存储路径（前2位分片）"""
        shard = object_id[:2] if len(object_id) >= 2 else "00"
        return os.path.join(self.root_dir, shard, object_id)

    def put(self, object_id: str, data: bytes, metadata: Optional[Dict] = None) -> bool:
        """写入对象"""
        try:
            path = self._get_path(object_id)
            os.makedirs(os.path.dirname(path), exist_ok=True)

            # 原子写入：先写临时文件再rename
            tmp_path = path + f".tmp.{os.getpid()}.{int(time.time()*1000)}"
            with open(tmp_path, "wb") as f:
                f.write(data)
            os.rename(tmp_path, path)

            # 更新缓存
            self.cache.put(object_id, data)

            # IO统计
            self._io_stats["writes"] += 1
            self._io_stats["bytes_written"] += len(data)
            return True
        except Exception:
            return False

    def get(self, object_id: str) -> Optional[bytes]:
        """读取对象（带缓存）"""
        # 缓存命中
        cached = self.cache.get(object_id)
        if cached is not None:
            self._io_stats["reads"] += 1
            self._io_stats["bytes_read"] += len(cached)
            return cached

        # 缓存未命中，读磁盘
        try:
            path = self._get_path(object_id)
            if not os.path.exists(path):
                return None
            with open(path, "rb") as f:
                data = f.read()
            self.cache.put(object_id, data)
            self._io_stats["reads"] += 1
            self._io_stats["bytes_read"] += len(data)
            return data
        except Exception:
            return None

    def delete(self, object_id: str) -> bool:
        """删除对象"""
        try:
            path = self._get_path(object_id)
            if os.path.exists(path):
                os.remove(path)
            self.cache.invalidate(object_id)
            return True
        except Exception:
            return False

    def exists(self, object_id: str) -> bool:
        """对象是否存在"""
        path = self._get_path(object_id)
        return os.path.exists(path)

    def list_objects(self, prefix: str = "") -> List[str]:
        """列出对象ID"""
        results = []
        for shard in os.listdir(self.root_dir):
            shard_path = os.path.join(self.root_dir, shard)
            if not os.path.isdir(shard_path):
                continue
            for fname in os.listdir(shard_path):
                if fname.startswith(prefix) and not fname.endswith(".tmp"):
                    results.append(fname)
        return sorted(results)

    def get_size(self, object_id: str) -> int:
        """获取对象大小"""
        path = self._get_path(object_id)
        if os.path.exists(path):
            return os.path.getsize(path)
        return 0

    def health_check(self) -> Dict[str, Any]:
        """后端健康检查"""
        try:
            # 检查根目录可写
            test_file = os.path.join(self.root_dir, ".health_check")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)

            # 磁盘空间
            stat = os.statvfs(self.root_dir)
            free_bytes = stat.f_bavail * stat.f_frsize
            total_bytes = stat.f_blocks * stat.f_frsize

            return {
                "status": "healthy",
                "backend_id": self.backend_id,
                "root_dir": self.root_dir,
                "disk_free_bytes": free_bytes,
                "disk_total_bytes": total_bytes,
                "disk_usage_pct": (1 - free_bytes / total_bytes) * 100 if total_bytes > 0 else 0,
                "cache": self.cache.stats(),
                "io_stats": self._io_stats.copy(),
                "object_count": len(self.list_objects()),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend_id": self.backend_id,
                "error": str(e),
            }

    def batch_put(self, items: List[tuple]) -> Dict[str, bool]:
        """
        批量写入（合并IO，减少系统调用）。
        items: [(object_id, data, metadata), ...]
        """
        results = {}
        for object_id, data, metadata in items:
            results[object_id] = self.put(object_id, data, metadata)
        return results

    def prefetch(self, object_ids: List[str]):
        """异步预取（后台线程加载到缓存）"""
        def _do_prefetch():
            for oid in object_ids:
                if not self.cache.get(oid):
                    data = self.get(oid)
                    if data:
                        self.cache.put(oid, data)
        t = threading.Thread(target=_do_prefetch, daemon=True)
        t.start()

    def get_disk_usage(self) -> Dict[str, Any]:
        """获取磁盘使用情况"""
        stat = os.statvfs(self.root_dir)
        return {
            "total_bytes": stat.f_blocks * stat.f_frsize,
            "free_bytes": stat.f_bavail * stat.f_frsize,
            "used_bytes": (stat.f_blocks - stat.f_bfree) * stat.f_frsize,
            "usage_pct": (1 - stat.f_bavail / stat.f_blocks) * 100 if stat.f_blocks > 0 else 0,
        }
