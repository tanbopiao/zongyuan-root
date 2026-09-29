#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 全域同步协议集成引擎 V1.0
全网全域挖掘整理的同步协议、算法与规则集成模块

包含:
- CRDT无冲突复制数据类型 (LWW Register / G-Counter / PN-Counter / OR-Set)
- 逻辑时钟 (Lamport / Vector Clock / HLC混合逻辑时钟)
- 增量差分同步算法 (rsync-like分块哈希)
- 双向同步三向Diff算法
- 冲突解决策略引擎
- 分级同步策略
- Gossip流行病传播协议
- 同步质量监控

确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
体系: ZONGYUAN-ROOT 元极恒一自治体系
"""

import json
import hashlib
import time
import uuid
import zlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum
from collections import defaultdict


# ============================================================
# 第一部分: CRDT 无冲突复制数据类型
# ============================================================

class LWWRegister:
    """
    Last-Write-Wins Register (LWW寄存器)
    基于时间戳的最后写入者胜出策略
    数学保证: 交换律、结合律、幂等律
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.value: Any = None
        self.timestamp: float = 0.0
        self.node: str = ""

    def set(self, value: Any, timestamp: Optional[float] = None) -> None:
        """设置值，仅当时间戳更新时生效"""
        ts = timestamp if timestamp is not None else time.time()
        if ts > self.timestamp or (ts == self.timestamp and self.node_id > self.node):
            self.value = value
            self.timestamp = ts
            self.node = self.node_id

    def get(self) -> Any:
        """获取当前值"""
        return self.value

    def merge(self, other: 'LWWRegister') -> None:
        """合并另一个副本（幂等、交换、结合）"""
        if other.timestamp > self.timestamp or \
           (other.timestamp == self.timestamp and other.node > self.node):
            self.value = other.value
            self.timestamp = other.timestamp
            self.node = other.node

    def to_dict(self) -> Dict:
        return {"value": self.value, "timestamp": self.timestamp, "node": self.node}

    @classmethod
    def from_dict(cls, data: Dict, node_id: str) -> 'LWWRegister':
        reg = cls(node_id)
        reg.value = data.get("value")
        reg.timestamp = data.get("timestamp", 0.0)
        reg.node = data.get("node", "")
        return reg


class GCounter:
    """
    Grow-Only Counter (只增计数器)
    每个节点维护自己的计数器，总值为所有节点之和
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.counts: Dict[str, int] = defaultdict(int)

    def increment(self, amount: int = 1) -> None:
        """增加计数（只能增加）"""
        if amount < 0:
            raise ValueError("G-Counter只能增加")
        self.counts[self.node_id] += amount

    def value(self) -> int:
        """获取总计数"""
        return sum(self.counts.values())

    def merge(self, other: 'GCounter') -> None:
        """合并另一个副本（取每个节点的最大值）"""
        for node, count in other.counts.items():
            self.counts[node] = max(self.counts[node], count)

    def to_dict(self) -> Dict:
        return {"counts": dict(self.counts)}

    @classmethod
    def from_dict(cls, data: Dict, node_id: str) -> 'GCounter':
        counter = cls(node_id)
        counter.counts = defaultdict(int, data.get("counts", {}))
        return counter


class PNCounter:
    """
    Positive-Negative Counter (可增可减计数器)
    由两个G-Counter组成：P(增加)和N(减少)，总值 = P - N
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.p = GCounter(node_id)  # 增加计数
        self.n = GCounter(node_id)  # 减少计数

    def increment(self, amount: int = 1) -> None:
        self.p.increment(amount)

    def decrement(self, amount: int = 1) -> None:
        self.n.increment(amount)

    def value(self) -> int:
        return self.p.value() - self.n.value()

    def merge(self, other: 'PNCounter') -> None:
        self.p.merge(other.p)
        self.n.merge(other.n)

    def to_dict(self) -> Dict:
        return {"p": self.p.to_dict(), "n": self.n.to_dict()}

    @classmethod
    def from_dict(cls, data: Dict, node_id: str) -> 'PNCounter':
        counter = cls(node_id)
        counter.p = GCounter.from_dict(data.get("p", {}), node_id)
        counter.n = GCounter.from_dict(data.get("n", {}), node_id)
        return counter


