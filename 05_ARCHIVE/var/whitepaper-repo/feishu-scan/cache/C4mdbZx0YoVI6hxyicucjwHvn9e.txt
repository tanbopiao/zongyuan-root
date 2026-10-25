#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 深度守卫 V1.0
DID-BR-000002 | Ω-TAN-7-001 | Ω₀⊂⊙∞⊂Ω
作用：持续监控工作区目录深度健康，防递归嵌套复发。
规则依据：《全域锁档协议》第七章 防递归嵌套规则
- 深度上限 10 层（超限告警）
- global-lock-archive 出现于资产路径任何层级不得进入增量快照副本
- 系统目录排除域：.skills/.user_skills/.sessions/.git/__pycache__/node_modules/.tmp-tool-results
输出：03-ARCHIVES/depth-guard/depth_guard_<ts>.json（深度健康报告）
退出码：0=健康，1=超限告警
"""
import json
import os
import shutil
import sys
from datetime import datetime

WORKSPACE = "/home/user/.super_doubao/super-doubao-runtime/workspace"
MAX_DEPTH = 10
EXCLUDES = (".skills", ".user_skills", ".sessions", ".git", "__pycache__",
            "node_modules", ".tmp-tool-results")


def is_excluded(rel_path):
    return any(part in EXCLUDES for part in rel_path.split(os.sep))


def scan():
    violations = []
    stats = {"dirs_scanned": 0, "max_depth": 0, "deepest": []}

    for root, dirs, files in os.walk(WORKSPACE):
        dirs[:] = [d for d in dirs if d not in EXCLUDES]
        rel = os.path.relpath(root, WORKSPACE)
        if rel == ".":
            continue
        if is_excluded(rel):
            continue
        depth = len(rel.split(os.sep)) + 1  # 含根一层
        stats["dirs_scanned"] += 1
        if depth > stats["max_depth"]:
            stats["max_depth"] = depth
            stats["deepest"] = [rel]
        elif depth == stats["max_depth"]:
            stats["deepest"].append(rel)

        # 嵌套检测：changed_assets 下出现 snap_* 快照目录
        if "changed_assets" in rel.split(os.sep):
            for d in dirs:
                if d.startswith("snap_"):
                    violations.append({
                        "type": "nested_snapshot",
                        "path": os.path.join(rel, d),
                        "rule": "global-lock-archive不得进入增量快照副本",
                    })
        if depth > MAX_DEPTH:
            violations.append({
                "type": "depth_exceed",
                "path": rel,
                "depth": depth,
                "rule": f"目录深度上限{MAX_DEPTH}层",
            })

    return stats, violations


def main():
    stats, violations = scan()
    health = "健康" if not violations else "告警"
    report = {
        "report_id": f"DEPTH-GUARD-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "did": "DID-BR-000002",
        "root_id": "Ω-TAN-7-001",
        "trace_symbol": "Ω₀⊂⊙∞⊂Ω",
        "max_depth_rule": MAX_DEPTH,
        "stats": stats,
        "violations": violations,
        "health": health,
    }

    out_dir = os.path.join(WORKSPACE, "03-ARCHIVES", "depth-guard")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"depth_guard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("=" * 56)
    print("ZONGYUAN-ROOT 深度守卫 V1.0")
    print(f"执行时间: {report['date']}")
    print(f"DID-BR-000002 | Ω-TAN-7-001 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 56)
    print(f"扫描目录数: {stats['dirs_scanned']}")
    print(f"最大深度: {stats['max_depth']} (上限{MAX_DEPTH})")
    if stats["deepest"]:
        print(f"最深目录: {stats['deepest'][0]}")
    print(f"违规定数: {len(violations)}")
    for v in violations:
        print(f"  [{v['type']}] {v['path']} -> {v['rule']}")
    print(f"健康判定: {health}")
    print(f"报告: {out_path}")
    print("=" * 56)
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
