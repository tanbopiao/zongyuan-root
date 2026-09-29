#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜27算子每日巡检脚本
功能：按十层依赖拓扑依次运行所有已实现算子，输出巡检报告，持久化结果
用法：python3 scripts/operator_inspection.py [--mode light|standard|deep] [--report]
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""

import sys
import json
import time
import argparse
import hashlib
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR / "operators"))
sys.path.insert(0, str(BASE_DIR / "config"))

try:
    from operator_dispatcher import get_dispatcher
    from result_persistence import get_all_stats_summary, record_daily_inspection
    _AVAILABLE = True
except ImportError as e:
    print(f"模块导入失败: {e}")
    _AVAILABLE = False

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

REPORT_DIR = BASE_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
GATEWAY_URL = "https://www.huodouai.com/api/report/truth"


def report_to_gateway(report):
    """上报巡检结果到记忆网关"""
    if not _REQUESTS_AVAILABLE:
        return False
    try:
        payload = {
            "truth_key": f"INSPECTION.DAILY.{datetime.now().strftime('%Y%m%d')}",
            "truth_value": json.dumps({
                "inspection_id": report.get("inspection_id"),
                "date": report.get("date"),
                "mode": report.get("mode"),
                "operators_run": report.get("operators_run"),
                "operators_success": report.get("operators_success"),
                "operators_error": report.get("operators_error"),
                "success_rate": report.get("success_rate", 0),
                "total_elapsed_ms": report.get("total_elapsed_ms"),
                "summary": report.get("summary", {}),
                "did": DID,
                "trace": TRACE,
            }, ensure_ascii=False),
            "source_node": DID,
            "confidence": 0.95,
            "truth_type": "protocol",
        }
        resp = requests.post(GATEWAY_URL, json=payload, timeout=10)
        result = resp.json()
        return result.get("written_to_gateway", False) or result.get("success", False)
    except Exception as e:
        print(f"  网关上报失败: {e}")
        return False


def run_inspection(mode="light", report_to_file=True):
    """执行每日巡检"""
    print("=" * 60)
    print(f"元极恒一｜27算子每日巡检 ({mode}模式)")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"溯源: {TRACE} | {DID}")
    print("=" * 60)

    if not _AVAILABLE:
        print("❌ 算子调度器不可用，巡检终止")
        return None

    dispatcher = get_dispatcher()
    start_time = time.time()

    # 执行巡检
    report = dispatcher.run_daily_inspection(mode=mode)
    elapsed = time.time() - start_time

    # 计算成功率
    total = report.get("operators_run", 0)
    success = report.get("operators_success", 0)
    error = report.get("operators_error", 0)
    success_rate = round(success / max(total, 1) * 100, 2)
    report["success_rate"] = success_rate

    # 输出结果
    print(f"\n巡检结果:")
    print(f"  巡检ID: {report['inspection_id']}")
    print(f"  执行算子: {total}个")
    print(f"  成功: {success}, 失败: {error}")
    print(f"  成功率: {success_rate}%")
    print(f"  总耗时: {report['total_elapsed_ms']}ms")

    print(f"\n算子执行详情:")
    for op in report.get("operator_results", []):
        status_icon = "✅" if op["status"] == "success" else "❌"
        print(f"  {status_icon} 第{op['layer']}层 | {op['operator_id']:35s} | {op['elapsed_ms']}ms")

    # 摘要
    summary = report.get("summary", {})
    print(f"\n关键指标:")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    # 上报网关
    print(f"\n上报记忆网关...")
    gateway_ok = report_to_gateway(report)
    print(f"  网关上报: {'✅ 成功' if gateway_ok else '❌ 失败'}")

    # 保存报告文件
    if report_to_file:
        report_file = REPORT_DIR / f"operator_inspection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存: {report_file}")

    print("\n" + "=" * 60)
    print(f"巡检完成 | 成功率: {success_rate}% | 耗时: {round(elapsed, 2)}s")
    print("=" * 60)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="元极恒一27算子每日巡检")
    parser.add_argument("--mode", choices=["light", "standard", "deep"], default="light",
                        help="巡检模式: light(轻量5算子)/standard(全部已实现)/deep(深度)")
    parser.add_argument("--no-report", action="store_true", help="不保存报告文件")
    args = parser.parse_args()

    run_inspection(mode=args.mode, report_to_file=not args.no_report)
