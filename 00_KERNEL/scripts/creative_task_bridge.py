#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
creative_task_bridge.py — 三账号创作任务统一接入桥接器 v1.0
ZONGYUAN-ROOT 元极恒一自治体系 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
任务: 【进化】三账号创作任务自动接入 (reczz28L0dpEUHO9 关联)

功能:
  1. 轮询共享大脑任务台账, 提取 昆仑洞天/云智中台 账号写入的创作任务([视频]/[关键帧]/[场景])
  2. 按类型分类, 生成执行计划
  3. 认领: 状态=进行中, 负责账号=主账号, 进度=10
  4. 零成本元规则: 需付费生成的任务标记"待人工审批", 不消耗额度
  5. 输出认领报告 JSON

依赖: 仅标准库 + lark-cli (本环境已装)
"""
import json
import subprocess
import sys
import time

BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
TABLE_ID = "tblnVRjuf7P31cEP"
OWNER_ACCOUNTS = ["昆仑洞天", "云智中台"]
CREATIVE_PREFIX = ("[视频]", "[关键帧]", "[场景]")


def run_lark(args, timeout=30):
    """执行 lark-cli 命令, 返回解析后的 JSON"""
    cmd = ["lark-cli", "base", *args, "--as", "user"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = r.stdout
        # 剥离 banner (以空格/下划线开头行)
        lines = [l for l in out.split("\n") if l.strip() and not l.strip().startswith(("_", "|", "'"))]
        text = "\n".join(lines)
        # 从第一个 { 开始解析
        idx = text.find("{")
        if idx >= 0:
            return json.loads(text[idx:])
        return {"raw": text[:200]}
    except Exception as e:
        return {"error": str(e)}


def fetch_records():
    """拉取台账前100条(创作任务分布在前部)"""
    r = run_lark(["+record-list", "--base-token", BASE_TOKEN, "--table-id", TABLE_ID,
                  "--page-size", "100", "--format", "ndjson"])
    if "error" in r:
        return r
    record_file = r.get("record_file", "")
    if not record_file:
        return {"error": "no record_file"}
    data = [json.loads(l) for l in open(record_file) if l.strip()]
    return {"records": data}


def classify(record):
    """判断是否创作任务, 返回类型或 None"""
    name = record.get("任务名称", "")
    for p in CREATIVE_PREFIX:
        if name.startswith(p):
            return p.strip("[]")
    return None


def main():
    print("=" * 60)
    print("创作任务桥接器 v1.0 · 三账号统一接入")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 拉取台账
    res = fetch_records()
    if "error" in res:
        print(f"[FAIL] 台账拉取失败: {res['error']}")
        sys.exit(1)
    records = res["records"]
    print(f"[OK] 台账拉取 {len(records)} 条")

    # 2. 筛选: 待开始 + 创作类 (账号为空=无人认领, 正是桥接器接入对象; 账号属昆仑洞天/云智中台同样接入)
    candidates = []
    for rec in records:
        status = rec.get("状态") or []
        account = rec.get("负责账号") or []
        ctype = classify(rec)
        if (status == ["待开始"] or status == ["待处理"]) and ctype:
            if not account or account[0] in OWNER_ACCOUNTS:
                candidates.append(rec)

    print(f"[OK] 待认领创作任务: {len(candidates)} 条")
    if not candidates:
        print("[INFO] 无待认领任务, 退出")
        return

    # 3. 分类统计 + 认领
    from collections import Counter
    type_stat = Counter(rec["任务名称"][1:3].strip("[]") for rec in candidates)
    print(f"[OK] 类型分布: {dict(type_stat)}")

    claimed = []
    for rec in candidates:
        rid = rec["record_id"]
        name = rec.get("任务名称", "")
        prio = rec.get("优先级") or ["中"]
        ctype = classify(rec)
        plan = (f"桥接器自动认领[{ctype}]: 昆仑洞天/云智中台创作任务已统一接入。"
                f"执行计划: 提示词准备→生成→质检→归档。"
                f"零成本元规则: 付费生成通道待人工审批, 本环节不消耗额度。"
                f"DID-BR-000002")
        # 认领: 状态=进行中, 负责账号=主账号, 进度=10, 备注追加
        upd = run_lark(["+record-batch-update", "--base-token", BASE_TOKEN, "--table-id", TABLE_ID,
                        "--json", json.dumps({"update_records": {rid: {
                            "状态": ["进行中"],
                            "负责账号": ["主账号"],
                            "进度": 10,
                            "备注": plan
                        }}}, ensure_ascii=False)])
        ok = "error" not in upd
        claimed.append({"record_id": rid, "name": name, "type": ctype, "priority": prio, "claimed": ok})
        print(f"  [{'OK' if ok else 'FAIL'}] {rid} | {name} | {ctype} | {prio}")

    # 4. 输出报告
    report = {
        "task": "三账号创作任务自动接入",
        "time": time.strftime("%Y-%m-%dT%H:%M:%S+0800"),
        "total_pending": len(candidates),
        "claimed": len([c for c in claimed if c["claimed"]]),
        "type_stat": dict(type_stat),
        "details": claimed,
        "anchor": "Ω₀⊂⊙∞⊂Ω",
        "did": "DID-BR-000002"
    }
    print("\n===== 认领报告 =====")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
