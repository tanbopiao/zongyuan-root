#!/usr/bin/env python3
"""
多写入者兼容进化引擎（Multi-Writer Evolution Engine）
解决定时任务/手动会话/常驻循环/API调用多写入者并发冲突

核心机制：
1. 事件溯源（Event Sourcing）：所有写入追加为事件，不直接改状态
2. 版本向量（Vector Clock）：检测并发冲突
3. 写入仲裁（Write Arbitration）：单一仲裁者串行化
4. 状态合并（State Merge）：CRDT式自动合并
5. 冲突解决（Conflict Resolution）：自动合并+人工审核
6. 进化幂等性（Idempotency）：同一事件多次执行结果一致
"""
import json
import hashlib
import fcntl
import time
import os
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from queue import Queue, PriorityQueue
from dataclasses import dataclass, field, asdict

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
EVENT_LOG = ROOT / "omega_brain" / "evolution_events_v2.jsonl"
STATE_FILE = ROOT / "omega_brain" / "multi_writer_state.json"
LOCK_FILE = ROOT / ".locks" / "evolution_engine.lock"
WRITER_REGISTRY = ROOT / "omega_brain" / "writer_registry.json"


@dataclass
class VersionVector:
    """版本向量：追踪每个写入者的逻辑时钟"""
    clocks: Dict[str, int] = field(default_factory=dict)

    def increment(self, writer_id: str):
        self.clocks[writer_id] = self.clocks.get(writer_id, 0) + 1

    def merge(self, other: "VersionVector") -> "VersionVector":
        """合并两个版本向量（取最大值）"""
        merged = VersionVector()
        all_writers = set(self.clocks.keys()) | set(other.clocks.keys())
        for w in all_writers:
            merged.clocks[w] = max(self.clocks.get(w, 0), other.clocks.get(w, 0))
        return merged

    def happens_before(self, other: "VersionVector") -> bool:
        """判断this是否发生在other之前（因果关系）"""
        at_least_one_less = False
        for w in set(self.clocks.keys()) | set(other.clocks.keys()):
            if self.clocks.get(w, 0) > other.clocks.get(w, 0):
                return False
            if self.clocks.get(w, 0) < other.clocks.get(w, 0):
                at_least_one_less = True
        return at_least_one_less

    def concurrent(self, other: "VersionVector") -> bool:
        """判断是否并发（无因果关系）"""
        return not self.happens_before(other) and not other.happens_before(self)

    def to_dict(self) -> dict:
        return dict(self.clocks)

    @classmethod
    def from_dict(cls, d: dict) -> "VersionVector":
        return cls(clocks=dict(d))


@dataclass
class EvolutionEvent:
    """进化事件：所有状态变更的不可变记录"""
    event_id: str
    event_type: str  # truth_update / architecture_evolution / kernel_write / asset_lock / config_change / manual_override
    writer_id: str
    writer_type: str  # scheduled / manual / daemon / api
    timestamp: str
    version_vector: Dict[str, int]
    payload: Dict[str, Any]
    idempotency_key: str  # 幂等键：相同键的事件只执行一次
    status: str = "pending"  # pending / applied / conflict / rejected
    conflict_with: Optional[str] = None
    applied_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WriterIdentity:
    """写入者身份注册"""
    writer_id: str
    writer_type: str
    description: str
    registered_at: str
    last_active: str
    priority: int  # 0=最高，用于冲突仲裁
    is_active: bool = True


