"""
Merkle-DAG遍历算子 - ZONGYUAN-ROOT 算子化架构
使用手动栈遍历Merkle-DAG，禁止递归（元规则：KD-STACK-0001）

算子ID: OP-MERKLE-DAG-WALK-001
算子名称: merkle_dag_walk
类别: 遍历/数据结构
版本: V1.0

元规则：禁止递归，必须使用手动栈/迭代
溯源标识：Ω₀⊂⊙∞⊂Ω
确权编码：DID-BR-000002
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from operator_base import BaseOperator, OperatorMetadata


class MerkleDAGWalkOperator(BaseOperator):
    """
    Merkle-DAG遍历算子 - 手动栈实现，禁止递归

    元规则：KD-STACK-0001 - 所有遍历必须使用手动栈，禁止递归调用
    """

    def __init__(self):
        metadata = OperatorMetadata(
            operator_id="OP-MERKLE-DAG-WALK-001",
            operator_name="merkle_dag_walk",
            version="V1.0",
            description="使用手动栈遍历Merkle-DAG，禁止递归（元规则：KD-STACK-0001）",
            category="merkle_dag_walk",
            inputs_schema={
                "dag_data": "Merkle-DAG数据字典（必需，包含nodes和edges）",
                "root_hash": "根节点哈希（可选，默认从dag_data获取）",
                "walk_mode": "遍历模式：dfs/bfs（默认dfs）",
                "max_nodes": "最大遍历节点数（默认1000）",
                "visit_action": "访问动作：collect/verify/hash（默认collect）",
            },
            outputs_schema={
                "walk_result": "遍历结果字典",
                "visited_nodes": "已访问节点列表",
                "node_count": "访问节点数",
                "root_hash": "根哈希",
                "integrity_verified": "完整性验证结果",
            },
        )
        super().__init__(metadata)

    def _compute_node_hash(self, node: Dict[str, Any]) -> str:
        """计算节点哈希"""
        content = json.dumps(node, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Merkle-DAG遍历 - 手动栈实现，禁止递归

        元规则：KD-STACK-0001 - 必须使用手动栈，禁止递归调用
        """
        dag_data = inputs.get("dag_data", {})
        root_hash = inputs.get("root_hash", "")
        walk_mode = inputs.get("walk_mode", "dfs")
        max_nodes = inputs.get("max_nodes", 1000)
        visit_action = inputs.get("visit_action", "collect")

        # 构建节点索引
        nodes = dag_data.get("nodes", {})
        edges = dag_data.get("edges", [])

        # 如果没有指定根哈希，找第一个没有父节点的节点
        if not root_hash:
            child_hashes = set()
            for edge in edges:
                child_hashes.add(edge.get("child", ""))
            for node_hash in nodes.keys():
                if node_hash not in child_hashes:
                    root_hash = node_hash
                    break

        if not root_hash or root_hash not in nodes:
            return {
                "walk_result": {"error": "无效的根哈希或空DAG"},
                "visited_nodes": [],
                "node_count": 0,
                "root_hash": root_hash,
                "integrity_verified": False,
            }

        # 构建子节点索引
        children_map = {}
        for edge in edges:
            parent = edge.get("parent", "")
            child = edge.get("child", "")
            if parent not in children_map:
                children_map[parent] = []
            children_map[parent].append(child)

        # 手动栈遍历 - 禁止递归（元规则：KD-STACK-0001）
        visited = set()
        visited_nodes = []
        integrity_verified = True

        # 使用列表作为栈（DFS）或队列（BFS）
        stack = [root_hash]
        visit_order = []

        while stack and len(visited) < max_nodes:
            if walk_mode == "dfs":
                current_hash = stack.pop()  # 栈：后进先出
            else:
                current_hash = stack.pop(0)  # 队列：先进先出

            if current_hash in visited:
                continue

            visited.add(current_hash)
            visit_order.append(current_hash)

            # 获取节点数据
            node = nodes.get(current_hash, {})

            # 执行访问动作
            node_result = {
                "hash": current_hash,
                "node": node,
                "visited_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            if visit_action in ["verify", "hash"]:
                # 验证节点哈希完整性
                computed_hash = self._compute_node_hash(node)
                hash_match = computed_hash == current_hash
                node_result["hash_verified"] = hash_match
                node_result["computed_hash"] = computed_hash
                if not hash_match:
                    integrity_verified = False

            visited_nodes.append(node_result)

            # 将子节点加入栈/队列（手动栈，禁递归）
            children = children_map.get(current_hash, [])
            for child_hash in children:
                if child_hash not in visited and child_hash in nodes:
                    stack.append(child_hash)

        walk_result = {
            "root_hash": root_hash,
            "walk_mode": walk_mode,
            "visit_order": visit_order,
            "total_nodes_in_dag": len(nodes),
            "visited_count": len(visited),
            "max_nodes_limit": max_nodes,
            "truncated": len(visited) >= max_nodes,
            "visit_action": visit_action,
            "integrity_verified": integrity_verified,
            "meta_rule": "KD-STACK-0001: 手动栈遍历，禁止递归",
        }

        return {
            "walk_result": walk_result,
            "visited_nodes": visited_nodes,
            "node_count": len(visited),
            "root_hash": root_hash,
            "integrity_verified": integrity_verified,
        }


# 算子单例
merkle_dag_walk_operator = MerkleDAGWalkOperator()