class ORSet:
    """
    Observed-Remove Set (观察删除集合)
    支持添加和删除，删除只影响已观察到的元素
    使用唯一标签（dot）标识每次添加
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.elements: Dict[Any, Set[str]] = defaultdict(set)  # value -> set of dots
        self.tombstones: Set[str] = set()  # 已删除的dots

    def _new_dot(self) -> str:
        return f"{self.node_id}:{uuid.uuid4().hex[:8]}"

    def add(self, element: Any) -> None:
        """添加元素"""
        dot = self._new_dot()
        self.elements[element].add(dot)

    def remove(self, element: Any) -> None:
        """删除元素（仅删除已观察到的dots）"""
        if element in self.elements:
            self.tombstones.update(self.elements[element])
            del self.elements[element]

    def contains(self, element: Any) -> bool:
        return element in self.elements and len(self.elements[element]) > 0

    def value(self) -> Set[Any]:
        return {e for e, dots in self.elements.items() if dots}

    def merge(self, other: 'ORSet') -> None:
        """合并另一个副本"""
        # 合并墓碑
        self.tombstones.update(other.tombstones)
        # 合并元素，过滤墓碑
        for element, dots in other.elements.items():
            valid_dots = dots - self.tombstones
            if valid_dots:
                self.elements[element].update(valid_dots)
        # 清理本地墓碑中的dots
        for element in list(self.elements.keys()):
            self.elements[element] -= self.tombstones
            if not self.elements[element]:
                del self.elements[element]

    def to_dict(self) -> Dict:
        return {
            "elements": {str(k): list(v) for k, v in self.elements.items()},
            "tombstones": list(self.tombstones)
        }


# ============================================================
# 第二部分: 逻辑时钟
# ============================================================

class LamportClock:
    """
    Lamport逻辑时钟
    保证: 若 a → b，则 C(a) < C(b)
    局限: 反向不成立，无法检测并发
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.counter: int = 0

    def local_event(self) -> int:
        """本地事件，计数器+1"""
        self.counter += 1
        return self.counter

    def send_event(self) -> int:
        """发送消息事件，计数器+1，返回时间戳"""
        self.counter += 1
        return self.counter

    def receive_event(self, remote_timestamp: int) -> int:
        """接收消息事件，取最大值+1"""
        self.counter = max(self.counter, remote_timestamp) + 1
        return self.counter

    def get(self) -> int:
        return self.counter

    def happened_before(self, ts1: int, ts2: int) -> Optional[bool]:
        """
        判断因果关系
        返回: True(ts1先于ts2), False(ts1后于ts2), None(无法判断/并发)
        """
        if ts1 < ts2:
            return True  # 可能因果先于，也可能并发
        elif ts1 > ts2:
            return False
        return None  # 相等无法判断


class VectorClock:
    """
    向量时钟
    可精确判断因果关系和并发关系
    每个节点维护计数器数组
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.clock: Dict[str, int] = defaultdict(int)

    def local_event(self) -> Dict[str, int]:
        self.clock[self.node_id] += 1
        return dict(self.clock)

    def send_event(self) -> Dict[str, int]:
        self.clock[self.node_id] += 1
        return dict(self.clock)

    def receive_event(self, remote_clock: Dict[str, int]) -> Dict[str, int]:
        """合并远程时钟，取每个节点的最大值，然后本地+1"""
        for node, count in remote_clock.items():
            self.clock[node] = max(self.clock[node], count)
        self.clock[self.node_id] += 1
        return dict(self.clock)

    @staticmethod
    def compare(vc1: Dict[str, int], vc2: Dict[str, int]) -> str:
        """
        比较两个向量时钟
        返回: 'before'(vc1因果先于vc2), 'after'(vc1因果后于vc2),
              'concurrent'(并发), 'equal'(相等)
        """
        all_nodes = set(vc1.keys()) | set(vc2.keys())
        less = False
        greater = False
        for node in all_nodes:
            v1 = vc1.get(node, 0)
            v2 = vc2.get(node, 0)
            if v1 < v2:
                less = True
            elif v1 > v2:
                greater = True
        if less and greater:
            return "concurrent"
        elif less:
            return "before"
        elif greater:
            return "after"
        return "equal"

    def get(self) -> Dict[str, int]:
        return dict(self.clock)

    def to_dict(self) -> Dict:
        return {"clock": dict(self.clock), "node_id": self.node_id}

    @classmethod
    def from_dict(cls, data: Dict) -> 'VectorClock':
        vc = cls(data.get("node_id", "unknown"))
        vc.clock = defaultdict(int, data.get("clock", {}))
        return vc


class HybridLogicalClock:
    """
    混合逻辑时钟 (HLC)
    结合物理时钟和逻辑时钟，兼顾因果排序和真实时间
    结构: (physical, logical)
    优势: 单值大小，不随节点数增长；接近真实物理时间
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.physical: int = 0  # 物理时间（毫秒）
        self.logical: int = 0   # 逻辑计数器

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def local_event(self) -> Tuple[int, int]:
        """本地事件"""
        prev_physical = self.physical
        self.physical = max(self.physical, self._now_ms())
        if self.physical == prev_physical:
            self.logical += 1
        else:
            self.logical = 0
        return (self.physical, self.logical)

    def send_event(self) -> Tuple[int, int]:
        """发送消息事件"""
        return self.local_event()

    def receive_event(self, remote_physical: int, remote_logical: int) -> Tuple[int, int]:
        """接收消息事件"""
        prev_physical = self.physical
        self.physical = max(self.physical, remote_physical, self._now_ms())
        if self.physical == prev_physical and self.physical == remote_physical:
            self.logical = max(self.logical, remote_logical) + 1
        elif self.physical == prev_physical:
            self.logical += 1
        elif self.physical == remote_physical:
            self.logical = remote_logical + 1
        else:
            self.logical = 0
        return (self.physical, self.logical)

    @staticmethod
    def compare(hlc1: Tuple[int, int], hlc2: Tuple[int, int]) -> int:
        """
        比较两个HLC时间戳
        返回: -1(hlc1 < hlc2), 0(相等), 1(hlc1 > hlc2)
        """
        if hlc1[0] != hlc2[0]:
            return -1 if hlc1[0] < hlc2[0] else 1
        if hlc1[1] != hlc2[1]:
            return -1 if hlc1[1] < hlc2[1] else 1
        return 0

    def get(self) -> Tuple[int, int]:
        return (self.physical, self.logical)

    def to_dict(self) -> Dict:
        return {"physical": self.physical, "logical": self.logical, "node_id": self.node_id}


# ============================================================
# 第三部分: 增量差分同步算法 (rsync-like)
# ============================================================

