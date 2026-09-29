#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分支合并算子 V1.0（Branch Merge Operator）
功能：多节点主链分叉识别 → 三维稳态仲裁 → 无冲突自动合并 / 有冲突人工闸门。
  1. 分叉识别：比对多节点主链快照，定位共同祖先/分叉点/差异资产清单
  2. 三维稳态仲裁：利益40% / 风险35% / 成本25% 加权评分，输出综合分与排序
  3. 合并策略：
     - 无冲突（不同资产区块/追加关系）：自动合并，生成合并链+新根哈希
     - 有冲突（同资产不同内容/同键不同值）：进入人工闸门，输出冲突清单与仲裁建议
确权：DID-BR-000002 | 溯源：Ω₀⊂⊙∞⊂Ω
"""
import hashlib
import json
import datetime
import os
import copy
from typing import Dict, Any, List, Optional

# ---- 双端兼容 ----
try:
    from core.base_operator import BaseOperator, OperatorResult, OperatorPriority
    from registry.operator_registry import register_operator
    _BASE = BaseOperator
    _DECORATOR = register_operator
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.base import BaseOperator, OperatorResult
    _BASE = BaseOperator
    _DECORATOR = lambda cls: cls


def _now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat()


def _sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


@_DECORATOR
class BranchMergeOperator(_BASE):
    """分支合并算子 V1（分叉识别+三维稳态仲裁+无冲突自动合并+人工闸门）"""

    # ---- 云端注册元数据 ----
    OPERATOR_ID = "branch-merge-v1"
    OPERATOR_NAME = "分支合并算子V1"
    OPERATOR_VERSION = "1.0.0"
    OPERATOR_GROUP = "archive"
    OPERATOR_DESCRIPTION = "多节点主链分叉识别+三维稳态仲裁(利益40/风险35/成本25)+无冲突自动合并+冲突人工闸门"
    PRIORITY = 80

    # ---- 本地注册元数据 ----
    name = "branch_merge"
    version = "1.0.0"
    description = OPERATOR_DESCRIPTION
    category = "archive"
    inputs_schema = {
        "branches": "list(必填,多节点主链快照[{node_id,chain:[blocks],meta:{}}])",
        "weights": "dict(可选,三维稳态权重,默认{benefit:0.40,risk:0.35,cost:0.25})",
        "auto_merge_conflict_free": "bool(可选,无冲突是否自动合并,默认True)",
        "human_gate": "bool(可选,冲突是否需人工闸门,默认True)",
    }
    outputs_schema = {
        "fork_point": "dict(共同祖先/分叉点)",
        "diff_assets": "list(差异资产)",
        "conflicts": "list(冲突清单)",
        "arbitration": "dict(三维稳态仲裁)",
        "merged_chain": "list(合并链)",
        "new_root_hash": "str",
        "merge_mode": "string(AUTO_MERGE/HUMAN_GATE)",
        "status": "string(MERGED/PENDING_REVIEW)",
    }

    # ---------- 1. 分叉识别 ----------
    def _find_fork(self, branches: List[Dict]) -> Dict:
        if not branches:
            return {"fork_block": None, "fork_index": 0, "nodes": 0}
        # 逐块比对共同前缀
        min_len = min(len(b.get("chain", [])) for b in branches)
        fork_index = 0
        fork_block = None
        for i in range(min_len):
            hashes = {b["chain"][i].get("hash") for b in branches if len(b.get("chain", [])) > i}
            if len(hashes) == 1:
                fork_index = i + 1
                fork_block = branches[0]["chain"][i]
            else:
                break
        return {"fork_block": fork_block, "fork_index": fork_index, "nodes": len(branches)}

    # ---------- 2. 差异资产与冲突检测 ----------
    def _collect_diffs(self, branches: List[Dict], fork_index: int) -> Dict:
        assets = {}   # asset_id -> {node_id: block}
        for b in branches:
            node_id = b.get("node_id", "unknown")
            for blk in b.get("chain", [])[fork_index:]:
                aid = blk.get("asset_id") or blk.get("block_id")
                if not aid:
                    continue
                assets.setdefault(aid, {})[node_id] = blk
        conflicts = []
        diffs = []
        for aid, holders in assets.items():
            contents = {n: h.get("block_content") or h.get("content") for n, h in holders.items()}
            unique = set(json.dumps(c, ensure_ascii=False, sort_keys=True) if not isinstance(c, str) else c for c in contents.values())
            if len(unique) > 1:
                conflicts.append({
                    "asset_id": aid,
                    "nodes": list(holders.keys()),
                    "contents": contents,
                    "type": "content_conflict",
                })
            else:
                diffs.append({"asset_id": aid, "nodes": list(holders.keys()), "type": "no_conflict"})
        return {"diffs": diffs, "conflicts": conflicts}

    # ---------- 3. 三维稳态仲裁 ----------
    def _arbitrate(self, conflicts: List[Dict], weights: Dict) -> Dict:
        w_b, w_r, w_c = weights.get("benefit", 0.40), weights.get("risk", 0.35), weights.get("cost", 0.25)
        items = []
        for c in conflicts:
            # 简化评分：内容长度信息量→利益；节点分歧度→风险；节点数→成本
            contents = list(c["contents"].values())
            total_len = sum(len(json.dumps(x, ensure_ascii=False)) if not isinstance(x, str) else len(x) for x in contents)
            benefit = min(100, 20 + total_len * 0.5)
            risk = min(100, 20 + (len(c["nodes"]) - 1) * 25 + len(contents))
            cost = min(100, 10 + len(c["nodes"]) * 15)
            score = w_b * benefit - w_r * risk - w_c * cost
            items.append({
                "asset_id": c["asset_id"],
                "benefit": round(benefit, 1), "risk": round(risk, 1), "cost": round(cost, 1),
                "score": round(score, 1),
                "verdict": "merge_recommended" if score >= 0 else "conflict_hold",
                "weights": {"benefit": w_b, "risk": w_r, "cost": w_c},
            })
        items.sort(key=lambda x: x["score"], reverse=True)
        return {"items": items, "formula": "score = 0.40*benefit - 0.35*risk - 0.25*cost"}

    # ---------- 4. 合并 ----------
    def _merge(self, branches: List[Dict], fork_index: int, diffs: List[Dict], conflicts: List[Dict], auto_merge: bool) -> Dict:
        if conflicts and not auto_merge:
            return {"mode": "HUMAN_GATE", "status": "PENDING_REVIEW", "chain": None, "root": None}
        # 无冲突：拼接共同前缀 + 各分支差异块（按 node 顺序去重）
        base_chain = []
        if branches:
            base_chain = list(branches[0].get("chain", [])[:fork_index])
        merged_chain = list(base_chain)
        seen_hashes = {b.get("hash") for b in merged_chain}
        for b in branches:
            for blk in b.get("chain", [])[fork_index:]:
                h = blk.get("hash")
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    merged_chain.append(blk)
        # 计算新根哈希
        root_hash = None
        if merged_chain:
            last = merged_chain[-1]
            root_hash = last.get("hash") or _sha256(last)
        return {"mode": "AUTO_MERGE", "status": "MERGED", "chain": merged_chain, "root": root_hash}

    def execute(self, inputs: Dict) -> OperatorResult:
        try:
            branches = inputs.get("branches", [])
            if not branches or len(branches) < 2:
                return OperatorResult(False, error="branches 至少需要2个节点主链快照")
            weights = inputs.get("weights") or {"benefit": 0.40, "risk": 0.35, "cost": 0.25}
            auto_merge = inputs.get("auto_merge_conflict_free", True)
            human_gate = inputs.get("human_gate", True)

            # 1. 分叉识别
            fork = self._find_fork(branches)
            # 2. 差异与冲突
            collected = self._collect_diffs(branches, fork["fork_index"])
            # 3. 仲裁（有冲突才需要）
            arbitration = {"items": [], "formula": "score = 0.40*benefit - 0.35*risk - 0.25*cost"}
            if collected["conflicts"]:
                arbitration = self._arbitrate(collected["conflicts"], weights)
            # 4. 合并
            merge = self._merge(branches, fork["fork_index"], collected["diffs"],
                                collected["conflicts"], auto_merge and not (collected["conflicts"] and human_gate))

            return OperatorResult(True, data={
                "fork_point": fork,
                "diff_assets": collected["diffs"],
                "conflicts": collected["conflicts"],
                "arbitration": arbitration,
                "merged_chain": merge.get("chain"),
                "new_root_hash": merge.get("root"),
                "merge_mode": merge.get("mode"),
                "status": merge.get("status"),
                "node_count": len(branches),
                "did": "DID-BR-000002",
                "trace": "Ω₀⊂⊙∞⊂Ω",
            })
        except Exception as e:
            return OperatorResult(False, error=str(e))


def _make_chain(node_id: str, blocks: List[Dict]) -> Dict:
    chain = []
    prev = "GENESIS"
    for i, b in enumerate(blocks):
        payload = {"node_id": node_id, "asset_id": b.get("asset_id"), "content": b.get("content"),
                   "prev_hash": prev, "index": i}
        h = _sha256(payload)
        chain.append({"hash": h, "asset_id": b.get("asset_id"), "block_content": b.get("content"), "prev_hash": prev})
        prev = h
    return {"node_id": node_id, "chain": chain}


if __name__ == "__main__":
    op = BranchMergeOperator()

    # 场景A：无冲突自动合并（共享前缀 + 各自独有区块）
    shared = [{"asset_id": "A1", "content": "根资产"}, {"asset_id": "A2", "content": "公共资产"}]
    b1 = _make_chain("node-1", shared + [{"asset_id": "B1", "content": "节点1独有"}])
    b2 = _make_chain("node-2", shared + [{"asset_id": "B2", "content": "节点2独有"}])
    r = op({"branches": [b1, b2]})
    print("=== 场景A：无冲突 ===")
    print("合并模式:", r.data["merge_mode"], "| 状态:", r.data["status"])
    print("分叉点:", r.data["fork_point"]["fork_block"]["asset_id"] if r.data["fork_point"]["fork_block"] else None,
          "@index", r.data["fork_point"]["fork_index"])
    print("合并链长度:", len(r.data["merged_chain"]), "| 新根哈希:", (r.data["new_root_hash"] or "")[:16], "...")

    # 场景B：有冲突 → 人工闸门 + 三维仲裁
    c1 = _make_chain("node-1", [{"asset_id": "X1", "content": "版本甲内容" * 20}])
    c2 = _make_chain("node-2", [{"asset_id": "X1", "content": "版本乙内容" * 10}])
    r2 = op({"branches": [c1, c2]})
    print("\n=== 场景B：同资产内容冲突 ===")
    print("冲突数:", len(r2.data["conflicts"]))
    print("仲裁评分:", r2.data["arbitration"]["items"][0]["score"],
          "| 结论:", r2.data["arbitration"]["items"][0]["verdict"])
    print("合并模式:", r2.data["merge_mode"], "| 状态:", r2.data["status"], "(等待人工闸门)")

    # 场景C：冲突但关闭人工闸门 → 自动合并
    r3 = op({"branches": [c1, c2], "human_gate": False})
    print("\n=== 场景C：冲突+关闭闸门 ===")
    print("合并模式:", r3.data["merge_mode"], "| 状态:", r3.data["status"])

    # 校验：无冲突场景A 合并链必须包含全部3个独有资产
    assets = {b.get("asset_id") for b in r.data["merged_chain"]}
    assert {"A1", "A2", "B1", "B2"} <= assets, "合并链资产缺失!"
    print("\n✅ 合并链资产完整性校验通过:", sorted(assets))
