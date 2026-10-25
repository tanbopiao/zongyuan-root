#!/usr/bin/env python3
"""汇总编排执行结果（JSONL）为结构化执行报告（JSON + Markdown）。

用法：
  python3 summarize_run.py results.jsonl [--out report.md] [--plan plan.json]
结果 JSONL 每行：{"unit": "u1", "status": "ok|fail|skipped", "output": "...", "path": "/abs/path"}
--plan 可选：合并计划字段到报告。
"""
import argparse
import json
import sys
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", help="执行结果 JSONL 路径或 -")
    ap.add_argument("--out", default="-", help="输出 Markdown 路径，默认 stdout")
    ap.add_argument("--plan", help="可选计划 JSON 路径")
    args = ap.parse_args()

    rows = []
    if args.results == "-":
        src = sys.stdin
    else:
        src = open(args.results, encoding="utf-8")
    with src as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    counts = {"ok": 0, "fail": 0, "skipped": 0}
    for r in rows:
        counts[r.get("status", "?")] = counts.get(r.get("status", "?"), 0) + 1

    plan_meta = {}
    if args.plan:
        with open(args.plan, encoding="utf-8") as f:
            plan_meta = json.load(f)

    report = {
        "report_type": "智能编排执行报告",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "goal": plan_meta.get("goal", ""),
        "summary": counts,
        "units": rows,
    }
    md = []
    md.append(f"# 智能编排执行报告\n")
    md.append(f"- 目标：{plan_meta.get('goal', '(未提供)')}")
    md.append(f"- 生成时间：{report['generated_at']}")
    md.append(f"- 汇总：✅ 成功 {counts.get('ok', 0)} ｜ ❌ 失败 {counts.get('fail', 0)} ｜ ⏭ 跳过 {counts.get('skipped', 0)}\n")
    md.append("| 单元 | 状态 | 产物 | 说明 |")
    md.append("|---|---|---|---|")
    for r in rows:
        mark = {"ok": "✅", "fail": "❌", "skipped": "⏭"}.get(r.get("status"), "❓")
        out = (r.get("output") or "")[:60].replace("|", "/")
        path = r.get("path") or ""
        md.append(f"| {r.get('unit','?')} | {mark} {r.get('status')} | `{path}` | {out} |")
    md.append("\n> 遗留/阻塞项以各单元 output 与验证为准。")

    text = "\n".join(md)
    if args.out == "-":
        print(text)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        with open(args.out.rsplit(".", 1)[0] + ".json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"报告已写入: {args.out} (+ .json)")
    return 0 if counts.get("fail", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
