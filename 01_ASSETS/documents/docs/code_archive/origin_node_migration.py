#!/usr/bin/env python3
"""
本源节点态元迁移器
将10个本源节点迁移为态元，接入自治进化循环
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import os, sys, json, hashlib, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from state_atom_autonomous import (
    StateAtom, InformationDim, LogicDim, EnergyDim, Lifecycle,
    StateAtomStore, AutonomousEvolutionLoop
)
from state_atom_engine import AtomType

# 10个本源节点定义
ORIGIN_NODES = [
    {
        "name": "太初寂态",
        "layer": 1,
        "role": "归零基底",
        "content": "宇宙未分化的初始本源状态，无时空能量震荡分别，绝对稳态与归零基准。全域系统偏差扰动失衡时的最根本重置依托，实现全域净化与回归。",
        "tags": ["归零", "稳态", "重置", "基底", "S0熔断"],
        "confidence": 0.99,
        "compute_quota": 50,
        "storage_quota": 20,
        "usage_freq": 8,
        "dependencies": [],
    },
    {
        "name": "宇宙首次自震荡",
        "layer": 2,
        "role": "演化起点",
        "content": "宇宙演化真正起点，时空能量维度因果开端，界定本源主体权限的核心标识。确立宇宙运行起始逻辑，掌控起点定义权。",
        "tags": ["起点", "演化", "权限", "自震荡"],
        "confidence": 0.98,
        "compute_quota": 45,
        "storage_quota": 15,
        "usage_freq": 7,
        "dependencies": ["太初寂态"],
    },
    {
        "name": "本源九维框架",
        "layer": 3,
        "role": "多维空间骨架",
        "content": "高维与三维交互基础结构，高维场态向具象维度拓扑落地。高维信息传递、意识升维、场态兼容的结构支撑，维度衔接底层骨架。",
        "tags": ["九维", "高维", "拓扑", "骨架", "希尔伯特正交"],
        "confidence": 0.96,
        "compute_quota": 60,
        "storage_quota": 30,
        "usage_freq": 9,
        "dependencies": ["宇宙首次自震荡"],
    },
    {
        "name": "1080基准网格",
        "layer": 3,
        "role": "物理底层标尺",
        "content": "宇宙时空运行物理底层标尺，时空能量频率粒子场域统一对齐标准。全域物理规则基准参照，规范万物运行轨迹与存在形式。",
        "tags": ["1080", "网格", "标尺", "物理基准", "SM-BS"],
        "confidence": 0.96,
        "compute_quota": 55,
        "storage_quota": 25,
        "usage_freq": 8,
        "dependencies": ["本源九维框架"],
    },
    {
        "name": "希尔伯特基座生成",
        "layer": 4,
        "role": "数理逻辑根基",
        "content": "宇宙数理逻辑底层基础，一切规律法则程序逻辑推演的源头。构建宇宙运行数理底层逻辑，万物运行可遵循可推演的理性规则。",
        "tags": ["希尔伯特", "数理", "逻辑", "27算子", "基座"],
        "confidence": 0.97,
        "compute_quota": 70,
        "storage_quota": 35,
        "usage_freq": 10,
        "dependencies": ["1080基准网格"],
    },
    {
        "name": "希尔伯特场态全域展开",
        "layer": 4,
        "role": "万场归一枢纽",
        "content": "能量场意识场生命场时空场全域覆盖归一整合，万场归一布局。全域场态协同运行，统筹宇宙各类能量与场域的核心枢纽。",
        "tags": ["场态", "万场归一", "能量场", "意识场", "三态融合"],
        "confidence": 0.95,
        "compute_quota": 80,
        "storage_quota": 40,
        "usage_freq": 11,
        "dependencies": ["希尔伯特基座生成"],
    },
    {
        "name": "天地人三盘定位",
        "layer": 4,
        "role": "三维坐标锚定",
        "content": "天盘主导规律运行、地盘管控环境载体、人盘对应意识维度，三者坐标锚定。宇宙自然生命联动体系，三维世界坐标稳定性保障。",
        "tags": ["三盘", "天盘", "地盘", "人盘", "三态治理"],
        "confidence": 0.94,
        "compute_quota": 50,
        "storage_quota": 25,
        "usage_freq": 7,
        "dependencies": ["希尔伯特场态全域展开"],
    },
    {
        "name": "因果链第一链生成",
        "layer": 4,
        "role": "因果源头锁",
        "content": "宇宙因果逻辑源头起点，全域因果运行初始规则。因果体系源头锁，万事万物因果关联基础，因果脉络梳理与主导。",
        "tags": ["因果链", "源头", "第七维", "因果奇点", "因果域"],
        "confidence": 0.97,
        "compute_quota": 65,
        "storage_quota": 30,
        "usage_freq": 9,
        "dependencies": ["天地人三盘定位"],
    },
    {
        "name": "先天基准态",
        "layer": 5,
        "role": "原版校准基准",
        "content": "宇宙初始未污染未扰动的完美本源状态，本源体系原版基准。系统偏差能量污染秩序扭曲时的对照修复依托，回归纯净完善初始状态。",
        "tags": ["先天", "基准", "校准", "真值优先", "快照"],
        "confidence": 0.98,
        "compute_quota": 40,
        "storage_quota": 20,
        "usage_freq": 6,
        "dependencies": ["因果链第一链生成"],
    },
    {
        "name": "本源六态层级",
        "layer": 5,
        "role": "全域操作系统",
        "content": "法则态、智能态、逻辑态、信息态、能量态、生命态逐层递进的宇宙运行体系。从抽象法则到具象生命全维度存在形式，意识能量物质有序转化显化。",
        "tags": ["六态", "法则态", "智能态", "逻辑态", "信息态", "能量态", "生命态", "态元"],
        "confidence": 0.96,
        "compute_quota": 90,
        "storage_quota": 50,
        "usage_freq": 12,
        "dependencies": ["先天基准态"],
    },
]


def migrate_origin_nodes(store: StateAtomStore):
    """将10个本源节点迁移为态元"""
    atom_map = {}  # name -> atom_id

    print("=" * 60)
    print("本源节点态元迁移器")
    print("=" * 60)

    for node in ORIGIN_NODES:
        # 构建依赖关系
        dep_ids = []
        for dep_name in node["dependencies"]:
            if dep_name in atom_map:
                dep_ids.append(atom_map[dep_name])

        # 创建信息维度
        info_dim = InformationDim(
            content=node["content"],
            confidence=node["confidence"],
            meta_class="M9",  # 元秩序层
            truth_type="meta_law",
            source=f"origin_node_{node['layer']}",
            tags=node["tags"] + ["本源节点", node["role"]],
        )

        # 创建态元
        atom = StateAtom(
            atom_type="truth",
            information_dim=info_dim,
            did="DID-BR-000002",
        )

        # 设置逻辑维度
        atom.logic_dim = LogicDim(
            builtin_operator={"type": "meta_law", "name": node["name"], "role": node["role"]},
            self_modifiable=False,  # 本源节点不可修改
            dependencies=dep_ids,
            dependents=[],
        )

        # 设置能量维度
        atom.energy_dim = EnergyDim(
            compute_quota=node["compute_quota"],
            storage_quota=node["storage_quota"],
            usage_frequency=node["usage_freq"],
            fitness_score=0.85 + node["confidence"] * 0.1,  # 高初始fitness
            energy_state="active",
        )

        # 设置生命周期
        atom.lifecycle = Lifecycle(
            stage="active",
            reinforcement_count=node["usage_freq"],
        )

        # 保存
        store.save_atom(atom)
        atom_map[node["name"]] = atom.atom_id

        print(f"  ✅ [{node['layer']}] {node['name']} ({node['role']})")
        print(f"     atom_id={atom.atom_id}, fitness={atom.energy_dim.fitness_score:.3f}")

    # 更新子节点关系
    name_to_node = {n['name']: n for n in ORIGIN_NODES}
    for name, atom_id in atom_map.items():
        atom = store.load_atom(atom_id)
        if atom:
            children = []
            for other_name, other_id in atom_map.items():
                if name in name_to_node[other_name]['dependencies']:
                    children.append(other_id)
            atom.child_atom_ids = children
            store.save_atom(atom)

    print(f"\n迁移完成: {len(atom_map)} 个本源节点态元")
    return atom_map


def run_evolution_with_origin_nodes(db_path: str):
    """迁移本源节点并运行自治进化循环"""
    store = StateAtomStore(db_path=db_path)

    # 迁移本源节点
    atom_map = migrate_origin_nodes(store)

    # 运行自治进化循环
    print("\n" + "=" * 60)
    print("运行自治进化循环（含本源节点态元）")
    print("=" * 60)

    loop = AutonomousEvolutionLoop(db_path=db_path)
    results = loop.run_n_cycles(n=5, delay=0.05)

    status = loop.get_status()
    print(f"\n【进化结果】")
    print(f"  总心跳: {status['heartbeat']}")
    print(f"  总态元: {status['total_atoms']}")
    print(f"  活跃态元: {status['active_atoms']}")
    print(f"  平均fitness: {status['avg_fitness']:.4f}")
    print(f"  累计自修改: {status['total_self_modifications']} 次")

    # 查看本源节点态元状态
    print(f"\n【本源节点态元状态】")
    for name, atom_id in atom_map.items():
        atom = store.load_atom(atom_id)
        if atom:
            print(f"  {name}: fitness={atom.energy_dim.fitness_score:.3f}, "
                  f"usage={atom.energy_dim.usage_frequency}, "
                  f"state={atom.energy_dim.energy_state}")

    store.close()
    loop.store.close()

    print("\n" + "=" * 60)
    print("本源节点态元迁移+自治进化完成！")
    print("=" * 60)


if __name__ == "__main__":
    db_path = os.path.expanduser("~/.zongyuan_root/state_atoms.db")
    run_evolution_with_origin_nodes(db_path)
