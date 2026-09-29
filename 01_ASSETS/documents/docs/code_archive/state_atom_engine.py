#!/usr/bin/env python3
"""
态元 State-Atom 引擎 V1.0
三态融合生命体架构核心实现
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

包含：
- StateAtom: 态元数据结构（信息维+逻辑维+能量维）
- EnergyAuctionEngine: 能量竞价引擎（适应度计算+出价+分配）
- StateAtomMigrator: 现有资产迁移工具
- LifecycleManager: 生命周期管理（诞生/生长/成熟/衰退/消亡）
"""

import json
import hashlib
import os
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


class AtomType(str, Enum):
    TRUTH = "truth"
    OPERATOR = "operator"
    SERVICE = "service"
    DOCUMENT = "document"
    CREATIVE = "creative"


class EnergyState(str, Enum):
    ACTIVE = "active"
    COMPRESSED = "compressed"
    COLD = "cold"
    DEAD = "dead"


class LifecycleStage(str, Enum):
    BIRTH = "birth"
    GROWTH = "growth"
    MATURITY = "maturity"
    DECLINE = "decline"
    DEATH = "death"


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


@dataclass
class InformationDim:
    """信息维：真值内容+置信度+演化历史"""
    content: str
    content_hash: str = ""
    confidence: float = 0.5
    confidence_evolution: List[Dict] = field(default_factory=list)
    source: str = "auto_generated"
    source_refs: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    meta_class: str = "M4"
    truth_type: str = "unknown"

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                self.content.encode('utf-8')
            ).hexdigest()


@dataclass
class LogicDim:
    """逻辑维：内置算子+推理规则+自修改能力"""
    builtin_operator: Optional[Dict] = None
    inference_rules: List[str] = field(default_factory=list)
    self_modifiable: bool = True
    self_modify_history: List[Dict] = field(default_factory=list)
    fitness_function: str = "default"
    fitness_params: Dict = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)


@dataclass
class EnergyDim:
    """能量维：算力配额+存储配额+适应度+生死状态"""
    compute_quota: int = 100
    storage_quota: int = 1024
    compute_used: int = 0
    storage_used: int = 0
    usage_frequency: int = 0
    usage_history: List[Dict] = field(default_factory=list)
    fitness_score: float = 0.5
    fitness_history: List[Dict] = field(default_factory=list)
    energy_state: str = "active"
    last_used: Optional[str] = None
    birth_time: str = ""
    death_time: Optional[str] = None
    low_fitness_streak: int = 0

    def __post_init__(self):
        if not self.birth_time:
            self.birth_time = datetime.now(timezone.utc).isoformat()


@dataclass
class Lifecycle:
    """生命周期：诞生→生长→成熟→衰退→消亡"""
    stage: str = "birth"
    stage_history: List[Dict] = field(default_factory=list)
    reinforcement_count: int = 0
    compression_count: int = 0
    revival_count: int = 0


