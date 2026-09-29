#!/usr/bin/env python3
"""
六态融合生命体架构引擎 V1.0
在三态（信息/逻辑/能量）基础上扩展法则态、智能态、生命态
构建完整六态层级生命体架构
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json, hashlib, os, time, sqlite3, threading
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


# ==================== 六态定义 ====================

class SixStateType(str, Enum):
    LAW = "law_state"           # 法则态：元规则/元法则/元宪法
    INTELLIGENCE = "intelligence_state"  # 智能态：认知/决策/学习
    LOGIC = "logic_state"       # 逻辑态：推理/执行/因果
    INFORMATION = "information_state"    # 信息态：数据/真值/知识
    ENERGY = "energy_state"     # 能量态：算力/资源/场态
    LIFE = "life_state"         # 生命态：自组织/自维持/自进化


# 六态层级关系（从高到低）
SIX_STATE_HIERARCHY = [
    SixStateType.LAW,           # 第6层：最高约束
    SixStateType.INTELLIGENCE,  # 第5层：认知决策
    SixStateType.LOGIC,         # 第4层：推理执行
    SixStateType.INFORMATION,   # 第3层：数据存储
    SixStateType.ENERGY,        # 第2层：资源分配
    SixStateType.LIFE,          # 第1层：物质载体
]

# 六态核心职责
SIX_STATE_RESPONSIBILITIES = {
    SixStateType.LAW: {
        "name": "法则态",
        "level": 6,
        "core": "元规则约束与最高裁决",
        "components": ["元宪法", "元法则", "元公理", "熔断公理S0/S1/S2", "真值优先原则"],
        "function": "约束所有其他态的运行边界，提供最高裁决依据",
        "corresponding": "META-CONSTITUTION-TRISTATE-LIFE-V1.0, 本源节点太初寂态",
    },
    SixStateType.INTELLIGENCE: {
        "name": "智能态",
        "level": 5,
        "core": "认知决策与自主学习",
        "components": ["自主决策引擎", "稳态裁决", "元学习进化", "意图识别", "经验沉淀"],
        "function": "感知环境→认知理解→决策判断→学习进化",
        "corresponding": "元学习自进化引擎, 决策工业化流水线, 三维稳态决策",
    },
    SixStateType.LOGIC: {
        "name": "逻辑态",
        "level": 4,
        "core": "推理执行与因果推演",
        "components": ["27算子十层拓扑", "因果奇点内核", "SM-BS流形映射", "CTE三适配器", "逻辑一致性校验"],
        "function": "执行规则运算、因果推演、逻辑推理，将决策转化为行动",
        "corresponding": "因果奇点内核V3.0, 真值生成引擎V3.0, CTE三位一体",
    },
    SixStateType.INFORMATION: {
        "name": "信息态",
        "level": 3,
        "core": "数据存储与真值管理",
        "components": ["真值库", "知识图谱", "记忆网关9120", "Merkle-DAG账本", "向量检索"],
        "function": "存储真值、管理知识、提供信息检索与一致性校验",
        "corresponding": "记忆网关9120, 知识关联引擎, 全域锁档台账",
    },
    SixStateType.ENERGY: {
        "name": "能量态",
        "level": 2,
        "core": "资源分配与算力调度",
        "components": ["算力路由", "能量竞价引擎", "场态全域展开", "资源配额管理", "用进废退"],
        "function": "为所有态提供算力资源，按fitness竞价分配，用进废退",
        "corresponding": "全域算力调度引擎, 态元能量竞价, 希尔伯特场态",
    },
    SixStateType.LIFE: {
        "name": "生命态",
        "level": 1,
        "core": "自组织自维持自进化",
        "components": ["态元自治进化", "新陈代谢", "自修复机制", "自主稳态", "生命体征监控"],
        "function": "物质载体与自组织基础，实现自维持、自修复、自进化的生命特征",
        "corresponding": "态元自治进化引擎V2.0, 本源六态层级, 先天基准态",
    },
}


# ==================== 六态交互协议 ====================

@dataclass
class SixStateInteraction:
    """六态间交互记录"""
    from_state: SixStateType
    to_state: SixStateType
    interaction_type: str  # constraint/call/data/feedback/resource
    content: str
    timestamp: str = ""
    signature: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        raw = f"{self.from_state}{self.to_state}{self.interaction_type}{self.content}{self.timestamp}"
        self.signature = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]


class SixStateInteractionBus:
    """六态交互总线：管理六态间的信号传递与协作"""

    def __init__(self):
        self.interactions: List[SixStateInteraction] = []
        self._lock = threading.Lock()

    def send(self, from_state: SixStateType, to_state: SixStateType,
             interaction_type: str, content: str) -> SixStateInteraction:
        """发送态间交互信号"""
        interaction = SixStateInteraction(
            from_state=from_state,
            to_state=to_state,
            interaction_type=interaction_type,
            content=content,
        )
        with self._lock:
            self.interactions.append(interaction)
        return interaction

    def get_interactions(self, state_type: SixStateType = None,
                         limit: int = 50) -> List[Dict]:
        """获取交互记录"""
        with self._lock:
            records = self.interactions[-limit:]
        if state_type:
            records = [i for i in records
                       if i.from_state == state_type or i.to_state == state_type]
        return [asdict(i) for i in records]

    def get_stats(self) -> Dict:
        """获取交互统计"""
        stats = {"total": len(self.interactions), "by_type": {}, "by_state": {}}
        for i in self.interactions:
            stats["by_type"][i.interaction_type] = stats["by_type"].get(i.interaction_type, 0) + 1
            key = f"{i.from_state.value}->{i.to_state.value}"
            stats["by_state"][key] = stats["by_state"].get(key, 0) + 1
        return stats


# ==================== 六态生命体 ====================

@dataclass
class SixStateLifeForm:
    """六态生命体：具备完整六态的自组织实体"""
    lifeform_id: str = ""
    name: str = ""
    states: Dict[str, Dict] = field(default_factory=dict)  # 六态状态
    interaction_bus: Optional[SixStateInteractionBus] = None
    heartbeat: int = 0
    created_at: str = ""
    updated_at: str = ""
    did: str = "DID-BR-000002"
    trace_mark: str = "Ω₀⊂⊙∞⊂Ω"

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now(timezone.utc).isoformat()
        if not self.lifeform_id:
            self.lifeform_id = f"SLF-{datetime.now().strftime('%Y%m%d')}-{os.getpid() % 1000:03d}{int(time.time()*1000) % 10000:04d}"
        if not self.interaction_bus:
            self.interaction_bus = SixStateInteractionBus()
        # 初始化六态
        for state_type in SIX_STATE_HIERARCHY:
            if state_type.value not in self.states:
                self.states[state_type.value] = {
                    "status": "active",
                    "level": SIX_STATE_RESPONSIBILITIES[state_type]["level"],
                    "fitness": 0.5,
                    "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                }

    def pulse(self) -> Dict:
        """六态生命体心跳：模拟一个完整的六态协同周期"""
        self.heartbeat += 1
        now = datetime.now(timezone.utc).isoformat()
        bus = self.interaction_bus

        # 1. 法则态发布约束（自上而下）
        bus.send(SixStateType.LAW, SixStateType.INTELLIGENCE, "constraint",
                 f"心跳#{self.heartbeat}: 法则态发布运行约束，真值优先原则生效")

        # 2. 智能态感知决策
        bus.send(SixStateType.INTELLIGENCE, SixStateType.LOGIC, "call",
                 f"心跳#{self.heartbeat}: 智能态发起推理请求，稳态裁决")

        # 3. 逻辑态查询信息
        bus.send(SixStateType.LOGIC, SixStateType.INFORMATION, "data",
                 f"心跳#{self.heartbeat}: 逻辑态请求真值数据，因果推演")

        # 4. 信息态返回数据
        bus.send(SixStateType.INFORMATION, SixStateType.LOGIC, "data",
                 f"心跳#{self.heartbeat}: 信息态返回真值，一致性校验通过")

        # 5. 逻辑态返回推理结果
        bus.send(SixStateType.LOGIC, SixStateType.INTELLIGENCE, "feedback",
                 f"心跳#{self.heartbeat}: 逻辑态返回推理结果，因果链完整")

        # 6. 智能态请求能量
        bus.send(SixStateType.INTELLIGENCE, SixStateType.ENERGY, "resource",
                 f"心跳#{self.heartbeat}: 智能态请求算力资源，执行决策")

        # 7. 能量态分配资源
        bus.send(SixStateType.ENERGY, SixStateType.LIFE, "resource",
                 f"心跳#{self.heartbeat}: 能量态分配算力，二八原则生效")

        # 8. 生命态执行自组织
        bus.send(SixStateType.LIFE, SixStateType.INTELLIGENCE, "feedback",
                 f"心跳#{self.heartbeat}: 生命态完成自组织，新陈代谢正常")

        # 9. 智能态反馈法则态（规则更新）
        bus.send(SixStateType.INTELLIGENCE, SixStateType.LAW, "feedback",
                 f"心跳#{self.heartbeat}: 智能态反馈运行经验，法则态评估规则更新")

        # 更新各态fitness
        for state_type in SIX_STATE_HIERARCHY:
            state = self.states[state_type.value]
            state["last_heartbeat"] = now
            state["fitness"] = min(1.0, state["fitness"] + 0.01)  # 用进废退

        self.updated_at = now
        return {
            "heartbeat": self.heartbeat,
            "interactions_this_cycle": 9,
            "all_states_active": all(s["status"] == "active" for s in self.states.values()),
            "avg_fitness": sum(s["fitness"] for s in self.states.values()) / 6,
        }

    def get_status(self) -> Dict:
        """获取生命体状态"""
        return {
            "lifeform_id": self.lifeform_id,
            "name": self.name,
            "heartbeat": self.heartbeat,
            "states": {k: {"level": v["level"], "status": v["status"],
                           "fitness": round(v["fitness"], 4)}
                       for k, v in self.states.items()},
            "interaction_stats": self.interaction_bus.get_stats() if self.interaction_bus else {},
            "created_at": self.created_at,
            "did": self.did,
        }


# ==================== 六态融合引擎 ====================

class SixStateFusionEngine:
    """六态融合引擎：管理六态生命体的创建、运行、进化"""

    def __init__(self, db_path: str = "six_state_life.db"):
        self.db_path = db_path
        self.lifeforms: Dict[str, SixStateLifeForm] = {}
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS lifeforms (
                lifeform_id TEXT PRIMARY KEY,
                name TEXT,
                heartbeat INTEGER DEFAULT 0,
                states_json TEXT,
                created_at TEXT,
                updated_at TEXT,
                did TEXT
            );
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lifeform_id TEXT,
                from_state TEXT,
                to_state TEXT,
                interaction_type TEXT,
                content TEXT,
                timestamp TEXT,
                signature TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_interactions_lifeform ON interactions(lifeform_id);
            CREATE INDEX IF NOT EXISTS idx_interactions_state ON interactions(from_state, to_state);
        """)

    def create_lifeform(self, name: str = "ZONGYUAN-ROOT六态生命体") -> SixStateLifeForm:
        """创建六态生命体"""
        lifeform = SixStateLifeForm(name=name)
        self.lifeforms[lifeform.lifeform_id] = lifeform
        self._save_lifeform(lifeform)
        return lifeform

    def _save_lifeform(self, lifeform: SixStateLifeForm):
        """保存生命体到数据库"""
        self.conn.execute("""
            INSERT OR REPLACE INTO lifeforms
            (lifeform_id, name, heartbeat, states_json, created_at, updated_at, did)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            lifeform.lifeform_id, lifeform.name, lifeform.heartbeat,
            json.dumps(lifeform.states, ensure_ascii=False),
            lifeform.created_at, lifeform.updated_at, lifeform.did
        ))
        # 保存交互记录
        if lifeform.interaction_bus:
            for interaction in lifeform.interaction_bus.interactions[-100:]:
                self.conn.execute("""
                    INSERT INTO interactions
                    (lifeform_id, from_state, to_state, interaction_type, content, timestamp, signature)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    lifeform.lifeform_id, interaction.from_state.value,
                    interaction.to_state.value, interaction.interaction_type,
                    interaction.content, interaction.timestamp, interaction.signature
                ))
        self.conn.commit()

    def run_pulse(self, lifeform_id: str, cycles: int = 5) -> List[Dict]:
        """运行生命体心跳周期"""
        if lifeform_id not in self.lifeforms:
            # 从数据库加载
            row = self.conn.execute("SELECT * FROM lifeforms WHERE lifeform_id=?",
                                    (lifeform_id,)).fetchone()
            if not row:
                raise ValueError(f"生命体不存在: {lifeform_id}")
            lifeform = SixStateLifeForm(
                lifeform_id=row["lifeform_id"], name=row["name"],
                heartbeat=row["heartbeat"],
                states=json.loads(row["states_json"]),
                created_at=row["created_at"], updated_at=row["updated_at"],
            )
            self.lifeforms[lifeform_id] = lifeform
        else:
            lifeform = self.lifeforms[lifeform_id]

        results = []
        for _ in range(cycles):
            result = lifeform.pulse()
            results.append(result)

        self._save_lifeform(lifeform)
        return results

    def get_lifeform_status(self, lifeform_id: str) -> Dict:
        """获取生命体状态"""
        if lifeform_id in self.lifeforms:
            return self.lifeforms[lifeform_id].get_status()
        row = self.conn.execute("SELECT * FROM lifeforms WHERE lifeform_id=?",
                                (lifeform_id,)).fetchone()
        if not row:
            return {"error": "生命体不存在"}
        return {
            "lifeform_id": row["lifeform_id"],
            "name": row["name"],
            "heartbeat": row["heartbeat"],
            "states": json.loads(row["states_json"]),
            "created_at": row["created_at"],
        }

    def get_interaction_stats(self, lifeform_id: str = None) -> Dict:
        """获取交互统计"""
        query = "SELECT from_state, to_state, interaction_type, COUNT(*) as cnt FROM interactions"
        params = []
        if lifeform_id:
            query += " WHERE lifeform_id=?"
            params.append(lifeform_id)
        query += " GROUP BY from_state, to_state, interaction_type"
        rows = self.conn.execute(query, params).fetchall()
        stats = {"total": 0, "by_pair": {}, "by_type": {}}
        for row in rows:
            key = f"{row['from_state']}->{row['to_state']}"
            stats["by_pair"][key] = row["cnt"]
            stats["by_type"][row["interaction_type"]] = stats["by_type"].get(row["interaction_type"], 0) + row["cnt"]
            stats["total"] += row["cnt"]
        return stats

    def close(self):
        self.conn.close()


