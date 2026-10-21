#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元法则 Schema 校验门（zongyuan-auto-lock 环节0）
对齐 kernel/core/meta_law.py 的 REQUIRED_KEYS 与 fail-closed 语义：
  - 必需字段: law_id, name, level, clauses
  - clauses 必须是非空 list
防止"新元法则文件写入 meta_laws 目录但 schema 不兼容 → 内核 load_laws 拒启"的断点复发。

用法:
  python3 meta_law_schema_check.py [--dir <meta_laws目录>] [--fix]
    --fix  自动把 {meta_law_id→law_id, core_truth_set→clauses} 转换为兼容 schema（幂等，仅缺字段时补）
退出码: 0=全部通过  1=存在不兼容(未fix)  2=目录不存在
"""
import argparse, json, sys
from pathlib import Path

REQUIRED_KEYS = ("law_id", "name", "level", "clauses")
DEFAULT_DIR = "/home/user/Doubao/chats/38412149511142658/zongyuan-kernel/config/meta_laws"


def convert_compat(law: dict) -> dict:
    """把外部格式（meta_law_id / core_truth_set）转换为内核 schema（幂等）。"""
    out = dict(law)
    if "law_id" not in out and "meta_law_id" in out:
        out["law_id"] = out["meta_law_id"]
    if "clauses" not in out:
        if isinstance(out.get("core_truth_set"), list) and out["core_truth_set"]:
            out["clauses"] = [a.get("axiom", a) for a in out["core_truth_set"]]
        else:
            out["clauses"] = []
    if "level" not in out:
        out["level"] = "P0"
    return out


def check_dir(laws_dir: Path, do_fix: bool):
    if not laws_dir.is_dir():
        print(f"ERROR: 目录不存在 {laws_dir}")
        return 2
    files = sorted(laws_dir.glob("*.json"))
    if not files:
        print("WARN: 目录下无 .json 文件")
        return 0
    all_ok = True
    fixed_any = False
    for f in files:
        try:
            law = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[FAIL] {f.name}: JSON 解析失败: {e}")
            all_ok = False
            continue
        missing = [k for k in REQUIRED_KEYS if k not in law]
        clauses_ok = isinstance(law.get("clauses"), list) and law.get("clauses")
        if not missing and clauses_ok:
            print(f"[PASS] {f.name}")
            continue
        if do_fix:
            fixed = convert_compat(law)
            fm = [k for k in REQUIRED_KEYS if k not in fixed]
            if not fm and isinstance(fixed.get("clauses"), list) and fixed["clauses"]:
                f.write_text(json.dumps(fixed, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[FIXED] {f.name}: 已转换兼容 schema (补 {missing}, clauses={len(fixed['clauses'])})")
                fixed_any = True
                continue
        print(f"[FAIL] {f.name}: 缺少字段 {missing} / clauses 非空list={clauses_ok}")
        all_ok = False
    if fixed_any:
        print("NOTE: 已修复文件需重新 init_baseline.py 重建 Merkle 基线")
    return 0 if all_ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--fix", action="store_true", help="自动转换为兼容 schema")
    args = ap.parse_args()
    rc = check_dir(Path(args.dir), args.fix)
    print(f"SCHEMA_CHECK_EXIT: {rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
