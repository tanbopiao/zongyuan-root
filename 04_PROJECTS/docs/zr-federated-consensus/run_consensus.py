#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zr-federated-consensus 入口
用法：
  python3 run_consensus.py                       # 标准仿真（共识+矩阵）
  python3 run_consensus.py --consensus-only     # 仅模块A 联邦共识
  python3 run_consensus.py --matrix-only        # 仅模块B 多模态矩阵
  python3 run_consensus.py --nodes 7 --malicious 2 --tasks 30
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from zrfc.consensus import run_consensus   # noqa: E402
from zrfc.matrix import run_matrix         # noqa: E402
from zrfc.report import to_json, consensus_html, matrix_html  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="ZONGYUAN-ROOT 联邦共识+多模态矩阵")
    ap.add_argument("--nodes", type=int, default=5, help="共识节点数")
    ap.add_argument("--malicious", type=int, default=1, help="恶意节点数")
    ap.add_argument("--proposals", type=int, default=8, help="共识提案数")
    ap.add_argument("--tasks", type=int, default=14, help="多模态任务数(默认=总容量14)")
    ap.add_argument("--consensus-only", action="store_true")
    ap.add_argument("--matrix-only", action="store_true")
    ap.add_argument("--out-dir", default="reports")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    results = {}

    if not args.matrix_only:
        c = run_consensus(node_count=args.nodes, proposals=args.proposals,
                          malicious=args.malicious)
        results["consensus"] = c
        to_json(c, os.path.join(args.out_dir, "FEDCONSENSUS-STD.json"))
        consensus_html(c, os.path.join(args.out_dir, "FEDCONSENSUS-STD.html"))
        print(json.dumps({k: v for k, v in c.items() if k != "nodes"},
                         ensure_ascii=False, indent=2))

    if not args.consensus_only:
        m = run_matrix(task_count=args.tasks)
        results["matrix"] = m
        to_json(m, os.path.join(args.out_dir, "MMATRIX-STD.json"))
        matrix_html(m, os.path.join(args.out_dir, "MMATRIX-STD.html"))
        print(json.dumps(m, ensure_ascii=False, indent=2))

    print(f"✅ 报告: {args.out_dir}/FEDCONSENSUS-STD.{'json/html'} + MMATRIX-STD.{'json/html'}")


if __name__ == "__main__":
    main()
