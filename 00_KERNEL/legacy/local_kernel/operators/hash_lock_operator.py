"""
哈希锁档算子 - ZONGYUAN-ROOT 算子化架构
对任意数据计算SHA256哈希，生成Merkle-DAG锁档凭证

算子ID: OP-HASH-LOCK-001
算子名称: hash_lock
类别: 哈希/确权
版本: V1.0

溯源标识：Ω₀⊂⊙∞⊂Ω
确权编码：DID-BR-000002
"""

import hashlib
import json
import time
from typing import Any, Dict

from operator_base import BaseOperator, OperatorMetadata


class HashLockOperator(BaseOperator):
    """哈希锁档算子 - 计算数据哈希并生成锁档凭证"""

    def __init__(self):
        metadata = OperatorMetadata(
            operator_id="OP-HASH-LOCK-001",
            operator_name="hash_lock",
            version="V1.0",
            description="对任意数据计算SHA256哈希，生成Merkle-DAG锁档凭证",
            category="hash_lock",
            inputs_schema={
                "data": "任意可序列化数据（必需）",
                "asset_id": "资产ID（可选）",
                "asset_name": "资产名称（可选）",
                "lock_level": "锁档等级（可选，默认Lv7）",
            },
            outputs_schema={
                "sha256": "SHA256哈希值",
                "lock_credential": "锁档凭证字典",
                "merkle_leaf": "Merkle叶子节点数据",
            },
        )
        super().__init__(metadata)

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行哈希锁档"""
        data = inputs.get("data", {})
        asset_id = inputs.get("asset_id", "UNKNOWN")
        asset_name = inputs.get("asset_name", "未命名资产")
        lock_level = inputs.get("lock_level", "Lv7")

        # 计算数据哈希
        if isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            data_bytes = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")

        sha256_hash = hashlib.sha256(data_bytes).hexdigest()

        # 生成锁档凭证
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        lock_credential = {
            "asset_id": asset_id,
            "asset_name": asset_name,
            "sha256": sha256_hash,
            "lock_level": lock_level,
            "lock_status": "BLOWN_PERMANENT",
            "locked_at": timestamp,
            "did": "DID-BR-000002",
            "trace_symbol": "Ω₀⊂⊙∞⊂Ω",
            "root_anchor": "ZONGYUAN-ROOT V1.7",
            "data_size_bytes": len(data_bytes),
        }

        # 生成Merkle叶子节点
        merkle_leaf = {
            "leaf_hash": sha256_hash,
            "asset_id": asset_id,
            "timestamp": timestamp,
            "credential_hash": hashlib.sha256(
                json.dumps(lock_credential, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
        }

        return {
            "sha256": sha256_hash,
            "lock_credential": lock_credential,
            "merkle_leaf": merkle_leaf,
        }


# 算子单例
hash_lock_operator = HashLockOperator()
