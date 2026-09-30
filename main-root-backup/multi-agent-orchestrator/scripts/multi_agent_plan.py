#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
昆仑洞天多智能体编排规划器 v1.0
Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZONGYUAN-ROOT

功能：
  - evaluate    : 评估任务规模是否达到多智能体编排门槛
  - scan-plan   : 生成跨平台全维资产扫描分片计划
  - merge-schema: 生成统一台账合并schema骨架
  - shard-plan  : 独立流水线单元分片规划（2-4个平衡分片）

用法:
    python3 multi_agent_plan.py --mode evaluate --objects 8 --dims 5 --channels 4 --units 12
    python3 multi_agent_plan.py --mode scan-plan --root <ZONGYUAN-ROOT路径> --channels drive,wiki,base,doc,sheet
    python3 multi_agent_plan.py --mode shard-plan --units "a,b,c,d,e,f,g,h" --shards 4
"""
from __future__ import annotations
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

DID = "DID-BR-000002"
TRACE_SYMBOL = "Ω₀⊂⊙∞⊂Ω"
VERSION = "1.0.0"


# ============================================================
# 委派门槛判定（对应 SKILL 第三章）
# ============================================================
def evaluate(**kw):
    """多智能体编排触发评估。返回决策对象。"""
    objects = kw.get("objects", 0)      # O 对象数/候选数
    dims = kw.get("dims", 0)            # D 实质维度数
    channels = kw.get("channels", 0)    # C 独立来源通道数
    units = kw.get("units", 0)          # U 独立流水线单元数
    records = kw.get("records", 0)      # N 记录数
    size_gb = kw.get("size_gb", 0)      # B 总体积GB
    scenarios = kw.get("scenarios", 0)  # 场景数(多场景检索)
    high_stakes = kw.get("high_stakes", False)  # 重大资金/人生转折

    triggers = []
    reasons = []

    # 重大资金/人生转折 —— 独立无条件触发
    if high_stakes:
        triggers.append("HIGH_STAKES")
        reasons.append("重大资金承诺或人生转折决策：无条件优先编排")

    # 多通道/平台研究
    if channels >= 5 or (channels >= 3 and objects * dims >= 12):
        triggers.append("MULTI_CHANNEL")
        reasons.append(f"多通道检索：channels={channels}, O×D={objects*dims}")

    # 多场景研究
    if scenarios >= 5 or (scenarios >= 3 and objects * dims >= 12):
        triggers.append("MULTI_SCENARIO")
        reasons.append(f"多场景研究：scenarios={scenarios}")

    # 重复独立流水线
    if units >= 20 or (units >= 8):
        # 每个单元需≥2个实质阶段(采集+处理/分析/校验)才计为流水线单元
        triggers.append("REPEATED_PIPELINE")
        reasons.append(f"重复独立流水线：units={units}")

    # 资源密集型
    if records >= 1_000_000 or size_gb >= 20:
        triggers.append("RESOURCE_HEAVY_STRONG")
        reasons.append(f"资源密集强：records={records}, size={size_gb}GB")
    elif records >= 100_000 or size_gb >= 2:
        triggers.append("RESOURCE_HEAVY_MODERATE")
        reasons.append(f"资源密集中：records={records}, size={size_gb}GB")

    moderate_count = sum(1 for t in ["MULTI_CHANNEL", "MULTI_SCENARIO", "REPEATED_PIPELINE", "RESOURCE_HEAVY_MODERATE"]
                         if t in triggers)
    strong_count = sum(1 for t in ["HIGH_STAKES", "MULTI_CHANNEL", "MULTI_SCENARIO", "REPEATED_PIPELINE", "RESOURCE_HEAVY_STRONG"]
                       if t in triggers and t not in ["MULTI_CHANNEL"]) 

    decision = {
        "should_delegate": bool(triggers) or moderate_count >= 2 or strong_count >= 1,
        "triggers": triggers,
        "reasons": reasons,
        "suggest": "委派编排智能体(OrganizerAgent)" if (triggers or moderate_count >= 2) else "主智能体直接执行",
    }
    return decision


# ============================================================
# 全维扫描分片计划
# ============================================================
def scan_plan(root: str, channels: str):
    """生成跨平台资产扫描分片计划（每个通道一个分片 + 本地根分片）。"""
    channel_list = [c.strip() for c in channels.split(",") if c.strip()]
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
    plan = {
        "plan_id": f"MAO-SCAN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "did": DID,
        "trace": TRACE_SYMBOL,
        "generated_at": now,
        "strategy": "platform-channel",
        "local_root": root,
        "shards": [],
    }
    # 本地内核分片
    plan["shards"].append({
        "shard_id": "shard-local-root",
        "scope": f"本地 ZONGYUAN-ROOT 内核资产扫描：{root}",
        "channel": "local",
        "pipeline": ["遍历目录树", "统计文件/快照/哈希账本", "识别未归档/临时/重复/空目录", "标准化输出"],
    })
    # 各通道分片
    for ch in channel_list:
        plan["shards"].append({
            "shard_id": f"shard-{ch}",
            "scope": f"飞书通道扫描：{ch}",
            "channel": ch,
            "pipeline": ["读技能规范", "只读清单检索", "统计数量与更新时间", "识别缺口", "标准化输出"],
        })
    plan["shard_count"] = len(plan["shards"])
    plan["merge_schema"] = merge_schema()
    return plan


# ============================================================
# 统一台账 schema
# ============================================================
def merge_schema():
    return {
        "ledger_version": "1.0",
        "generated_at": None,
        "total_assets": 0,
        "by_source": {
            "local_kernel": 0, "drive": 0, "wiki": 0,
            "base": 0, "doc": 0, "sheet": 0
        },
        "assets": [
            {
                "id": None, "name": None, "source": None,
                "type": None, "location_url": None,
                "size_bytes": None, "last_updated": None,
                "status": None, "gaps": []
            }
        ],
        "gaps": [],
        "duplicates": [],
        "unsynced_local_locked": []
    }


# ============================================================
# 独立流水线单元分片（平衡分片 2-4）
# ============================================================
def shard_plan(units: list, shards: int):
    """把互不依赖的流水线单元均衡分到 shards 个分片中。"""
    shards = max(2, min(4, shards))  # 标准分片 2-4
    n = len(units)
    buckets = [[] for _ in range(shards)]
    # 简单轮转均衡分配（保持各分片单元数平衡）
    for i, u in enumerate(units):
        buckets[i % shards].append(u)
    result = {
        "shards": [{"shard_id": f"shard-{i+1}", "units": b} for i, b in enumerate(buckets)],
        "shard_count": shards,
        "unit_count": n,
    }
    return result


# ============================================================
# main
# ============================================================
def main():
    ap = argparse.ArgumentParser(description="昆仑洞天多智能体编排规划器")
    ap.add_argument("--mode", required=True, choices=["evaluate", "scan-plan", "shard-plan", "merge-schema"])
    ap.add_argument("--objects", type=int, default=0)
    ap.add_argument("--dims", type=int, default=0)
    ap.add_argument("--channels", type=str, default="")
    ap.add_argument("--units", type=str, default="")
    ap.add_argument("--shards", type=int, default=0)
    ap.add_argument("--scenarios", type=int, default=0)
    ap.add_argument("--records", type=int, default=0)
    ap.add_argument("--size-gb", type=float, default=0.0)
    ap.add_argument("--high-stakes", action="store_true")
    ap.add_argument("--root", type=str, default=os.getcwd())
    args = ap.parse_args()

    if args.mode == "evaluate":
        ch = len([c for c in args.channels.split(",") if c.strip()]) if args.channels else 0
        dec = evaluate(objects=args.objects, dims=args.dims, channels=ch,
                       units=args.units.count(",") + 1 if args.units else 0,
                       records=args.records, size_gb=args.size_gb,
                       scenarios=args.scenarios, high_stakes=args.high_stakes)
        print(json.dumps(dec, ensure_ascii=False, indent=2))

    elif args.mode == "scan-plan":
        if not args.channels:
            print(json.dumps({"error": "需要 --channels 指定扫描通道，如 drive,wiki,base,doc,sheet"}, ensure_ascii=False))
            return
        plan = scan_plan(args.root, args.channels)
        print(json.dumps(plan, ensure_ascii=False, indent=2))

    elif args.mode == "shard-plan":
        if not args.units:
            print(json.dumps({"error": "需要 --units 指定独立单元，用逗号分隔"}, ensure_ascii=False))
            return
        units = [u.strip() for u in args.units.split(",") if u.strip()]
        res = shard_plan(units, args.shards or 3)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.mode == "merge-schema":
        print(json.dumps(merge_schema(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