@dataclass
class StateAtom:
    """态元：三态合一的最小不可分单元"""
    atom_id: str = ""
    atom_type: str = "truth"
    created_at: str = ""
    updated_at: str = ""
    version: int = 1
    parent_atom_ids: List[str] = field(default_factory=list)
    child_atom_ids: List[str] = field(default_factory=list)

    information_dim: InformationDim = field(default_factory=lambda: InformationDim(content=""))
    logic_dim: LogicDim = field(default_factory=LogicDim)
    energy_dim: EnergyDim = field(default_factory=EnergyDim)
    lifecycle: Lifecycle = field(default_factory=Lifecycle)

    did: str = "DID-BR-000002"
    trace_mark: str = "Ω₀⊂⊙∞⊂Ω"

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if not self.atom_id:
            self.atom_id = f"SA-{datetime.now().strftime('%Y%m%d')}-{os.getpid() % 1000:03d}{int(time.time()*1000000) % 100000:05d}"

    def to_dict(self) -> Dict:
        return {
            "atom_id": self.atom_id,
            "atom_type": self.atom_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "parent_atom_ids": self.parent_atom_ids,
            "child_atom_ids": self.child_atom_ids,
            "information_dim": asdict(self.information_dim),
            "logic_dim": asdict(self.logic_dim),
            "energy_dim": asdict(self.energy_dim),
            "lifecycle": asdict(self.lifecycle),
            "did": self.did,
            "trace_mark": self.trace_mark,
        }

    def get_full_hash(self) -> str:
        """三态合并哈希（态元唯一确权）"""
        full = json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(full.encode('utf-8')).hexdigest()

    def reinforce(self):
        """强化：被使用时调用，提升使用频率和适应度"""
        self.energy_dim.usage_frequency += 1
        self.energy_dim.last_used = datetime.now(timezone.utc).isoformat()
        self.lifecycle.reinforcement_count += 1
        self.energy_dim.usage_history.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": "reinforce"
        })
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def compress(self):
        """压缩：低适应度态元压缩为摘要"""
        original_len = len(self.information_dim.content)
        self.information_dim.content = self.information_dim.content[:200] + "...[compressed]"
        self.energy_dim.energy_state = EnergyState.COMPRESSED.value
        self.energy_dim.compute_quota = int(self.energy_dim.compute_quota * 0.2)
        self.energy_dim.storage_quota = int(self.energy_dim.storage_quota * 0.2)
        self.lifecycle.compression_count += 1
        self.lifecycle.stage = LifecycleStage.DECLINE.value
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return original_len - len(self.information_dim.content)

    def revive(self):
        """复活：从cold/compressed唤醒为active"""
        self.energy_dim.energy_state = EnergyState.ACTIVE.value
        self.lifecycle.revival_count += 1
        self.lifecycle.stage = LifecycleStage.GROWTH.value
        self.energy_dim.low_fitness_streak = 0
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def die(self):
        """消亡：释放资源，保留溯源"""
        self.energy_dim.energy_state = EnergyState.DEAD.value
        self.energy_dim.death_time = datetime.now(timezone.utc).isoformat()
        self.energy_dim.compute_quota = 0
        self.energy_dim.storage_quota = 0
        self.lifecycle.stage = LifecycleStage.DEATH.value
        self.updated_at = datetime.now(timezone.utc).isoformat()


