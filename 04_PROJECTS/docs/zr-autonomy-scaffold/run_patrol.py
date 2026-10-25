#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zr-autonomy-scaffold 入口
用法：
  python3 run_patrol.py                      # 轻量模式巡检，输出 JSON+HTML
  python3 run_patrol.py --mode deep          # 深度模式（全量重消耗计算）
  python3 run_patrol.py --json-only          # 仅输出 JSON
  python3 run_patrol.py --out-dir <dir>      # 指定输出目录
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scaffold.engine import run_patrol          # noqa: E402
from scaffold.report import to_json, to_html    # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="ZONGYUAN-ROOT 自治巡检脚手架")
    ap.add_argument("--mode", choices=["light", "deep"], default="light",
                    help="轻量/深度模式（默认 light，高消耗算子轻量执行）")
    ap.add_argument("--patrol-id", default=None, help="巡检编号")
    ap.add_argument("--prev-root", default=None, help="上一轮 Merkle 根哈希")
    ap.add_argument("--chain-len", type=int, default=None, help="主链长度")
    ap.add_argument("--json-only", action="store_true", help="仅输出 JSON")
    ap.add_argument("--out-dir", default="reports", help="输出目录")
    ap.add_argument("--fragment", action="append", default=None, help="输入碎片（可多次）")
    args = ap.parse_args()

    report = run_patrol(
        patrol_id=args.patrol_id,
        mode=args.mode,
        fragments=args.fragment,
        prev_root_hash=args.prev_root,
        chain_len=args.chain_len,
    )

    os.makedirs(args.out_dir, exist_ok=True)
    json_path = os.path.join(args.out_dir, f"{report['patrol_id']}.json")
    to_json(report, json_path)

    print(json.dumps({k: v for k, v in report.items() if k != "operator_results"},
                     ensure_ascii=False, indent=2))
    print(f"\n✅ JSON 报告: {json_path}")

    if not args.json_only:
        html_path = os.path.join(args.out_dir, f"{report['patrol_id']}.html")
        to_html(report, html_path)
        print(f"✅ HTML 报告: {html_path}")
        print(f"   Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 确权锚定")


if __name__ == "__main__":
    main()
