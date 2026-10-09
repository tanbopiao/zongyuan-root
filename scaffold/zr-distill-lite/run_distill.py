#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zr-distill-lite 入口
用法：
  python3 run_distill.py                     # 标准蒸馏仿真
  python3 run_distill.py --alpha 0.6 --T 4.0 # 自定义蒸馏温度
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from distill.pipeline import run_distill  # noqa: E402
from distill.report import to_json, to_html  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="ZONGYUAN-ROOT 模型蒸馏轻量化")
    ap.add_argument("--alpha", type=float, default=0.7, help="硬标签CE权重")
    ap.add_argument("--T", type=float, default=3.0, help="蒸馏温度")
    ap.add_argument("--prune", type=float, default=0.3, help="剪枝比例")
    ap.add_argument("--out-dir", default="reports")
    args = ap.parse_args()

    r = run_distill(alpha=args.alpha, T=args.T, prune_ratio=args.prune)

    os.makedirs(args.out_dir, exist_ok=True)
    name = "DISTILL-STD"
    to_json(r, os.path.join(args.out_dir, f"{name}.json"))
    to_html(r, os.path.join(args.out_dir, f"{name}.html"))

    print(json.dumps(r, ensure_ascii=False, indent=2))
    print(f"✅ 报告: {args.out_dir}/{name}.json / .html")


if __name__ == "__main__":
    main()