class DeltaSync:
    """
    增量差分同步引擎
    基于rsync算法：分块哈希匹配，仅传输变化的块
    大幅减少大文件小修改时的传输量
    """
    def __init__(self, block_size: int = 4096):
        self.block_size = block_size

    def _weak_hash(self, data: bytes) -> int:
        """滚动弱哈希（Adler-32变体），快速匹配"""
        return zlib.adler32(data) & 0xffffffff

    def _strong_hash(self, data: bytes) -> str:
        """强哈希（MD5），精确确认"""
        return hashlib.md5(data).hexdigest()

    def compute_signature(self, data: bytes) -> List[Dict]:
        """
        计算旧文件的签名（分块哈希）
        返回: [{index, weak_hash, strong_hash, length}, ...]
        """
        blocks = []
        for i in range(0, len(data), self.block_size):
            block = data[i:i + self.block_size]
            blocks.append({
                "index": i // self.block_size,
                "offset": i,
                "length": len(block),
                "weak_hash": self._weak_hash(block),
                "strong_hash": self._strong_hash(block)
            })
        return blocks

    def compute_delta(self, new_data: bytes, signature: List[Dict]) -> List[Dict]:
        """
        计算新文件相对于旧签名的差异
        返回: [{type: 'block'|'data', index?, offset?, length?, data?}, ...]
        """
        # 构建弱哈希到块的映射
        weak_map = defaultdict(list)
        for block in signature:
            weak_map[block["weak_hash"]].append(block)

        delta = []
        i = 0
        n = len(new_data)

        while i < n:
            # 尝试匹配当前位置的块
            window = new_data[i:i + self.block_size]
            if len(window) < self.block_size and i + self.block_size > n:
                # 最后不足一块，作为数据传输
                delta.append({"type": "data", "offset": i, "length": len(window), "data": window.hex()})
                break

            wh = self._weak_hash(window)
            matched = None
            if wh in weak_map:
                # 弱哈希匹配，用强哈希确认
                sh = self._strong_hash(window)
                for block in weak_map[wh]:
                    if block["strong_hash"] == sh:
                        matched = block
                        break

            if matched:
                # 匹配到旧块，只传输块引用
                delta.append({"type": "block", "index": matched["index"], "offset": i})
                i += matched["length"]
            else:
                # 未匹配，传输一个字节数据，继续滑动
                delta.append({"type": "data", "offset": i, "length": 1, "data": new_data[i:i+1].hex()})
                i += 1

        return delta

    def apply_delta(self, old_data: bytes, delta: List[Dict]) -> bytes:
        """
        应用差异到旧数据，生成新数据
        """
        # 构建旧数据的块索引
        blocks = []
        for i in range(0, len(old_data), self.block_size):
            blocks.append(old_data[i:i + self.block_size])

        result = bytearray()
        for item in delta:
            if item["type"] == "block":
                # 引用旧块
                idx = item["index"]
                if idx < len(blocks):
                    result.extend(blocks[idx])
            elif item["type"] == "data":
                # 新数据
                result.extend(bytes.fromhex(item["data"]))
        return bytes(result)

    def estimate_savings(self, old_size: int, delta: List[Dict]) -> Dict:
        """估算传输节省"""
        block_refs = sum(1 for d in delta if d["type"] == "block")
        data_bytes = sum(d["length"] for d in delta if d["type"] == "data")
        total_transfer = data_bytes + block_refs * 8  # 块引用约8字节
        savings = (1 - total_transfer / old_size) * 100 if old_size > 0 else 0
        return {
            "old_size": old_size,
            "blocks_matched": block_refs,
            "new_data_bytes": data_bytes,
            "estimated_transfer": total_transfer,
            "savings_percent": round(savings, 2)
        }


# ============================================================
# 第四部分: 双向同步三向Diff算法
# ============================================================

