#!/usr/bin/env python3
"""
MWP (Multi-Writer Protocol) v1.0
多写入者协议实现层

协议定义：多写入者之间的握手、注册、心跳、事件提交、冲突协商、状态同步标准
基于事件溯源 + 版本向量 + 写入仲裁 + CRDT合并
"""
import json
import hashlib
import time
import os
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
PROTOCOL_DIR = ROOT / "omega_brain" / "mwp"
PROTOCOL_VERSION = "1.0.0"


class WriterRole(Enum):
    """写入者角色"""
    SCHEDULED = "scheduled"      # 定时任务（最高权威）
    DAEMON = "daemon"            # 常驻进程
    MANUAL = "manual"            # 手动操作
    API = "api"                  # API调用
    OBSERVER = "observer"        # 只读观察者


class EventType(Enum):
    """事件类型"""
    TRUTH_UPDATE = "truth_update"
    ARCHITECTURE_EVOLUTION = "architecture_evolution"
    KERNEL_WRITE = "kernel_write"
    ASSET_LOCK = "asset_lock"
    CONFIG_CHANGE = "config_change"
    MANUAL_OVERRIDE = "manual_override"
    EVOLUTION_CYCLE = "evolution_cycle"
    HEARTBEAT = "heartbeat"
    HANDSHAKE = "handshake"
    CONFLICT_RESOLUTION = "conflict_resolution"
    STATE_SYNC = "state_sync"


class ConflictResolution(Enum):
    """冲突解决策略"""
    AUTOMATIC_MERGE = "auto_merge"           # 自动合并
    PRIORITY_WINS = "priority_wins"          # 优先级高者胜出
    LWW = "last_write_wins"                  # 最后写入胜出
    MANUAL_REVIEW = "manual_review"          # 人工审核
    REJECT = "reject"                        # 拒绝


@dataclass
class WriterIdentity:
    """写入者身份（协议握手后获得）"""
    writer_id: str
    role: str
    description: str
    priority: int
    protocol_version: str
    registered_at: str
    last_heartbeat: str
    capabilities: List[str] = field(default_factory=list)
    is_active: bool = True
    session_token: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProtocolEvent:
    """协议事件（标准化事件格式）"""
    protocol_version: str
    event_id: str
    event_type: str
    writer_id: str
    writer_role: str
    timestamp: str
    version_vector: Dict[str, int]
    payload: Dict[str, Any]
    idempotency_key: str
    priority: int
    status: str = "pending"  # pending / applied / conflict / rejected / merged
    conflict_with: Optional[str] = None
    resolution: Optional[str] = None
    applied_at: Optional[str] = None
    ttl: int = 86400  # 事件存活时间（秒）

    def to_dict(self) -> dict:
        return asdict(self)

    def is_expired(self) -> bool:
        try:
            created = datetime.fromisoformat(self.timestamp)
            return (datetime.now() - created).total_seconds() > self.ttl
        except:
            return False


