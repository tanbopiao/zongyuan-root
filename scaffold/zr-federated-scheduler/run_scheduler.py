#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zr-federated-scheduler 入口
用法：
  python3 run_scheduler.py                    # 12任务五节点仿真
  python3 run_scheduler.py --crash node-gpu-edge  # 模拟GPU节点崩溃验证超时回收
  python3 run_scheduler.py --tasks 20
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from zfsched.scheduler import run_simulation  # noqa: E402
from zfsched.report import to_json, to_html    # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="ZONGYUAN-ROOT 联邦调度引擎")
    ap.add_argument("--tasks", type=int, default=12, help="任务数量")
    ap.add_argument("--crash", default=None, help="模拟崩溃节点 node_id")
    ap.add_argument("--out-dir", default="reports", help="输出目录")
    args = ap.parse_args()

    sched = run_simulation(crash_node=args.crash, task_count=args.tasks)
    s = sched.summary()

    os.makedirs(args.out_dir, exist_ok=True)
    name = "FEDSCHED-STD" if not args.crash else f"FEDSCHED-CRASH-{args.crash}"
    to_json({"simulation": s, "tasks": sched.task_table()}, os.path.join(args.out_dir, f"{name}.json"))
    to_html(sched, os.path.join(args.out_dir, f"{name}.html"))

    print(json.dumps({k: v for k, v in s.items() if k != "nodes"}, ensure_ascii=False, indent=2))
    print(f"✅ 报告: {args.out_dir}/{name}.json / .html")


if __name__ == "__main__":
    main()
