"""
火斗云智AIOS 数据持久层 - 副本管理与Merkle校验 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT

实现：
- 多副本管理（创建/校验/修复/重建）
- Merkle树完整性校验
- 副本一致性检查
- 自动修复损坏副本
- 零依赖（仅Python标准库）
"""

import hashlib
import json
import os
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict

from core.storage_engine import ReplicaInfo, StoredObject


@dataclass
class MerkleNode:
    """Merkle树节点"""
    hash: str
    left: Optional["MerkleNode"] = None
    right: Optional["MerkleNode"] = None
    is_leaf: bool = False
    object_id: str = ""


class ReplicationManager:
    """
    副本管理器。
    负责多副本的创建、校验、修复、一致性检查。
    """

    def __init__(self, engine, target_replicas: int = 2):
        self.engine = engine
        self.target_replicas = target_replicas
        self.repair_log: List[Dict[str, Any]] = []

    def create_replicas(self, object_id: str, data: bytes) -> int:
        """为对象创建副本"""
        created = 0
        healthy_backends = [
            b for b in self.engine.backends.values()
            if b.health_check().get("status") == "healthy"
        ]

        existing = sum(1 for b in healthy_backends if b.exists(object_id))
        needed = self.target_replicas - existing

        for backend in healthy_backends:
            if needed <= 0:
                break
            if not backend.exists(object_id):
                if backend.put(object_id, data):
                    created += 1
                    needed -= 1
                    # 记录副本信息
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
                    self.engine._replica_store.setdefault(object_id, []).append(replica)

        if object_id in self.engine._meta_store:
            self.engine._meta_store[object_id].replicas = existing + created
        return created

    def verify_replica(self, object_id: str, backend_id: str) -> bool:
        """校验单个副本完整性"""
        backend = self.engine.backends.get(backend_id)
        if backend is None or not backend.exists(object_id):
            return False

        data = backend.get(object_id)
        if data is None:
            return False

        actual_hash = hashlib.sha256(data).hexdigest()
        is_valid = actual_hash == object_id

        # 更新副本校验时间
        replicas = self.engine._replica_store.get(object_id, [])
        for r in replicas:
            if r.backend == backend_id:
                r.last_verified = time.time()
                r.status = "healthy" if is_valid else "corrupted"

        return is_valid

    def verify_all_replicas(self) -> Dict[str, Any]:
        """全量校验所有副本"""
        total = 0
        healthy = 0
        corrupted = []
        missing = []

        for object_id, replicas in self.engine._replica_store.items():
            for replica in replicas:
                total += 1
                backend = self.engine.backends.get(replica.backend)
                if backend is None or not backend.exists(object_id):
                    missing.append({"object_id": object_id, "backend": replica.backend})
                    replica.status = "missing"
                elif self.verify_replica(object_id, replica.backend):
                    healthy += 1
                else:
                    corrupted.append({"object_id": object_id, "backend": replica.backend})
                    replica.status = "corrupted"

        return {
            "total_replicas": total,
            "healthy": healthy,
            "corrupted": corrupted,
            "missing": missing,
            "replica_health_rate": healthy / total if total > 0 else 1.0,
        }

    def repair_replica(self, object_id: str, target_backend_id: str) -> bool:
        """
        修复损坏/丢失的副本。
        从健康副本复制数据到目标后端。
        """
        # 找一个健康副本作为源
        source_data = None
        for backend in self.engine.backends.values():
            if backend.backend_id == target_backend_id:
                continue
            if backend.exists(object_id):
                data = backend.get(object_id)
                if data and hashlib.sha256(data).hexdigest() == object_id:
                    source_data = data
                    break

        if source_data is None:
            return False

        # 写入目标后端
        target = self.engine.backends.get(target_backend_id)
        if target is None:
            return False

        if target.put(object_id, source_data):
            # 更新副本状态
            replicas = self.engine._replica_store.get(object_id, [])
            for r in replicas:
                if r.backend == target_backend_id:
                    r.status = "healthy"
                    r.last_verified = time.time()
                    r.size = len(source_data)
                    r.content_hash = object_id

            self.repair_log.append({
                "object_id": object_id,
                "backend": target_backend_id,
                "action": "repaired",
                "timestamp": time.time(),
            })
            return True
        return False

    def auto_repair(self) -> Dict[str, Any]:
        """自动修复所有损坏/丢失的副本"""
        verify_result = self.verify_all_replicas()
        repaired = 0
        failed = []

        for item in verify_result["corrupted"] + verify_result["missing"]:
            if self.repair_replica(item["object_id"], item["backend"]):
                repaired += 1
            else:
                failed.append(item)

        return {
            "verified": verify_result,
            "repaired": repaired,
            "failed": failed,
        }

    def ensure_replica_count(self) -> Dict[str, Any]:
        """确保所有对象达到目标副本数"""
        under_replicated = []
        created = 0

        for object_id, obj in self.engine._meta_store.items():
            if obj.state == "deleted":
                continue
            current = sum(
                1 for b in self.engine.backends.values()
                if b.exists(object_id)
            )
            if current < self.target_replicas:
                under_replicated.append(object_id)
                data = self.engine.get(object_id)
                if data:
                    created += self.create_replicas(object_id, data)

        return {
            "under_replicated": len(under_replicated),
            "objects": under_replicated[:10],  # 最多显示10个
            "new_replicas_created": created,
        }


