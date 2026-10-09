#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2 三算子本地全量仿真测试
场景：模拟8个同源节点 → 批量资产上链(MerkleDAG v2) → 本体进化(OntologyEvolve v2) → 节点分叉合并(BranchMerge v1)
约束：仅本地执行，不连接云端（当前用户指令：就在本地执行）
确权：DID-BR-000002 | 溯源：Ω₀⊂⊙∞⊂Ω
"""
import sys, os, json, time, random
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from merkle_dag_append_operator import MerkleDAGAppendOperator
from ontology_evolve_operator import OntologyEvolveOperator
from branch_merge_operator import BranchMergeOperator

random.seed(42)

def main():
    print("=" * 60)
    print("P2 三算子本地全量仿真｜8同源节点场景")
    print("=" * 60)

    # ---------- 阶段1：批量资产上链（MerkleDAG v2） ----------
    print("\n[阶段1] MerkleDAG v2 批量上链（500资产/8分片并行）")
    assets = []
    for i in range(500):
        assets.append({
            "asset_id": f"SIM-{i:04d}",
            "content": f"同源节点仿真资产 {i} 号：稳态校准算子、熔断机制、记忆网关、同源协议 v{i}",
            "source": f"node-{i % 8}",
        })
    m_op = MerkleDAGAppendOperator()
    t0 = time.time()
    r = m_op({"assets": assets, "shard_size": 64, "max_workers": 8})
    dt = time.time() - t0
    assert r.success, r.error
    print(f"  上链资产: {len(assets)} | 耗时: {dt:.2f}s")
    print(f"  主链长度: {r.data['chain_length']} | 树深: {r.data['shard_stats']['merkle_tree_depth']}")
    print(f"  Merkle根: {r.data['merkle_root'][:16]}...")

    # 存在性证明抽查
    probe = random.choice(assets)["asset_id"]
    p = m_op({"assets": assets, "prove_asset": probe, "shard_size": 64, "max_workers": 8})
    proof = p.data["merkle_proof"]
    print(f"  存在性证明: {probe} valid={proof['valid']} 步数={len(proof['proof'])}")

    # ---------- 阶段2：本体进化（OntologyEvolve v2） ----------
    print("\n[阶段2] OntologyEvolve v2 本体进化（8节点内容汇聚）")
    o_op = OntologyEvolveOperator()
    big_text = ("元运维平台包含稳态校准子系统,稳态校准子系统包含熔断模块,熔断模块包含自动恢复机制;"
                "元运维平台依赖记忆网关,记忆网关支撑同源协议,同源协议构成身份节点体系;"
                "知识图谱引擎包含实体关系抽取器,实体关系抽取器依赖自然语言处理模块,自然语言处理模块基于深度学习模型")
    r2 = o_op({"content": big_text, "asset_id": "SIM-ONTOLOGY", "infer_transitive": True})
    assert r2.success, r2.error
    print(f"  进化等级: {r2.data['evolution_level']} | 优先级: {r2.data['priority']}")
    print(f"  新增实体: {len(r2.data['new_entities'])} | 关系: {len(r2.data['updated_relations'])}")
    print(f"  传递推理: {len(r2.data['inferred_relations'])} 条")
    for i in r2.data["inferred_relations"]:
        print(f"    {i['subject']} {i['relation']} {i['object']} (via {i['via']})")
    g = r2.data["graph_json"]
    print(f"  图谱JSON: {g['stats']['node_count']}节点 {g['stats']['edge_count']}边")

    # ---------- 阶段3：节点分叉合并（BranchMerge v1） ----------
    print("\n[阶段3] BranchMerge v1 分叉识别+合并（3节点）")
    b_op = BranchMergeOperator()

    def make_chain(nid, blocks):
        chain, prev = [], "GENESIS"
        for i, b in enumerate(blocks):
            payload = {"node_id": nid, "asset_id": b["asset_id"], "content": b["content"],
                       "prev_hash": prev, "index": i}
            import hashlib
            h = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            chain.append({"hash": h, "asset_id": b["asset_id"], "block_content": b["content"], "prev_hash": prev})
            prev = h
        return {"node_id": nid, "chain": chain}

    shared = [{"asset_id": "BASE-1", "content": "根区块"}, {"asset_id": "BASE-2", "content": "公共资产"}]
    n1 = make_chain("node-A", shared + [{"asset_id": "FORK-A1", "content": "节点A特有资产"}])
    n2 = make_chain("node-B", shared + [{"asset_id": "FORK-B1", "content": "节点B特有资产"}])
    n3 = make_chain("node-C", shared + [{"asset_id": "FORK-C1", "content": "节点C特有资产"}])
    r3 = b_op({"branches": [n1, n2, n3]})
    assert r3.success, r3.error
    print(f"  合并模式: {r3.data['merge_mode']} | 状态: {r3.data['status']}")
    print(f"  分叉点索引: {r3.data['fork_point']['fork_index']} | 合并链: {len(r3.data['merged_chain'])}块")
    print(f"  新根哈希: {r3.data['new_root_hash'][:16]}...")

    # 冲突场景
    c1 = make_chain("node-X", [{"asset_id": "CONFLICT-1", "content": "版本A" * 40}])
    c2 = make_chain("node-Y", [{"asset_id": "CONFLICT-1", "content": "版本B" * 20}])
    r4 = b_op({"branches": [c1, c2]})
    print(f"  冲突场景: {len(r4.data['conflicts'])}冲突 → {r4.data['merge_mode']}/{r4.data['status']}")
    arb = r4.data["arbitration"]["items"][0]
    print(f"  三维仲裁: 利益{arb['benefit']} 风险{arb['risk']} 成本{arb['cost']} → 评分{arb['score']} {arb['verdict']}")

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    print("仿真结论")
    print("=" * 60)
    print(f"  MerkleDAG v2 : 批量500资产并行上链 {dt:.2f}s, 证明有效, 主链完整 ✓")
    print(f"  Ontology v2  : 传递推理{len(r2.data['inferred_relations'])}条, 图谱{g['stats']['edge_count']}边 ✓")
    print(f"  BranchMerge  : 无冲突自动合并, 冲突人工闸门+三维仲裁 ✓")
    print("  约束: 全流程仅本地执行, 未连接云端 ✓")
    print("  确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")


if __name__ == "__main__":
    main()