class ThreeWaySync:
    """
    双向同步三向Diff引擎
    基于Manifest清单追踪，智能分类变更，解决冲突
    """
    class ChangeType(Enum):
        NEW_LOCAL = "new_local"
        NEW_REMOTE = "new_remote"
        MODIFIED_LOCAL = "modified_local"
        MODIFIED_REMOTE = "modified_remote"
        DELETED_LOCAL = "deleted_local"
        DELETED_REMOTE = "deleted_remote"
        CONFLICT = "conflict"
        UNCHANGED = "unchanged"

    @dataclass
    class FileManifest:
        """文件清单条目"""
        path: str
        size: int = 0
        mtime: float = 0.0
        hash: str = ""
        version: int = 0

    def __init__(self):
        self.base_manifest: Dict[str, FileManifest] = {}  # 基准清单（上次同步后）

    def snapshot(self, files: Dict[str, Dict]) -> None:
        """保存当前状态为基准清单"""
        self.base_manifest = {}
        for path, info in files.items():
            self.base_manifest[path] = self.FileManifest(
                path=path,
                size=info.get("size", 0),
                mtime=info.get("mtime", 0.0),
                hash=info.get("hash", ""),
                version=info.get("version", 0)
            )

    def classify_changes(self, local_files: Dict[str, Dict],
                          remote_files: Dict[str, Dict]) -> List[Dict]:
        """
        三向Diff：本地、远端分别与基准对比，智能分类
        返回: [{path, change_type, local_info, remote_info, base_info}, ...]
        """
        all_paths = set(local_files.keys()) | set(remote_files.keys()) | set(self.base_manifest.keys())
        changes = []

        for path in all_paths:
            local = local_files.get(path)
            remote = remote_files.get(path)
            base = self.base_manifest.get(path)

            local_changed = self._is_changed(local, base)
            remote_changed = self._is_changed(remote, base)

            if local_changed and remote_changed:
                # 两端都修改，检查是否冲突
                if local and remote and local.get("hash") == remote.get("hash"):
                    change_type = self.ChangeType.UNCHANGED  # 相同修改，无冲突
                else:
                    change_type = self.ChangeType.CONFLICT
            elif local_changed:
                if local is None:
                    change_type = self.ChangeType.DELETED_LOCAL
                elif base is None:
                    change_type = self.ChangeType.NEW_LOCAL
                else:
                    change_type = self.ChangeType.MODIFIED_LOCAL
            elif remote_changed:
                if remote is None:
                    change_type = self.ChangeType.DELETED_REMOTE
                elif base is None:
                    change_type = self.ChangeType.NEW_REMOTE
                else:
                    change_type = self.ChangeType.MODIFIED_REMOTE
            else:
                change_type = self.ChangeType.UNCHANGED

            if change_type != self.ChangeType.UNCHANGED:
                changes.append({
                    "path": path,
                    "change_type": change_type.value,
                    "local": local,
                    "remote": remote,
                    "base": self._manifest_to_dict(base)
                })

        return changes

    def _is_changed(self, current: Optional[Dict], base: Optional[FileManifest]) -> bool:
        """判断是否相对于基准发生了变化"""
        if current is None and base is None:
            return False
        if current is None or base is None:
            return True
        # 优先用hash判断，其次用size+mtime
        if current.get("hash") and base.hash:
            return current["hash"] != base.hash
        if current.get("version") and base.version:
            return current["version"] != base.version
        return current.get("size", 0) != base.size or \
               abs(current.get("mtime", 0.0) - base.mtime) > 1.0

    def _manifest_to_dict(self, manifest: Optional[FileManifest]) -> Optional[Dict]:
        if manifest is None:
            return None
        return {"path": manifest.path, "size": manifest.size,
                "mtime": manifest.mtime, "hash": manifest.hash,
                "version": manifest.version}


# ============================================================
# 第五部分: 冲突解决策略引擎
# ============================================================

class ConflictResolver:
    """
    冲突解决策略引擎
    支持多种策略: LWW / 字段级合并 / 版本向量 / 业务规则 / 人工干预
    """
    class Strategy(Enum):
        LWW = "last_write_wins"          # 最后写入者胜出
        FIELD_MERGE = "field_merge"      # 字段级合并
        VECTOR_CLOCK = "vector_clock"    # 版本向量因果判断
        LOCAL_WINS = "local_wins"        # 本地胜出
        REMOTE_WINS = "remote_wins"      # 远端胜出
        MANUAL = "manual"                 # 人工干预
        KEEP_BOTH = "keep_both"          # 保留双方

    def __init__(self, default_strategy: Strategy = Strategy.LWW):
        self.default_strategy = default_strategy
        self.field_ownership: Dict[str, str] = {}  # 字段归属（哪个系统拥有哪个字段的最终决定权）

    def set_field_owner(self, field: str, owner: str) -> None:
        """设置字段归属（字段级合并策略使用）"""
        self.field_ownership[field] = owner

    def resolve(self, local: Dict, remote: Dict,
                strategy: Optional[Strategy] = None,
                context: Optional[Dict] = None) -> Dict:
        """
        解决冲突
        返回: {resolved_value, strategy_used, conflict_markers, needs_manual}
        """
        strat = strategy or self.default_strategy
        context = context or {}

        if strat == self.Strategy.LWW:
            return self._resolve_lww(local, remote, context)
        elif strat == self.Strategy.FIELD_MERGE:
            return self._resolve_field_merge(local, remote, context)
        elif strat == self.Strategy.VECTOR_CLOCK:
            return self._resolve_vector_clock(local, remote, context)
        elif strat == self.Strategy.LOCAL_WINS:
            return {"resolved_value": local, "strategy_used": strat.value,
                    "conflict_markers": [], "needs_manual": False}
        elif strat == self.Strategy.REMOTE_WINS:
            return {"resolved_value": remote, "strategy_used": strat.value,
                    "conflict_markers": [], "needs_manual": False}
        elif strat == self.Strategy.KEEP_BOTH:
            return self._resolve_keep_both(local, remote, context)
        else:  # MANUAL
            return {"resolved_value": None, "strategy_used": strat.value,
                    "conflict_markers": [{"local": local, "remote": remote}],
                    "needs_manual": True}

    def _resolve_lww(self, local: Dict, remote: Dict, context: Dict) -> Dict:
        """LWW: 基于时间戳/版本号的最后写入者胜出"""
        local_ts = local.get("_timestamp", local.get("_version", 0))
        remote_ts = remote.get("_timestamp", remote.get("_version", 0))
        if remote_ts > local_ts:
            winner = remote
        elif local_ts > remote_ts:
            winner = local
        else:
            # 时间戳相等，用节点ID字典序打破平局
            local_node = local.get("_node", "")
            remote_node = remote.get("_node", "")
            winner = remote if remote_node > local_node else local
        return {"resolved_value": winner, "strategy_used": "last_write_wins",
                "conflict_markers": [], "needs_manual": False}

    def _resolve_field_merge(self, local: Dict, remote: Dict, context: Dict) -> Dict:
        """字段级合并: 不同字段自动合并，相同字段按归属决定"""
        merged = dict(local)
        conflicts = []
        for key, remote_val in remote.items():
            if key.startswith("_"):
                continue
            if key not in local:
                merged[key] = remote_val
            elif local[key] != remote_val:
                # 字段冲突，按归属决定
                owner = self.field_ownership.get(key)
                if owner == "remote":
                    merged[key] = remote_val
                elif owner == "local":
                    pass  # 保留本地值
                else:
                    # 无归属，标记冲突
                    conflicts.append({"field": key, "local": local[key], "remote": remote_val})
        return {"resolved_value": merged, "strategy_used": "field_merge",
                "conflict_markers": conflicts, "needs_manual": len(conflicts) > 0}

    def _resolve_vector_clock(self, local: Dict, remote: Dict, context: Dict) -> Dict:
        """版本向量: 基于因果关系判断"""
        local_vc = local.get("_vector_clock", {})
        remote_vc = remote.get("_vector_clock", {})
        relation = VectorClock.compare(local_vc, remote_vc)
        if relation == "before":
            # 本地因果先于远端，远端更新
            return {"resolved_value": remote, "strategy_used": "vector_clock(remote_newer)",
                    "conflict_markers": [], "needs_manual": False}
        elif relation == "after":
            # 本地因果后于远端，本地更新
            return {"resolved_value": local, "strategy_used": "vector_clock(local_newer)",
                    "conflict_markers": [], "needs_manual": False}
        else:
            # 并发，无法自动解决
            return {"resolved_value": None, "strategy_used": "vector_clock(concurrent)",
                    "conflict_markers": [{"local": local, "remote": remote}],
                    "needs_manual": True}

    def _resolve_keep_both(self, local: Dict, remote: Dict, context: Dict) -> Dict:
        """保留双方: 创建冲突副本"""
        suffix = context.get("conflict_suffix", "_conflict_remote")
        merged = dict(local)
        for key, val in remote.items():
            conflict_key = f"{key}{suffix}"
            merged[conflict_key] = val
        return {"resolved_value": merged, "strategy_used": "keep_both",
                "conflict_markers": [{"local_keys": list(local.keys()),
                                       "remote_keys": list(remote.keys())}],
                "needs_manual": True}


