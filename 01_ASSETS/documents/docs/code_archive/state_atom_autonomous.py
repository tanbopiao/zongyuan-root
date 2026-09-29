#!/usr/bin/env python3
"""
态元自治进化引擎 V2.0
三态融合生命体架构 — 完整自治运行系统

在V1.0基础上扩展：
- StateAtomStore: SQLite持久化存储+高效查询
- AtomMessageBus: 态元间通讯协议（信号传递+协作）
- SelfModifyEngine: 态元自修改框架（算子自进化）
- AutonomousEvolutionLoop: 自治进化循环（自动心跳+竞价+演化）
- LocalTruthMigrator: 本地真值库迁移为态元

DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import json
import hashlib
import os
import time
import sqlite3
import threading
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

# 复用V1.0的核心类
from state_atom_engine import (
    StateAtom, InformationDim, LogicDim, EnergyDim, Lifecycle,
    EnergyAuctionEngine, StateAtomMigrator,
    AtomType, EnergyState, LifecycleStage, TruthType,
)


# ============================================================
# 1. SQLite持久化存储
# ============================================================

class StateAtomStore:
    """态元SQLite持久化存储：支持高效查询、索引、演化追踪"""

    def __init__(self, db_path: str = "state_atoms.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS atoms (
                    atom_id TEXT PRIMARY KEY,
                    atom_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT,
                    confidence REAL DEFAULT 0.5,
                    meta_class TEXT DEFAULT 'M4',
                    truth_type TEXT DEFAULT 'unknown',
                    self_modifiable INTEGER DEFAULT 1,
                    compute_quota INTEGER DEFAULT 100,
                    storage_quota INTEGER DEFAULT 1024,
                    usage_frequency INTEGER DEFAULT 0,
                    fitness_score REAL DEFAULT 0.5,
                    energy_state TEXT DEFAULT 'active',
                    lifecycle_stage TEXT DEFAULT 'birth',
                    version INTEGER DEFAULT 1,
                    parent_atom_ids TEXT DEFAULT '[]',
                    child_atom_ids TEXT DEFAULT '[]',
                    dependencies TEXT DEFAULT '[]',
                    dependents TEXT DEFAULT '[]',
                    full_hash TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    birth_time TEXT,
                    death_time TEXT,
                    last_used TEXT,
                    low_fitness_streak INTEGER DEFAULT 0,
                    reinforcement_count INTEGER DEFAULT 0,
                    compression_count INTEGER DEFAULT 0,
                    revival_count INTEGER DEFAULT 0,
                    source TEXT DEFAULT 'auto_generated',
                    tags TEXT DEFAULT '[]',
                    did TEXT DEFAULT 'DID-BR-000002'
                );

                CREATE INDEX IF NOT EXISTS idx_atoms_type ON atoms(atom_type);
                CREATE INDEX IF NOT EXISTS idx_atoms_energy_state ON atoms(energy_state);
                CREATE INDEX IF NOT EXISTS idx_atoms_fitness ON atoms(fitness_score);
                CREATE INDEX IF NOT EXISTS idx_atoms_meta_class ON atoms(meta_class);
                CREATE INDEX IF NOT EXISTS idx_atoms_truth_type ON atoms(truth_type);
                CREATE INDEX IF NOT EXISTS idx_atoms_lifecycle ON atoms(lifecycle_stage);

                CREATE TABLE IF NOT EXISTS fitness_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    atom_id TEXT,
                    heartbeat INTEGER,
                    fitness REAL,
                    timestamp TEXT,
                    FOREIGN KEY (atom_id) REFERENCES atoms(atom_id)
                );

                CREATE TABLE IF NOT EXISTS atom_evolution (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    atom_id TEXT,
                    action TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    reason TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (atom_id) REFERENCES atoms(atom_id)
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id TEXT,
                    receiver_id TEXT,
                    message_type TEXT,
                    payload TEXT,
                    timestamp TEXT,
                    processed INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id, processed);
            """)
            self.conn.commit()

    def save_atom(self, atom: StateAtom):
        """保存态元到数据库"""
        cols = (
            "atom_id,atom_type,content,content_hash,confidence,meta_class,"
            "truth_type,self_modifiable,compute_quota,storage_quota,usage_frequency,"
            "fitness_score,energy_state,lifecycle_stage,version,parent_atom_ids,"
            "child_atom_ids,dependencies,dependents,full_hash,created_at,updated_at,"
            "birth_time,death_time,last_used,low_fitness_streak,reinforcement_count,"
            "compression_count,revival_count,source,tags,did"
        )
        placeholders = ",".join(["?"] * 32)
        values = (
            atom.atom_id, atom.atom_type,
            atom.information_dim.content,
            atom.information_dim.content_hash,
            atom.information_dim.confidence,
            atom.information_dim.meta_class,
            atom.information_dim.truth_type,
            1 if atom.logic_dim.self_modifiable else 0,
            atom.energy_dim.compute_quota,
            atom.energy_dim.storage_quota,
            atom.energy_dim.usage_frequency,
            atom.energy_dim.fitness_score,
            atom.energy_dim.energy_state,
            atom.lifecycle.stage,
            atom.version,
            json.dumps(atom.parent_atom_ids),
            json.dumps(atom.child_atom_ids),
            json.dumps(atom.logic_dim.dependencies),
            json.dumps(atom.logic_dim.dependents),
            atom.get_full_hash(),
            atom.created_at, atom.updated_at,
            atom.energy_dim.birth_time, atom.energy_dim.death_time,
            atom.energy_dim.last_used,
            atom.energy_dim.low_fitness_streak,
            atom.lifecycle.reinforcement_count,
            atom.lifecycle.compression_count,
            atom.lifecycle.revival_count,
            atom.information_dim.source,
            json.dumps(atom.information_dim.tags),
            atom.did,
        )
        with self._lock:
            self.conn.execute(f"INSERT OR REPLACE INTO atoms ({cols}) VALUES ({placeholders})", values)
            self.conn.commit()

    def load_atom(self, atom_id: str) -> Optional[StateAtom]:
        """从数据库加载态元"""
        with self._lock:
            row = self.conn.execute("SELECT * FROM atoms WHERE atom_id=?", (atom_id,)).fetchone()
        if not row:
            return None
        return self._row_to_atom(row)

    def _row_to_atom(self, row) -> StateAtom:
        return StateAtom(
            atom_id=row['atom_id'],
            atom_type=row['atom_type'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            version=row['version'],
            parent_atom_ids=json.loads(row['parent_atom_ids']),
            child_atom_ids=json.loads(row['child_atom_ids']),
            information_dim=InformationDim(
                content=row['content'],
                content_hash=row['content_hash'],
                confidence=row['confidence'],
                meta_class=row['meta_class'],
                truth_type=row['truth_type'],
                source=row['source'],
                tags=json.loads(row['tags']),
            ),
            logic_dim=LogicDim(
                self_modifiable=bool(row['self_modifiable']),
                dependencies=json.loads(row['dependencies']),
                dependents=json.loads(row['dependents']),
            ),
            energy_dim=EnergyDim(
                compute_quota=row['compute_quota'],
                storage_quota=row['storage_quota'],
                usage_frequency=row['usage_frequency'],
                fitness_score=row['fitness_score'],
                energy_state=row['energy_state'],
                birth_time=row['birth_time'],
                death_time=row['death_time'],
                last_used=row['last_used'],
                low_fitness_streak=row['low_fitness_streak'],
            ),
            lifecycle=Lifecycle(
                stage=row['lifecycle_stage'],
                reinforcement_count=row['reinforcement_count'],
                compression_count=row['compression_count'],
                revival_count=row['revival_count'],
            ),
        )

    def query_atoms(self, filters: Dict = None, limit: int = 100, offset: int = 0) -> List[StateAtom]:
        """按条件查询态元"""
        query = "SELECT * FROM atoms WHERE 1=1"
        params = []
        if filters:
            for key, value in filters.items():
                query += f" AND {key}=?"
                params.append(value)
        query += " ORDER BY fitness_score DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._lock:
            rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_atom(row) for row in rows]

    def get_all_active_atoms(self) -> List[StateAtom]:
        """获取所有活跃态元"""
        return self.query_atoms({"energy_state": "active"})

    def get_stats(self) -> Dict:
        """获取态元库统计"""
        with self._lock:
            total = self.conn.execute("SELECT COUNT(*) FROM atoms").fetchone()[0]
            by_state = {}
            for row in self.conn.execute("SELECT energy_state, COUNT(*) as c FROM atoms GROUP BY energy_state"):
                by_state[row['energy_state']] = row['c']
            by_lifecycle = {}
            for row in self.conn.execute("SELECT lifecycle_stage, COUNT(*) as c FROM atoms GROUP BY lifecycle_stage"):
                by_lifecycle[row['lifecycle_stage']] = row['c']
            by_type = {}
            for row in self.conn.execute("SELECT atom_type, COUNT(*) as c FROM atoms GROUP BY atom_type"):
                by_type[row['atom_type']] = row['c']
            avg_fitness = self.conn.execute("SELECT AVG(fitness_score) FROM atoms WHERE lifecycle_stage='active'").fetchone()[0] or 0
        return {
            "total": total,
            "by_energy_state": by_state,
            "by_lifecycle_stage": by_lifecycle,
            "by_type": by_type,
            "avg_fitness_active": round(avg_fitness, 4),
        }

    def record_fitness(self, atom_id: str, heartbeat: int, fitness: float):
        """记录适应度历史"""
        with self._lock:
            self.conn.execute(
                "INSERT INTO fitness_history (atom_id, heartbeat, fitness, timestamp) VALUES (?,?,?,?)",
                (atom_id, heartbeat, fitness, datetime.now(timezone.utc).isoformat())
            )
            self.conn.commit()

    def record_evolution(self, atom_id: str, action: str, old_value: str, new_value: str, reason: str):
        """记录演化事件"""
        with self._lock:
            self.conn.execute(
                "INSERT INTO atom_evolution (atom_id, action, old_value, new_value, reason, timestamp) VALUES (?,?,?,?,?,?)",
                (atom_id, action, old_value, new_value, reason, datetime.now(timezone.utc).isoformat())
            )
            self.conn.commit()

    def close(self):
        self.conn.close()


