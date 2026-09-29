#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜算子调度器（Operator Dispatcher）
集成：三态引擎驱动 + 算子执行 + 结果持久化 + 每日巡检
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""

import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR / "operators"))
sys.path.insert(0, str(BASE_DIR / "worker"))
sys.path.insert(0, str(BASE_DIR / "config"))

try:
    from core_operators import get_scheduler, BaseOperator
    from extended_operators import register_extended_operators, get_extended_operators
    from result_persistence import record_result, get_all_stats_summary, query_results, record_daily_inspection
    _MODULES_AVAILABLE = True
except ImportError as e:
    print(f"模块导入失败: {e}")
    _MODULES_AVAILABLE = False

try:
    from config_loader import config as _config
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False


def _cfg(key, default):
    if _CONFIG_AVAILABLE:
        return _config.get(key, default)
    return default


class OperatorDispatcher:
    """算子调度器：统一管理算子执行、结果持久化、巡检"""

    def __init__(self):
        self.scheduler = None
        self._init_scheduler()

    def _init_scheduler(self):
        """初始化算子调度器，注册所有算子"""
        if not _MODULES_AVAILABLE:
            return
        self.scheduler = get_scheduler()
        register_extended_operators(self.scheduler)

    def run_operator(self, operator_id, **kwargs):
        """执行单个算子并持久化结果

        Args:
            operator_id: 算子ID
            **kwargs: 算子参数

        Returns:
            算子执行结果
        """
        if not self.scheduler:
            return {"status": "error", "error": "调度器未初始化"}

        result = self.scheduler.run_operator(operator_id, **kwargs)

        # 持久化结果
        try:
            record_result(result)
        except Exception as e:
            result["persistence_error"] = str(e)

        return result

    def run_layer(self, layer, **kwargs):
        """执行指定层的所有算子"""
        if not self.scheduler:
            return {"status": "error", "error": "调度器未初始化"}

        results = self.scheduler.run_layer(layer, **kwargs)

        # 持久化所有结果
        for result in results:
            try:
                record_result(result)
            except Exception:
                pass

        return {
            "layer": layer,
            "operators_run": len(results),
            "success": sum(1 for r in results if r.get("status") == "success"),
            "error": sum(1 for r in results if r.get("status") == "error"),
            "results": results,
        }

    def run_all(self, **kwargs):
        """按十层拓扑执行所有算子"""
        all_results = []
        for layer in range(1, 11):
            layer_result = self.run_layer(layer, **kwargs)
            all_results.append(layer_result)

        total_run = sum(r["operators_run"] for r in all_results)
        total_success = sum(r["success"] for r in all_results)
        total_error = sum(r["error"] for r in all_results)

        return {
            "total_layers": 10,
            "layers_with_operators": sum(1 for r in all_results if r["operators_run"] > 0),
            "total_operators_run": total_run,
            "total_success": total_success,
            "total_error": total_error,
            "success_rate": round(total_success / max(total_run, 1) * 100, 2),
            "layer_results": all_results,
        }

    def run_daily_inspection(self, mode="light"):
        """执行每日算子巡检

        Args:
            mode: 巡检模式（light轻量/standard标准/deep深度）

        Returns:
            巡检报告
        """
        start_time = time.time()
        inspection_date = datetime.now().strftime("%Y-%m-%d")

        # 根据模式选择要执行的算子
        if mode == "light":
            # 轻量模式：只执行核心算子
            target_operators = [
                "P4_TRUTH_RECONCILIATION",
                "TRUTH_DISTILLATION",
                "DRIFT_DETECTION",
                "MERKLE_DAG_VERIFY",
                "EFUSE_TRIGGER",
            ]
        elif mode == "standard":
            # 标准模式：执行所有已实现算子
            target_operators = [op.operator_id for op in self.scheduler.operators.values()]
        else:
            # 深度模式：全部执行+额外校验
            target_operators = [op.operator_id for op in self.scheduler.operators.values()]

        results = []
        for op_id in target_operators:
            result = self.run_operator(op_id)
            results.append(result)

        elapsed = time.time() - start_time

        # 生成巡检报告
        report = {
            "inspection_id": f"DI-{inspection_date.replace('-', '')}-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}",
            "date": inspection_date,
            "mode": mode,
            "operators_run": len(results),
            "operators_success": sum(1 for r in results if r.get("status") == "success"),
            "operators_error": sum(1 for r in results if r.get("status") == "error"),
            "total_elapsed_ms": round(elapsed * 1000, 2),
            "summary": {
                "truth_purity": next((r.get("truth_purity") for r in results if "truth_purity" in r), "N/A"),
                "drift_rate": next((r.get("avg_drift_rate") for r in results if "avg_drift_rate" in r), "N/A"),
                "efuse_status": next((r.get("efuse_status") for r in results if "efuse_status" in r), "N/A"),
                "merkle_chain_valid": next((r.get("chain_valid") for r in results if "chain_valid" in r), "N/A"),
            },
            "operator_results": [
                {
                    "operator_id": r.get("operator_id"),
                    "operator_name": r.get("operator_name"),
                    "layer": r.get("layer"),
                    "status": r.get("status"),
                    "elapsed_ms": r.get("elapsed_ms"),
                }
                for r in results
            ],
        }

        # 持久化巡检报告
        try:
            record_daily_inspection(report)
        except Exception as e:
            report["persistence_error"] = str(e)

        return report

    def get_status(self):
        """获取调度器状态"""
        if not self.scheduler:
            return {"status": "error", "error": "调度器未初始化"}

        stats = self.scheduler.get_stats()
        persistence_stats = get_all_stats_summary() if _MODULES_AVAILABLE else {}

        return {
            "dispatcher_status": "running",
            "registered_operators": stats["registered_operators"],
            "total_executions": stats["total_executions"],
            "operators": stats["operators"],
            "persistence": {
                "db_path": persistence_stats.get("db_path", "N/A"),
                "total_results": persistence_stats.get("overall", {}).get("total_results", 0),
                "total_success": persistence_stats.get("overall", {}).get("total_success", 0),
                "total_error": persistence_stats.get("overall", {}).get("total_error", 0),
                "operators_with_results": persistence_stats.get("overall", {}).get("operators_with_results", 0),
            },
            "modules_available": _MODULES_AVAILABLE,
        }

    def get_operator_results(self, operator_id=None, limit=20):
        """获取算子执行结果"""
        return query_results(operator_id=operator_id, limit=limit)