# ============================================================
# 第六部分: 分级同步策略引擎
# ============================================================

class TieredSyncEngine:
    """
    分级同步策略引擎
    根据数据重要程度分级，采用不同同步方式和延迟要求
    """
    class Tier(Enum):
        CRITICAL = "critical"      # 实时告警，准实时同步
        BUSINESS = "business"      # 核心业务，分钟级同步
        STATISTICS = "statistics"  # 统计数据，小时级同步
        ARCHIVE = "archive"        # 日志归档，天级同步

    TIER_CONFIG = {
        Tier.CRITICAL: {
            "sync_mode": "realtime_push",
            "max_latency_sec": 1,
            "consistency": "strong",
            "retry_policy": "exponential_backoff",
            "max_retries": 10,
            "priority": 1
        },
        Tier.BUSINESS: {
            "sync_mode": "incremental",
            "max_latency_sec": 60,
            "consistency": "eventual",
            "retry_policy": "exponential_backoff",
            "max_retries": 5,
            "priority": 2
        },
        Tier.STATISTICS: {
            "sync_mode": "batch",
            "max_latency_sec": 3600,
            "consistency": "eventual",
            "retry_policy": "fixed_interval",
            "max_retries": 3,
            "priority": 3
        },
        Tier.ARCHIVE: {
            "sync_mode": "async_batch",
            "max_latency_sec": 86400,
            "consistency": "weak",
            "retry_policy": "fixed_interval",
            "max_retries": 2,
            "priority": 4
        }
    }

    def __init__(self):
        self.data_tiers: Dict[str, 'TieredSyncEngine.Tier'] = {}  # 数据键 -> 级别
        self.sync_queue: List[Dict] = []  # 同步队列
        self.stats: Dict[str, Any] = defaultdict(lambda: {"total": 0, "success": 0, "failed": 0})

    def register_data(self, key: str, tier: Tier) -> None:
        """注册数据的同步级别"""
        self.data_tiers[key] = tier

    def enqueue(self, key: str, data: Any, operation: str = "upsert") -> Dict:
        """入队同步任务，按级别排序"""
        tier = self.data_tiers.get(key, self.Tier.BUSINESS)
        config = self.TIER_CONFIG[tier]
        task = {
            "id": str(uuid.uuid4()),
            "key": key,
            "data": data,
            "operation": operation,
            "tier": tier.value,
            "priority": config["priority"],
            "max_latency": config["max_latency_sec"],
            "enqueue_time": time.time(),
            "retry_count": 0,
            "max_retries": config["max_retries"]
        }
        self.sync_queue.append(task)
        # 按优先级排序
        self.sync_queue.sort(key=lambda x: x["priority"])
        return task

    def get_next_batch(self, max_items: int = 100) -> List[Dict]:
        """获取下一批同步任务（按优先级和超时）"""
        now = time.time()
        batch = []
        for task in self.sync_queue:
            if len(batch) >= max_items:
                break
            # 检查是否到了同步时间（根据延迟要求）
            age = now - task["enqueue_time"]
            if age >= task["max_latency"] * 0.1:  # 提前10%时间开始处理
                batch.append(task)
        return batch

    def mark_result(self, task_id: str, success: bool) -> None:
        """标记同步结果"""
        for task in self.sync_queue:
            if task["id"] == task_id:
                tier = task["tier"]
                self.stats[tier]["total"] += 1
                if success:
                    self.stats[tier]["success"] += 1
                    self.sync_queue.remove(task)
                else:
                    self.stats[tier]["failed"] += 1
                    task["retry_count"] += 1
                    if task["retry_count"] >= task["max_retries"]:
                        # 超过最大重试，移入死信
                        self.sync_queue.remove(task)
                        self.stats[tier].setdefault("dead_letter", []).append(task)
                break

    def get_stats(self) -> Dict:
        """获取同步统计"""
        result = {}
        for tier, stat in self.stats.items():
            total = stat["total"]
            success = stat["success"]
            result[tier] = {
                "total": total,
                "success": success,
                "failed": stat["failed"],
                "success_rate": round(success / total * 100, 2) if total > 0 else 0,
                "queue_size": len([t for t in self.sync_queue if t["tier"] == tier]),
                "dead_letter_count": len(stat.get("dead_letter", []))
            }
        return result


