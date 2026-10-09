#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
巡检引擎：严格按十层依赖拓扑顺序执行，上游输出作为下游输入
支持轻量/深度双模式；输出运行状态 + 汇总指标
"""
import json
import time
from .topology import LAYER_TOPOLOGY, OPERATOR_REGISTRY, HEAVY_OPS, validate_topology
from .operators import OPERATOR_EXEC, LIGHT_PARAM_OPS


def run_patrol(patrol_id=None, mode="light", fragments=None,
               prev_root_hash=None, chain_len=None):
    """
    执行一次完整自治巡检
    :param patrol_id: 巡检编号；缺省自动生成
    :param mode: light(轻量，高消耗算子轻量执行) / deep(深度)
    :param fragments: 输入碎片列表
    :param prev_root_hash: 上一轮根哈希（Merkle 链）
    :param chain_len: 主链长度
    :return: 巡检报告 dict
    """
    validate_topology()
    patrol_id = patrol_id or f"PATROL-{time.strftime('%Y%m%d-%H%M%S')}"
    ctx = {
        "patrol_id": patrol_id,
        "input_fragments": fragments or ["事实:元极恒一体系V5.6运行中",
                                          "猜想:未来或出现奇点事件",
                                          "观点:体系设计优秀"],
        "prev_root_hash": prev_root_hash or "0" * 64,
        "chain_len": chain_len or 1399,
        "mode": mode,
    }

    results = {}
    started = time.time()
    for layer in range(1, 11):
        layer_ops = LAYER_TOPOLOGY[layer]
        for op_id in layer_ops:
            fn = OPERATOR_EXEC[op_id]
            # 轻量模式：高消耗算子走 light 分支；深度模式走完整计算
            light_flag = (mode == "light")
            kwargs = {"light": light_flag} if op_id in LIGHT_PARAM_OPS else {}
            try:
                t0 = time.time()
                out = fn(ctx, **kwargs) if kwargs else fn(ctx)
                results[op_id] = {
                    "name": next(o["name"] for o in OPERATOR_REGISTRY if o["id"] == op_id),
                    "layer": layer,
                    "status": "RUN_OK",
                    "duration_ms": round((time.time() - t0) * 1000, 1),
                    "output": out,
                }
            except Exception as e:  # 单算子失败不拖垮整条链
                results[op_id] = {
                    "name": next(o["name"] for o in OPERATOR_REGISTRY if o["id"] == op_id),
                    "layer": layer,
                    "status": f"ERROR:{e}",
                    "duration_ms": 0,
                    "output": {},
                }
    elapsed = round(time.time() - started, 3)

    # 汇总指标
    ok = sum(1 for r in results.values() if r["status"] == "RUN_OK")
    heavy_skipped = [oid for oid in HEAVY_OPS if mode == "light" and oid in LIGHT_PARAM_OPS]
    report = {
        "patrol_id": patrol_id,
        "mode": mode,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "operators_total": 27,
        "operators_ok": ok,
        "operators_failed": 27 - ok,
        "layers": 10,
        "duration_sec": elapsed,
        "heavy_mode": heavy_skipped,
        "purity_score": ctx.get("L1_distill", {}).get("purity", 0),
        "drift_alert": ctx.get("L2_drift", {}).get("alert_level", "绿"),
        "kg_triples": ctx.get("L3_triples", {}).get("triple_count", 0),
        "singularity_alert": ctx.get("L4_singularity", {}).get("alert", "蓝"),
        "dag_root": ctx.get("L6_dag", {}).get("root_hash", ""),
        "chain_len": ctx.get("chain_len", 1399),
        "efuse": ctx.get("L8_efuse", {}).get("efuse_count", 768),
        "recommendation": ctx.get("L9_plan", {}).get("recommended", ""),
        "risk_matrix": ctx.get("L9_risk", {}).get("matrix", ""),
        "trace_mark": "Ω₀⊂⊙∞⊂Ω",
        "did": "DID-BR-000002",
        "operator_results": results,
    }
    return report


if __name__ == "__main__":
    rep = run_patrol(mode="light")
    print(json.dumps({k: v for k, v in rep.items() if k != "operator_results"},
                     ensure_ascii=False, indent=2))