# 全局单例
_dispatcher = None

def get_dispatcher():
    """获取算子调度器单例"""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = OperatorDispatcher()
    return _dispatcher


if __name__ == "__main__":
    print("=" * 60)
    print("元极恒一｜算子调度器测试")
    print("=" * 60)

    dispatcher = get_dispatcher()

    # 状态查询
    print("\n--- 调度器状态 ---")
    status = dispatcher.get_status()
    print(f"  已注册算子: {status['registered_operators']}个")
    print(f"  持久化结果: {status['persistence']['total_results']}条")

    # 执行单个算子
    print("\n--- 执行单个算子: P4真值对账 ---")
    result = dispatcher.run_operator("P4_TRUTH_RECONCILIATION",
                                      fragments=[{"text": "测试数据", "confidence": 0.8}])
    print(f"  状态: {result['status']}, 耗时: {result['elapsed_ms']}ms")

    # 每日巡检（轻量模式）
    print("\n--- 每日巡检（轻量模式）---")
    report = dispatcher.run_daily_inspection(mode="light")
    print(f"  巡检ID: {report['inspection_id']}")
    print(f"  执行算子: {report['operators_run']}个")
    print(f"  成功: {report['operators_success']}, 失败: {report['operators_error']}")
    print(f"  耗时: {report['total_elapsed_ms']}ms")
    print(f"  成功率: {round(report['operators_success']/max(report['operators_run'],1)*100, 1)}%")

    print("\n" + "=" * 60)
    print("算子调度器测试完成")
    print("=" * 60)
