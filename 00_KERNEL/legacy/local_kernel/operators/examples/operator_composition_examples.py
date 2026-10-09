"""
算子组合示例 - ZONGYUAN-ROOT 算子化架构
展示如何通过组合算子完成复杂任务

示例1：部署闭环（4个算子串行）
    AutoCheck → Deploy → APICall(验证) → HashLock(锁档)

示例2：巡检闭环（手动栈遍历+验证）
    MerkleDAGWalk(遍历所有快照) → AutoCheck(批量检查) → HashLock(锁档结果)

示例3：TryCatch-Fallback（API调用失败切换备用）
    TryCatch(主API, 备用API)

示例4：循环迭代（批量处理）
    LoopIterator(文件操作算子, 批量处理文件列表)

溯源标识：Ω₀⊂⊙∞⊂Ω
确权编码：DID-BR-000002
"""

import sys
import os

# 添加算子目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from operator_base import OperatorResult
from composition_engine import SerialPipeline, TryCatch, LoopIterator, ConditionalBranch
from operator_registry import register_default_operators
from hash_lock_operator import HashLockOperator
from auto_check_operator import AutoCheckOperator
from deploy_operator import DeployOperator
from api_call_operator import APICallOperator
from merkle_dag_walk_operator import MerkleDAGWalkOperator
from file_operation_operator import FileOperationOperator


def example_deploy_pipeline():
    """
    示例1：部署闭环（4个算子串行）
    AutoCheck → Deploy → APICall(验证) → HashLock(锁档)
    """
    print("=" * 60)
    print("示例1：部署闭环（4个算子串行）")
    print("=" * 60)

    # 创建算子实例
    auto_check = AutoCheckOperator()
    deploy = DeployOperator()
    api_call = APICallOperator()
    hash_lock = HashLockOperator()

    # 创建串行管道
    pipeline = SerialPipeline(
        operators=[auto_check, deploy, api_call, hash_lock],
        name="deploy_pipeline"
    )

    # 执行部署管道
    result = pipeline({
        "check_type": "service",
        "service_ports": [8020],
        "deploy_type": "service",
        "target": "gov_server",
        "dry_run": True,  # 预演模式
        "url": "http://127.0.0.1:8020/api/health",
        "method": "GET",
        "timeout": 5,
        "data": {"deploy_pipeline": "completed"},
        "asset_id": "DEPLOY-001",
        "asset_name": "部署闭环测试",
    })

    print(f"\n部署管道执行结果:")
    print(f"  成功: {result.success}")
    print(f"  执行时间: {result.execution_time_ms}ms")
    if result.data.get("steps"):
        for step in result.data["steps"]:
            print(f"  步骤{step['step']}: {step['operator']} - {'✅' if step['success'] else '❌'}")

    return result


def example_try_catch_fallback():
    """
    示例2：TryCatch-Fallback（API调用失败切换备用）
    """
    print("\n" + "=" * 60)
    print("示例2：TryCatch-Fallback（API调用失败切换备用）")
    print("=" * 60)

    # 创建主API算子（会失败的URL）
    primary_api = APICallOperator()
    # 创建备用API算子
    fallback_api = APICallOperator()

    # 创建TryCatch
    try_catch = TryCatch(
        primary_operator=primary_api,
        fallback_operator=fallback_api,
        name="api_failover"
    )

    # 执行（主API使用无效URL，会触发fallback）
    result = try_catch({
        "url": "http://127.0.0.1:9999/invalid",  # 无效URL
        "method": "GET",
        "timeout": 3,
        "max_retries": 0,
        # fallback参数
        "fallback_url": "http://127.0.0.1:8020/api/health",
    })

    print(f"\nTryCatch执行结果:")
    print(f"  成功: {result.success}")
    print(f"  主算子执行: {result.data.get('primary_executed')}")
    print(f"  主算子成功: {result.data.get('primary_success')}")
    print(f"  Fallback执行: {result.data.get('fallback_executed')}")

    return result


