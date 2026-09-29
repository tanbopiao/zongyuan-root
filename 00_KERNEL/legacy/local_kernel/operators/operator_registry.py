"""
算子注册表 - ZONGYUAN-ROOT 算子化架构
统一管理所有标准算子，支持注册、查询、列举、锁档

算子ID分配规则：
- OP-HASH-LOCK-001    哈希锁档算子
- OP-AUTO-CHECK-001   自动检查算子
- OP-DEPLOY-001       部署算子
- OP-API-CALL-001     API调用算子
- OP-MERKLE-DAG-WALK-001  Merkle-DAG遍历算子
- OP-FILE-OPERATION-001   文件操作算子
- OP-DECISION-3D-STEADY-001  三维稳态校准决策算子

溯源标识：Ω₀⊂⊙∞⊂Ω
确权编码：DID-BR-000002
根挂载：ZONGYUAN-ROOT V1.7
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from operator_base import BaseOperator, OperatorMetadata


class OperatorRegistry:
    """
    算子注册表 - 统一管理所有标准算子

    功能：
    1. 算子注册和注销
    2. 算子查询（按ID/名称/类别）
    3. 算子列举
    4. 算子锁档（生成Merkle根哈希）
    5. 算子统计
    """

    def __init__(self):
        self._operators: Dict[str, BaseOperator] = {}
        self._categories: Dict[str, List[str]] = {}
        self._registry_hash: str = ""

    def register(self, operator: BaseOperator) -> bool:
        """注册算子"""
        op_id = operator.metadata.operator_id
        if op_id in self._operators:
            return False

        self._operators[op_id] = operator

        # 按类别索引
        category = operator.metadata.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(op_id)

        # 更新注册表哈希
        self._update_registry_hash()
        return True

    def unregister(self, operator_id: str) -> bool:
        """注销算子"""
        if operator_id not in self._operators:
            return False

        operator = self._operators[operator_id]
        category = operator.metadata.category

        del self._operators[operator_id]
        if category in self._categories:
            if operator_id in self._categories[category]:
                self._categories[category].remove(operator_id)
            if not self._categories[category]:
                del self._categories[category]

        self._update_registry_hash()
        return True

    def get(self, operator_id: str) -> Optional[BaseOperator]:
        """按ID获取算子"""
        return self._operators.get(operator_id)

    def get_by_name(self, operator_name: str) -> Optional[BaseOperator]:
        """按名称获取算子"""
        for operator in self._operators.values():
            if operator.metadata.operator_name == operator_name:
                return operator
        return None

    def list_by_category(self, category: str) -> List[BaseOperator]:
        """按类别列举算子"""
        op_ids = self._categories.get(category, [])
        return [self._operators[op_id] for op_id in op_ids if op_id in self._operators]

    def list_all(self) -> List[BaseOperator]:
        """列举所有算子"""
        return list(self._operators.values())

    def list_categories(self) -> List[str]:
        """列举所有类别"""
        return list(self._categories.keys())

    def _update_registry_hash(self):
        """更新注册表哈希"""
        all_metadata = []
        for op_id in sorted(self._operators.keys()):
            operator = self._operators[op_id]
            all_metadata.append(operator.metadata.to_dict())

        content = json.dumps(all_metadata, sort_keys=True, ensure_ascii=False)
        self._registry_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get_registry_hash(self) -> str:
        """获取注册表哈希"""
        return self._registry_hash

    def get_lock_data(self) -> Dict[str, Any]:
        """获取锁档数据 - 用于Merkle-DAG确权"""
        operators_info = []
        for op_id in sorted(self._operators.keys()):
            operator = self._operators[op_id]
            operators_info.append({
                "operator_id": operator.metadata.operator_id,
                "operator_name": operator.metadata.operator_name,
                "version": operator.metadata.version,
                "category": operator.metadata.category,
                "hash": operator.metadata.compute_hash(),
            })

        return {
            "registry_hash": self._registry_hash,
            "operator_count": len(self._operators),
            "categories": self.list_categories(),
            "operators": operators_info,
            "locked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "trace_symbol": "Ω₀⊂⊙∞⊂Ω",
            "did": "DID-BR-000002",
            "root_anchor": "ZONGYUAN-ROOT V1.7",
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取注册表统计信息"""
        total_executions = 0
        total_execution_time = 0.0

        for operator in self._operators.values():
            stats = operator.get_stats()
            total_executions += stats["execution_count"]
            total_execution_time += stats["total_execution_time_ms"]

        return {
            "total_operators": len(self._operators),
            "total_categories": len(self._categories),
            "total_executions": total_executions,
            "total_execution_time_ms": round(total_execution_time, 2),
            "registry_hash": self._registry_hash,
        }


# 全局算子注册表单例
_global_registry: Optional[OperatorRegistry] = None


def get_registry() -> OperatorRegistry:
    """获取全局算子注册表单例"""
    global _global_registry
    if _global_registry is None:
        _global_registry = OperatorRegistry()
    return _global_registry


def register_default_operators() -> OperatorRegistry:
    """注册所有默认标准算子"""
    registry = get_registry()

    # 导入所有算子
    from hash_lock_operator import hash_lock_operator
    from auto_check_operator import auto_check_operator
    from deploy_operator import deploy_operator
    from api_call_operator import api_call_operator
    from merkle_dag_walk_operator import merkle_dag_walk_operator
    from file_operation_operator import file_operation_operator
    from decision_3d_steady import decision_3d_steady

    # 注册算子
    operators = [
        hash_lock_operator,
        auto_check_operator,
        deploy_operator,
        api_call_operator,
        merkle_dag_walk_operator,
        file_operation_operator,
        decision_3d_steady,
    ]

    for operator in operators:
        registry.register(operator)

    return registry
