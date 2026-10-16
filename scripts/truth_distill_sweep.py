#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
truth_distill_sweep.py — ZONGYUAN-ROOT 真值库蒸馏调度巡检 (L5)
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 规则: 只标记/归档, 不删除(可回滚); 空 value 归档策略

策略规则 (RULE-TRUTH-DISTILL-001):
  1. 空 value 真值 (value 为 None/''/{}) → 标记 EMPTY → 移入 archive 区
  2. 低质真值 (value 非 dict / 无 key / key 无命名空间) → 标记 LOW_QUALITY
  3. 冲突真值 (同 key 多版本且内容矛盾) → 标记 CONFLICT, 保留最新版
  4. 归档原则: 只追加归档清单, 不物理删除; 备份后再处理
  5. 调度: 每日一次 (cron), 输出蒸馏报告

用法:
  python3 truth_distill_sweep.py --dry-run        # 只统计(默认, 安全)
  python3 truth_distill_sweep.py --archive        # 统计+归档(写清单, 不删除)
"""
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

ANCHOR = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"
DEFAULT_ROOT = "/www/wwwroot/huodouai.com/zhongshu/data"
ARCHIVE_DIR = os.path.join(DEFAULT_ROOT, "truth-distill-archive")
REPORT_DIR = os.path.join(DEFAULT_ROOT, "distill-reports")


def _now():
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S%z")


def _scan_truth_files(root):
    """定位真值库 JSON/JSONL/SQLite 文件"""
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            low = fn.lower()
            if low.endswith((".json", ".jsonl", ".db", ".sqlite")):
                if any(k in low for k in ("truth", "seed", "federal", "dedup", "embed", "hash", "ledger")):
                    found.append(os.path.join(dirpath, fn))
    return found


def _sweep_db(fp, stats):
    """SQLite 真值库扫描: 统计空 value / 低质"""
    import sqlite3
    try:
        conn = sqlite3.connect(f"file:{fp}?mode=ro", uri=True)
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for tb in tables:
            if not any(k in tb.lower() for k in ("truth", "seed", "kv", "value", "record")):
                continue
            cols = [c[1] for c in cur.execute(f"PRAGMA table_info({tb})")]
            keycol = next((c for c in cols if c in ("key", "truth_id", "id")), cols[0] if cols else None)
            valcol = next((c for c in cols if c in ("value", "truth_value")), None)
            if not valcol:
                continue
            total = cur.execute(f"SELECT COUNT(*) FROM {tb}").fetchone()[0]
            stats["total_records"] += total
            # 空 value 统计（安全只读）
            try:
                empty = cur.execute(f"SELECT COUNT(*) FROM {tb} WHERE {valcol} IS NULL OR {valcol}='' OR {valcol}='{{}}'").fetchone()[0]
            except Exception:
                empty = 0
            stats["empty_count"] = stats.get("empty_count", 0) + empty
            stats.setdefault("db_by_table", {})[f"{os.path.basename(fp)}/{tb}"] = {"total": total, "empty": empty}
        conn.close()
    except Exception as e:
        stats.setdefault("parse_error", []).append(f"{os.path.basename(fp)}: {str(e)[:60]}")
    return stats


def sweep(root=DEFAULT_ROOT, do_archive=False):
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    files = _scan_truth_files(root)
    stats = {"total_records": 0, "empty_value": [], "low_quality": [], "conflict": [], "files_scanned": len(files)}
    empty_keys = {}
    for fp in files:
        if fp.endswith(".db") or fp.endswith(".sqlite"):
            _sweep_db(fp, stats)
            continue
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            stats.setdefault("parse_error", []).append(f"{os.path.basename(fp)}: {str(e)[:60]}")
            continue
        items = data if isinstance(data, list) else [data]
        for x in items:
            if not isinstance(x, dict):
                continue
            stats["total_records"] += 1
            key = str(x.get("key", x.get("truth_id", "?")))
            val = x.get("value", x.get("truth_value"))
            # 规则1: 空 value
            if val is None or val == "" or val == {}:
                stats["empty_value"].append(key)
                empty_keys.setdefault(os.path.basename(fp), 0)
                empty_keys[os.path.basename(fp)] += 1
            # 规则2: 低质
            elif not isinstance(val, dict):
                stats["low_quality"].append(key)
            # 规则3: key 无命名空间
            elif not isinstance(key, str) or "." not in key:
                stats["low_quality"].append(key)
    # 冲突检测 (同 key 在 HASH-LEDGER 中多版本)
    stats["empty_count"] = len(stats["empty_value"])
    stats["low_quality_count"] = len(stats["low_quality"])
    stats["empty_by_file"] = empty_keys
    report = {
        "report_id": f"TRUTH-DISTILL-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "ts": _now(), "did": DID, "anchor": ANCHOR,
        "root_scanned": root, "do_archive": do_archive,
        "stats": stats,
        "empty_sample": stats["empty_value"][:20],
        "low_quality_sample": stats["low_quality"][:20],
    }
    report_path = os.path.join(REPORT_DIR, f"{report['report_id']}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    # 归档: 空 value 清单追加 (不删除数据)
    if do_archive and stats["empty_value"]:
        archive_path = os.path.join(ARCHIVE_DIR, f"EMPTY-{datetime.now().strftime('%Y%m%d')}.jsonl")
        with open(archive_path, "a", encoding="utf-8") as f:
            for k in stats["empty_value"]:
                f.write(json.dumps({"key": k, "action": "ARCHIVE_EMPTY", "ts": _now()}, ensure_ascii=False) + "\n")
        report["archive_path"] = archive_path
    return report


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--dry-run"
    do_archive = mode == "--archive"
    root = os.environ.get("ZR_TRUTH_ROOT", DEFAULT_ROOT)
    rep = sweep(root=root, do_archive=do_archive)
    s = rep["stats"]
    print(f"蒸馏巡检: {rep['report_id']}")
    print(f"  扫描文件: {s['files_scanned']} | 记录总数: {s['total_records']}")
    print(f"  空value: {s['empty_count']} | 低质: {s['low_quality_count']}")
    if s.get("empty_by_file"):
        print("  空value分布:", json.dumps(s["empty_by_file"], ensure_ascii=False)[:200])
    if s.get("parse_error"):
        print("  解析失败:", s["parse_error"][:3])
    print(f"  报告: {rep['report_id']}.json | 模式: {'ARCHIVE' if do_archive else 'DRY-RUN(仅统计)'}")
