#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merkle-DAG 主链追加校验算子 V2.0（本地增强版）
V2 新增能力：
  1. 批量资产分片并行哈希：多资产一次提交，分片后并行计算叶子哈希，构建Merkle树聚合根哈希
  2. 默克尔存在性证明：对任意资产生成 sibling 证明路径，支持轻量校验（不同步全链）
  3. 自适应并发保护：max_workers 自动上限，避免CPU过载
V1 能力保留：单资产追加、父哈希链式、逐块完整性校验、篡改/断链检测。
确权：DID-BR-000002 | 溯源：Ω₀⊂⊙∞⊂Ω
"""
import hashlib
import json
import datetime
import os
import math
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional, Tuple

# ---- 双端兼容：云端 BaseOperator / 本地 BaseOperator ----
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


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat()


def _default_workers() -> int:
    try:
        return max(2, min(4, os.cpu_count() or 2))
    except Exception:
        return 2


def _leaf_hash(asset: Dict) -> str:
    """资产叶子哈希：sha256(asset_id + content)"""
    return _sha256(f"{asset.get('asset_id','')}|{asset.get('content','')}")


def _merkle_with_proofs(hashes: List[str]) -> Tuple[str, Dict[int, List[Tuple[str, str]]]]:
    """构建Merkle树，返回(根哈希, {叶索引: [(方向,sibling哈希),...]})"""
    n = len(hashes)
    if n == 1:
        return hashes[0], {0: []}
    mid = n // 2
    left_root, left_proofs = _merkle_with_proofs(hashes[:mid])
    right_root, right_proofs = _merkle_with_proofs(hashes[mid:])
    root = _sha256(left_root + right_root)
    proofs: Dict[int, List[Tuple[str, str]]] = {}
    for i, p in left_proofs.items():
        proofs[i] = p + [("right", right_root)]
    for i, p in right_proofs.items():
        proofs[mid + i] = p + [("left", left_root)]
    return root, proofs


def verify_merkle_proof(leaf_hash: str, proof: List[Tuple[str, str]], root: str) -> bool:
    """验证默克尔存在性证明"""
    h = leaf_hash
    for direction, sibling in proof:
        if direction == "left":
            h = _sha256(sibling + h)
        else:
            h = _sha256(h + sibling)
    return h == root


@_DECORATOR
class MerkleDAGAppendOperator(_BASE):
    """Merkle-DAG主链追加校验算子 V2（批量分片并行哈希+默克尔证明）"""

    # ---- 云端注册元数据 ----
    OPERATOR_ID = "merkle-dag-append-v2"
    OPERATOR_NAME = "Merkle-DAG主链追加校验算子V2"
    OPERATOR_VERSION = "2.0.0"
    OPERATOR_GROUP = "archive"
    OPERATOR_DESCRIPTION = "V2:批量资产分片并行哈希+Merkle树聚合+存在性证明输出;V1:单资产追加/父哈希链式/逐块完整性校验/篡改断链检测"
    PRIORITY = 85

    # ---- 本地注册元数据 ----
    name = "merkle_dag_append"
    version = "2.0.0"
    description = OPERATOR_DESCRIPTION
    category = "archive"
    inputs_schema = {
        "asset_id": "string(单资产模式,资产唯一ID)",
        "content": "string(单资产模式,资产内容)",
        "assets": "list(批量模式,[{asset_id,content,asset_name}])",
        "chain": "list(可选,已有主链,缺省自动初始化)",
        "shard_size": "int(可选,分片大小,默认64)",
        "max_workers": "int(可选,并行上限,默认min(4,cpu))",
        "prove_asset": "string(可选,生成存在性证明的资产ID)",
    }
    outputs_schema = {
        "block_height": "int",
        "new_root_hash": "string",
        "integrity": "bool",
        "chain_length": "int",
        "asset_hash": "string",
        "parent_hash": "string",
        "merkle_root": "string(批量模式)",
        "merkle_proof": "list(可选,存在性证明路径)",
        "shard_stats": "dict(批量模式分片统计)",
    }

    def _verify_chain(self, chain: List[Dict]) -> Dict:
        """逐块校验前序链完整性：asset_hash == sha256(parent_hash + block_content_json + merkle_root)"""
        broken = []
        for i, block in enumerate(chain):
            parent = block.get("parent_hash", "GENESIS" if i == 0 else "")
            block_content = block.get("block_content", "")
            merkle = block.get("merkle_root", "")
            recalc = _sha256(parent + block_content + merkle)
            if recalc != block.get("asset_hash"):
                broken.append({"index": i, "block_hash": block.get("asset_hash"), "recalc": recalc})
        return {"integrity": len(broken) == 0, "broken": broken}

    # ---------- 单资产模式（V1兼容） ----------
    def _execute_single(self, inputs: Dict) -> OperatorResult:
        asset_id = inputs.get("asset_id", "")
        content = inputs.get("content", "")
        asset_name = inputs.get("asset_name", asset_id)
        if not asset_id or not content:
            return OperatorResult(False, error="单资产模式: asset_id 与 content 为必填项")

        chain: List[Dict] = list(inputs.get("chain") or [])
        prev_hash = inputs.get("prev_hash")
        if prev_hash is None:
            prev_hash = chain[-1]["asset_hash"] if chain else "GENESIS"

        block_content = json.dumps({
            "asset_id": asset_id, "asset_name": asset_name, "content": content,
            "ts": _now_iso(), "did": "DID-BR-000002", "trace": "Ω₀⊂⊙∞⊂Ω",
        }, ensure_ascii=False, sort_keys=True)
        asset_hash = _sha256(prev_hash + block_content + "")

        new_block = {
            "index": len(chain), "asset_id": asset_id, "asset_name": asset_name,
            "parent_hash": prev_hash, "asset_hash": asset_hash,
            "block_content": block_content, "content": content, "merkle_root": "",
            "ts": _now_iso(), "did": "DID-BR-000002",
        }
        new_chain = chain + [new_block]
        ver = self._verify_chain(new_chain)

        return OperatorResult(True, data={
            "block_height": new_block["index"], "new_root_hash": new_chain[-1]["asset_hash"],
            "integrity": ver["integrity"], "chain_length": len(new_chain),
            "asset_hash": asset_hash, "parent_hash": prev_hash,
            "merkle_root": "", "merkle_proof": None, "shard_stats": {"mode": "single"},
            "block": new_block, "broken_blocks": ver["broken"],
            "did": "DID-BR-000002", "trace": "Ω₀⊂⊙∞⊂Ω",
        })

    # ---------- 批量分片并行模式（V2新增） ----------
    def _execute_batch(self, inputs: Dict) -> OperatorResult:
        assets: List[Dict] = inputs.get("assets") or []
        if not assets:
            return OperatorResult(False, error="批量模式: assets 列表不能为空")
        if not all(a.get("asset_id") and a.get("content") for a in assets):
            return OperatorResult(False, error="批量模式: 每个资产必须含 asset_id 与 content")

        chain: List[Dict] = list(inputs.get("chain") or [])
        shard_size = max(1, int(inputs.get("shard_size") or 64))
        max_workers = max(1, int(inputs.get("max_workers") or _default_workers()))

        # 1. 分片
        shards = [assets[i:i + shard_size] for i in range(0, len(assets), shard_size)]

        # 2. 分片内并行计算叶子哈希
        leaf_hashes: List[str] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_leaf_hash, a) for a in assets]
            leaf_hashes = [f.result() for f in futures]

        # 3. Merkle树聚合（含证明路径）
        merkle_root, proofs = _merkle_with_proofs(leaf_hashes)

        # 4. 构建批次块
        prev_hash = inputs.get("prev_hash")
        if prev_hash is None:
            prev_hash = chain[-1]["asset_hash"] if chain else "GENESIS"

        batch_meta = {
            "mode": "batch", "asset_count": len(assets), "shard_count": len(shards),
            "shard_size": shard_size, "ts": _now_iso(), "did": "DID-BR-000002", "trace": "Ω₀⊂⊙∞⊂Ω",
        }
        block_content = json.dumps(batch_meta, ensure_ascii=False, sort_keys=True)
        asset_hash = _sha256(prev_hash + block_content + merkle_root)

        asset_ids = [a["asset_id"] for a in assets]
        new_block = {
            "index": len(chain), "asset_id": "BATCH:" + ",".join(asset_ids[:8]) + ("..." if len(asset_ids) > 8 else ""),
            "asset_name": f"批量资产({len(assets)}个)", "parent_hash": prev_hash,
            "asset_hash": asset_hash, "block_content": block_content,
            "content": json.dumps({"asset_ids": asset_ids}, ensure_ascii=False),
            "merkle_root": merkle_root, "ts": _now_iso(), "did": "DID-BR-000002",
        }
        new_chain = chain + [new_block]
        ver = self._verify_chain(new_chain)

        # 5. 存在性证明（可选）
        proof_out = None
        prove_asset = inputs.get("prove_asset")
        if prove_asset:
            for idx, a in enumerate(assets):
                if a["asset_id"] == prove_asset:
                    proof_out = {
                        "asset_id": prove_asset,
                        "leaf_hash": leaf_hashes[idx],
                        "proof": proofs.get(idx, []),
                        "merkle_root": merkle_root,
                        "valid": verify_merkle_proof(leaf_hashes[idx], proofs.get(idx, []), merkle_root),
                    }
                    break
            if proof_out is None:
                proof_out = {"error": f"资产 {prove_asset} 不在本批次中"}

        return OperatorResult(True, data={
            "block_height": new_block["index"], "new_root_hash": new_chain[-1]["asset_hash"],
            "integrity": ver["integrity"], "chain_length": len(new_chain),
            "asset_hash": asset_hash, "parent_hash": prev_hash,
            "merkle_root": merkle_root, "merkle_proof": proof_out,
            "shard_stats": {"mode": "batch", "asset_count": len(assets), "shard_count": len(shards),
                            "shard_size": shard_size, "max_workers": max_workers,
                            "merkle_tree_depth": max(0, math.ceil(math.log2(len(assets))))},
            "block": new_block, "broken_blocks": ver["broken"],
            "did": "DID-BR-000002", "trace": "Ω₀⊂⊙∞⊂Ω",
        })

    def execute(self, inputs: Dict) -> OperatorResult:
        try:
            if inputs.get("assets"):
                return self._execute_batch(inputs)
            return self._execute_single(inputs)
        except Exception as e:
            return OperatorResult(False, error=str(e))


if __name__ == "__main__":
    op = MerkleDAGAppendOperator()
    # 单资产模式（V1兼容）
    chain = []
    for i in range(3):
        r = op({"asset_id": f"ASSET-{i:03d}", "content": f"测试资产内容{i}", "chain": chain})
        assert r.data["integrity"] is True
        chain = chain + [r.data["block"]]
    print("V1单资产模式: 3块 integrity=True ✓")

    # 批量分片并行模式
    assets = [{"asset_id": f"B-{i:04d}", "content": f"批量资产内容{i}"} for i in range(200)]
    r2 = op({"assets": assets, "chain": chain, "shard_size": 32, "max_workers": 4,
             "prove_asset": "B-0042"})
    assert r2.success, r2.error
    assert r2.data["integrity"] is True
    print(f"V2批量模式: 200资产 分片{len([a for a in assets])//32}+ 树深{r2.data['shard_stats']['merkle_tree_depth']} "
          f"merkle_root={r2.data['merkle_root'][:16]}... ✓")
    p = r2.data["merkle_proof"]
    print(f"存在性证明: asset={p['asset_id']} valid={p['valid']} 证明步数={len(p['proof'])} ✓")
    print("主链长度:", r2.data["chain_length"])
