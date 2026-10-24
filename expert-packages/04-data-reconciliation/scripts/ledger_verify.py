#!/usr/bin/env python3
"""账本 Merkle 完整性校验 v1.0 —— 重算 append-only 账本累积哈希 vs 存储根（纯标准库）

用法:
  python3 scripts/ledger_verify.py --ledger <账本.jsonl> [--state <状态.json>] [--write-state]
"""
import os, sys, json, hashlib, time, argparse
from pathlib import Path


def compute_merkle(ledger: Path) -> str:
    """OP-03 Merkle 根：账本全部行按序累积哈希（0000 起始）"""
    root = "0000"
    lines = 0
    if ledger.exists():
        with open(ledger, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    root = hashlib.sha256((root + line.strip()).encode()).hexdigest()
                    lines += 1
    return root, lines


def main():
    ap = argparse.ArgumentParser(description="账本 Merkle 完整性校验")
    ap.add_argument("--ledger", required=True, help="append-only 账本路径（.jsonl）")
    ap.add_argument("--state", default="", help="状态文件路径（存 merkle_root）")
    ap.add_argument("--write-state", action="store_true", help="将重算根写入状态文件")
    args = ap.parse_args()

    ledger = Path(args.ledger)
    if not ledger.exists():
        print(json.dumps({"status": "ERROR", "reason": "ledger not found"}, ensure_ascii=False))
        return 2

    computed, lines = compute_merkle(ledger)
    stored = ""
    if args.state and Path(args.state).exists():
        stored = json.load(open(args.state, encoding="utf-8")).get("merkle_root", "")

    result = {"computed": computed, "stored": stored, "ledger_lines": lines,
              "consistent": (not stored) or computed == stored,
              "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

    if args.write_state and args.state:
        with open(args.state, "w", encoding="utf-8") as f:
            json.dump({"merkle_root": computed, "ledger_lines": lines,
                       "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, f, ensure_ascii=False, indent=1)
        result["state_written"] = True

    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if result["consistent"] else 1


if __name__ == "__main__":
    sys.exit(main())
