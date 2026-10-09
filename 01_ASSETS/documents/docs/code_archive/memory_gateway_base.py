#!/usr/bin/env python3
"""
记忆网关基底 V1.0
ZONGYUAN-ROOT元极恒一自治体系核心基础设施
集成：真值存储 + 节点注册 + 审计日志 + 同源握手 + 态元/六态生命体接入
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json, hashlib, os, time, sqlite3, threading
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


# ==================== 常量定义 ====================

DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"
GATEWAY_VERSION = "V1.0-LOCAL-BASE"
DEFAULT_DB_PATH = os.path.expanduser("~/.zongyuan_root/memory_gateway.db")


# ==================== 真值类型 ====================

class TruthType(str, Enum):
    META_LAW = "meta_law"
    RULE = "rule"
    CONFIG = "config"
    DECISION = "decision"
    DATA = "data"
    CREATIVE = "creative"
    RISK = "risk"
    PROTOCOL = "protocol"
    UNKNOWN = "unknown"


class NodeStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    SYNCING = "syncing"
    DEGRADED = "degraded"


# ==================== 数据模型 ====================

@dataclass
class TruthEntry:
    """真值条目"""
    truth_key: str
    truth_value: str
    truth_type: str = "unknown"
    source_node: str = ""
    confidence: float = 0.8
    tags: List[str] = field(default_factory=list)
    truth_hash: str = ""
    created_at: str = ""
    updated_at: str = ""
    version: int = 1
    is_active: bool = True

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.truth_hash:
            raw = f"{self.truth_key}{self.truth_value}{self.truth_type}{self.confidence}"
            self.truth_hash = hashlib.sha256(raw.encode('utf-8')).hexdigest()


@dataclass
class NodeEntry:
    """同源节点"""
    node_id: str
    node_name: str = ""
    node_type: str = "worker"  # worker/master/gateway/agent
    status: str = "offline"
    last_heartbeat: str = ""
    registered_at: str = ""
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    did: str = DID

    def __post_init__(self):
        if not self.registered_at:
            self.registered_at = datetime.now(timezone.utc).isoformat()
        if not self.last_heartbeat:
            self.last_heartbeat = self.registered_at


@dataclass
class AuditLog:
    """审计日志"""
    log_id: str = ""
    action: str = ""
    actor: str = ""
    target: str = ""
    detail: str = ""
    timestamp: str = ""
    signature: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.log_id:
            self.log_id = f"AUD-{int(time.time()*1000)}-{os.getpid() % 10000:04d}-{os.urandom(2).hex()}"
        if not self.signature:
            raw = f"{self.log_id}{self.action}{self.actor}{self.target}{self.timestamp}"
            self.signature = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]


# ==================== 记忆网关核心 ====================

class MemoryGateway:
    """记忆网关核心：真值存储 + 节点管理 + 审计日志 + 同源握手"""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        self._register_self()

    def _init_db(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS truths (
                truth_key TEXT PRIMARY KEY,
                truth_value TEXT NOT NULL,
                truth_type TEXT DEFAULT 'unknown',
                source_node TEXT,
                confidence REAL DEFAULT 0.8,
                tags TEXT,
                truth_hash TEXT,
                created_at TEXT,
                updated_at TEXT,
                version INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_truths_type ON truths(truth_type);
            CREATE INDEX IF NOT EXISTS idx_truths_source ON truths(source_node);
            CREATE INDEX IF NOT EXISTS idx_truths_active ON truths(is_active);

            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                node_name TEXT,
                node_type TEXT DEFAULT 'worker',
                status TEXT DEFAULT 'offline',
                last_heartbeat TEXT,
                registered_at TEXT,
                capabilities TEXT,
                metadata TEXT,
                did TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_status ON nodes(status);

            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id TEXT PRIMARY KEY,
                action TEXT,
                actor TEXT,
                target TEXT,
                detail TEXT,
                timestamp TEXT,
                signature TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);

            CREATE TABLE IF NOT EXISTS handshake_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_node TEXT,
                to_node TEXT,
                handshake_type TEXT,
                payload TEXT,
                result TEXT,
                timestamp TEXT
            );
        """)
        self.conn.commit()

    def _register_self(self):
        """注册自身为网关节点"""
        self.register_node(
            node_id="gateway-local-base",
            node_name="本地记忆网关基底",
            node_type="gateway",
            capabilities=["truth_storage", "node_registry", "audit_log", "handshake", "state_atom", "six_state_life"],
        )

    # ===== 真值管理 =====

    def put_truth(self, truth_key: str, truth_value: str,
                  truth_type: str = "unknown", source_node: str = "",
                  confidence: float = 0.8, tags: List[str] = None) -> Dict:
        """写入/更新真值"""
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            existing = self.conn.execute("SELECT * FROM truths WHERE truth_key=?", (truth_key,)).fetchone()

            if existing:
                # 更新已有真值
                new_version = existing["version"] + 1
                new_hash = hashlib.sha256(f"{truth_key}{truth_value}{truth_type}{confidence}".encode()).hexdigest()
                self.conn.execute("""
                    UPDATE truths SET truth_value=?, truth_type=?, source_node=?, confidence=?,
                    tags=?, truth_hash=?, updated_at=?, version=? WHERE truth_key=?
                """, (truth_value, truth_type, source_node, confidence,
                      json.dumps(tags or [], ensure_ascii=False), new_hash, now, new_version, truth_key))
                action = "truth_update"
            else:
                # 新增真值
                new_hash = hashlib.sha256(f"{truth_key}{truth_value}{truth_type}{confidence}".encode()).hexdigest()
                self.conn.execute("""
                    INSERT INTO truths (truth_key, truth_value, truth_type, source_node, confidence,
                    tags, truth_hash, created_at, updated_at, version, is_active)
                    VALUES (?,?,?,?,?,?,?,?,?,?,1)
                """, (truth_key, truth_value, truth_type, source_node, confidence,
                      json.dumps(tags or [], ensure_ascii=False), new_hash, now, now, 1))
                action = "truth_insert"

            self.conn.commit()
            self._add_audit(action, source_node or "gateway-local-base", truth_key,
                           f"confidence={confidence}, type={truth_type}")

            return {"status": "ok", "truth_key": truth_key, "version": existing["version"] + 1 if existing else 1,
                    "truth_hash": new_hash}

    def get_truth(self, truth_key: str) -> Optional[Dict]:
        """查询真值"""
        row = self.conn.execute("SELECT * FROM truths WHERE truth_key=? AND is_active=1", (truth_key,)).fetchone()
        if not row:
            return None
        return dict(row)

    def search_truths(self, keyword: str = "", truth_type: str = "",
                      limit: int = 50, offset: int = 0) -> List[Dict]:
        """搜索真值"""
        query = "SELECT * FROM truths WHERE is_active=1"
        params = []
        if keyword:
            query += " AND (truth_key LIKE ? OR truth_value LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if truth_type:
            query += " AND truth_type=?"
            params.append(truth_type)
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_truth_stats(self) -> Dict:
        """获取真值统计"""
        total = self.conn.execute("SELECT COUNT(*) as c FROM truths WHERE is_active=1").fetchone()["c"]
        by_type = self.conn.execute("SELECT truth_type, COUNT(*) as c FROM truths WHERE is_active=1 GROUP BY truth_type").fetchall()
        avg_conf = self.conn.execute("SELECT AVG(confidence) as a FROM truths WHERE is_active=1").fetchone()["a"]
        return {
            "total_truths": total,
            "by_type": {r["truth_type"]: r["c"] for r in by_type},
            "avg_confidence": round(avg_conf, 4) if avg_conf else 0,
        }

    # ===== 节点管理 =====

    def register_node(self, node_id: str, node_name: str = "", node_type: str = "worker",
                      capabilities: List[str] = None, metadata: Dict = None) -> Dict:
        """注册节点"""
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            existing = self.conn.execute("SELECT * FROM nodes WHERE node_id=?", (node_id,)).fetchone()
            if existing:
                self.conn.execute("""
                    UPDATE nodes SET node_name=?, node_type=?, status='online', last_heartbeat=?,
                    capabilities=?, metadata=? WHERE node_id=?
                """, (node_name, node_type, now, json.dumps(capabilities or []),
                      json.dumps(metadata or {}), node_id))
                action = "node_update"
            else:
                self.conn.execute("""
                    INSERT INTO nodes (node_id, node_name, node_type, status, last_heartbeat,
                    registered_at, capabilities, metadata, did)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (node_id, node_name, node_type, "online", now, now,
                      json.dumps(capabilities or []), json.dumps(metadata or {}), DID))
                action = "node_register"

            self.conn.commit()
            self._add_audit(action, node_id, node_id, f"type={node_type}")
            return {"status": "ok", "node_id": node_id, "status": "online"}

    def heartbeat(self, node_id: str, metadata: Dict = None) -> Dict:
        """节点心跳"""
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            self.conn.execute("UPDATE nodes SET status='online', last_heartbeat=?, metadata=? WHERE node_id=?",
                            (now, json.dumps(metadata or {}), node_id))
            self.conn.commit()
        return {"status": "ok", "node_id": node_id, "heartbeat_at": now}

    def get_nodes(self, status: str = "") -> List[Dict]:
        """获取节点列表"""
        if status:
            rows = self.conn.execute("SELECT * FROM nodes WHERE status=?", (status,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM nodes ORDER BY registered_at").fetchall()
        return [dict(r) for r in rows]

    def get_node_stats(self) -> Dict:
        """获取节点统计"""
        total = self.conn.execute("SELECT COUNT(*) as c FROM nodes").fetchone()["c"]
        online = self.conn.execute("SELECT COUNT(*) as c FROM nodes WHERE status='online'").fetchone()["c"]
        return {"total_nodes": total, "online_nodes": online, "offline_nodes": total - online}

    # ===== 审计日志 =====

    def _add_audit(self, action: str, actor: str, target: str, detail: str = ""):
        """添加审计日志（内部调用）"""
        log = AuditLog(action=action, actor=actor, target=target, detail=detail)
        self.conn.execute("""
            INSERT INTO audit_logs (log_id, action, actor, target, detail, timestamp, signature)
            VALUES (?,?,?,?,?,?,?)
        """, (log.log_id, log.action, log.actor, log.target, log.detail, log.timestamp, log.signature))
        self.conn.commit()

    def get_audit_logs(self, action: str = "", limit: int = 100) -> List[Dict]:
        """获取审计日志"""
        if action:
            rows = self.conn.execute("SELECT * FROM audit_logs WHERE action=? ORDER BY timestamp DESC LIMIT ?",
                                    (action, limit)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    # ===== 同源握手 =====

    def handshake(self, from_node: str, to_node: str, handshake_type: str = "ping",
                  payload: Dict = None) -> Dict:
        """同源节点握手"""
        now = datetime.now(timezone.utc).isoformat()
        result = "success"
        # 检查目标节点是否存在
        target = self.conn.execute("SELECT * FROM nodes WHERE node_id=?", (to_node,)).fetchone()
        if not target:
            result = "target_not_found"

        self.conn.execute("""
            INSERT INTO handshake_records (from_node, to_node, handshake_type, payload, result, timestamp)
            VALUES (?,?,?,?,?,?)
        """, (from_node, to_node, handshake_type, json.dumps(payload or {}), result, now))
        self.conn.commit()
        self._add_audit("handshake", from_node, to_node, f"type={handshake_type}, result={result}")

        return {"status": result, "from": from_node, "to": to_node, "type": handshake_type, "timestamp": now}

    # ===== 网关状态 =====

    def get_status(self) -> Dict:
        """获取网关完整状态"""
        truth_stats = self.get_truth_stats()
        node_stats = self.get_node_stats()
        audit_count = self.conn.execute("SELECT COUNT(*) as c FROM audit_logs").fetchone()["c"]
        handshake_count = self.conn.execute("SELECT COUNT(*) as c FROM handshake_records").fetchone()["c"]

        return {
            "status": "ok",
            "version": GATEWAY_VERSION,
            "did": DID,
            "trace_mark": TRACE_MARK,
            "storage": "SQLite",
            "db_path": self.db_path,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "stats": {
                **truth_stats,
                **node_stats,
                "audit_logs": audit_count,
                "handshakes": handshake_count,
            },
        }

    def close(self):
        self.conn.close()


# ==================== 集成态元与六态生命体 ====================

class IntegratedMemoryGateway(MemoryGateway):
    """集成记忆网关：接入态元引擎 + 六态生命体"""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        super().__init__(db_path)
        self.atom_db_path = os.path.expanduser("~/.zongyuan_root/state_atoms.db")
        self.life_db_path = os.path.expanduser("~/.zongyuan_root/six_state_life.db")

    def get_atom_stats(self) -> Dict:
        """获取态元库统计"""
        if not os.path.exists(self.atom_db_path):
            return {"status": "not_found"}
        try:
            conn = sqlite3.connect(self.atom_db_path)
            conn.row_factory = sqlite3.Row
            total = conn.execute("SELECT COUNT(*) as c FROM atoms").fetchone()["c"]
            active = conn.execute("SELECT COUNT(*) as c FROM atoms WHERE lifecycle_stage='active'").fetchone()["c"]
            meta9 = conn.execute("SELECT COUNT(*) as c FROM atoms WHERE meta_class='M9'").fetchone()["c"]
            avg_fit = conn.execute("SELECT AVG(fitness_score) as a FROM atoms").fetchone()["a"]
            conn.close()
            return {
                "status": "ok",
                "total_atoms": total,
                "active_atoms": active,
                "meta_law_atoms": meta9,
                "avg_fitness": round(avg_fit, 4) if avg_fit else 0,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_lifeform_stats(self) -> Dict:
        """获取六态生命体统计"""
        if not os.path.exists(self.life_db_path):
            return {"status": "not_found"}
        try:
            conn = sqlite3.connect(self.life_db_path)
            conn.row_factory = sqlite3.Row
            lifeforms = conn.execute("SELECT * FROM lifeforms").fetchall()
            interactions = conn.execute("SELECT COUNT(*) as c FROM interactions").fetchone()["c"]
            conn.close()
            return {
                "status": "ok",
                "total_lifeforms": len(lifeforms),
                "total_interactions": interactions,
                "lifeforms": [{"id": l["lifeform_id"], "name": l["name"], "heartbeat": l["heartbeat"]}
                              for l in lifeforms],
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_full_status(self) -> Dict:
        """获取完整集成状态"""
        base_status = self.get_status()
        base_status["state_atoms"] = self.get_atom_stats()
        base_status["six_state_life"] = self.get_lifeform_stats()
        return base_status


# ==================== 演示 ====================

def run_demo():
    """记忆网关基底演示"""
    print("=" * 60)
    print("记忆网关基底 V1.0")
    print("ZONGYUAN-ROOT元极恒一自治体系核心基础设施")
    print("=" * 60)

    gateway = IntegratedMemoryGateway()

    # 1. 注册节点
    print("\n【1】注册同源节点")
    gateway.register_node("node-dev-001", "本地开发节点", "worker",
                         ["truth_report", "state_atom", "development"])
    gateway.register_node("node-sim-001", "仿真测试节点", "worker",
                         ["simulation", "testing"])
    print("  ✅ 注册2个工作节点")

    # 2. 写入真值
    print("\n【2】写入核心真值")
    truths = [
        ("META_LAW.MEMORY_GATEWAY_BASE.V1.0",
         "记忆网关基底V1.0：真值存储+节点注册+审计日志+同源握手+态元/六态生命体集成。本地SQLite持久化，支持多节点协同。",
         "meta_law", 0.95),
        ("PROTOCOL.HOMOLOGOUS_HANDSHAKE.V1.0",
         "同源握手协议V1.0：节点间通过gateway.handshake进行身份验证与能力交换，支持ping/sync/capability_exchange三种类型。",
         "protocol", 0.92),
        ("RULE.TRUTH_CONFIDENCE_SCORING.V1.0",
         "真值置信度评分标准：交叉验证>0.95，单源验证0.8-0.95，推演0.6-0.8，猜想<0.6。低于0.6标记为待验证。",
         "rule", 0.90),
    ]
    for key, value, ttype, conf in truths:
        result = gateway.put_truth(key, value, ttype, "gateway-local-base", conf, ["memory_gateway", "base"])
        print(f"  ✅ {key}: hash={result['truth_hash'][:12]}...")

    # 3. 节点心跳
    print("\n【3】节点心跳")
    gateway.heartbeat("node-dev-001", {"cpu": 35, "memory": 62, "tasks": 3})
    gateway.heartbeat("node-sim-001", {"cpu": 12, "memory": 28, "tasks": 1})
    print("  ✅ 2个节点心跳上报")

    # 4. 同源握手
    print("\n【4】同源握手")
    result = gateway.handshake("node-dev-001", "gateway-local-base", "capability_exchange",
                              {"capabilities": ["truth_report", "state_atom"]})
    print(f"  ✅ 握手结果: {result['status']}")

    # 5. 查询真值
    print("\n【5】查询真值")
    truth = gateway.get_truth("META_LAW.MEMORY_GATEWAY_BASE.V1.0")
    if truth:
        print(f"  ✅ 找到: {truth['truth_key']} (v{truth['version']}, conf={truth['confidence']})")

    # 6. 完整状态
    print("\n【6】网关完整状态")
    status = gateway.get_full_status()
    print(f"  版本: {status['version']}")
    print(f"  真值: {status['stats']['total_truths']}条 (avg conf={status['stats']['avg_confidence']})")
    print(f"  节点: {status['stats']['online_nodes']}/{status['stats']['total_nodes']}在线")
    print(f"  审计: {status['stats']['audit_logs']}条")
    print(f"  握手: {status['stats']['handshakes']}次")
    if status['state_atoms']['status'] == 'ok':
        print(f"  态元: {status['state_atoms']['total_atoms']}个 (avg fitness={status['state_atoms']['avg_fitness']})")
    if status['six_state_life']['status'] == 'ok':
        print(f"  六态生命体: {status['six_state_life']['total_lifeforms']}个 ({status['six_state_life']['total_interactions']}次交互)")

    # 7. 审计日志
    print("\n【7】最近审计日志")
    logs = gateway.get_audit_logs(limit=5)
    for log in logs:
        print(f"  [{log['timestamp'][:19]}] {log['action']}: {log['actor']} -> {log['target']}")

    gateway.close()
    print(f"\n{'=' * 60}")
    print("记忆网关基底演示完成！")
    print(f"数据库: {DEFAULT_DB_PATH}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    run_demo()