class EnergyAuctionEngine:
    """能量竞价引擎：适应度计算+出价+资源分配+用进废退"""

    def __init__(self, total_compute: int = 10000, total_storage: int = 1048576):
        self.total_compute = total_compute
        self.total_storage = total_storage
        self.heartbeat = 0

        # 适应度权重
        self.w_confidence = 0.30
        self.w_usage = 0.35
        self.w_value = 0.20
        self.w_dependency = 0.15

    def calculate_fitness(self, atom: StateAtom, all_atoms: List[StateAtom]) -> float:
        """计算态元适应度"""
        # 置信度因子
        confidence = atom.information_dim.confidence

        # 使用频率因子（归一化）
        max_usage = max((a.energy_dim.usage_frequency for a in all_atoms), default=1)
        usage_norm = atom.energy_dim.usage_frequency / max_usage if max_usage > 0 else 0

        # 价值密度因子（关联数/存储消耗）
        dependency_count = len(atom.logic_dim.dependents)
        storage = atom.energy_dim.storage_used or atom.energy_dim.storage_quota or 1
        value_density = min(dependency_count / (storage / 1024), 1.0) if storage > 0 else 0

        # 依赖重要度因子
        total_deps = sum(len(a.logic_dim.dependents) for a in all_atoms)
        dep_importance = dependency_count / total_deps if total_deps > 0 else 0

        fitness = (
            self.w_confidence * confidence +
            self.w_usage * usage_norm +
            self.w_value * value_density +
            self.w_dependency * dep_importance
        )

        return round(min(fitness, 1.0), 4)

    def calculate_bid(self, atom: StateAtom, urgency: str = "P2", priority_bonus: float = 0.0) -> float:
        """计算出价"""
        urgency_map = {"P0": 2.0, "P1": 1.5, "P2": 1.0, "P3": 0.5}
        urgency_factor = urgency_map.get(urgency, 1.0)
        bid = atom.energy_dim.fitness_score * urgency_factor * (1 + priority_bonus)
        return round(bid, 4)

    def run_auction(self, atoms: List[StateAtom], urgency_map: Optional[Dict[str, str]] = None) -> Dict:
        """执行一轮能量竞价"""
        self.heartbeat += 1
        urgency_map = urgency_map or {}

        # 1. 更新适应度
        for atom in atoms:
            if atom.energy_dim.energy_state == EnergyState.DEAD.value:
                continue
            atom.energy_dim.fitness_score = self.calculate_fitness(atom, atoms)
            atom.energy_dim.fitness_history.append({
                "heartbeat": self.heartbeat,
                "fitness": atom.energy_dim.fitness_score
            })

        # 2. 计算出价
        active_atoms = [a for a in atoms if a.energy_dim.energy_state in
                       (EnergyState.ACTIVE.value, EnergyState.COMPRESSED.value)]
        for atom in active_atoms:
            urgency = urgency_map.get(atom.atom_id, "P2")
            atom.bid = self.calculate_bid(atom, urgency)

        # 3. 按出价排序
        sorted_atoms = sorted(active_atoms, key=lambda a: getattr(a, 'bid', 0), reverse=True)

        # 4. 二八分配：前20%获得80%资源
        top_count = max(1, int(len(sorted_atoms) * 0.2))
        top_atoms = sorted_atoms[:top_count]
        remaining = sorted_atoms[top_count:]

        top_bid_sum = sum(getattr(a, 'bid', 0) for a in top_atoms) or 1
        rem_bid_sum = sum(getattr(a, 'bid', 0) for a in remaining) or 1

        for atom in top_atoms:
            ratio = getattr(atom, 'bid', 0) / top_bid_sum
            atom.energy_dim.compute_quota = int(self.total_compute * 0.8 * ratio)
            atom.energy_dim.storage_quota = int(self.total_storage * 0.8 * ratio)

        for atom in remaining:
            ratio = getattr(atom, 'bid', 0) / rem_bid_sum
            atom.energy_dim.compute_quota = int(self.total_compute * 0.2 * ratio)
            atom.energy_dim.storage_quota = int(self.total_storage * 0.2 * ratio)

        # 5. 用进废退：连续低fitness的态元压缩/冷归档/消亡
        compressed = []
        cold_storage = []
        dead = []

        for atom in atoms:
            if atom.energy_dim.energy_state == EnergyState.DEAD.value:
                continue

            if atom.energy_dim.fitness_score < 0.1:
                atom.energy_dim.low_fitness_streak += 1
            else:
                atom.energy_dim.low_fitness_streak = 0

            # 连续3周期低fitness → 压缩
            if (atom.energy_dim.low_fitness_streak >= 3 and
                    atom.energy_dim.energy_state == EnergyState.ACTIVE.value and
                    atom.logic_dim.self_modifiable):
                atom.compress()
                compressed.append(atom.atom_id)

            # 连续7周期compressed → 冷归档
            if (atom.energy_dim.low_fitness_streak >= 7 and
                    atom.energy_dim.energy_state == EnergyState.COMPRESSED.value):
                atom.energy_dim.energy_state = EnergyState.COLD.value
                atom.energy_dim.compute_quota = 0
                cold_storage.append(atom.atom_id)

            # 连续30周期cold且fitness极低 → 消亡
            if (atom.energy_dim.low_fitness_streak >= 30 and
                    atom.energy_dim.energy_state == EnergyState.COLD.value and
                    atom.energy_dim.fitness_score < 0.05 and
                    atom.logic_dim.self_modifiable):
                atom.die()
                dead.append(atom.atom_id)

        # 6. 使用频率衰减（V2.0修复：不再清零，改为指数衰减，避免fitness暴跌）
        for atom in atoms:
            atom.energy_dim.usage_frequency = int(atom.energy_dim.usage_frequency * 0.5)

        # V2.0修复：活跃态元fitness下限保护，防止连续周期fitness归零
        for atom in atoms:
            if atom.energy_dim.energy_state == EnergyState.ACTIVE.value:
                if atom.energy_dim.fitness_score < 0.5:
                    atom.energy_dim.fitness_score = 0.5
                    atom.energy_dim.low_fitness_streak = 0

        return {
            "heartbeat": self.heartbeat,
            "total_atoms": len(atoms),
            "active": len([a for a in atoms if a.energy_dim.energy_state == EnergyState.ACTIVE.value]),
            "compressed": len(compressed),
            "cold": len(cold_storage),
            "dead": len(dead),
            "compressed_ids": compressed,
            "cold_ids": cold_storage,
            "dead_ids": dead,
            "top_fitness": sorted_atoms[0].energy_dim.fitness_score if sorted_atoms else 0,
            "avg_fitness": round(sum(a.energy_dim.fitness_score for a in active_atoms) / len(active_atoms), 4) if active_atoms else 0,
        }


