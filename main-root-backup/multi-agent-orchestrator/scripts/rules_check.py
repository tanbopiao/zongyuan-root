#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多智能体编排 · 调度规则校验器 v1.0
Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZONGYUAN-ROOT

校验 scheduling-rules.md 中可程序化的规则：
  - balance     : 规则三 负载均衡（各分片权重占比<=40%）
  - dependency  : 规则二 依赖合法性（片间并行/片内串行）
  - schema      : 规则四 统一输出schema一致性
  - ledger      : 规则七 确权记录落盘
  - all         : 全部检查

用法:
    python3 rules_check.py --mode balance   --weights '5,4,4,3' --shards 4
    python3 rules_check.py --mode dependency --plan <plan.json> [--json]
    python3 rules_check.py --mode schema     --schemas 'a,b,a' --shards 3
    python3 rules_check.py --mode all --weights '5,4,4,3' --shards 4
"""
from __future__ import annotations
import os
import sys
import json
import argparse
import hashlib
from pathlib import Path
from datetime import datetime

DID = "DID-BR-000002"
TRACE_SYMBOL = "Ω₀⊂⊙∞⊂Ω"
VERSION = "1.0.0"

BALANCE_MAX_SHARE = 0.40   # 规则三：单分片权重占比上限 40%
SHARD_MIN = 2
SHARD_MAX = 4               # 规则一：分片数 2-4


def _now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")


def check_balance(weights, shards, verbose=True):
    """规则三：负载均衡。返回 {pass, results}。"""
    if shards < SHARD_MIN or shards > SHARD_MAX:
        return {"pass": False, "error": f"分片数{shards}不在2-4范围"}
    total = sum(weights)
    if total <= 0:
        return {"pass": False, "error": "总权重为0"}
    results = []
    ok = True
    for i, w in enumerate(weights):
        share = w / total
        res = {"shard": f"shard-{i+1}", "weight": w, "share": round(share, 3), "ok": share <= BALANCE_MAX_SHARE}
        if not res["ok"]:
            ok = False
        results.append(res)
    return {"pass": ok, "rule": "R3_balance", "threshold": BALANCE_MAX_SHARE, "results": results}


def check_dependency(plan_path, verbose=True):
    """规则二：依赖合法性。plan.json 需含 shards[].dependencies（不存在的片或自依赖视为非法）。"""
    try:
        plan = json.load(open(plan_path, encoding="utf-8"))
    except Exception as e:
        return {"pass": False, "rule": "R2_dependency", "error": f"读取计划失败: {e}"}
    shards = plan.get("shards", [])
    ids = {s.get("shard_id") for s in shards}
    errors = []
    for s in shards:
        sid = s.get("shard_id")
        deps = s.get("dependencies", [])
        for d in deps:
            if d == sid:
                errors.append(f"{sid} 自依赖")
            if d not in ids:
                errors.append(f"{sid} 依赖不存在的 {d}")
    # 简单环检测（A→B 且 B→A）
    dep_map = {s.get("shard_id"): s.get("dependencies", []) for s in shards}
    for a in ids:
        for b in dep_map.get(a, []):
            if a in dep_map.get(b, []):
                errors.append(f"{a} <-> {b} 形成环")
    return {"pass": not errors, "rule": "R2_dependency", "errors": errors}


def check_schema(schemas, shards, verbose=True):
    """规则四：统一schema一致性。所有分片 schema 必须一致。"""
    if len(schemas) != shards:
        return {"pass": False, "rule": "R4_schema", "error": f"schema数{len(schemas)}≠分片数{shards}"}
    uniq = set(schemas)
    if len(uniq) == 1:
        return {"pass": True, "rule": "R4_schema", "schema": schemas[0], "consistent": True}
    return {"pass": False, "rule": "R4_schema", "consistent": False, "differing": list(uniq)}


def check_ledger(ledger_path, verbose=True):
    """规则七：确权记录。检查台账文件存在且非空。"""
    if not os.path.exists(ledger_path):
        return {"pass": False, "rule": "R7_ledger", "error": f"台账不存在: {ledger_path}"}
    size = os.path.getsize(ledger_path)
    return {"pass": size > 0, "rule": "R7_ledger", "size_bytes": size}


def main():
    ap = argparse.ArgumentParser(description="多智能体编排调度规则校验器")
    ap.add_argument("--mode", required=True, choices=["balance", "dependency", "schema", "ledger", "all"])
    ap.add_argument("--weights", type=str, default="")
    ap.add_argument("--shards", type=int, default=0)
    ap.add_argument("--plan", type=str, default="")
    ap.add_argument("--schemas", type=str, default="")
    ap.add_argument("--ledger", type=str, default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    out = {"checker": "multi-agent-orchestrator/rules_check", "version": VERSION,
           "did": DID, "trace": TRACE_SYMBOL, "checked_at": _now(), "results": []}
    overall = True

    if args.mode in ("balance", "all"):
        w = [int(x) for x in args.weights.split(",") if x.strip()] if args.weights else []
        r = check_balance(w, args.shards)
        out["results"].append(r)
        overall = overall and r.get("pass", False)

    if args.mode in ("dependency", "all"):
        if args.plan:
            r = check_dependency(args.plan)
            out["results"].append(r)
            overall = overall and r.get("pass", False)

    if args.mode in ("schema", "all"):
        s = [x for x in args.schemas.split(",") if x.strip()] if args.schemas else []
        r = check_schema(s, args.shards)
        out["results"].append(r)
        overall = overall and r.get("pass", False)

    if args.mode in ("ledger", "all"):
        if args.ledger:
            r = check_ledger(args.ledger)
            out["results"].append(r)
            overall = overall and r.get("pass", False)

    out["overall_pass"] = overall
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
