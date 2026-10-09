#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真值自动元秩序化引擎 - 入口脚本
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω

用法:
  python3 run.py --run          # 执行一次元秩序化
  python3 run.py --status       # 查看引擎状态
  python3 run.py --daemon       # 守护进程模式（定时执行）
  python3 run.py --dry-run      # 试运行（不写入）
"""

import os
import sys
import json
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import TruthMetaOrderEngine
from config import SCHEDULER_CONFIG


def run_once(engine, dry_run=False):
    """执行一次元秩序化"""
    if dry_run:
        print("【试运行模式】不写入任何数据")
        # 试运行：只采集和分析，不写入
        engine.hasher.config["merkle_dag"]["enabled"] = False

    result = engine.run()

    print("\n" + "=" * 60)
    print("元秩序化运行结果")
    print("=" * 60)
    print(f"  运行ID: {result['run_id']}")
    print(f"  状态: {result['status']}")
    print(f"  处理真值数: {result['processed_count']}")
    print(f"  耗时: {result['duration_seconds']}秒")
    print(f"  Merkle-DAG总资产: {result['dag_total_assets']}")
    if result.get('dag_root_hash'):
        print(f"  Merkle-DAG根哈希: {result['dag_root_hash'][:32]}...")

    if result.get('class_distribution'):
        print(f"\n  九大元类分布:")
        for cls_name, count in sorted(result['class_distribution'].items(), key=lambda x: -x[1]):
            print(f"    {cls_name}: {count}条")

    if result.get('processed_truths_sample'):
        print(f"\n  处理样本（前5条）:")
        for item in result['processed_truths_sample']:
            print(f"    [{item['meta_class']}] {item['original_key'][:50]} "
                  f"(置信度{item['confidence']:.2f}, {item['verification_status']})")

    return result


def show_status(engine):
    """显示引擎状态"""
    status = engine.get_status()
    print("\n" + "=" * 60)
    print("真值自动元秩序化引擎 - 状态")
    print("=" * 60)
    print(json.dumps(status, indent=2, ensure_ascii=False))


def run_daemon(engine):
    """守护进程模式"""
    interval = SCHEDULER_CONFIG["interval_minutes"] * 60
    print(f"\n【守护进程模式】每{SCHEDULER_CONFIG['interval_minutes']}分钟执行一次")
    print("按Ctrl+C停止\n")

    try:
        while True:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 执行元秩序化...")
            result = engine.run()
            print(f"  完成: 处理{result['processed_count']}条, 耗时{result['duration_seconds']}秒, 状态{result['status']}")
            print(f"  等待{interval}秒...\n")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n守护进程已停止。")


def main():
    parser = argparse.ArgumentParser(
        description="真值自动元秩序化引擎 - 全自动流水线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
流水线：真值采集 → 四层结构化 → 九大元类 → SHA256确权 → Merkle-DAG → 锁档归档 → 上报中枢
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
        """
    )
    parser.add_argument("--run", action="store_true", help="执行一次元秩序化")
    parser.add_argument("--status", action="store_true", help="查看引擎状态")
    parser.add_argument("--daemon", action="store_true", help="守护进程模式")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式（不写入）")

    args = parser.parse_args()

    print("初始化真值自动元秩序化引擎...")
    engine = TruthMetaOrderEngine()
    engine.initialize()

    if args.run:
        run_once(engine, dry_run=args.dry_run)
    elif args.status:
        show_status(engine)
    elif args.daemon:
        run_daemon(engine)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