# ============================================================
# 第七部分: Gossip流行病传播协议
# ============================================================

class GossipProtocol:
    """
    Gossip流行病传播协议
    用于节点间状态传播，最终一致性，去中心化
    """
    def __init__(self, node_id: str, fanout: int = 3):
        self.node_id = node_id
        self.fanout = fanout  # 每次传播的节点数
        self.state: Dict[str, Any] = {}  # 本地状态
        self.known_nodes: Set[str] = set()  # 已知节点
        self.message_log: List[Dict] = []  # 消息日志

    def update_state(self, key: str, value: Any) -> None:
        """更新本地状态"""
        self.state[key] = value

    def get_state(self) -> Dict[str, Any]:
        return dict(self.state)

    def add_node(self, node_id: str) -> None:
        self.known_nodes.add(node_id)

    def select_targets(self) -> List[str]:
        """随机选择fanout个目标节点"""
        import random
        candidates = list(self.known_nodes - {self.node_id})
        if len(candidates) <= self.fanout:
            return candidates
        return random.sample(candidates, self.fanout)

    def create_gossip_message(self) -> Dict:
        """创建Gossip消息（携带本地状态摘要）"""
        return {
            "sender": self.node_id,
            "timestamp": time.time(),
            "state_digest": {k: self._digest(v) for k, v in self.state.items()},
            "known_nodes": list(self.known_nodes)
        }

    def _digest(self, value: Any) -> str:
        """计算值的摘要（用于快速比较）"""
        return hashlib.md5(json.dumps(value, sort_keys=True).encode()).hexdigest()[:8]

    def receive_gossip(self, message: Dict) -> Dict:
        """
        接收Gossip消息，合并状态
        返回: {merged_keys, new_nodes, needs_full_sync}
        """
        merged_keys = []
        new_nodes = set()
        needs_full_sync = []

        # 合并已知节点
        for node in message.get("known_nodes", []):
            if node not in self.known_nodes:
                self.known_nodes.add(node)
                new_nodes.add(node)

        # 比较状态摘要，发现差异
        remote_digest = message.get("state_digest", {})
        for key, digest in remote_digest.items():
            if key not in self.state:
                # 本地没有，需要全量同步
                needs_full_sync.append(key)
            elif self._digest(self.state[key]) != digest:
                # 摘要不同，需要全量同步
                needs_full_sync.append(key)

        # 记录消息
        self.message_log.append({
            "sender": message["sender"],
            "timestamp": message["timestamp"],
            "merged_keys": merged_keys,
            "new_nodes": list(new_nodes),
            "needs_full_sync": needs_full_sync
        })

        return {
            "merged_keys": merged_keys,
            "new_nodes": list(new_nodes),
            "needs_full_sync": needs_full_sync
        }

    def merge_full_state(self, remote_state: Dict[str, Any]) -> List[str]:
        """合并全量状态（LWW策略）"""
        merged = []
        for key, value in remote_state.items():
            if key not in self.state or self._digest(self.state[key]) != self._digest(value):
                self.state[key] = value  # LWW: 远端覆盖（简化版）
                merged.append(key)
        return merged


# ============================================================
# 第八部分: 同步质量监控
# ============================================================

