#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""并行调度规则校验器 v1.0 —— R2 依赖 / R3 负载均衡 / R4 统一schema / R7 确权台账（纯标准库）

用法:
  python3 rules_check.py --mode balance  --weights '5,4,4,3' --shards 4 [--max-share 0.40]
  python3 rules_check.py --mode dependency --plan examples/sample-plan.json
  python3 rules_check.py --mode schema   --schemas 'ledger-v1,ledger-v1,ledger-v1' --shards 3
  python3 rules_check.py --mode ledger   --ledger examples/sample-ledger.json
  python3 rules_check.py --mode all --weights '5,4,4,3' --shards 4 --plan examples/sample-plan.json \\
                           --schemas 'a,a,a' --ledger examples/sample-ledger.json
退出码：全部通过 0；任一失败 1；参数错误 2。
"""
from __future__ import annotations
import os, sys, json, argparse
from datetime import datetime

VERSION = "1.0.0"
SHARD_MIN, SHARD_MAX = 2, 4


def check_balance(weights, shards, max_share=0.40):
    if not (SHARD_MIN <= shards <= SHARD_MAX):
        return {"pass": False, "rule": "R3_balance",
                "error": f"分片数 {shards} 不在 {SHARD_MIN}-{SHARD_MAX} 范围"}
    total = sum(weights)
    if total <= 0:
        return {"pass": False, "rule": "R3_balance", "error": "总权重为 0"}
    rows = []
    ok = True
    for i, w in enumerate(weights):
        share = round(w / total, 3)
        good = share <= max_share
        ok = ok and good
        rows.append({"shard": f"shard-{i+1}", "weight": w, "share": share, "ok": good})
    return {"pass": ok, "rule": "R3_balance", "threshold": max_share, "results": rows}


def check_dependency(plan_path):
    try:
        plan = json.load(open(plan_path, encoding="utf-8"))
    except Exception as e:
        return {"pass": False, "rule": "R2_dependency", "error": f"读取计划失败: {e}"}
    shards = plan.get("shards", [])
    ids = {s.get("shard_id") for s in shards}
    errors = []
    dep_map = {}
    for s in shards:
        sid = s.get("shard_id")
        deps = s.get("dependencies", []) or []
        dep_map[sid] = deps
        for d in deps:
            if d == sid:
                errors.append(f"{sid} 自依赖")
            if d not in ids:
                errors.append(f"{sid} 依赖不存在的 {d}")
    for a, deps in dep_map.items():
        for b in deps:
            if b in dep_map and a in dep_map[b]:
                errors.append(f"{a} <-> {b} 形成循环依赖")
    return {"pass": not errors, "rule": "R2_dependency", "errors": errors,
            "shard_count": len(shards)}


def check_schema(schemas, shards):
    if len(schemas) != shards:
        return {"pass": False, "rule": "R4_schema",
                "error": f"schema 数 {len(schemas)} != 分片数 {shards}"}
    uniq = set(schemas)
    if len(uniq) == 1:
        return {"pass": True, "rule": "R4_schema", "consistent": True, "schema": schemas[0]}
    return {"pass": False, "rule": "R4_schema", "consistent": False, "differing": sorted(uniq)}


REQUIRED_LEDGER_FIELDS = {"ledger_version", "generated_at", "total_items",
                          "items", "gaps", "duplicates", "provenance"}


def check_ledger(ledger_path):
    if not os.path.exists(ledger_path):
        return {"pass": False, "rule": "R7_ledger", "error": f"台账不存在: {ledger_path}"}
    try:
        data = json.load(open(ledger_path, encoding="utf-8"))
    except Exception as e:
        return {"pass": False, "rule": "R7_ledger", "error": f"非法 JSON: {e}"}
    missing = sorted(REQUIRED_LEDGER_FIELDS - set(data.keys()))
    prov = data.get("provenance", {}) or {}
    ok = not missing and bool(prov.get("did")) and bool(prov.get("plan_id"))
    return {"pass": ok, "rule": "R7_ledger", "missing_fields": missing,
            "provenance": {"has_did": bool(prov.get("did")),
                           "has_plan_id": bool(prov.get("plan_id"))}}


def main():
    ap = argparse.ArgumentParser(description="并行调度规则校验器")
    ap.add_argument("--mode", required=True,
                    choices=["balance", "dependency", "schema", "ledger", "all"])
    ap.add_argument("--weights", type=str, default="")
    ap.add_argument("--shards", type=int, default=0)
    ap.add_argument("--max-share", type=float, default=0.40)
    ap.add_argument("--plan", type=str, default="")
    ap.add_argument("--schemas", type=str, default="")
    ap.add_argument("--ledger", type=str, default="")
    args = ap.parse_args()

    out = {"checker": "agent-orchestrator/rules_check", "version": VERSION,
           "checked_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
           "results": []}
    overall = True

    def add(r):
        nonlocal overall
        out["results"].append(r)
        overall = overall and r.get("pass", False)

    if args.mode in ("balance", "all"):
        w = [int(x) for x in args.weights.split(",") if x.strip()] if args.weights else []
        if w:
            add(check_balance(w, args.shards, args.max_share))
    if args.mode in ("dependency", "all") and args.plan:
        add(check_dependency(args.plan))
    if args.mode in ("schema", "all"):
        s = [x.strip() for x in args.schemas.split(",") if x.strip()] if args.schemas else []
        if s:
            add(check_schema(s, args.shards))
    if args.mode in ("ledger", "all") and args.ledger:
        add(check_ledger(args.ledger))

    out["overall_pass"] = overall
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