def example_loop_iterator():
    """
    示例3：循环迭代（批量处理文件哈希）
    """
    print("\n" + "=" * 60)
    print("示例3：循环迭代（批量处理文件哈希）")
    print("=" * 60)

    # 创建文件操作算子
    file_op = FileOperationOperator()

    # 定义继续条件：还有文件未处理
    file_list = [
        r"C:\Users\4906\.zongyuan_root\operators\operator_base.py",
        r"C:\Users\4906\.zongyuan_root\operators\composition_engine.py",
        r"C:\Users\4906\.zongyuan_root\operators\hash_lock_operator.py",
    ]

    def continue_condition(inputs, iteration):
        return iteration < len(file_list)

    # 创建循环迭代器
    loop = LoopIterator(
        operator=file_op,
        max_iterations=len(file_list),
        continue_condition=continue_condition,
        name="batch_hash_loop"
    )

    # 执行循环
    result = loop({
        "operation": "hash",
        "path": file_list[0],  # 第一个文件
        "hash_algorithm": "sha256",
        "file_list": file_list,
        "current_index": 0,
    })

    print(f"\n循环迭代执行结果:")
    print(f"  成功: {result.success}")
    print(f"  总迭代次数: {result.data.get('total_iterations')}")
    if result.data.get("iterations"):
        for iter_info in result.data["iterations"]:
            hash_val = iter_info.get("data", {}).get("result", {}).get("hash", "N/A")
            print(f"  迭代{iter_info['iteration']}: {'✅' if iter_info['success'] else '❌'} hash={hash_val[:16]}...")

    return result


def example_merkle_dag_walk():
    """
    示例4：Merkle-DAG遍历（手动栈，禁递归）
    """
    print("\n" + "=" * 60)
    print("示例4：Merkle-DAG遍历（手动栈，禁递归）")
    print("=" * 60)

    # 创建一个简单的Merkle-DAG
    import hashlib
    import json

    def node_hash(data):
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    # 构建DAG：root -> child1, child2 -> grandchild
    grandchild = {"id": "grandchild", "data": "孙节点数据"}
    child1 = {"id": "child1", "data": "子节点1数据"}
    child2 = {"id": "child2", "data": "子节点2数据"}
    root = {"id": "root", "data": "根节点数据"}

    gc_hash = node_hash(grandchild)
    c1_hash = node_hash(child1)
    c2_hash = node_hash(child2)
    root_hash = node_hash(root)

    dag_data = {
        "nodes": {
            root_hash: root,
            c1_hash: child1,
            c2_hash: child2,
            gc_hash: grandchild,
        },
        "edges": [
            {"parent": root_hash, "child": c1_hash},
            {"parent": root_hash, "child": c2_hash},
            {"parent": c1_hash, "child": gc_hash},
        ],
    }

    # 创建遍历算子
    dag_walk = MerkleDAGWalkOperator()

    # 执行遍历
    result = dag_walk({
        "dag_data": dag_data,
        "walk_mode": "dfs",
        "visit_action": "verify",
    })

    print(f"\nMerkle-DAG遍历结果:")
    print(f"  成功: {result.success}")
    print(f"  根哈希: {result.data.get('root_hash', '')[:16]}...")
    print(f"  访问节点数: {result.data.get('node_count')}")
    print(f"  完整性验证: {result.data.get('integrity_verified')}")
    if result.data.get('walk_result', {}).get('visit_order'):
        print(f"  访问顺序:")
        for i, h in enumerate(result.data['walk_result']['visit_order']):
            print(f"    {i+1}. {h[:16]}...")

    return result


def example_registry():
    """
    示例5：算子注册表
    """
    print("\n" + "=" * 60)
    print("示例5：算子注册表")
    print("=" * 60)

    # 注册所有默认算子
    registry = register_default_operators()

    # 获取统计信息
    stats = registry.get_stats()
    print(f"\n注册表统计:")
    print(f"  总算子数: {stats['total_operators']}")
    print(f"  总类别数: {stats['total_categories']}")
    print(f"  注册表哈希: {stats['registry_hash'][:16]}...")

    # 列举所有算子
    print(f"\n已注册算子:")
    for operator in registry.list_all():
        print(f"  - {operator.metadata.operator_id}: {operator.metadata.operator_name} ({operator.metadata.category})")

    # 列举类别
    print(f"\n算子类别:")
    for category in registry.list_categories():
        ops = registry.list_by_category(category)
        print(f"  - {category}: {len(ops)}个算子")

    # 获取锁档数据
    lock_data = registry.get_lock_data()
    print(f"\n锁档数据:")
    print(f"  锁档时间: {lock_data['locked_at']}")
    print(f"  溯源标识: {lock_data['trace_symbol']}")
    print(f"  确权DID: {lock_data['did']}")

    return registry


def main():
    """运行所有示例"""
    print("\n" + "█" * 60)
    print("█" + " " * 20 + "ZONGYUAN-ROOT 算子化架构" + " " * 14 + "█")
    print("█" + " " * 18 + "从代码堆叠升级到算子组合" + " " * 16 + "█")
    print("█" * 60)
    print(f"\n溯源标识: Ω₀⊂⊙∞⊂Ω")
    print(f"确权编码: DID-BR-000002")
    print(f"版本: V1.0")

    # 运行示例
    example_registry()
    example_deploy_pipeline()
    example_try_catch_fallback()
    example_loop_iterator()
    example_merkle_dag_walk()

    print("\n" + "=" * 60)
    print("所有示例执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
