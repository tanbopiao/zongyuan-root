#!/usr/bin/env python3
"""记忆检索（MemoryQuery）：把 experience.db + audit.jsonl 变成可检索的结构化记忆。

用法：
  memory_query.py <keyword> [--limit N] [--since YYYY-MM-DD] [--source all|experience|audit]
示例：
  memory_query.py fuse --limit 10            # 检索所有熔断相关记忆
  memory_query.py truth --since 2026-09-26   # 检索真值积累相关审计
"""
import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "var" / "state" / "experience.db"
AUDIT = ROOT / "var" / "audit" / "audit.jsonl"


def query_experience(keyword, limit, since_ts=None):
    out = []
    if not EXP.exists():
        return out, "experience.db 不存在"
    try:
        with sqlite3.connect(EXP) as con:
            sql = ("SELECT action, result, outcome, tags, note, created_at FROM experiences "
                   "WHERE (action LIKE ? OR result LIKE ? OR outcome LIKE ? OR tags LIKE ? OR note LIKE ?)")
            like = f"%{keyword}%"
            args = [like] * 5
            if since_ts:
                sql += " AND created_at >= ?"
                args.append(since_ts)
            sql += " ORDER BY created_at DESC LIMIT ?"
            args.append(limit)
            rows = con.execute(sql, args).fetchall()
        cols = ["action", "result", "outcome", "tags", "note", "created_at"]
        for r in rows:
            out.append(dict(zip(cols, r)))
    except Exception as e:
        return out, f"查询失败: {e}"
    return out, None


def query_audit(keyword, limit, since=None):
    out = []
    if not AUDIT.exists():
        return out, "audit.jsonl 不存在"
    try:
        n = 0
        for line in reversed(AUDIT.read_text(encoding="utf-8").splitlines()):
            if n >= limit:
                break
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if since and rec.get("ts", "")[:10] < since:
                continue
            blob = json.dumps(rec, ensure_ascii=False)
            if keyword.lower() in blob.lower():
                out.append({"ts": rec.get("ts"), "event": rec.get("event"),
                            "actor": rec.get("actor"), "action": rec.get("action"),
                            "result": rec.get("result"), "detail": rec.get("detail")})
                n += 1
    except Exception as e:
        return out, f"审计读取失败: {e}"
    return out, None


def main():
    ap = argparse.ArgumentParser(description="结构化记忆检索")
    ap.add_argument("keyword")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--since", default=None, help="YYYY-MM-DD")
    ap.add_argument("--source", choices=["all", "experience", "audit"], default="all")
    args = ap.parse_args()
    since_ts = f"{args.since} 00:00:00" if args.since else None

    result = {"keyword": args.keyword, "query_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "hits": {}}
    if args.source in ("all", "experience"):
        exp, err = query_experience(args.keyword, args.limit, since_ts)
        result["hits"]["experience"] = {"count": len(exp), "rows": exp, "error": err}
    if args.source in ("all", "audit"):
        aud, err = query_audit(args.keyword, args.limit, args.since)
        result["hits"]["audit"] = {"count": len(aud), "rows": aud, "error": err}
    total = sum(v["count"] for v in result["hits"].values())
    result["total_hits"] = total
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n=== 命中 {total} 条（experience={result['hits'].get('experience',{}).get('count',0)} / audit={result['hits'].get('audit',{}).get('count',0)}）===", file=sys.stderr)


if __name__ == "__main__":
    main()