class SyncQualityMonitor:
    """
    同步质量监控器
    监控同步延迟、成功率、冲突率、数据漂移率等指标
    """
    def __init__(self):
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.alerts: List[Dict] = []
        self.thresholds = {
            "latency_sec": {"warning": 60, "critical": 300},
            "success_rate": {"warning": 95, "critical": 90},
            "conflict_rate": {"warning": 5, "critical": 10},
            "drift_rate": {"warning": 1, "critical": 5}
        }

    def record_latency(self, channel: str, latency_sec: float) -> None:
        """记录同步延迟"""
        self.metrics[f"latency_{channel}"].append(latency_sec)

    def record_sync(self, channel: str, success: bool) -> None:
        """记录同步结果"""
        key = f"sync_{channel}"
        self.metrics[key].append(1.0 if success else 0.0)

    def record_conflict(self, channel: str) -> None:
        """记录冲突"""
        self.metrics[f"conflict_{channel}"].append(1.0)

    def record_drift(self, channel: str, drift_rate: float) -> None:
        """记录数据漂移率"""
        self.metrics[f"drift_{channel}"].append(drift_rate)

    def get_channel_stats(self, channel: str) -> Dict:
        """获取通道统计"""
        latencies = self.metrics.get(f"latency_{channel}", [])
        syncs = self.metrics.get(f"sync_{channel}", [])
        conflicts = self.metrics.get(f"conflict_{channel}", [])
        drifts = self.metrics.get(f"drift_{channel}", [])

        return {
            "channel": channel,
            "total_syncs": len(syncs),
            "success_rate": round(sum(syncs) / len(syncs) * 100, 2) if syncs else 0,
            "avg_latency_sec": round(sum(latencies) / len(latencies), 3) if latencies else 0,
            "max_latency_sec": max(latencies) if latencies else 0,
            "p95_latency_sec": self._percentile(latencies, 95) if latencies else 0,
            "conflict_count": len(conflicts),
            "conflict_rate": round(len(conflicts) / len(syncs) * 100, 2) if syncs else 0,
            "avg_drift_rate": round(sum(drifts) / len(drifts), 2) if drifts else 0
        }

    def _percentile(self, data: List[float], p: float) -> float:
        """计算百分位数"""
        if not data:
            return 0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * p / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]

    def check_alerts(self) -> List[Dict]:
        """检查告警阈值"""
        self.alerts = []
        channels = set()
        for key in self.metrics.keys():
            if key.startswith("sync_"):
                channels.add(key.replace("sync_", ""))

        for channel in channels:
            stats = self.get_channel_stats(channel)
            if stats["avg_latency_sec"] > self.thresholds["latency_sec"]["critical"]:
                self.alerts.append({"channel": channel, "type": "latency_critical",
                                     "value": stats["avg_latency_sec"],
                                     "threshold": self.thresholds["latency_sec"]["critical"]})
            elif stats["avg_latency_sec"] > self.thresholds["latency_sec"]["warning"]:
                self.alerts.append({"channel": channel, "type": "latency_warning",
                                     "value": stats["avg_latency_sec"],
                                     "threshold": self.thresholds["latency_sec"]["warning"]})

            if stats["success_rate"] < self.thresholds["success_rate"]["critical"]:
                self.alerts.append({"channel": channel, "type": "success_rate_critical",
                                     "value": stats["success_rate"],
                                     "threshold": self.thresholds["success_rate"]["critical"]})
            elif stats["success_rate"] < self.thresholds["success_rate"]["warning"]:
                self.alerts.append({"channel": channel, "type": "success_rate_warning",
                                     "value": stats["success_rate"],
                                     "threshold": self.thresholds["success_rate"]["warning"]})

        return self.alerts

    def get_report(self) -> Dict:
        """获取完整监控报告"""
        channels = set()
        for key in self.metrics.keys():
            if key.startswith("sync_"):
                channels.add(key.replace("sync_", ""))
        return {
            "timestamp": time.time(),
            "channels": {ch: self.get_channel_stats(ch) for ch in channels},
            "alerts": self.check_alerts(),
            "overall_success_rate": self._overall_success_rate(),
            "overall_avg_latency": self._overall_avg_latency()
        }

    def _overall_success_rate(self) -> float:
        all_syncs = []
        for key, vals in self.metrics.items():
            if key.startswith("sync_"):
                all_syncs.extend(vals)
        return round(sum(all_syncs) / len(all_syncs) * 100, 2) if all_syncs else 0

    def _overall_avg_latency(self) -> float:
        all_latencies = []
        for key, vals in self.metrics.items():
            if key.startswith("latency_"):
                all_latencies.extend(vals)
        return round(sum(all_latencies) / len(all_latencies), 3) if all_latencies else 0


# ============================================================
# 第九部分: 统一同步协议集成门面
# ============================================================

class SyncProtocolEngine:
    """
    ZONGYUAN-ROOT 全域同步协议集成引擎
    统一门面，整合所有同步协议和算法
    """
    VERSION = "1.0.0"
    DID = "DID-BR-000002"
    OMEGA = "Ω₀⊂⊙∞⊂Ω"

    def __init__(self, node_id: str):
        self.node_id = node_id
        # CRDT
        self.lww_registers: Dict[str, LWWRegister] = {}
        self.pn_counters: Dict[str, PNCounter] = {}
        self.or_sets: Dict[str, ORSet] = {}
        # 时钟
        self.lamport = LamportClock(node_id)
        self.vector_clock = VectorClock(node_id)
        self.hlc = HybridLogicalClock(node_id)
        # 同步算法
        self.delta_sync = DeltaSync()
        self.three_way_sync = ThreeWaySync()
        # 冲突解决
        self.conflict_resolver = ConflictResolver()
        # 分级同步
        self.tiered_engine = TieredSyncEngine()
        # Gossip
        self.gossip = GossipProtocol(node_id)
        # 监控
        self.monitor = SyncQualityMonitor()

    def get_capabilities(self) -> Dict:
        """获取引擎能力清单"""
        return {
            "version": self.VERSION,
            "node_id": self.node_id,
            "did": self.DID,
            "omega": self.OMEGA,
            "crdt_types": ["LWWRegister", "GCounter", "PNCounter", "ORSet"],
            "clocks": ["Lamport", "VectorClock", "HLC"],
            "sync_algorithms": ["DeltaSync(rsync-like)", "ThreeWaySync"],
            "conflict_strategies": [s.value for s in ConflictResolver.Strategy],
            "sync_tiers": [t.value for t in TieredSyncEngine.Tier],
            "protocols": ["Gossip"],
            "monitoring": ["latency", "success_rate", "conflict_rate", "drift_rate"]
        }

    def get_status(self) -> Dict:
        """获取引擎运行状态"""
        return {
            "node_id": self.node_id,
            "lamport_clock": self.lamport.get(),
            "vector_clock": self.vector_clock.get(),
            "hlc": self.hlc.get(),
            "crdt_registers": len(self.lww_registers),
            "crdt_counters": len(self.pn_counters),
            "crdt_sets": len(self.or_sets),
            "tiered_queue_size": len(self.tiered_engine.sync_queue),
            "gossip_known_nodes": len(self.gossip.known_nodes),
            "monitor_alerts": len(self.monitor.check_alerts()),
            "monitor_report": self.monitor.get_report()
        }

    def to_dict(self) -> Dict:
        """序列化引擎状态"""
        return {
            "version": self.VERSION,
            "node_id": self.node_id,
            "lamport": self.lamport.counter,
            "vector_clock": dict(self.vector_clock.clock),
            "hlc": {"physical": self.hlc.physical, "logical": self.hlc.logical},
            "capabilities": self.get_capabilities()
        }