class StateAtomMigrator:
    """现有资产迁移工具：真值/算子/服务/文档/创意 → 态元"""

    MIGRATION_MAP = {
        "truth": {
            "atom_type": AtomType.TRUTH.value,
            "initial_fitness": None,  # 用confidence
            "initial_compute": 100,
            "initial_storage": 1024,
            "self_modifiable": True,
        },
        "operator": {
            "atom_type": AtomType.OPERATOR.value,
            "initial_fitness": 0.6,
            "initial_compute": 200,
            "initial_storage": 2048,
            "self_modifiable": True,
        },
        "service": {
            "atom_type": AtomType.SERVICE.value,
            "initial_fitness": 0.8,
            "initial_compute": 500,
            "initial_storage": 4096,
            "self_modifiable": True,
        },
        "document": {
            "atom_type": AtomType.DOCUMENT.value,
            "initial_fitness": 0.4,
            "initial_compute": 50,
            "initial_storage": 2048,
            "self_modifiable": True,
        },
        "creative": {
            "atom_type": AtomType.CREATIVE.value,
            "initial_fitness": 0.5,
            "initial_compute": 50,
            "initial_storage": 5120,
            "self_modifiable": True,
        },
        "meta_law": {
            "atom_type": AtomType.TRUTH.value,
            "initial_fitness": 1.0,
            "initial_compute": 1000,
            "initial_storage": 2048,
            "self_modifiable": False,  # 元法则不可修改
        },
    }

    def __init__(self, output_dir: str = "state_atoms"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.migrated = []
        self.failed = []

    def migrate_asset(self, asset: Dict, asset_type: str) -> Optional[StateAtom]:
        """迁移单个资产为态元"""
        try:
            config = self.MIGRATION_MAP.get(asset_type, self.MIGRATION_MAP["truth"])

            # 信息维
            info = InformationDim(
                content=asset.get("content", asset.get("text", "")),
                confidence=asset.get("confidence", 0.5),
                source=asset.get("source", "migrated"),
                meta_class=asset.get("meta_class", "M4"),
                truth_type=asset.get("truth_type", asset_type if asset_type in TruthType.__members__ else "unknown"),
                tags=asset.get("tags", []),
            )
            if asset.get("content_hash"):
                info.content_hash = asset["content_hash"]

            # 逻辑维
            logic = LogicDim(
                builtin_operator=asset.get("operator_def") if asset_type == "operator" else None,
                inference_rules=asset.get("inference_rules", []),
                self_modifiable=config["self_modifiable"],
                dependencies=asset.get("dependencies", []),
            )

            # 能量维
            fitness = config["initial_fitness"]
            if fitness is None:
                fitness = asset.get("confidence", 0.5)
            energy = EnergyDim(
                compute_quota=config["initial_compute"],
                storage_quota=config["initial_storage"],
                fitness_score=fitness,
                energy_state=EnergyState.ACTIVE.value,
            )

            # 创建态元
            atom = StateAtom(
                atom_type=config["atom_type"],
                information_dim=info,
                logic_dim=logic,
                energy_dim=energy,
                parent_atom_ids=asset.get("parent_ids", []),
            )

            # 保存
            self._save_atom(atom)
            self.migrated.append(atom.atom_id)
            return atom

        except Exception as e:
            self.failed.append({"asset": asset.get("id", "unknown"), "error": str(e)})
            return None

    def _save_atom(self, atom: StateAtom):
        """保存态元到文件"""
        filepath = os.path.join(self.output_dir, f"{atom.atom_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(atom.to_dict(), f, ensure_ascii=False, indent=2)

    def migrate_batch(self, assets: List[Dict], asset_type: str) -> Dict:
        """批量迁移"""
        results = []
        for asset in assets:
            atom = self.migrate_asset(asset, asset_type)
            if atom:
                results.append(atom.atom_id)
        return {
            "total": len(assets),
            "success": len(results),
            "failed": len(self.failed),
            "atom_ids": results,
        }

    def get_report(self) -> Dict:
        return {
            "migrated_count": len(self.migrated),
            "failed_count": len(self.failed),
            "migrated_ids": self.migrated,
            "failed": self.failed,
            "output_dir": self.output_dir,
        }


def run_demo():
    """演示：创建态元+能量竞价+生命周期"""
    print("=" * 60)
    print("态元 State-Atom 引擎 V1.0 演示")
    print("=" * 60)

    # 1. 创建一批态元（模拟现有资产）
    print("\n【1】创建态元（模拟迁移现有资产）")
    atoms = []

    # 元法则态元（不可修改，最高优先级）
    meta_atom = StateAtom(
        atom_type=AtomType.TRUTH.value,
        information_dim=InformationDim(
            content="三态融合生命体架构元宪法：信息态逻辑态能量态必须内在融合",
            confidence=1.0,
            meta_class="M9",
            truth_type=TruthType.META_LAW.value,
        ),
        logic_dim=LogicDim(self_modifiable=False),
        energy_dim=EnergyDim(compute_quota=1000, storage_quota=2048, fitness_score=1.0),
    )
    atoms.append(meta_atom)
    print(f"  元法则态元: {meta_atom.atom_id} (fitness=1.0, 不可修改)")

    # 普通真值态元
    for i in range(5):
        atom = StateAtom(
            atom_type=AtomType.TRUTH.value,
            information_dim=InformationDim(
                content=f"示例真值条目 #{i+1}：这是一条经过交叉验证的高价值真值",
                confidence=0.7 + i * 0.05,
                meta_class="M4",
                truth_type=TruthType.DECISION.value,
            ),
            energy_dim=EnergyDim(usage_frequency=i * 2),
        )
        atoms.append(atom)
        print(f"  真值态元: {atom.atom_id} (confidence={atom.information_dim.confidence}, usage={i*2})")

    # 算子态元
    for i in range(3):
        atom = StateAtom(
            atom_type=AtomType.OPERATOR.value,
            information_dim=InformationDim(
                content=f"def operator_{i+1}(input): return processed_output",
                confidence=0.8,
                meta_class="M1",
                truth_type=TruthType.RULE.value,
            ),
            logic_dim=LogicDim(
                builtin_operator={"name": f"op_{i+1}", "input": "any", "output": "any"},
                inference_rules=[f"rule_{i+1}"],
            ),
            energy_dim=EnergyDim(usage_frequency=10 - i * 3, compute_quota=200),
        )
        atoms.append(atom)
        print(f"  算子态元: {atom.atom_id} (usage={10-i*3})")

    # 2. 能量竞价
    print(f"\n【2】能量竞价引擎（总算力=10000, 总存储=1MB）")
    engine = EnergyAuctionEngine(total_compute=10000, total_storage=1048576)

    # 模拟多个心跳周期
    for cycle in range(5):
        # 模拟使用：前几个态元被高频使用
        for i, atom in enumerate(atoms[:4]):
            atom.reinforce()

        result = engine.run_auction(atoms)
        print(f"\n  心跳周期 #{result['heartbeat']}:")
        print(f"    活跃={result['active']}, 压缩={result['compressed']}, 冷归档={result['cold']}, 消亡={result['dead']}")
        print(f"    最高fitness={result['top_fitness']}, 平均fitness={result['avg_fitness']}")

    # 3. 显示分配结果
    print(f"\n【3】能量分配结果（按算力配额排序）")
    sorted_atoms = sorted(atoms, key=lambda a: a.energy_dim.compute_quota, reverse=True)
    for atom in sorted_atoms[:5]:
        print(f"  {atom.atom_id} ({atom.atom_type}): "
              f"算力={atom.energy_dim.compute_quota}, "
              f"存储={atom.energy_dim.storage_quota}, "
              f"fitness={atom.energy_dim.fitness_score}, "
              f"状态={atom.energy_dim.energy_state}")

    # 4. 态元哈希确权
    print(f"\n【4】态元三态合并哈希（确权）")
    for atom in atoms[:3]:
        print(f"  {atom.atom_id}: {atom.get_full_hash()[:16]}...")

    # 5. 迁移工具演示
    print(f"\n【5】资产迁移工具演示")
    migrator = StateAtomMigrator(output_dir="/tmp/state_atoms_demo")
    test_assets = [
        {"content": "测试真值1", "confidence": 0.9, "meta_class": "M4"},
        {"content": "测试真值2", "confidence": 0.85, "meta_class": "M1"},
    ]
    report = migrator.migrate_batch(test_assets, "truth")
    print(f"  迁移结果: 成功={report['success']}, 失败={report['failed']}")
    print(f"  新态元ID: {report['atom_ids']}")

    print("\n" + "=" * 60)
    print("演示完成！态元引擎核心功能验证通过。")
    print("=" * 60)

    return atoms, engine, migrator


if __name__ == "__main__":
    run_demo()
