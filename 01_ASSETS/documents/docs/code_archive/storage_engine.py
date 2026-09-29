"""
火斗云智AIOS 数据持久层 - 统一存储接口抽象 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT

核心设计：
- 零依赖（仅Python标准库），适配政务内网/精简环境
- 统一存储接口，支持多后端（本地/对象存储/网络存储）
- 内容寻址（Content-Addressed），以SHA256哈希为唯一标识
- 内置副本管理、哈希校验、冷热分层
"""

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple


# ============================================================
# 数据模型
# ============================================================

class StorageTier(Enum):
    """数据分层：热/温/冷/归档"""
    HOT = "hot"        # 高频访问，SSD
    WARM = "warm"      # 中频访问
    COLD = "cold"      # 低频访问
    ARCHIVE = "archive"  # 归档，几乎不访问


class DataState(Enum):
    """数据状态"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    CORRUPTED = "corrupted"
    DELETED = "deleted"


@dataclass
class StoredObject:
    """存储对象元数据"""
    object_id: str                    # 内容哈希（SHA256）
    size: int                         # 字节数
    content_hash: str                 # 内容SHA256
    tier: str                         # 存储层级 hot/warm/cold/archive
    state: str                        # 状态 active/archived/corrupted
    created_at: float                 # 创建时间戳
    updated_at: float                 # 更新时间戳
    last_access_at: float             # 最后访问时间
    access_count: int = 0             # 访问次数
    replicas: int = 1                 # 副本数
    metadata: Dict[str, Any] = field(default_factory=dict)  # 扩展元数据
    tags: List[str] = field(default_factory=list)           # 标签
    source: str = ""                  # 来源标识

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StoredObject":
        return cls(**d)


@dataclass
class ReplicaInfo:
    """副本信息"""
    replica_id: str
    backend: str                      # 后端标识
    path: str                         # 存储路径
    node_id: str                      # 节点ID
    status: str                       # healthy/corrupted/missing
    last_verified: float              # 最后校验时间
    size: int = 0
    content_hash: str = ""


@dataclass
class StorageStats:
    """存储统计"""
    total_objects: int = 0
    total_size: int = 0
    hot_objects: int = 0
    warm_objects: int = 0
    cold_objects: int = 0
    archive_objects: int = 0
    corrupted_objects: int = 0
    total_replicas: int = 0
    healthy_replicas: int = 0


# ============================================================
# 统一存储后端抽象基类
# ============================================================

class StorageBackend(ABC):
    """
    存储后端抽象基类。
    所有存储后端（本地文件/对象存储/网络存储）必须实现这些接口。
    """

    def __init__(self, backend_id: str, config: Optional[Dict[str, Any]] = None):
        self.backend_id = backend_id
        self.config = config or {}
        self._initialized = False

    @abstractmethod
    def initialize(self) -> bool:
        """初始化后端（创建目录/连接等）"""
        pass

    @abstractmethod
    def put(self, object_id: str, data: bytes, metadata: Optional[Dict] = None) -> bool:
        """写入对象"""
        pass

    @abstractmethod
    def get(self, object_id: str) -> Optional[bytes]:
        """读取对象"""
        pass

    @abstractmethod
    def delete(self, object_id: str) -> bool:
        """删除对象"""
        pass

    @abstractmethod
    def exists(self, object_id: str) -> bool:
        """对象是否存在"""
        pass

    @abstractmethod
    def list_objects(self, prefix: str = "") -> List[str]:
        """列出对象ID"""
        pass

    @abstractmethod
    def get_size(self, object_id: str) -> int:
        """获取对象大小"""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """后端健康检查"""
        pass

    def compute_hash(self, data: bytes) -> str:
        """计算内容SHA256"""
        return hashlib.sha256(data).hexdigest()

    def verify_integrity(self, object_id: str, expected_hash: str) -> bool:
        """校验对象完整性"""
        data = self.get(object_id)
        if data is None:
            return False
        return self.compute_hash(data) == expected_hash


# ============================================================
# 统一存储引擎（门面模式）
# ============================================================

class UnifiedStorageEngine:
    """
    统一存储引擎 - 数据持久层核心入口。
    对外提供统一API，内部管理多后端、副本、校验、分层。
    """

    def __init__(self, base_dir: str = "./storage_data", replicas: int = 2):
        self.base_dir = os.path.abspath(base_dir)
        self.target_replicas = replicas
        self.backends: Dict[str, StorageBackend] = {}
        self._meta_store: Dict[str, StoredObject] = {}
        self._replica_store: Dict[str, List[ReplicaInfo]] = {}
        self._initialized = False

    def register_backend(self, backend: StorageBackend) -> bool:
        """注册存储后端"""
        if backend.initialize():
            self.backends[backend.backend_id] = backend
            return True
        return False

    def initialize(self) -> bool:
        """初始化引擎"""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "meta"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "hot"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "warm"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "cold"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "archive"), exist_ok=True)
        self._load_metadata()
        self._initialized = True
        return True

    # ---- 核心API ----

    def put(self, data: bytes, metadata: Optional[Dict] = None,
            tier: str = "hot", tags: Optional[List[str]] = None,
            source: str = "") -> Tuple[Optional[str], Optional[StoredObject]]:
        """
        写入数据，返回 (object_id, StoredObject)。
        内容寻址：相同内容返回相同object_id（去重）。
        """
        if not self._initialized:
            self.initialize()

        content_hash = hashlib.sha256(data).hexdigest()
        object_id = content_hash

        # 去重检查
        if object_id in self._meta_store:
            obj = self._meta_store[object_id]
            obj.access_count += 1
            obj.last_access_at = time.time()
            self._save_metadata()
            return object_id, obj

        # 写入主后端
        primary = self._get_primary_backend()
        if primary is None:
            return None, None

        if not primary.put(object_id, data, metadata):
            return None, None

        # 创建元数据
        now = time.time()

        # 记录主后端副本信息
        primary_replica = ReplicaInfo(
            replica_id=f"{object_id[:8]}_{primary.backend_id}",
            backend=primary.backend_id,
            path=f"{primary.backend_id}/{object_id[:2]}/{object_id}",
            node_id="local",
            status="healthy",
            last_verified=now,
            size=len(data),
            content_hash=content_hash,
        )
        self._replica_store[object_id] = [primary_replica]
        obj = StoredObject(
            object_id=object_id,
            size=len(data),
            content_hash=content_hash,
            tier=tier,
            state=DataState.ACTIVE.value,
            created_at=now,
            updated_at=now,
            last_access_at=now,
            access_count=1,
            replicas=1,
            metadata=metadata or {},
            tags=tags or [],
            source=source,
        )
        self._meta_store[object_id] = obj

        # 创建副本
        self._create_replicas(object_id, data)

        self._save_metadata()
        return object_id, obj

    def get(self, object_id: str) -> Optional[bytes]:
        """读取数据"""
        if object_id not in self._meta_store:
            return None

        obj = self._meta_store[object_id]
        if obj.state == DataState.DELETED.value:
            return None

        # 从健康副本读取
        for backend in self.backends.values():
            if backend.exists(object_id):
                data = backend.get(object_id)
                if data and hashlib.sha256(data).hexdigest() == object_id:
                    obj.access_count += 1
                    obj.last_access_at = time.time()
                    self._save_metadata()
                    return data

        # 所有副本损坏，尝试修复
        return self._repair_and_get(object_id)

    def delete(self, object_id: str, permanent: bool = False) -> bool:
        """删除对象（软删除/硬删除）"""
        if object_id not in self._meta_store:
            return False

        if permanent:
            for backend in self.backends.values():
                backend.delete(object_id)
            del self._meta_store[object_id]
            self._replica_store.pop(object_id, None)
        else:
            self._meta_store[object_id].state = DataState.DELETED.value
            self._meta_store[object_id].updated_at = time.time()

        self._save_metadata()
        return True

    def stat(self, object_id: str) -> Optional[StoredObject]:
        """获取对象元数据"""
        return self._meta_store.get(object_id)

    def list_objects(self, tier: Optional[str] = None,
                     tag: Optional[str] = None,
                     state: str = "active") -> List[StoredObject]:
        """列出对象"""
        results = []
        for obj in self._meta_store.values():
            if state and obj.state != state:
                continue
            if tier and obj.tier != tier:
                continue
            if tag and tag not in obj.tags:
                continue
            results.append(obj)
        return sorted(results, key=lambda x: x.created_at, reverse=True)

    def verify_all(self) -> Dict[str, Any]:
        """全量校验所有对象完整性"""
        total = 0
        healthy = 0
        corrupted = []
        missing = []

        for object_id, obj in self._meta_store.items():
            if obj.state == DataState.DELETED.value:
                continue
            total += 1
            data = self.get(object_id)
            if data is None:
                missing.append(object_id)
            elif hashlib.sha256(data).hexdigest() == object_id:
                healthy += 1
            else:
                corrupted.append(object_id)

        return {
            "total": total,
            "healthy": healthy,
            "corrupted": corrupted,
            "missing": missing,
            "integrity_rate": healthy / total if total > 0 else 1.0,
        }

    def get_stats(self) -> StorageStats:
        """获取存储统计"""
        stats = StorageStats()
        for obj in self._meta_store.values():
            if obj.state == DataState.DELETED.value:
                continue
            stats.total_objects += 1
            stats.total_size += obj.size
            if obj.tier == StorageTier.HOT.value:
                stats.hot_objects += 1
            elif obj.tier == StorageTier.WARM.value:
                stats.warm_objects += 1
            elif obj.tier == StorageTier.COLD.value:
                stats.cold_objects += 1
            elif obj.tier == StorageTier.ARCHIVE.value:
                stats.archive_objects += 1
            if obj.state == DataState.CORRUPTED.value:
                stats.corrupted_objects += 1
            replicas = self._replica_store.get(obj.object_id, [])
            stats.total_replicas += len(replicas)
            stats.healthy_replicas += sum(1 for r in replicas if r.status == "healthy")
        return stats

    def migrate_tier(self, object_id: str, target_tier: str) -> bool:
        """数据分层迁移"""
        if object_id not in self._meta_store:
            return False
        obj = self._meta_store[object_id]
        obj.tier = target_tier
        obj.updated_at = time.time()
        self._save_metadata()
        return True

    def auto_tier(self, hot_threshold_days: int = 7,
                  warm_threshold_days: int = 30,
                  cold_threshold_days: int = 90) -> int:
        """自动分层：根据最后访问时间迁移"""
        now = time.time()
        migrated = 0
        for obj in self._meta_store.values():
            if obj.state == DataState.DELETED.value:
                continue
            days_since_access = (now - obj.last_access_at) / 86400
            if days_since_access > cold_threshold_days and obj.tier != StorageTier.ARCHIVE.value:
                self.migrate_tier(obj.object_id, StorageTier.ARCHIVE.value)
                migrated += 1
            elif days_since_access > warm_threshold_days and obj.tier == StorageTier.HOT.value:
                self.migrate_tier(obj.object_id, StorageTier.WARM.value)
                migrated += 1
            elif days_since_access > hot_threshold_days and obj.tier == StorageTier.HOT.value:
                self.migrate_tier(obj.object_id, StorageTier.WARM.value)
                migrated += 1
        return migrated

    # ---- 内部方法 ----

    def _get_primary_backend(self) -> Optional[StorageBackend]:
        """获取主后端（第一个健康的）"""
        for backend in self.backends.values():
            health = backend.health_check()
            if health.get("status") == "healthy":
                return backend
        return None

    def _create_replicas(self, object_id: str, data: bytes) -> int:
        """创建副本"""
        created = 0
        healthy_backends = [b for b in self.backends.values()
                           if b.health_check().get("status") == "healthy"]

        for backend in healthy_backends[1:self.target_replicas]:
            if not backend.exists(object_id):
                if backend.put(object_id, data):
                    replica = ReplicaInfo(
                        replica_id=f"{object_id[:8]}_{backend.backend_id}",
                        backend=backend.backend_id,
                        path=f"{backend.backend_id}/{object_id[:2]}/{object_id}",
                        node_id="local",
                        status="healthy",
                        last_verified=time.time(),
                        size=len(data),
                        content_hash=object_id,
                    )
                    self._replica_store.setdefault(object_id, []).append(replica)
                    created += 1

        if object_id in self._meta_store:
            self._meta_store[object_id].replicas = 1 + created
        return created

    def _repair_and_get(self, object_id: str) -> Optional[bytes]:
        """修复损坏副本并返回数据"""
        # 找一个健康副本
        for backend in self.backends.values():
            if backend.exists(object_id):
                data = backend.get(object_id)
                if data and hashlib.sha256(data).hexdigest() == object_id:
                    # 用健康副本修复其他后端
                    for other in self.backends.values():
                        if other.backend_id != backend.backend_id:
                            other.put(object_id, data)
                    return data
        return None

    def _save_metadata(self):
        """持久化元数据"""
        meta_path = os.path.join(self.base_dir, "meta", "objects.json")
        data = {
            "objects": {k: v.to_dict() for k, v in self._meta_store.items()},
            "replicas": {k: [asdict(r) for r in v] for k, v in self._replica_store.items()},
            "saved_at": time.time(),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_metadata(self):
        """加载元数据"""
        meta_path = os.path.join(self.base_dir, "meta", "objects.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._meta_store = {
                    k: StoredObject.from_dict(v)
                    for k, v in data.get("objects", {}).items()
                }
                self._replica_store = {
                    k: [ReplicaInfo(**r) for r in v]
                    for k, v in data.get("replicas", {}).items()
                }
            except Exception:
                pass