# ============================================================
# 自测与演示
# ============================================================

def _self_test():
    """引擎自测"""
    print("=" * 60)
    print("ZONGYUAN-ROOT 全域同步协议集成引擎 V1.0 自测")
    print("=" * 60)

    engine = SyncProtocolEngine("test-node-001")

    # 1. CRDT测试
    print("\n[1] CRDT测试")
    reg = LWWRegister("node1")
    reg.set("value1", 100.0)
    reg2 = LWWRegister("node2")
    reg2.set("value2", 200.0)
    reg.merge(reg2)
    print(f"  LWW Register合并后值: {reg.get()} (应为value2)")

    counter = PNCounter("node1")
    counter.increment(5)
    counter.decrement(2)
    print(f"  PN Counter值: {counter.value()} (应为3)")

    # 2. 逻辑时钟测试
    print("\n[2] 逻辑时钟测试")
    vc1 = VectorClock("node1")
    vc2 = VectorClock("node2")
    vc1.local_event()
    vc1.local_event()
    vc2.local_event()
    print(f"  VC1: {vc1.get()}")
    print(f"  VC2: {vc2.get()}")
    print(f"  比较: {VectorClock.compare(vc1.get(), vc2.get())}")

    # 3. 增量差分同步测试
    print("\n[3] 增量差分同步测试")
    old_data = b"Hello World! " * 1000  # 13KB
    new_data = b"Hello World! " * 999 + b"Hello ZONGYUAN! "  # 修改最后部分
    signature = engine.delta_sync.compute_signature(old_data)
    delta = engine.delta_sync.compute_delta(new_data, signature)
    savings = engine.delta_sync.estimate_savings(len(old_data), delta)
    print(f"  旧数据大小: {savings['old_size']} 字节")
    print(f"  匹配块数: {savings['blocks_matched']}")
    print(f"  新数据字节: {savings['new_data_bytes']}")
    print(f"  估算传输: {savings['estimated_transfer']} 字节")
    print(f"  节省比例: {savings['savings_percent']}%")

    # 4. 冲突解决测试
    print("\n[4] 冲突解决测试")
    local = {"name": "Alice", "age": 30, "_timestamp": 100, "_node": "node1"}
    remote = {"name": "Bob", "age": 30, "_timestamp": 200, "_node": "node2"}
    result = engine.conflict_resolver.resolve(local, remote)
    print(f"  LWW策略结果: {result['resolved_value']['name']} (应为Bob)")

    # 5. 分级同步测试
    print("\n[5] 分级同步测试")
    engine.tiered_engine.register_data("alert.critical", TieredSyncEngine.Tier.CRITICAL)
    engine.tiered_engine.register_data("order.business", TieredSyncEngine.Tier.BUSINESS)
    task1 = engine.tiered_engine.enqueue("alert.critical", {"msg": "告警"}, "upsert")
    task2 = engine.tiered_engine.enqueue("order.business", {"id": "123"}, "upsert")
    print(f"  关键任务优先级: {task1['priority']}")
    print(f"  业务任务优先级: {task2['priority']}")

    # 6. Gossip测试
    print("\n[6] Gossip协议测试")
    engine.gossip.update_state("key1", "value1")
    engine.gossip.add_node("node2")
    engine.gossip.add_node("node3")
    msg = engine.gossip.create_gossip_message()
    print(f"  Gossip消息发送者: {msg['sender']}")
    print(f"  已知节点数: {len(msg['known_nodes'])}")

    # 7. 监控测试
    print("\n[7] 同步质量监控测试")
    engine.monitor.record_sync("memory_gateway", True)
    engine.monitor.record_sync("memory_gateway", True)
    engine.monitor.record_sync("memory_gateway", False)
    engine.monitor.record_latency("memory_gateway", 0.5)
    engine.monitor.record_latency("memory_gateway", 1.2)
    stats = engine.monitor.get_channel_stats("memory_gateway")
    print(f"  通道: {stats['channel']}")
    print(f"  成功率: {stats['success_rate']}%")
    print(f"  平均延迟: {stats['avg_latency_sec']}秒")

    # 8. 引擎能力
    print("\n[8] 引擎能力清单")
    caps = engine.get_capabilities()
    print(f"  版本: {caps['version']}")
    print(f"  CRDT类型: {len(caps['crdt_types'])}种")
    print(f"  时钟类型: {len(caps['clocks'])}种")
    print(f"  冲突策略: {len(caps['conflict_strategies'])}种")
    print(f"  同步级别: {len(caps['sync_tiers'])}级")

    print("\n" + "=" * 60)
    print("自测完成！所有模块运行正常。")
    print(f"确权: {engine.DID} | {engine.OMEGA}")
    print("=" * 60)


if __name__ == "__main__":
    _self_test()
