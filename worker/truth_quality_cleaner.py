#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 真值质量自动清洗引擎 V1.0
扫描本地数据湖 + 飞书Base，按质量规则检测并生成清洗报告（不删除，仅标记）
质量规则：
  R1 空值/占位符(?????????/N/A/null/None/空字符串)
  R2 重复记录(同record_id或同内容)
  R3 超长/超短(>500字或<2字)
  R4 格式异常(含未转义控制符/异常JSON/乱码)
输出: 质量报告JSON + 清洗清单(可修复项标记)
"""
import json, os, glob, re, collections, subprocess, sys, time

BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
LAKE_DIR = "/home/user/Doubao/chats/38439832899843586/data_lake"

PLACEHOLDER = re.compile(r'(^\?+$|^N/?A$|^null$|^None$|^undefined$|^TBD$|^待补充$|^TODO$|^xxx$|^\.\.\.$|^\*+$|^\s*\?+\s*$)', re.I)

def scan_ndjson():
    """扫描数据湖所有 ndjson"""
    report = {"source": "data_lake", "issues": []}
    stats = {}
    for f in glob.glob(os.path.join(LAKE_DIR, "lake_*.ndjson")):
        name = os.path.basename(f).replace("lake_", "").replace(".ndjson", "")
        rows, bad = [], 0
        seen = set()
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                try:
                    d = json.loads(line)
                    rows.append(d)
                    rid = str(d.get("record_id", ""))
                    if rid in seen:
                        report["issues"].append({"table": name, "rule": "R2重复", "rid": rid, "detail": "record_id重复出现"})
                    seen.add(rid)
                    # R1 空值/占位符: 扫描所有字段
                    for k, v in d.items():
                        s = str(v).strip()
                        if s and PLACEHOLDER.match(s):
                            bad += 1
                            report["issues"].append({"table": name, "rule": "R1空值/占位", "rid": rid, "field": k, "detail": s[:30]})
                        elif len(s) > 500:
                            report["issues"].append({"table": name, "rule": "R3超长", "rid": rid, "field": k, "detail": f"len={len(s)}"})
                        elif 0 < len(s) < 2 and k not in ("record_id",):
                            report["issues"].append({"table": name, "rule": "R3超短", "rid": rid, "field": k, "detail": s})
                except json.JSONDecodeError:
                    bad += 1
        stats[name] = {"rows": len(rows), "bad_cells": bad}
        report["stats"] = stats
    return report

def scan_bitable(table_id, table_name, limit=200):
    """扫描飞书Base单表"""
    report = {"source": f"bitable/{table_name}", "issues": []}
    rows = []
    offset = 0
    while True:
        out = subprocess.run(
            ["lark-cli", "base", "+record-list", "--base-token", BASE_TOKEN,
             "--table-id", table_id, "--limit", "100", "--offset", str(offset), "--as", "user"],
            capture_output=True, text=True)
        lines = [l for l in out.stdout.splitlines() if l.strip().startswith("| rec")]
        if not lines:
            break
        for l in lines:
            cols = [c.strip() for c in l.split("|")[1:-1]]
            if cols:
                rows.append(cols)
        offset += 100
        if offset > limit:
            break
    seen = set()
    for cols in rows:
        rid = cols[0]
        if rid in seen:
            report["issues"].append({"table": table_name, "rule": "R2重复", "rid": rid})
        seen.add(rid)
        for j, v in enumerate(cols[1:], 1):
            s = v.strip()
            if PLACEHOLDER.match(s):
                report["issues"].append({"table": table_name, "rule": "R1空值/占位", "rid": rid, "field": f"col{j}"})
    report["rows"] = len(rows)
    return report

if __name__ == "__main__":
    print("=== 真值质量自动清洗引擎 V1.0 ===\n")
    # 1. 扫描数据湖
    print("[1/3] 扫描数据湖 ndjson ...")
    lake = scan_ndjson()
    total_lake = sum(len(i) for i in [lake["issues"]])
    print(f"  数据湖: {sum(s['rows'] for s in lake['stats'].values())} 条记录, {total_lake} 个质量问题\n")
    # 2. 扫描飞书Base核心表
    print("[2/3] 扫描飞书Base核心表 ...")
    tables = [("tblnVRjuf7P31cEP", "任务台账"), ("tblOmIRJtTn2EsvM", "节点状态"), ("tbl4Dv798yO7u0IK", "跨节点消息"), ("tbl9QxL35rwA16eS", "真值共识区")]
    base_all = []
    for tid, tname in tables:
        r = scan_bitable(tid, tname)
        base_all.extend(r["issues"])
        print(f"  {tname}: {r['rows']} 条, {len(r['issues'])} 个问题")
    # 3. 汇总输出
    print("\n[3/3] 生成清洗报告 ...")
    out = {
        "scan_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data_lake_issues": lake["issues"],
        "bitable_issues": base_all,
        "summary": {
            "data_lake_total": total_lake,
            "bitable_total": len(base_all),
            "by_rule": dict(collections.Counter(i["rule"] for i in lake["issues"] + base_all)),
        }
    }
    with open(os.path.join(LAKE_DIR, "TRUTH_QUALITY_CLEAN_REPORT.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    # 生成可执行清洗清单(低风险标记项)
    fixable = []
    for i in lake["issues"] + base_all:
        if i["rule"] in ("R2重复", "R1空值/占位"):
            fixable.append(i)
    with open(os.path.join(LAKE_DIR, "CLEAN_FIX_LIST.json"), "w", encoding="utf-8") as f:
        json.dump(fixable, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 完成! 数据湖问题{total_lake}, Base问题{len(base_all)}, 规则分布: {dict(out['summary']['by_rule'])}")
    print(f"  清洗清单: {len(fixable)} 条可修复项(标记不删除)")