# ==================== 演示 ====================

def run_demo():
    """运行六态融合生命体演示"""
    print("=" * 60)
    print("六态融合生命体架构引擎 V1.0")
    print("=" * 60)

    db_path = os.path.expanduser("~/.zongyuan_root/six_state_life.db")
    engine = SixStateFusionEngine(db_path=db_path)

    # 创建生命体
    lifeform = engine.create_lifeform("ZONGYUAN-ROOT本源六态生命体")
    print(f"\n✅ 生命体创建: {lifeform.lifeform_id}")
    print(f"   名称: {lifeform.name}")
    print(f"   六态初始化完成")

    # 运行心跳
    print(f"\n--- 运行10个心跳周期 ---")
    results = engine.run_pulse(lifeform.lifeform_id, cycles=10)
    for i, r in enumerate(results):
        print(f"  心跳#{r['heartbeat']}: 交互{r['interactions_this_cycle']}次, "
              f"平均fitness={r['avg_fitness']:.4f}, 全态活跃={r['all_states_active']}")

    # 获取状态
    status = engine.get_lifeform_status(lifeform.lifeform_id)
    print(f"\n--- 生命体最终状态 ---")
    print(f"  总心跳: {status['heartbeat']}")
    print(f"  六态fitness:")
    for state, info in status['states'].items():
        state_name = SIX_STATE_RESPONSIBILITIES[SixStateType(state)]['name']
        print(f"    L{info['level']} {state_name}({state}): fitness={info['fitness']}")

    # 交互统计
    stats = engine.get_interaction_stats(lifeform.lifeform_id)
    print(f"\n--- 态间交互统计 ---")
    print(f"  总交互: {stats['total']}")
    print(f"  按类型: {stats['by_type']}")
    print(f"  按态对: {stats['by_pair']}")

    engine.close()
    print(f"\n{'=' * 60}")
    print("六态融合生命体演示完成！")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    run_demo()