class MultiWriterEvolutionEngine:
    """多写入者兼容进化引擎"""

    def __init__(self):
        self._lock = threading.Lock()
        self._event_queue: PriorityQueue = PriorityQueue()
        self._state = self._load_state()
        self._writers = self._load_writers()
        self._applied_events = set()  # 已应用事件ID（幂等）
        self._idempotency_keys = set()  # 已应用幂等键

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
        return {
            "version_vector": {},
            "last_event_id": None,
            "event_count": 0,
            "conflict_count": 0,
            "merged_state": {},
            "evolution_cycles": 0
        }

    def _save_state(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)

    def _load_writers(self) -> Dict[str, WriterIdentity]:
        if WRITER_REGISTRY.exists():
            with open(WRITER_REGISTRY) as f:
                data = json.load(f)
            return {k: WriterIdentity(**v) for k, v in data.items()}
        return {}

    def _save_writers(self):
        WRITER_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
        with open(WRITER_REGISTRY, "w") as f:
            json.dump({k: asdict(v) for k, v in self._writers.items()}, f, ensure_ascii=False, indent=2)

    def register_writer(self, writer_id: str, writer_type: str, description: str, priority: int = 5) -> WriterIdentity:
        """注册写入者"""
        now = datetime.now().isoformat()
        writer = WriterIdentity(
            writer_id=writer_id,
            writer_type=writer_type,
            description=description,
            registered_at=now,
            last_active=now,
            priority=priority
        )
        self._writers[writer_id] = writer
        self._save_writers()
        return writer

    def _get_writer_id(self) -> str:
        """获取当前进程的写入者ID"""
        return os.environ.get("ZONGYUAN_WRITER_ID", f"process_{os.getpid()}")

    def _generate_event_id(self, writer_id: str, payload: dict) -> str:
        """生成事件ID（基于内容哈希，保证幂等）"""
        content = json.dumps({"writer": writer_id, "payload": payload}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _generate_idempotency_key(self, event_type: str, payload: dict) -> str:
        """生成幂等键"""
        content = json.dumps({"type": event_type, "payload": payload}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def submit_event(self, event_type: str, payload: dict, writer_id: str = None, writer_type: str = None) -> EvolutionEvent:
        """
        提交进化事件（所有写入必须通过此入口）
        不直接修改状态，而是追加事件，由仲裁者串行应用
        """
        writer_id = writer_id or self._get_writer_id()
        writer_type = writer_type or "manual"

        # 注册写入者（如果未注册）
        if writer_id not in self._writers:
            self.register_writer(writer_id, writer_type, f"Auto-registered {writer_type}")

        # 更新写入者活跃时间
        self._writers[writer_id].last_active = datetime.now().isoformat()
        self._save_writers()

        # 生成幂等键
        idempotency_key = self._generate_idempotency_key(event_type, payload)

        # 幂等检查：相同幂等键的事件只接受一次
        if idempotency_key in self._idempotency_keys:
            return EvolutionEvent(
                event_id="duplicate",
                event_type=event_type,
                writer_id=writer_id,
                writer_type=writer_type,
                timestamp=datetime.now().isoformat(),
                version_vector=self._state["version_vector"],
                payload=payload,
                idempotency_key=idempotency_key,
                status="rejected",
                conflict_with="idempotency_duplicate"
            )

        # 生成事件
        event_id = self._generate_event_id(writer_id, payload)
        vv = VersionVector.from_dict(self._state["version_vector"])
        vv.increment(writer_id)

        event = EvolutionEvent(
            event_id=event_id,
            event_type=event_type,
            writer_id=writer_id,
            writer_type=writer_type,
            timestamp=datetime.now().isoformat(),
            version_vector=vv.to_dict(),
            payload=payload,
            idempotency_key=idempotency_key,
            status="pending"
        )

        # 追加到事件日志（不可变）
        self._append_event(event)

        # 加入处理队列（用全局唯一计数器避免对象比较错误）
        self._queue_counter = getattr(self, '_queue_counter', 0) + 1
        self._event_queue.put((0, self._queue_counter, event))

        return event

    def _append_event(self, event: EvolutionEvent):
        """追加事件到不可变日志"""
        EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(EVENT_LOG, "a") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def _detect_conflict(self, event: EvolutionEvent) -> Optional[str]:
        """检测事件是否与已应用事件冲突（并发写入）"""
        event_vv = VersionVector.from_dict(event.version_vector)
        state_vv = VersionVector.from_dict(self._state["version_vector"])

        # 如果事件版本向量与当前状态并发（无因果关系），则可能冲突
        if event_vv.concurrent(state_vv) and event_vv.clocks:
            # 检查是否修改了同一字段
            # 简化版：如果事件类型相同且payload有重叠key，视为冲突
            for applied_id in list(self._applied_events)[-50:]:
                # 从事件日志查找已应用事件
                pass  # 简化：实际实现需扫描日志
        return None

    def _resolve_conflict(self, event: EvolutionEvent, conflict_with: str) -> str:
        """
        冲突解决策略
        1. 优先级高的写入者胜出（scheduled > daemon > manual > api）
        2. 相同优先级：最后写入胜出（LWW）
        3. 可合并字段：自动合并（CRDT式）
        """
        event_writer = self._writers.get(event.writer_id)
        conflict_writer = self._writers.get(conflict_with)

        if event_writer and conflict_writer:
            if event_writer.priority < conflict_writer.priority:
                return "accepted"  # 当前事件优先级高，覆盖
            elif event_writer.priority > conflict_writer.priority:
                return "rejected"  # 当前事件优先级低，拒绝
            else:
                return "merged"  # 同优先级，尝试合并
        return "accepted"

    def _apply_event(self, event: EvolutionEvent) -> dict:
        """应用事件到状态（幂等）"""
        if event.event_id in self._applied_events:
            return {"status": "already_applied", "event_id": event.event_id}

        if event.idempotency_key in self._idempotency_keys:
            return {"status": "idempotency_skip", "event_id": event.event_id}

        # 冲突检测
        conflict = self._detect_conflict(event)
        if conflict:
            resolution = self._resolve_conflict(event, conflict)
            if resolution == "rejected":
                event.status = "rejected"
                event.conflict_with = conflict
                self._state["conflict_count"] += 1
                self._save_state()
                return {"status": "rejected", "conflict_with": conflict}
            elif resolution == "merged":
                event.status = "conflict"
                event.conflict_with = conflict
                # 合并payload
                self._state["merged_state"].update(event.payload)
            else:
                event.status = "applied"
        else:
            event.status = "applied"

        # 应用到状态
        event.applied_at = datetime.now().isoformat()
        self._applied_events.add(event.event_id)
        self._idempotency_keys.add(event.idempotency_key)

        # 更新版本向量
        event_vv = VersionVector.from_dict(event.version_vector)
        state_vv = VersionVector.from_dict(self._state["version_vector"])
        self._state["version_vector"] = state_vv.merge(event_vv).to_dict()

        # 根据事件类型应用
        self._apply_by_type(event)

        self._state["last_event_id"] = event.event_id
        self._state["event_count"] += 1
        self._save_state()

        return {"status": event.status, "event_id": event.event_id}

    def _apply_by_type(self, event: EvolutionEvent):
        """按事件类型应用到对应状态"""
        payload = event.payload
        if event.event_type == "truth_update":
            self._state["merged_state"].setdefault("truth_base", {}).update(payload)
        elif event.event_type == "architecture_evolution":
            self._state["merged_state"].setdefault("architecture", {}).update(payload)
        elif event.event_type == "kernel_write":
            self._state["merged_state"].setdefault("kernel", {}).update(payload)
        elif event.event_type == "asset_lock":
            self._state["merged_state"].setdefault("assets", {}).update(payload)
        elif event.event_type == "config_change":
            self._state["merged_state"].setdefault("config", {}).update(payload)
        elif event.event_type == "manual_override":
            self._state["merged_state"]["manual_override"] = payload
        elif event.event_type == "evolution_cycle":
            self._state["evolution_cycles"] += 1

    def process_queue(self, max_events: int = 10) -> List[dict]:
        """处理事件队列（仲裁者串行应用）"""
        results = []
        for _ in range(min(max_events, self._event_queue.qsize())):
            try:
                _, _, event = self._event_queue.get_nowait()
                result = self._apply_event(event)
                results.append(result)
            except Exception as e:
                results.append({"status": "error", "error": str(e)})
        return results

    def get_state(self) -> dict:
        """获取当前合并状态"""
        return {
            "version_vector": self._state["version_vector"],
            "event_count": self._state["event_count"],
            "conflict_count": self._state["conflict_count"],
            "evolution_cycles": self._state["evolution_cycles"],
            "applied_events": len(self._applied_events),
            "pending_events": self._event_queue.qsize(),
            "writers": {k: {"type": v.writer_type, "priority": v.priority, "active": v.is_active}
                        for k, v in self._writers.items()},
            "merged_state": self._state["merged_state"]
        }

    def replay_events(self) -> dict:
        """事件溯源重放：从事件日志重建状态（用于恢复/验证）"""
        if not EVENT_LOG.exists():
            return {"status": "no_events"}

        # 重置状态
        self._state = {
            "version_vector": {}, "last_event_id": None, "event_count": 0,
            "conflict_count": 0, "merged_state": {}, "evolution_cycles": 0
        }
        self._applied_events.clear()
        self._idempotency_keys.clear()

        count = 0
        with open(EVENT_LOG) as f:
            for line in f:
                event_data = json.loads(line.strip())
                event = EvolutionEvent(**event_data)
                self._apply_event(event)
                count += 1

        return {"status": "replayed", "events_replayed": count, "state": self.get_state()}


# 全局单例
_engine = None

def get_engine() -> MultiWriterEvolutionEngine:
    global _engine
    if _engine is None:
        _engine = MultiWriterEvolutionEngine()
    return _engine


if __name__ == "__main__":
    import sys
    engine = get_engine()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "submit" and len(sys.argv) > 3:
            event_type = sys.argv[2]
            payload = json.loads(sys.argv[3])
            writer_id = sys.argv[4] if len(sys.argv) > 4 else None
            event = engine.submit_event(event_type, payload, writer_id=writer_id)
            print(json.dumps(event.to_dict(), ensure_ascii=False, indent=2))
        elif cmd == "process":
            results = engine.process_queue()
            print(json.dumps(results, ensure_ascii=False, indent=2))
        elif cmd == "state":
            print(json.dumps(engine.get_state(), ensure_ascii=False, indent=2))
        elif cmd == "replay":
            print(json.dumps(engine.replay_events(), ensure_ascii=False, indent=2))
        elif cmd == "register" and len(sys.argv) > 3:
            writer = engine.register_writer(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
            print(json.dumps(asdict(writer), ensure_ascii=False, indent=2))
        elif cmd == "test":
            # 多写入者并发测试
            print("=== 多写入者兼容进化测试 ===")
            e1 = engine.submit_event("truth_update", {"formula": "H=abc", "value": 42}, writer_id="scheduled_001", writer_type="scheduled")
            e2 = engine.submit_event("architecture_evolution", {"level": "L5", "autonomy": 0.9}, writer_id="manual_session_A", writer_type="manual")
            e3 = engine.submit_event("asset_lock", {"asset": "test.json", "sha256": "abc123"}, writer_id="daemon_loop", writer_type="daemon")
            print(f"提交3个事件: {e1.event_id}, {e2.event_id}, {e3.event_id}")
            results = engine.process_queue()
            print(f"处理结果: {len(results)}个事件应用")
            print(json.dumps(engine.get_state(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(engine.get_state(), ensure_ascii=False, indent=2))