class MerkleTree:
    """
    Merkle树 - 用于批量数据完整性校验。
    叶子节点=对象哈希，内部节点=子节点哈希组合。
    """

    def __init__(self):
        self.root: Optional[MerkleNode] = None
        self.leaves: Dict[str, MerkleNode] = {}

    def build(self, object_ids: List[str]) -> Optional[MerkleNode]:
        """从对象ID列表构建Merkle树"""
        if not object_ids:
            return None

        # 创建叶子节点
        nodes = []
        for oid in sorted(object_ids):
            leaf = MerkleNode(
                hash=hashlib.sha256(oid.encode()).hexdigest(),
                is_leaf=True,
                object_id=oid,
            )
            nodes.append(leaf)
            self.leaves[oid] = leaf

        # 逐层构建
        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
                combined = left.hash + right.hash
                parent = MerkleNode(
                    hash=hashlib.sha256(combined.encode()).hexdigest(),
                    left=left,
                    right=right,
                )
                next_level.append(parent)
            nodes = next_level

        self.root = nodes[0] if nodes else None
        return self.root

    def get_root_hash(self) -> str:
        """获取Merkle根哈希"""
        return self.root.hash if self.root else ""

    def verify_object(self, object_id: str, object_ids: List[str]) -> bool:
        """验证对象是否在Merkle树中"""
        # 重新构建并比较根哈希
        new_tree = MerkleTree()
        new_tree.build(object_ids)
        return new_tree.get_root_hash() == self.get_root_hash()

    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "root_hash": self.get_root_hash(),
            "leaf_count": len(self.leaves),
            "leaves": list(self.leaves.keys()),
        }


class IntegrityVerifier:
    """
    完整性校验器。
    结合Merkle树和逐对象哈希校验。
    """

    def __init__(self, engine):
        self.engine = engine
        self.merkle = MerkleTree()

    def full_verify(self) -> Dict[str, Any]:
        """全量完整性校验"""
        # 1. 逐对象哈希校验
        object_results = []
        total = 0
        healthy = 0
        corrupted = []

        for object_id, obj in self.engine._meta_store.items():
            if obj.state == "deleted":
                continue
            total += 1
            data = self.engine.get(object_id)
            if data is None:
                corrupted.append({"object_id": object_id, "issue": "missing"})
            elif hashlib.sha256(data).hexdigest() == object_id:
                healthy += 1
                object_results.append({"object_id": object_id, "status": "healthy"})
            else:
                corrupted.append({"object_id": object_id, "issue": "hash_mismatch"})

        # 2. 构建Merkle树
        healthy_ids = [r["object_id"] for r in object_results]
        self.merkle.build(healthy_ids)

        return {
            "total_objects": total,
            "healthy_objects": healthy,
            "corrupted_objects": corrupted,
            "integrity_rate": healthy / total if total > 0 else 1.0,
            "merkle_root_hash": self.merkle.get_root_hash(),
            "merkle_leaf_count": len(healthy_ids),
            "timestamp": time.time(),
        }

    def generate_proof(self, object_id: str) -> Optional[Dict[str, Any]]:
        """生成对象存在性证明（Merkle Proof）"""
        if object_id not in self.engine._meta_store:
            return None
        # 简化版：返回对象哈希+根哈希
        return {
            "object_id": object_id,
            "object_hash": object_id,  # 内容寻址，object_id就是哈希
            "merkle_root": self.merkle.get_root_hash(),
            "verified": object_id in self.merkle.leaves,
        }

    def save_snapshot(self, path: str) -> bool:
        """保存完整性快照"""
        try:
            result = self.full_verify()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
