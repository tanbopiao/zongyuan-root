#!/usr/bin/env python3
"""
账本同步与完整性校验 - 本地/云端双端账本一致性保障
- 本地→云端同步
- 云端→本地同步
- 全链哈希完整性校验
- 冲突检测与合并
"""
import hashlib
import json
import time
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class ChainBlock:
    """链区块"""
    height: int
    asset_id: str
    asset_hash: str
    parent_hash: str
    root_hash: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "height": self.height,
            "asset_id": self.asset_id,
            "asset_hash": self.asset_hash,
            "parent_hash": self.parent_hash,
            "root_hash": self.root_hash,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    direction: str  # local_to_cloud / cloud_to_local
    blocks_synced: int = 0
    conflicts_found: int = 0
    conflicts_resolved: int = 0
    local_height_before: int = 0
    local_height_after: int = 0
    cloud_height_before: int = 0
    cloud_height_after: int = 0
    local_root_before: str = ""
    local_root_after: str = ""
    cloud_root_before: str = ""
    cloud_root_after: str = ""
    errors: List[str] = field(default_factory=list)
    sync_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "direction": self.direction,
            "blocks_synced": self.blocks_synced,
            "conflicts_found": self.conflicts_found,
            "conflicts_resolved": self.conflicts_resolved,
            "local_height": {"before": self.local_height_before, "after": self.local_height_after},
            "cloud_height": {"before": self.cloud_height_before, "after": self.cloud_height_after},
            "local_root": {"before": self.local_root_before, "after": self.local_root_after},
            "cloud_root": {"before": self.cloud_root_before, "after": self.cloud_root_after},
            "errors": self.errors,
            "sync_time_ms": round(self.sync_time_ms, 2),
        }


@dataclass
class IntegrityResult:
    """完整性校验结果"""
    valid: bool
    total_blocks: int = 0
    checked_blocks: int = 0
    broken_links: List[Dict[str, Any]] = field(default_factory=list)
    hash_mismatches: List[Dict[str, Any]] = field(default_factory=list)
    missing_blocks: List[int] = field(default_factory=list)
    duplicate_heights: List[int] = field(default_factory=list)
    check_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "total_blocks": self.total_blocks,
            "checked_blocks": self.checked_blocks,
            "broken_links": len(self.broken_links),
            "hash_mismatches": len(self.hash_mismatches),
            "missing_blocks": self.missing_blocks,
            "duplicate_heights": self.duplicate_heights,
            "details": {
                "broken_links": self.broken_links[:10],
                "hash_mismatches": self.hash_mismatches[:10],
            },
            "check_time_ms": round(self.check_time_ms, 2),
        }


