#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能体编排规划器 v1.0 —— 规模门槛评估 / 分片计划 / 台账合并 schema（纯标准库）

功能：
  evaluate     : 评估任务规模是否达到多智能体并行编排门槛
  shard-plan   : 把互不依赖的流水线单元均衡分到 2-4 个分片
  scan-plan    : 按来源通道生成跨系统并行盘点分片计划
  merge-schema : 输出统一台账合并 schema 骨架

用法:
  python3 plan.py --mode evaluate --objects 8 --dims 5 --channels 4 --units 12 --records 200000
  python3 plan.py --mode shard-plan --units "仓储,工单,合同,代码,文档,数据库,日志,报表" --shards 4
  python3 plan.py --mode scan-plan --root /data --channels nas,wiki,biz-system,doc-lib,db
  python3 plan.py --mode merge-schema
"""
from __future__ import annotations
import os, sys, json, argparse
from datetime import datetime

VERSION = "1.0.0"


def evaluate(objects=0, dims=0, channels=0, units=0, records=0,
             size_gb=0.0, scenarios=0, high_stakes=False, cfg=None):
    """规模门槛评估。返回决策对象。"""
    cfg = cfg or {}
    t_ch = cfg.get("channels_min", 3)
    t_ch_prod = cfg.get("channels_prod", 12)          # channels>=3 且 O×D>=该值
    t_units = cfg.get("units_min", 8)
    t_records_strong = cfg.get("records_strong", 1_000_000)
    t_records_mod = cfg.get("records_moderate", 100_000)
    t_size_strong = cfg.get("size_gb_strong", 20)
    t_size_mod = cfg.get("size_gb_moderate", 2)

    triggers, reasons = [], []
    if high_stakes:
        triggers.append("HIGH_STAKES")
        reasons.append("重大资金承诺或关键业务决策：无条件优先编排")
    if channels >= 5 or (channels >= t_ch and objects * dims >= t_ch_prod):
        triggers.append("MULTI_CHANNEL")
        reasons.append(f"多来源通道检索：channels={channels}, O×D={objects*dims}")
    if scenarios >= 5 or (scenarios >= 3 and objects * dims >= t_ch_prod):
        triggers.append("MULTI_SCENARIO")
        reasons.append(f"多场景并行：scenarios={scenarios}")
    if units >= t_units:
        triggers.append("REPEATED_PIPELINE")
        reasons.append(f"重复独立流水线单元：units={units}")
    if records >= t_records_strong or size_gb >= t_size_strong:
        triggers.append("RESOURCE_HEAVY_STRONG")
        reasons.append(f"资源密集(强)：records={records}, size={size_gb}GB")
    elif records >= t_records_mod or size_gb >= t_size_mod:
        triggers.append("RESOURCE_HEAVY_MODERATE")
        reasons.append(f"资源密集(中)：records={records}, size={size_gb}GB")

    moderate = sum(1 for t in ["MULTI_CHANNEL", "MULTI_SCENARIO",
                               "REPEATED_PIPELINE", "RESOURCE_HEAVY_MODERATE"] if t in triggers)
    strong = sum(1 for t in ["HIGH_STAKES", "RESOURCE_HEAVY_STRONG"] if t in triggers)
    delegate = bool(triggers) and (strong >= 1 or moderate >= 2 or
                                   channels >= 5 or units >= t_units or high_stakes)
    return {
        "should_delegate": delegate,
        "triggers": triggers,
        "reasons": reasons,
        "suggest": "委派编排智能体(Organizer)并行分片" if delegate
                   else "主执行体直接完成（未达门槛）",
        "metrics": {"objects": objects, "dims": dims, "channels": channels,
                    "units": units, "records": records, "size_gb": size_gb},
    }


def shard_plan(units, shards, weights=None, max_share=None):
    """把互不依赖的单元均衡分到 shards 个分片（2-4）；可选按预估权重加权。"""
    shards = max(2, min(4, shards or 3))
    buckets = [[] for _ in range(shards)]
    bucket_w = [0.0] * shards
    if weights and len(weights) == len(units):
        for i, u in enumerate(units):
            k = min(range(shards), key=lambda b: bucket_w[b])
            buckets[k].append(u)
            bucket_w[k] += float(weights[i])
    else:
        for i, u in enumerate(units):
            buckets[i % shards].append(u)
            bucket_w[i % shards] += 1
    total = sum(bucket_w) or 1
    result = {
        "plan_id": f"ORCH-PLAN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "shard_count": shards,
        "unit_count": len(units),
        "shards": [{"shard_id": f"shard-{i+1}", "units": b,
                    "estimated_weight": round(bucket_w[i], 2),
                    "share": round(bucket_w[i] / total, 3)}
                   for i, b in enumerate(buckets)],
    }
    if max_share is not None:
        result["balance_threshold"] = max_share
        result["balance_ok"] = all(s["share"] <= max_share for s in result["shards"])
    return result


def merge_schema():
    return {
        "ledger_version": "1.0",
        "generated_at": None,
        "total_items": 0,
        "by_source": {},
        "items": [{
            "id": None, "name": None, "source": None,
            "type": None, "location": None,
            "size_bytes": None, "last_updated": None,
            "status": None, "gaps": [],
        }],
        "gaps": [], "duplicates": [], "failed_shards": [],
        "provenance": {"plan_id": None, "did": None},
    }


def scan_plan(root, channels):
    chs = [c.strip() for c in channels.split(",") if c.strip()]
    plan = {
        "plan_id": f"ORCH-SCAN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "strategy": "source-channel",
        "root": root,
        "shards": [{"shard_id": "shard-local", "scope": f"本地根目录盘点: {root}",
                    "channel": "local",
                    "pipeline": ["遍历目录树", "统计文件/哈希", "识别重复/缺口", "标准化输出"]}],
        "merge_schema": merge_schema(),
    }
    for ch in chs:
        plan["shards"].append({
            "shard_id": f"shard-{ch}", "scope": f"来源通道盘点: {ch}",
            "channel": ch,
            "pipeline": ["只读清单检索", "统计数量与更新时间", "识别缺口", "标准化输出"],
        })
    plan["shard_count"] = len(plan["shards"])
    return plan


def main():
    ap = argparse.ArgumentParser(description="智能体编排规划器")
    ap.add_argument("--mode", required=True,
                    choices=["evaluate", "shard-plan", "scan-plan", "merge-schema"])
    ap.add_argument("--objects", type=int, default=0)
    ap.add_argument("--dims", type=int, default=0)
    ap.add_argument("--channels", type=str, default="")
    ap.add_argument("--units", type=str, default="")
    ap.add_argument("--weights", type=str, default="")
    ap.add_argument("--shards", type=int, default=0)
    ap.add_argument("--scenarios", type=int, default=0)
    ap.add_argument("--records", type=int, default=0)
    ap.add_argument("--size-gb", type=float, default=0.0)
    ap.add_argument("--max-share", type=float, default=0.40)
    ap.add_argument("--high-stakes", action="store_true")
    ap.add_argument("--root", type=str, default=os.getcwd())
    args = ap.parse_args()

    ch = len([c for c in args.channels.split(",") if c.strip()]) if args.channels else 0
    if args.mode == "evaluate":
        units = [u for u in args.units.split(",") if u.strip()] if args.units else []
        print(json.dumps(evaluate(objects=args.objects, dims=args.dims, channels=ch,
                                  units=len(units), records=args.records,
                                  size_gb=args.size_gb, scenarios=args.scenarios,
                                  high_stakes=args.high_stakes),
                         ensure_ascii=False, indent=2))
    elif args.mode == "shard-plan":
        units = [u.strip() for u in args.units.split(",") if u.strip()]
        w = [float(x) for x in args.weights.split(",") if x.strip()]
        if not units:
            print(json.dumps({"error": "需要 --units 指定独立单元，逗号分隔"}, ensure_ascii=False)); sys.exit(2)
        print(json.dumps(shard_plan(units, args.shards, w or None, args.max_share),
                         ensure_ascii=False, indent=2))
    elif args.mode == "scan-plan":
        if not args.channels:
            print(json.dumps({"error": "需要 --channels，如 nas,wiki,biz-system,doc-lib,db"},
                             ensure_ascii=False)); sys.exit(2)
        print(json.dumps(scan_plan(args.root, args.channels), ensure_ascii=False, indent=2))
    elif args.mode == "merge-schema":
        print(json.dumps(merge_schema(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