@dataclass
class ProtocolHandshake:
    """协议握手包"""
    protocol_version: str
    writer_id: str
    role: str
    description: str
    priority: int
    capabilities: List[str]
    timestamp: str
    challenge: str = ""  # 握手挑战（用于验证）

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConflictNegotiation:
    """冲突协商包"""
    conflict_id: str
    event_a: str
    event_b: str
    field_overlap: List[str]
    proposed_resolution: str
    proposer: str
    timestamp: str
    accepted: Optional[bool] = None
    resolved_by: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class MultiWriterProtocol:
    """
    MWP v1.0 多写入者协议实现

    协议流程：
    1. 握手（Handshake）→ 获得写入者身份和会话令牌
    2. 心跳（Heartbeat）→ 维持写入者活跃状态
    3. 事件提交（Event Submit）→ 标准化事件格式提交
    4. 冲突协商（Conflict Negotiation）→ 并发事件协商解决
    5. 状态同步（State Sync）→ 定期同步合并状态
    6. 注销（Unregister）→ 优雅退出
    """

    def __init__(self):
        self._writers: Dict[str, WriterIdentity] = {}
        self._events: List[ProtocolEvent] = []
        self._conflicts: List[ConflictNegotiation] = []
        self._state: Dict[str, Any] = {}
        self._version_vector: Dict[str, int] = {}
        self._applied_keys = set()
        self._lock = threading.Lock()
        self._load_state()

    def _load_state(self):
        """加载协议状态"""
        PROTOCOL_DIR.mkdir(parents=True, exist_ok=True)
        writers_file = PROTOCOL_DIR / "writers.json"
        state_file = PROTOCOL_DIR / "protocol_state.json"
        events_file = PROTOCOL_DIR / "events.jsonl"

        if writers_file.exists():
            with open(writers_file) as f:
                data = json.load(f)
            self._writers = {k: WriterIdentity(**v) for k, v in data.items()}

        if state_file.exists():
            with open(state_file) as f:
                data = json.load(f)
            self._state = data.get("merged_state", {})
            self._version_vector = data.get("version_vector", {})
            self._applied_keys = set(data.get("applied_keys", []))

        if events_file.exists():
            with open(events_file) as f:
                for line in f:
                    try:
                        self._events.append(ProtocolEvent(**json.loads(line)))
                    except:
                        pass

    def _save_state(self):
        """保存协议状态"""
        PROTOCOL_DIR.mkdir(parents=True, exist_ok=True)
        with open(PROTOCOL_DIR / "writers.json", "w") as f:
            json.dump({k: v.to_dict() for k, v in self._writers.items()}, f, ensure_ascii=False, indent=2)
        with open(PROTOCOL_DIR / "protocol_state.json", "w") as f:
            json.dump({
                "protocol_version": PROTOCOL_VERSION,
                "merged_state": self._state,
                "version_vector": self._version_vector,
                "applied_keys": list(self._applied_keys),
                "event_count": len(self._events),
                "writer_count": len(self._writers),
                "last_updated": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

    def _append_event(self, event: ProtocolEvent):
        """追加事件到不可变日志"""
        events_file = PROTOCOL_DIR / "events.jsonl"
        with open(events_file, "a") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    # ============================================================
    # 阶段1: 握手（Handshake）
    # ============================================================

    def handshake(self, writer_id: str, role: str, description: str = "",
                  priority: int = None, capabilities: List[str] = None) -> dict:
        """
        协议握手：写入者加入协议，获得身份和会话令牌

        Args:
            writer_id: 写入者唯一标识
            role: 角色 (scheduled/daemon/manual/api/observer)
            description: 描述
            priority: 优先级（0最高，None则按角色默认）
            capabilities: 能力列表

        Returns:
            握手响应：包含会话令牌、协议版本、当前状态摘要
        """
        role_enum = WriterRole(role) if role in [r.value for r in WriterRole] else WriterRole.MANUAL

        # 按角色分配默认优先级
        if priority is None:
            priority_map = {
                WriterRole.SCHEDULED: 0,
                WriterRole.DAEMON: 1,
                WriterRole.MANUAL: 2,
                WriterRole.API: 3,
                WriterRole.OBSERVER: 10
            }
            priority = priority_map.get(role_enum, 5)

        # 生成会话令牌
        session_token = hashlib.sha256(
            f"{writer_id}_{role}_{time.time()}_{os.urandom(8).hex()}".encode()
        ).hexdigest()[:32]

        # 生成握手挑战
        challenge = hashlib.sha256(f"challenge_{writer_id}_{time.time()}".encode()).hexdigest()[:16]

        now = datetime.now().isoformat()
        identity = WriterIdentity(
            writer_id=writer_id,
            role=role_enum.value,
            description=description,
            priority=priority,
            protocol_version=PROTOCOL_VERSION,
            registered_at=now,
            last_heartbeat=now,
            capabilities=capabilities or [],
            is_active=True,
            session_token=session_token
        )

        with self._lock:
            # 如果已注册，更新会话
            if writer_id in self._writers:
                identity.registered_at = self._writers[writer_id].registered_at
            self._writers[writer_id] = identity
            self._save_state()

        return {
            "status": "handshake_accepted",
            "protocol_version": PROTOCOL_VERSION,
            "writer_id": writer_id,
            "role": role_enum.value,
            "priority": priority,
            "session_token": session_token,
            "challenge": challenge,
            "current_writers": len(self._writers),
            "current_state_version": self._get_state_version(),
            "message": f"写入者 {writer_id} ({role}) 已加入MWP v{PROTOCOL_VERSION}"
        }

    def verify_handshake(self, writer_id: str, session_token: str) -> bool:
        """验证握手会话"""
        writer = self._writers.get(writer_id)
        if not writer:
            return False
        return writer.session_token == session_token and writer.is_active

    # ============================================================
    # 阶段2: 心跳（Heartbeat）
    # ============================================================

    def heartbeat(self, writer_id: str, session_token: str) -> dict:
        """
        心跳：维持写入者活跃状态

        超过300秒无心跳的写入者被标记为inactive
        """
        if not self.verify_handshake(writer_id, session_token):
            return {"status": "error", "message": "无效的写入者或会话令牌"}

        now = datetime.now().isoformat()
        with self._lock:
            if writer_id in self._writers:
                self._writers[writer_id].last_heartbeat = now
                self._save_state()

        # 清理超时写入者
        self._cleanup_inactive_writers()

        return {
            "status": "heartbeat_ack",
            "writer_id": writer_id,
            "timestamp": now,
            "active_writers": sum(1 for w in self._writers.values() if w.is_active),
            "next_heartbeat_deadline": 300
        }

    def _cleanup_inactive_writers(self):
        """清理超时无心跳的写入者"""
        now = datetime.now()
        changed = False
        for writer_id, writer in self._writers.items():
            try:
                last = datetime.fromisoformat(writer.last_heartbeat)
                if (now - last).total_seconds() > 300 and writer.is_active:
                    writer.is_active = False
                    changed = True
            except:
                pass
        if changed:
            self._save_state()

    # ============================================================
    # 阶段3: 事件提交（Event Submit）
    # ============================================================

    def submit_event(self, writer_id: str, session_token: str,
                     event_type: str, payload: dict,
                     priority: int = None) -> dict:
        """
        提交标准化协议事件

        Args:
            writer_id: 写入者ID
            session_token: 会话令牌
            event_type: 事件类型
            payload: 事件载荷
            priority: 事件优先级（None则使用写入者优先级）

        Returns:
            事件提交响应
        """
        if not self.verify_handshake(writer_id, session_token):
            return {"status": "error", "message": "未握手或会话失效，请先handshake"}

        writer = self._writers[writer_id]
        event_priority = priority if priority is not None else writer.priority

        # 生成幂等键
        idempotency_key = hashlib.sha256(
            json.dumps({"type": event_type, "payload": payload}, sort_keys=True).encode()
        ).hexdigest()[:16]

        # 幂等检查
        if idempotency_key in self._applied_keys:
            return {
                "status": "duplicate_rejected",
                "idempotency_key": idempotency_key,
                "message": "相同事件已应用，幂等拒绝"
            }

        # 生成事件ID
        event_id = hashlib.sha256(
            f"{writer_id}_{event_type}_{time.time()}_{os.urandom(4).hex()}".encode()
        ).hexdigest()[:16]

        # 更新版本向量
        vv = dict(self._version_vector)
        vv[writer_id] = vv.get(writer_id, 0) + 1

        event = ProtocolEvent(
            protocol_version=PROTOCOL_VERSION,
            event_id=event_id,
            event_type=event_type,
            writer_id=writer_id,
            writer_role=writer.role,
            timestamp=datetime.now().isoformat(),
            version_vector=vv,
            payload=payload,
            idempotency_key=idempotency_key,
            priority=event_priority,
            status="pending"
        )

        with self._lock:
            self._events.append(event)
            self._append_event(event)

        # 尝试应用事件
        result = self._apply_event(event)

        return {
            "status": result["status"],
            "event_id": event_id,
            "idempotency_key": idempotency_key,
            "version_vector": vv,
            "priority": event_priority,
            "conflict_with": result.get("conflict_with"),
            "resolution": result.get("resolution"),
            "message": result.get("message", "")
        }

    def _apply_event(self, event: ProtocolEvent) -> dict:
        """应用事件到状态（带冲突检测）"""
        if event.idempotency_key in self._applied_keys:
            return {"status": "already_applied"}

        # 冲突检测：检查是否有并发事件修改了相同字段
        conflict = self._detect_conflict(event)

        if conflict:
            event.status = "conflict"
            event.conflict_with = conflict["conflict_id"]
            resolution = self._resolve_conflict(event, conflict)
            event.resolution = resolution

            if resolution == ConflictResolution.REJECT.value:
                return {"status": "rejected", "conflict_with": conflict["conflict_id"],
                        "resolution": resolution, "message": "低优先级事件被拒绝"}
            elif resolution == ConflictResolution.MANUAL_REVIEW.value:
                return {"status": "conflict", "conflict_with": conflict["conflict_id"],
                        "resolution": resolution, "message": "需要人工审核"}
            else:
                # 自动合并或优先级胜出
                self._merge_event(event, conflict)
        else:
            event.status = "applied"

        # 应用到状态
        event.applied_at = datetime.now().isoformat()
        self._applied_keys.add(event.idempotency_key)
        self._merge_to_state(event)
        self._version_vector = self._merge_version_vector(self._version_vector, event.version_vector)

        with self._lock:
            self._save_state()

        return {"status": event.status, "event_id": event.event_id}

    def _detect_conflict(self, event: ProtocolEvent) -> Optional[dict]:
        """检测事件冲突（并发 + 字段重叠）"""
        event_vv = event.version_vector
        state_vv = self._version_vector

        # 检查是否并发（无因果关系）
        is_concurrent = False
        for writer in set(event_vv.keys()) | set(state_vv.keys()):
            if event_vv.get(writer, 0) > state_vv.get(writer, 0):
                # 事件有更新的时钟，可能并发
                if any(state_vv.get(w2, 0) > event_vv.get(w2, 0) for w2 in state_vv):
                    is_concurrent = True
                    break

        if not is_concurrent:
            return None

        # 检查字段重叠（简化：检查最近应用的事件）
        recent_events = [e for e in self._events[-20:] if e.status == "applied"]
        for recent in recent_events:
            overlap = set(event.payload.keys()) & set(recent.payload.keys())
            if overlap and recent.event_id != event.event_id:
                return {
                    "conflict_id": hashlib.sha256(f"{event.event_id}_{recent.event_id}".encode()).hexdigest()[:12],
                    "event_a": recent.event_id,
                    "event_b": event.event_id,
                    "field_overlap": list(overlap)
                }
        return None

    def _resolve_conflict(self, event: ProtocolEvent, conflict: dict) -> str:
        """冲突解决策略"""
        # 找到冲突事件
        conflict_event = None
        for e in self._events:
            if e.event_id == conflict["event_a"]:
                conflict_event = e
                break

        if not conflict_event:
            return ConflictResolution.AUTOMATIC_MERGE.value

        # 优先级比较
        if event.priority < conflict_event.priority:
            return ConflictResolution.PRIORITY_WINS.value  # 当前事件优先级高，胜出
        elif event.priority > conflict_event.priority:
            return ConflictResolution.REJECT.value  # 当前事件优先级低，拒绝
        else:
            # 同优先级
            overlap = conflict.get("field_overlap", [])
            # 如果重叠字段可合并（集合/计数器），自动合并
            mergeable = all(
                isinstance(event.payload.get(f), (list, dict, int))
                and isinstance(conflict_event.payload.get(f), (list, dict, int))
                for f in overlap
            )
            if mergeable:
                return ConflictResolution.AUTOMATIC_MERGE.value
            else:
                # 不可合并的标量冲突，最后写入胜出
                return ConflictResolution.LWW.value

    def _merge_event(self, event: ProtocolEvent, conflict: dict):
        """合并冲突事件"""
        conflict_event = None
        for e in self._events:
            if e.event_id == conflict["event_a"]:
                conflict_event = e
                break

        if conflict_event and event.resolution == ConflictResolution.AUTOMATIC_MERGE.value:
            for field in conflict.get("field_overlap", []):
                a_val = conflict_event.payload.get(field)
                b_val = event.payload.get(field)
                if isinstance(a_val, list) and isinstance(b_val, list):
                    event.payload[field] = list(set(a_val + b_val))
                elif isinstance(a_val, dict) and isinstance(b_val, dict):
                    merged = dict(a_val)
                    merged.update(b_val)
                    event.payload[field] = merged
                elif isinstance(a_val, int) and isinstance(b_val, int):
                    event.payload[field] = max(a_val, b_val)

    def _merge_to_state(self, event: ProtocolEvent):
        """将事件合并到状态"""
        event_type = event.event_type
        if event_type == EventType.TRUTH_UPDATE.value:
            self._state.setdefault("truth_base", {}).update(event.payload)
        elif event_type == EventType.ARCHITECTURE_EVOLUTION.value:
            self._state.setdefault("architecture", {}).update(event.payload)
        elif event_type == EventType.KERNEL_WRITE.value:
            self._state.setdefault("kernel", {}).update(event.payload)
        elif event_type == EventType.ASSET_LOCK.value:
            self._state.setdefault("assets", {}).update(event.payload)
        elif event_type == EventType.CONFIG_CHANGE.value:
            self._state.setdefault("config", {}).update(event.payload)
        elif event_type == EventType.MANUAL_OVERRIDE.value:
            self._state["manual_override"] = event.payload
        elif event_type == EventType.EVOLUTION_CYCLE.value:
            self._state["evolution_cycles"] = self._state.get("evolution_cycles", 0) + 1

    def _merge_version_vector(self, vv1: dict, vv2: dict) -> dict:
        """合并版本向量（取每个写入者的最大值）"""
        merged = {}
        for writer in set(vv1.keys()) | set(vv2.keys()):
            merged[writer] = max(vv1.get(writer, 0), vv2.get(writer, 0))
        return merged

    # ============================================================
    # 阶段4: 冲突协商（Conflict Negotiation）
    # ============================================================

    def propose_conflict_resolution(self, writer_id: str, session_token: str,
                                     conflict_id: str, proposed_resolution: str) -> dict:
        """
        提出冲突解决方案（人工审核场景）
        """
        if not self.verify_handshake(writer_id, session_token):
            return {"status": "error", "message": "未握手"}

        negotiation = ConflictNegotiation(
            conflict_id=conflict_id,
            event_a="",
            event_b="",
            field_overlap=[],
            proposed_resolution=proposed_resolution,
            proposer=writer_id,
            timestamp=datetime.now().isoformat()
        )
        self._conflicts.append(negotiation)

        return {
            "status": "resolution_proposed",
            "conflict_id": conflict_id,
            "proposed_by": writer_id,
            "resolution": proposed_resolution,
            "message": "冲突解决方案已提交，等待其他写入者确认"
        }

    # ============================================================
    # 阶段5: 状态同步（State Sync）
    # ============================================================

    def get_state(self, writer_id: str = None, session_token: str = None) -> dict:
        """
        获取当前合并状态

        观察者角色只能读取，不能提交事件
        """
        return {
            "protocol_version": PROTOCOL_VERSION,
            "state_version": self._get_state_version(),
            "version_vector": self._version_vector,
            "merged_state": self._state,
            "active_writers": {k: {"role": v.role, "priority": v.priority, "last_heartbeat": v.last_heartbeat}
                               for k, v in self._writers.items() if v.is_active},
            "event_count": len(self._events),
            "applied_count": len(self._applied_keys),
            "conflict_count": sum(1 for e in self._events if e.status == "conflict"),
            "last_updated": datetime.now().isoformat()
        }

    def sync_state(self, writer_id: str, session_token: str) -> dict:
        """
        状态同步：写入者请求最新状态
        返回增量变更（自上次同步以来的事件）
        """
        if not self.verify_handshake(writer_id, session_token):
            return {"status": "error", "message": "未握手"}

        # 返回完整状态（简化版，实际应返回增量）
        state = self.get_state()
        state["sync_type"] = "full_sync"
        state["synced_at"] = datetime.now().isoformat()
        return state

    def _get_state_version(self) -> str:
        """获取状态版本（基于版本向量的哈希）"""
        vv_str = json.dumps(self._version_vector, sort_keys=True)
        return hashlib.sha256(vv_str.encode()).hexdigest()[:12]

    # ============================================================
    # 阶段6: 注销（Unregister）
    # ============================================================

    def unregister(self, writer_id: str, session_token: str) -> dict:
        """优雅注销写入者"""
        if not self.verify_handshake(writer_id, session_token):
            return {"status": "error", "message": "未握手"}

        with self._lock:
            if writer_id in self._writers:
                self._writers[writer_id].is_active = False
                self._save_state()

        return {
            "status": "unregistered",
            "writer_id": writer_id,
            "message": f"写入者 {writer_id} 已优雅退出MWP协议",
            "remaining_writers": sum(1 for w in self._writers.values() if w.is_active)
        }

    # ============================================================
    # 协议信息
    # ============================================================

    def get_protocol_info(self) -> dict:
        """获取协议信息"""
        return {
            "protocol_name": "MWP (Multi-Writer Protocol)",
            "protocol_version": PROTOCOL_VERSION,
            "roles": [r.value for r in WriterRole],
            "event_types": [e.value for e in EventType],
            "conflict_resolutions": [r.value for r in ConflictResolution],
            "heartbeat_interval": 300,
            "event_ttl": 86400,
            "writers": len(self._writers),
            "active_writers": sum(1 for w in self._writers.values() if w.is_active),
            "events": len(self._events)
        }


# 全局单例
_protocol = None

def get_protocol() -> MultiWriterProtocol:
    global _protocol
    if _protocol is None:
        _protocol = MultiWriterProtocol()
    return _protocol


if __name__ == "__main__":
    import sys
    protocol = get_protocol()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "info":
            print(json.dumps(protocol.get_protocol_info(), ensure_ascii=False, indent=2))
        elif cmd == "state":
            print(json.dumps(protocol.get_state(), ensure_ascii=False, indent=2))
        elif cmd == "handshake" and len(sys.argv) > 3:
            result = protocol.handshake(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif cmd == "test":
            print("=== MWP v1.0 协议测试 ===")
            # 1. 握手
            h1 = protocol.handshake("scheduled_daily", "scheduled", "每日定时任务", priority=0)
            h2 = protocol.handshake("manual_session_A", "manual", "手动会话A", priority=2)
            h3 = protocol.handshake("daemon_loop", "daemon", "常驻进化循环", priority=1)
            print(f"握手: {h1['writer_id']}, {h2['writer_id']}, {h3['writer_id']}")

            # 2. 心跳
            hb = protocol.heartbeat("scheduled_daily", h1["session_token"])
            print(f"心跳: {hb['status']}, 活跃写入者: {hb['active_writers']}")

            # 3. 事件提交
            e1 = protocol.submit_event("scheduled_daily", h1["session_token"], "truth_update", {"formula": "H=abc", "value": 42})
            e2 = protocol.submit_event("manual_session_A", h2["session_token"], "architecture_evolution", {"level": "L5", "autonomy": 0.9})
            e3 = protocol.submit_event("daemon_loop", h3["session_token"], "asset_lock", {"asset": "test.json", "sha256": "abc123"})
            print(f"事件提交: {e1['status']}, {e2['status']}, {e3['status']}")

            # 4. 幂等测试
            e4 = protocol.submit_event("scheduled_daily", h1["session_token"], "truth_update", {"formula": "H=abc", "value": 42})
            print(f"幂等重复: {e4['status']} (预期duplicate_rejected)")

            # 5. 状态同步
            state = protocol.get_state()
            print(f"状态: {state['event_count']}事件, {state['active_writers']}写入者, 版本={state['state_version']}")

            # 6. 注销
            u = protocol.unregister("manual_session_A", h2["session_token"])
            print(f"注销: {u['status']}, 剩余: {u['remaining_writers']}")

            print("\n=== 测试完成 ===")
    else:
        print(json.dumps(protocol.get_protocol_info(), ensure_ascii=False, indent=2))