# ============================================================
# 2. 态元间通讯协议（生命体的神经系统）
# ============================================================

class AtomMessageBus:
    """态元间通讯协议：信号传递+协作机制+事件驱动"""

    class MessageType(str, Enum):
        REINFORCE = "reinforce"        # 强化信号（被使用）
        REQUEST = "request"            # 请求协作
        RESPONSE = "response"          # 响应协作
        CONFLICT = "conflict"          # 冲突告警
        EVOLVE = "evolve"              # 演化通知
        DEATH = "death"                # 消亡通知
        BIRTH = "birth"                # 诞生通知

    def __init__(self, store: StateAtomStore):
        self.store = store
        self.subscribers: Dict[str, List[Callable]] = {}

    def send_message(self, sender_id: str, receiver_id: str,
                     message_type: str, payload: Dict) -> int:
        """发送消息"""
        with self.store._lock:
            cursor = self.store.conn.execute(
                "INSERT INTO messages (sender_id, receiver_id, message_type, payload, timestamp) VALUES (?,?,?,?,?)",
                (sender_id, receiver_id, message_type, json.dumps(payload),
                 datetime.now(timezone.utc).isoformat())
            )
            self.store.conn.commit()
            return cursor.lastrowid

    def get_pending_messages(self, receiver_id: str, limit: int = 50) -> List[Dict]:
        """获取待处理消息"""
        with self.store._lock:
            rows = self.store.conn.execute(
                "SELECT * FROM messages WHERE receiver_id=? AND processed=0 ORDER BY id LIMIT ?",
                (receiver_id, limit)
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_processed(self, message_id: int):
        """标记消息已处理"""
        with self.store._lock:
            self.store.conn.execute("UPDATE messages SET processed=1 WHERE id=?", (message_id,))
            self.store.conn.commit()

    def broadcast(self, sender_id: str, message_type: str, payload: Dict,
                  receiver_filter: Dict = None):
        """广播消息给所有符合条件的态元"""
        atoms = self.store.query_atoms(receiver_filter or {}, limit=1000)
        for atom in atoms:
            if atom.atom_id != sender_id:
                self.send_message(sender_id, atom.atom_id, message_type, payload)

    def process_messages_for_atom(self, atom: StateAtom) -> List[Dict]:
        """处理态元的所有待处理消息，返回处理结果"""
        messages = self.get_pending_messages(atom.atom_id)
        results = []
        for msg in messages:
            payload = json.loads(msg['payload'])
            result = self._handle_message(atom, msg, payload)
            results.append(result)
            self.mark_processed(msg['id'])
        return results

    def _handle_message(self, atom: StateAtom, msg: Dict, payload: Dict) -> Dict:
        """处理单条消息"""
        msg_type = msg['message_type']

        if msg_type == self.MessageType.REINFORCE.value:
            atom.reinforce()
            self.store.save_atom(atom)
            return {"message_id": msg['id'], "action": "reinforced", "atom": atom.atom_id}

        elif msg_type == self.MessageType.REQUEST.value:
            # 请求协作：检查是否能提供帮助
            can_help = payload.get('required_type') == atom.atom_type
            return {"message_id": msg['id'], "action": "request_received",
                    "can_help": can_help, "atom": atom.atom_id}

        elif msg_type == self.MessageType.CONFLICT.value:
            # 冲突告警：降低置信度
            atom.information_dim.confidence = max(0.1, atom.information_dim.confidence - 0.1)
            atom.energy_dim.low_fitness_streak += 1
            self.store.save_atom(atom)
            return {"message_id": msg['id'], "action": "conflict_processed",
                    "new_confidence": atom.information_dim.confidence}

        elif msg_type == self.MessageType.EVOLVE.value:
            # 演化通知：记录演化
            self.store.record_evolution(atom.atom_id, "evolve_notify",
                                        "", json.dumps(payload), "external_evolve")
            return {"message_id": msg['id'], "action": "evolve_recorded"}

        return {"message_id": msg['id'], "action": "ignored", "type": msg_type}


# ============================================================
# 3. 态元自修改框架（自进化闭环的核心）
# ============================================================

class SelfModifyEngine:
    """态元自修改框架：算子态元可修改自身逻辑，实现自进化"""

    def __init__(self, store: StateAtomStore, message_bus: AtomMessageBus):
        self.store = store
        self.message_bus = message_bus
        self.modify_count = 0
        self.max_modifications_per_cycle = 5  # 每周期最多自修改次数

    def can_modify(self, atom: StateAtom) -> bool:
        """检查态元是否允许自修改"""
        return (atom.logic_dim.self_modifiable and
                atom.energy_dim.energy_state == EnergyState.ACTIVE.value and
                atom.energy_dim.fitness_score > 0.3)

    def propose_modification(self, atom: StateAtom) -> Optional[Dict]:
        """提议自修改（基于当前状态生成改进建议）"""
        if not self.can_modify(atom):
            return None

        # 基于态元类型生成不同的修改策略
        if atom.atom_type == AtomType.OPERATOR.value:
            # 算子态元：优化推理规则
            if len(atom.logic_dim.inference_rules) < 5:
                return {
                    "type": "add_inference_rule",
                    "field": "logic_dim.inference_rules",
                    "old_value": str(atom.logic_dim.inference_rules),
                    "new_value": str(atom.logic_dim.inference_rules +
                                    [f"auto_rule_{int(time.time())}"]),
                    "reason": "fitness-based optimization: adding rule to improve coverage",
                }

        elif atom.atom_type == AtomType.TRUTH.value:
            # 真值态元：提升置信度（如果被高频使用）
            if (atom.energy_dim.usage_frequency > 10 and
                    atom.information_dim.confidence < 0.95):
                new_conf = min(0.95, atom.information_dim.confidence + 0.05)
                return {
                    "type": "boost_confidence",
                    "field": "information_dim.confidence",
                    "old_value": str(atom.information_dim.confidence),
                    "new_value": str(new_conf),
                    "reason": "high usage frequency indicates reliability",
                }

        # 通用：版本号递增
        return {
            "type": "version_bump",
            "field": "version",
            "old_value": str(atom.version),
            "new_value": str(atom.version + 1),
            "reason": "routine evolution checkpoint",
        }

    def apply_modification(self, atom: StateAtom, modification: Dict) -> bool:
        """应用自修改"""
        try:
            field = modification['field']

            if field == "logic_dim.inference_rules":
                atom.logic_dim.inference_rules = json.loads(modification['new_value'])
            elif field == "information_dim.confidence":
                atom.information_dim.confidence = float(modification['new_value'])
            elif field == "version":
                atom.version = int(modification['new_value'])

            atom.updated_at = datetime.now(timezone.utc).isoformat()
            self.store.save_atom(atom)
            self.store.record_evolution(
                atom.atom_id, modification['type'],
                modification['old_value'], modification['new_value'],
                modification['reason']
            )
            self.modify_count += 1

            # 广播演化通知
            self.message_bus.broadcast(
                atom.atom_id, AtomMessageBus.MessageType.EVOLVE.value,
                {"modification": modification['type'], "reason": modification['reason']}
            )
            return True
        except Exception as e:
            self.store.record_evolution(atom.atom_id, "modify_failed",
                                        "", str(e), "self_modify_error")
            return False

    def run_self_modification_cycle(self, atoms: List[StateAtom]) -> Dict:
        """运行一轮自修改周期"""
        modified = []
        failed = []

        # 按fitness排序，优先修改高价值态元
        candidates = sorted(atoms, key=lambda a: a.energy_dim.fitness_score, reverse=True)

        for atom in candidates[:self.max_modifications_per_cycle]:
            mod = self.propose_modification(atom)
            if mod:
                if self.apply_modification(atom, mod):
                    modified.append({"atom_id": atom.atom_id, "mod": mod['type']})
                else:
                    failed.append(atom.atom_id)

        return {
            "modified_count": len(modified),
            "failed_count": len(failed),
            "modified": modified,
            "failed": failed,
            "total_modifications": self.modify_count,
        }


# ============================================================
# 4. 本地真值迁移器
# ============================================================

class LocalTruthMigrator:
    """从本地内核和已知真值库迁移为态元"""

    def __init__(self, store: StateAtomStore):
        self.store = store

    def migrate_kernel_truths(self, kernel_path: str = None) -> Dict:
        """迁移内核中的真值（constitutions/state_atom_engine等）"""
        kernel_path = kernel_path or os.path.expanduser("~/.zongyuan_root/kernel/kernel_state.json")
        if not os.path.exists(kernel_path):
            return {"error": "kernel not found", "path": kernel_path}

        with open(kernel_path) as f:
            kernel = json.load(f)

        migrated = []

        # 迁移constitutions（元宪法级）
        for const in kernel.get('constitutions', []):
            atom = StateAtom(
                atom_type=AtomType.TRUTH.value,
                information_dim=InformationDim(
                    content=f"{const.get('name','')}: {const.get('description','')}",
                    confidence=1.0,
                    meta_class="M9",
                    truth_type=TruthType.META_LAW.value,
                    source="kernel_constitution",
                ),
                logic_dim=LogicDim(self_modifiable=False),  # 元宪法不可修改
                energy_dim=EnergyDim(compute_quota=1000, storage_quota=2048, fitness_score=1.0),
            )
            self.store.save_atom(atom)
            migrated.append(atom.atom_id)

        # 迁移state_atom_engine配置
        if 'state_atom_engine' in kernel:
            sae = kernel['state_atom_engine']
            atom = StateAtom(
                atom_type=AtomType.SERVICE.value,
                information_dim=InformationDim(
                    content=f"态元引擎{sae.get('version','')}: {','.join(sae.get('implemented',[]))}",
                    confidence=0.95,
                    meta_class="M6",
                    truth_type=TruthType.CONFIG.value,
                    source="kernel_config",
                ),
                energy_dim=EnergyDim(compute_quota=500, storage_quota=4096, fitness_score=0.9),
            )
            self.store.save_atom(atom)
            migrated.append(atom.atom_id)

        # 迁移breakthrough_plans
        if 'breakthrough_plans' in kernel:
            for plan in kernel['breakthrough_plans']:
                if isinstance(plan, dict):
                    atom = StateAtom(
                        atom_type=AtomType.TRUTH.value,
                        information_dim=InformationDim(
                            content=f"破局计划{plan.get('plan_id','')}: {json.dumps(plan.get('tasks',[]),ensure_ascii=False)[:500]}",
                            confidence=0.9,
                            meta_class="M8",
                            truth_type=TruthType.DECISION.value,
                            source="kernel_breakthrough",
                        ),
                        energy_dim=EnergyDim(compute_quota=300, fitness_score=0.85),
                    )
                    self.store.save_atom(atom)
                    migrated.append(atom.atom_id)

        return {
            "migrated_count": len(migrated),
            "atom_ids": migrated,
            "source": "kernel_state.json",
        }

    def migrate_known_truths(self, truths: List[Dict]) -> Dict:
        """迁移已知真值列表"""
        migrator = StateAtomMigrator(output_dir="/tmp/state_atoms_migrated")
        results = []
        for truth in truths:
            atom = migrator.migrate_asset(truth, truth.get('type', 'truth'))
            if atom:
                self.store.save_atom(atom)
                results.append(atom.atom_id)
        return {"migrated_count": len(results), "atom_ids": results}


# ============================================================
# 5. 自治进化循环（生命体的自主运行）
# ============================================================

class AutonomousEvolutionLoop:
    """自治进化循环：自动心跳+能量竞价+消息处理+自修改+演化"""

    def __init__(self, db_path: str = "state_atoms.db",
                 total_compute: int = 10000, total_storage: int = 1048576):
        self.store = StateAtomStore(db_path)
        self.message_bus = AtomMessageBus(self.store)
        self.self_modify_engine = SelfModifyEngine(self.store, self.message_bus)
        self.auction_engine = EnergyAuctionEngine(total_compute, total_storage)
        self.heartbeat = 0
        self.running = False

    def run_cycle(self) -> Dict:
        """运行一个完整的自治进化周期"""
        self.heartbeat += 1
        cycle_start = time.time()

        # 步骤1：加载所有活跃态元
        atoms = self.store.get_all_active_atoms()
        if not atoms:
            return {"heartbeat": self.heartbeat, "status": "no_atoms", "action": "waiting_for_migration"}

        # 步骤2：处理消息（态元间通讯）
        messages_processed = 0
        for atom in atoms:
            msgs = self.message_bus.process_messages_for_atom(atom)
            messages_processed += len(msgs)

        # 步骤3：能量竞价
        auction_result = self.auction_engine.run_auction(atoms)

        # 记录适应度历史
        for atom in atoms:
            self.store.record_fitness(atom.atom_id, self.heartbeat,
                                      atom.energy_dim.fitness_score)
            self.store.save_atom(atom)

        # 步骤4：自修改（高fitness态元优先）
        modify_result = self.self_modify_engine.run_self_modification_cycle(atoms)

        # 步骤5：统计
        stats = self.store.get_stats()
        cycle_time = round(time.time() - cycle_start, 3)

        result = {
            "heartbeat": self.heartbeat,
            "cycle_time_seconds": cycle_time,
            "atoms_total": stats['total'],
            "atoms_active": auction_result['active'],
            "atoms_compressed": auction_result['compressed'],
            "atoms_cold": auction_result['cold'],
            "atoms_dead": auction_result['dead'],
            "messages_processed": messages_processed,
            "avg_fitness": auction_result['avg_fitness'],
            "top_fitness": auction_result['top_fitness'],
            "self_modified": modify_result['modified_count'],
            "self_modify_failed": modify_result['failed_count'],
            "by_type": stats['by_type'],
            "by_energy_state": stats['by_energy_state'],
            "status": "healthy" if auction_result['active'] > 0 else "degraded",
        }

        return result

    def run_n_cycles(self, n: int = 10, delay: float = 0.1) -> List[Dict]:
        """运行N个周期"""
        results = []
        for i in range(n):
            result = self.run_cycle()
            results.append(result)
            if delay > 0:
                time.sleep(delay)
        return results

    def get_status(self) -> Dict:
        """获取自治系统状态"""
        stats = self.store.get_stats()
        return {
            "heartbeat": self.heartbeat,
            "running": self.running,
            "total_atoms": stats['total'],
            "active_atoms": stats['by_lifecycle_stage'].get('active', 0),
            "avg_fitness": stats['avg_fitness_active'],
            "by_type": stats['by_type'],
            "total_self_modifications": self.self_modify_engine.modify_count,
        }


# ============================================================
# 演示与测试
# ============================================================

def run_autonomous_demo():
    """自治进化引擎完整演示"""
    print("=" * 60)
    print("态元自治进化引擎 V2.0 演示")
    print("=" * 60)

    db_path = "/tmp/state_atoms_autonomous.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    loop = AutonomousEvolutionLoop(db_path=db_path)

    # 1. 迁移本地内核真值
    print("\n【1】迁移本地内核真值为态元")
    migrator = LocalTruthMigrator(loop.store)
    kernel_result = migrator.migrate_kernel_truths()
    print(f"  内核迁移: {kernel_result.get('migrated_count', 0)} 条")

    # 2. 迁移已知高价值真值
    print("\n【2】迁移已知高价值真值")
    known_truths = [
        {"content": "三态融合生命体架构元宪法：信息态逻辑态能量态必须内在融合",
         "confidence": 1.0, "meta_class": "M9", "type": "meta_law"},
        {"content": "能量竞价算法：fitness=0.30置信度+0.35使用频率+0.20价值密度+0.15依赖重要度",
         "confidence": 0.95, "meta_class": "M1", "type": "rule"},
        {"content": "单兵破局作战规划：尖刀产品昆仑洞天AI短剧，四阶段0→1→10→100→∞",
         "confidence": 0.9, "meta_class": "M8", "type": "decision"},
        {"content": "SOP七步闭环：意图校准→拉记忆→全域对比→稳态裁决→执行容错→上报→沉淀",
         "confidence": 0.92, "meta_class": "M9", "type": "meta_law"},
        {"content": "API对接方案：5个P0核心产品+4条核心调用链+统一API网关",
         "confidence": 0.88, "meta_class": "M3", "type": "config"},
    ]
    known_result = migrator.migrate_known_truths(known_truths)
    print(f"  已知真值迁移: {known_result['migrated_count']} 条")

    # 3. 创建算子态元
    print("\n【3】创建算子态元（可自修改）")
    for i in range(3):
        atom = StateAtom(
            atom_type=AtomType.OPERATOR.value,
            information_dim=InformationDim(
                content=f"def auto_operator_{i+1}(input): return optimized_output",
                confidence=0.85, meta_class="M1", truth_type=TruthType.RULE.value,
            ),
            logic_dim=LogicDim(
                builtin_operator={"name": f"auto_op_{i+1}"},
                inference_rules=[f"rule_{i+1}"],
                self_modifiable=True,
            ),
            energy_dim=EnergyDim(usage_frequency=15 - i * 4, compute_quota=200, fitness_score=0.7),
        )
        loop.store.save_atom(atom)
        print(f"  算子态元: {atom.atom_id} (usage={15-i*4})")

    # 4. 运行自治进化循环
    print(f"\n【4】运行自治进化循环（10个心跳周期）")
    results = loop.run_n_cycles(n=10, delay=0.05)

    print(f"\n  周期摘要:")
    for r in results[::3]:  # 每3个周期显示一次
        print(f"    心跳#{r['heartbeat']}: 活跃={r['atoms_active']}, "
              f"平均fitness={r['avg_fitness']}, 自修改={r['self_modified']}, "
              f"消息处理={r['messages_processed']}")

    # 5. 最终状态
    print(f"\n【5】自治系统最终状态")
    status = loop.get_status()
    print(f"  总心跳: {status['heartbeat']}")
    print(f"  总态元: {status['total_atoms']}")
    print(f"  活跃态元: {status['active_atoms']}")
    print(f"  平均fitness: {status['avg_fitness']}")
    print(f"  累计自修改: {status['total_self_modifications']} 次")
    print(f"  态元类型分布: {status['by_type']}")

    # 6. 态元间通讯测试
    print(f"\n【6】态元间通讯测试")
    atoms = loop.store.get_all_active_atoms()
    if atoms:
        sender = atoms[0]
        receiver = atoms[-1]
        msg_id = loop.message_bus.send_message(
            sender.atom_id, receiver.atom_id,
            AtomMessageBus.MessageType.REINFORCE.value,
            {"reason": "cross-atom collaboration"}
        )
        print(f"  发送消息: {sender.atom_id} → {receiver.atom_id} (id={msg_id})")
        processed = loop.message_bus.process_messages_for_atom(receiver)
        print(f"  处理结果: {processed}")

    loop.store.close()

    print("\n" + "=" * 60)
    print("自治进化引擎 V2.0 演示完成！")
    print("核心能力：持久化存储 + 态元通讯 + 自修改 + 自治循环")
    print("=" * 60)

    return loop


if __name__ == "__main__":
    run_autonomous_demo()
