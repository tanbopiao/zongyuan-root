# -*- coding: utf-8 -*-
"""
federated_memory_pool 联邦记忆池核心模块
ZONGYUAN-ROOT 元极恒一自治体系 ｜ 锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002
纯标准库实现，零第三方依赖
"""
import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

ANCHOR = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"

TRUTH_TYPES = ("meta_law", "rule", "config", "decision", "data",
               "creative", "risk", "protocol", "unknown")


def sha256(text: str) -> str:
    """SHA256 唯一指纹"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class MemoryRecord:
    """记忆真值条目"""
    key: str
    value: object
    truth_type: str = "data"
    anchor: str = ANCHOR
    did: str = DID
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    version: int = 1
    source: str = ""

    def __post_init__(self):
        if self.truth_type not in TRUTH_TYPES:
            raise ValueError(f"非法 truth_type: {self.truth_type}")
        self.hash = self._calc_hash()
        self.stored_hash = ""  # 加载时保留磁盘原始哈希，用于篡改检测

    def _calc_hash(self) -> str:
        payload = json.dumps(
            {"key": self.key, "value": self.value, "truth_type": self.truth_type,
             "anchor": self.anchor, "did": self.did, "version": self.version},
            ensure_ascii=False, sort_keys=True)
        return sha256(payload)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("stored_hash", None)
        d["hash"] = self.hash
        return d

    def is_tampered(self) -> bool:
        """存储哈希存在且与当前重算不一致 = 被篡改"""
        return bool(self.stored_hash) and self.stored_hash != self._calc_hash()


class MemoryNode:
    """记忆节点：本地实例持久层 / 账号持久层 / 云端中枢 / 魔搭数据湖 / 共享大脑"""

    def __init__(self, name: str, base_dir: str):
        self.name = name
        self.base_dir = base_dir
        self.records: Dict[str, MemoryRecord] = {}
        os.makedirs(base_dir, exist_ok=True)
        self._load()

    def _path(self) -> str:
        return os.path.join(self.base_dir, f"{self.name}_memory.json")

    def _load(self):
        p = self._path()
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            for key, rec in data.items():
                try:
                    r = MemoryRecord(
                        key=rec["key"], value=rec.get("value"),
                        truth_type=rec.get("truth_type", "data"),
                        anchor=rec.get("anchor", ANCHOR),
                        did=rec.get("did", DID),
                        created_at=rec.get("created_at", ""),
                        version=rec.get("version", 1),
                        source=rec.get("source", ""))
                    r.stored_hash = rec.get("hash", "")
                    self.records[key] = r
                except (KeyError, ValueError):
                    continue  # 跳过损坏条目

    def add(self, record: MemoryRecord) -> str:
        """写入（同 key 覆盖升级）"""
        old = self.records.get(record.key)
        if old and old.value != record.value:
            record.version = old.version + 1
        self.records[record.key] = record
        self._save()
        return record.hash

    def query(self, key: str) -> Optional[MemoryRecord]:
        return self.records.get(key)

    def search(self, keyword: str) -> List[MemoryRecord]:
        return [r for r in self.records.values()
                if keyword in r.key or keyword in str(r.value)]

    def count(self) -> int:
        return len(self.records)

    def verify(self) -> Dict[str, bool]:
        """全量哈希校验，防篡改（比对存储哈希与当前重算哈希）"""
        result = {}
        for key, rec in self.records.items():
            result[key] = not rec.is_tampered()
        return result

    def _save(self):
        with open(self._path(), "w", encoding="utf-8") as f:
            json.dump({k: v.to_dict() for k, v in self.records.items()},
                      f, ensure_ascii=False, indent=2)


class FederatedMemoryPool:
    """联邦记忆池：多节点注册 + 增量同步 + 冲突消解"""

    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        os.makedirs(root_dir, exist_ok=True)
        self.nodes: Dict[str, MemoryNode] = {}

    def register_node(self, name: str) -> MemoryNode:
        """注册记忆节点（本地/账号/云端/魔搭/大脑）"""
        node_dir = os.path.join(self.root_dir, "nodes")
        node = MemoryNode(name, node_dir)
        self.nodes[name] = node
        return node

    def discover(self) -> Dict[str, MemoryNode]:
        """从磁盘发现已存在节点"""
        node_dir = os.path.join(self.root_dir, "nodes")
        if os.path.isdir(node_dir):
            for fn in sorted(os.listdir(node_dir)):
                if fn.endswith("_memory.json"):
                    name = fn[:-len("_memory.json")]
                    if name not in self.nodes:
                        self.nodes[name] = MemoryNode(name, node_dir)
        return self.nodes

    def sync(self, source: str, targets: List[str],
             incremental: bool = True) -> dict:
        """跨节点增量同步；incremental=False 全量覆盖"""
        src = self.nodes[source]
        report = {"source": source, "pushed": 0, "skipped": 0,
                  "conflicts": 0, "to_targets": {}}
        for tname in targets:
            tgt = self.nodes[tname]
            pushed = skipped = 0
            for key, rec in src.records.items():
                existing = tgt.query(key)
                if existing and existing.value == rec.value and incremental:
                    skipped += 1
                    continue
                if existing and existing.value != rec.value:
                    # 冲突消解：取 version 高者
                    if existing.version >= rec.version:
                        report["conflicts"] += 1
                        continue
                tgt.add(rec)
                pushed += 1
            report["pushed"] += pushed
            report["skipped"] += skipped
            report["to_targets"][tname] = {"pushed": pushed, "skipped": skipped}
        return report

    def merge_stats(self) -> dict:
        """各节点记忆统计 + 总哈希"""
        stats = {}
        all_keys = set()
        for name, node in self.nodes.items():
            stats[name] = {"count": node.count(), "hash": sha256(
                json.dumps(sorted(node.records.keys()), ensure_ascii=False))}
            all_keys |= set(node.records.keys())
        stats["_federation"] = {"total_unique_records": len(all_keys)}
        return stats