class ChainSynchronizer:
    """
    账本同步器 - 本地/云端双端账本一致性保障
    """

    def __init__(self, local_chain_path: str, cloud_chain_path: str = ""):
        self.local_chain_path = local_chain_path
        self.cloud_chain_path = cloud_chain_path
        self.conflict_resolution_strategy = "cloud_wins"  # cloud_wins / local_wins / merge

    def _load_chain(self, path: str) -> Optional[Dict[str, Any]]:
        """加载链数据"""
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _save_chain(self, path: str, chain: Dict[str, Any]) -> bool:
        """保存链数据"""
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(chain, f, indent=2, ensure_ascii=False)
            return True
        except IOError:
            return False

    def _extract_blocks(self, chain: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从链数据中提取区块列表"""
        blocks = chain.get("blocks", [])
        return sorted(blocks, key=lambda b: b.get("height", 0))

    def sync_local_to_cloud(self) -> SyncResult:
        """本地→云端同步"""
        start_time = time.time()
        result = SyncResult(success=False, direction="local_to_cloud")

        local_chain = self._load_chain(self.local_chain_path)
        cloud_chain = self._load_chain(self.cloud_chain_path)

        if not local_chain:
            result.errors.append("本地链不存在或无法加载")
            result.sync_time_ms = (time.time() - start_time) * 1000
            return result

        result.local_height_before = local_chain.get("height", local_chain.get("current_height", 0))
        result.local_root_before = local_chain.get("root_hash", local_chain.get("global_root_hash", ""))

        if cloud_chain:
            result.cloud_height_before = cloud_chain.get("block_height", cloud_chain.get("height", 0))
            result.cloud_root_before = cloud_chain.get("current_root_hash", cloud_chain.get("root_hash", ""))

        # 如果云端不存在，直接复制本地
        if not cloud_chain:
            cloud_chain = {
                "block_height": result.local_height_before,
                "current_root_hash": result.local_root_before,
                "total_assets": local_chain.get("total_assets", 0),
                "blocks": self._extract_blocks(local_chain),
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S.%f+00:00", time.gmtime()),
                "did": "DID-BR-000002",
                "trace_mark": "Ω₀⊂⊙∞⊂Ω",
            }
            result.blocks_synced = len(cloud_chain["blocks"])
            result.cloud_height_after = result.local_height_before
            result.cloud_root_after = result.local_root_before
            result.success = self._save_chain(self.cloud_chain_path, cloud_chain)
            result.sync_time_ms = (time.time() - start_time) * 1000
            return result

        # 查找差异区块（本地有但云端没有的）
        local_blocks = self._extract_blocks(local_chain)
        cloud_blocks = self._extract_blocks(cloud_chain)
        cloud_heights = {b.get("height") for b in cloud_blocks}

        new_blocks = [b for b in local_blocks if b.get("height") not in cloud_heights]

        # 冲突检测：相同高度但哈希不同
        conflicts = []
        local_by_height = {b.get("height"): b for b in local_blocks}
        cloud_by_height = {b.get("height"): b for b in cloud_blocks}

        for height in set(local_by_height.keys()) & set(cloud_by_height.keys()):
            local_block = local_by_height[height]
            cloud_block = cloud_by_height[height]
            local_root = local_block.get("new_root_hash", local_block.get("root_hash", ""))
            cloud_root = cloud_block.get("new_root_hash", cloud_block.get("root_hash", ""))
            if local_root and cloud_root and local_root.upper() != cloud_root.upper():
                conflicts.append({"height": height, "local_root": local_root, "cloud_root": cloud_root})

        result.conflicts_found = len(conflicts)

        # 冲突解决：默认云端优先
        if conflicts and self.conflict_resolution_strategy == "cloud_wins":
            # 保留云端区块，不覆盖
            result.conflicts_resolved = len(conflicts)
            new_blocks = [b for b in new_blocks if b.get("height") not in {c["height"] for c in conflicts}]

        # 追加新区块
        cloud_blocks.extend(new_blocks)
        cloud_blocks = sorted(cloud_blocks, key=lambda b: b.get("height", 0))

        # 更新云端链状态
        if cloud_blocks:
            latest = cloud_blocks[-1]
            cloud_chain["block_height"] = latest.get("height", 0)
            cloud_chain["current_root_hash"] = latest.get("new_root_hash", latest.get("root_hash", ""))
            cloud_chain["total_assets"] = cloud_chain.get("total_assets", 0) + len(new_blocks)
            cloud_chain["blocks"] = cloud_blocks[-50:]  # 只保留最近50个区块
            cloud_chain["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S.%f+00:00", time.gmtime())

        result.blocks_synced = len(new_blocks)
        result.cloud_height_after = cloud_chain.get("block_height", 0)
        result.cloud_root_after = cloud_chain.get("current_root_hash", "")
        result.local_height_after = result.local_height_before
        result.local_root_after = result.local_root_before
        result.success = self._save_chain(self.cloud_chain_path, cloud_chain)
        result.sync_time_ms = (time.time() - start_time) * 1000

        return result

    def sync_cloud_to_local(self) -> SyncResult:
        """云端→本地同步（反向同步，逻辑类似）"""
        start_time = time.time()
        result = SyncResult(success=False, direction="cloud_to_local")

        local_chain = self._load_chain(self.local_chain_path)
        cloud_chain = self._load_chain(self.cloud_chain_path)

        if not cloud_chain:
            result.errors.append("云端链不存在或无法加载")
            result.sync_time_ms = (time.time() - start_time) * 1000
            return result

        result.cloud_height_before = cloud_chain.get("block_height", cloud_chain.get("height", 0))
        result.cloud_root_before = cloud_chain.get("current_root_hash", cloud_chain.get("root_hash", ""))

        if local_chain:
            result.local_height_before = local_chain.get("height", local_chain.get("current_height", 0))
            result.local_root_before = local_chain.get("root_hash", local_chain.get("global_root_hash", ""))

        # 查找差异区块
        local_blocks = self._extract_blocks(local_chain) if local_chain else []
        cloud_blocks = self._extract_blocks(cloud_chain)
        local_heights = {b.get("height") for b in local_blocks}

        new_blocks = [b for b in cloud_blocks if b.get("height") not in local_heights]

        # 追加新区块
        all_blocks = local_blocks + new_blocks
        all_blocks = sorted(all_blocks, key=lambda b: b.get("height", 0))

        # 更新本地链
        if not local_chain:
            local_chain = {
                "did": "DID-BR-000002",
                "trace_mark": "Ω₀⊂⊙∞⊂Ω",
                "efuse_registry": [],
            }

        if all_blocks:
            latest = all_blocks[-1]
            local_chain["height"] = latest.get("height", 0)
            local_chain["current_height"] = latest.get("height", 0)
            local_chain["root_hash"] = latest.get("new_root_hash", latest.get("root_hash", ""))
            local_chain["global_root_hash"] = latest.get("new_root_hash", latest.get("root_hash", ""))
            local_chain["blocks"] = all_blocks
            local_chain["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S.%f+00:00", time.gmtime())

        result.blocks_synced = len(new_blocks)
        result.local_height_after = local_chain.get("height", 0)
        result.local_root_after = local_chain.get("root_hash", "")
        result.cloud_height_after = result.cloud_height_before
        result.cloud_root_after = result.cloud_root_before
        result.success = self._save_chain(self.local_chain_path, local_chain)
        result.sync_time_ms = (time.time() - start_time) * 1000

        return result


class ChainIntegrityChecker:
    """
    账本完整性校验器 - 全链哈希校验，检测断链/篡改/缺失
    """

    def __init__(self, chain_path: str):
        self.chain_path = chain_path

    def _load_chain(self) -> Optional[Dict[str, Any]]:
        if not os.path.exists(self.chain_path):
            return None
        try:
            with open(self.chain_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def verify(self) -> IntegrityResult:
        """执行完整性校验"""
        start_time = time.time()
        result = IntegrityResult(valid=True)

        chain = self._load_chain()
        if not chain:
            result.valid = False
            result.errors = ["链文件不存在或无法加载"] if hasattr(result, "errors") else []
            result.check_time_ms = (time.time() - start_time) * 1000
            return result

        blocks = chain.get("blocks", [])
        result.total_blocks = len(blocks)

        if not blocks:
            result.valid = False
            result.check_time_ms = (time.time() - start_time) * 1000
            return result

        # 按高度排序
        sorted_blocks = sorted(blocks, key=lambda b: b.get("height", 0))

        # 检查缺失高度和重复高度
        heights = [b.get("height") for b in sorted_blocks]
        min_height = min(heights) if heights else 0
        max_height = max(heights) if heights else 0

        height_counts = {}
        for h in heights:
            height_counts[h] = height_counts.get(h, 0) + 1
        result.duplicate_heights = [h for h, c in height_counts.items() if c > 1]

        expected_heights = set(range(min_height, max_height + 1))
        actual_heights = set(heights)
        result.missing_blocks = sorted(expected_heights - actual_heights)

        # 链式哈希校验
        for i in range(1, len(sorted_blocks)):
            prev_block = sorted_blocks[i - 1]
            curr_block = sorted_blocks[i]
            result.checked_blocks += 1

            prev_root = prev_block.get("new_root_hash", prev_block.get("root_hash", ""))
            curr_parent = curr_block.get("parent_hash", curr_block.get("parent_root_hash", ""))

            if prev_root and curr_parent and prev_root.upper() != curr_parent.upper():
                result.broken_links.append({
                    "height": curr_block.get("height"),
                    "asset_id": curr_block.get("asset_id"),
                    "expected_parent": prev_root,
                    "actual_parent": curr_parent,
                })
                result.valid = False

        # 校验最终根哈希
        if sorted_blocks:
            latest = sorted_blocks[-1]
            latest_root = latest.get("new_root_hash", latest.get("root_hash", ""))
            chain_root = chain.get("root_hash", chain.get("global_root_hash", chain.get("current_root_hash", "")))

            if latest_root and chain_root and latest_root.upper() != chain_root.upper():
                result.hash_mismatches.append({
                    "type": "root_hash_mismatch",
                    "latest_block_root": latest_root,
                    "chain_root": chain_root,
                })
                result.valid = False

        result.check_time_ms = (time.time() - start_time) * 1000
        return result
