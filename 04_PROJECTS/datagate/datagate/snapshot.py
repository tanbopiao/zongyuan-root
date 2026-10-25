"""快照引擎: Merkle-DAG 锚定 + StateVersion + TTL —— 方案 §二.3 / Step3.5

- 每次拉取/变更生产数据生成快照, 计算 TruthRootHash(SHA256 Merkle 根)
- StateVersion 跟随业务变更单调递增, 支持回退到上一版生产快照
- Agent 拿到的是带哈希背书的实体视图, 不是原始库数据
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field


def _h(x: str) -> str:
    return hashlib.sha256(x.encode()).hexdigest()


def merkle_root(field_hashes: list[str]) -> str:
    """两两归并的简化 Merkle 根; 空集返回空哈希占位。"""
    if not field_hashes:
        return _h("")
    layer = sorted(field_hashes)            # 排序保证字段序无关
    while len(layer) > 1:
        layer = [_h(layer[i] + layer[i + 1]) if i + 1 < len(layer)
                 else _h(layer[i] + layer[i]) for i in range(0, len(layer), 2)]
    return layer[0]


@dataclass
class Snapshot:
    eid: str
    state_version: int
    truth_root_hash: str
    data: dict
    source_system: str
    source_primary_key: str
    is_real_time: bool                     # True=CDC/API实时, False=文件离线(stale标签)
    ttl_seconds: float
    committed_at: float = field(default_factory=time.time)

    def is_stale(self, now: float | None = None) -> bool:
        """TTL 超时 → data_stale 熔断(方案 §三 新增熔断掩码)。"""
        now = time.time() if now is None else now
        return (now - self.committed_at) > self.ttl_seconds

    def age(self, now: float | None = None) -> float:
        now = time.time() if now is None else now
        return now - self.committed_at


class SnapshotStore:
    """快照存储(内存骨架, 持久化介质预留: 本地文件/Merkle-DAG 叶子)。"""

    def __init__(self) -> None:
        self._latest: dict[str, Snapshot] = {}      # eid -> 最新快照
        self._history: dict[str, list[Snapshot]] = {}
        self._version = 0                            # 全局单调递增 StateVersion

    @property
    def state_version(self) -> int:
        return self._version

    def commit(self, eid: str, data: dict, *, source_system: str,
               source_primary_key: str, is_real_time: bool,
               ttl_seconds: float) -> Snapshot:
        """生成新快照: 计算 TruthRootHash, StateVersion 单调+1。"""
        self._version += 1
        field_hashes = [_h(f"{k}={json.dumps(v, ensure_ascii=False, sort_keys=True)}")
                        for k, v in sorted(data.items())]
        snap = Snapshot(
            eid=eid, state_version=self._version,
            truth_root_hash=merkle_root(field_hashes), data=dict(data),
            source_system=source_system, source_primary_key=source_primary_key,
            is_real_time=is_real_time, ttl_seconds=ttl_seconds,
        )
        self._latest[eid] = snap
        self._history.setdefault(eid, []).append(snap)
        return snap

    def latest(self, eid: str) -> Snapshot | None:
        return self._latest.get(eid)

    def rollback(self, eid: str, state_version: int) -> Snapshot | None:
        """按 StateVersion 回退到指定历史快照(方案 §二.3 / 协议 §2.3 第6步)。"""
        for snap in reversed(self._history.get(eid, [])):
            if snap.state_version == state_version:
                self._latest[eid] = snap
                return snap
        return None
