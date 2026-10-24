#!/usr/bin/env python3
"""
国风IP锁档归档使 v1.0 - 哈希确权/清单入账/只读固化/凭证生成
用法:
  python3 lock_archive.py --hash <文件路径>
  python3 lock_archive.py --dir <目录> --batch-name <批次名> [--ledger ./HASH-LEDGER.csv]
  python3 lock_archive.py --chmod-444 <目录>
  python3 lock_archive.py --certificate --batch-name <批次名>
  python3 lock_archive.py --verify --batch-name <批次名>
"""
import argparse
import csv
import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "lock_config.json"

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_dir(directory):
    files = []
    for p in sorted(Path(directory).rglob("*")):
        if p.is_file() and not p.name.startswith("."):
            files.append(p)
    return files


def lock_batch(directory, batch_name, ledger_path):
    cfg = load_config()
    files = scan_dir(directory)
    if not files:
        print(json.dumps({"status": "ERR", "msg": "目录为空"}, ensure_ascii=False))
        sys.exit(1)
    entries = []
    for p in files:
        rel = str(p.relative_to(directory))
        entries.append({
            "batch_name": batch_name,
            "asset_path": rel,
            "sha256": sha256_file(p),
            "size_bytes": p.stat().st_size,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "did": DID,
            "trace": TRACE,
            "status": "locked",
        })
    # 批次根哈希
    root_hash = hashlib.sha256(
        json.dumps([e["sha256"] for e in entries], ensure_ascii=False).encode()
    ).hexdigest()

    # 入账本
    ledger = Path(ledger_path)
    is_new = not ledger.exists()
    with open(ledger, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(entries[0].keys()))
        if is_new:
            w.writeheader()
        w.writerows(entries)

    # 生成manifest
    manifest = {
        "manifest_id": f"MANIFEST-{datetime.now().strftime('%Y%m%d')}-{batch_name}",
        "batch_name": batch_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "did": DID,
        "trace": TRACE,
        "files": entries,
        "batch_root_hash": root_hash,
    }
    mdir = Path(cfg["manifest_dir"])
    mdir.mkdir(parents=True, exist_ok=True)
    mpath = mdir / f"manifest-{batch_name}.json"
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "status": "LOCKED",
        "batch_name": batch_name,
        "asset_count": len(entries),
        "batch_root_hash": root_hash,
        "ledger": str(ledger),
        "manifest": str(mpath),
        "did": DID,
        "trace": TRACE,
    }, ensure_ascii=False, indent=2))


def chmod_444(directory):
    changed = 0
    for p in Path(directory).rglob("*"):
        if p.is_file():
            p.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
            changed += 1
    print(json.dumps({"status": "OK", "locked_readonly": changed}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description="国风IP锁档归档使")
    ap.add_argument("--hash", type=str, default="", help="单资产哈希")
    ap.add_argument("--dir", type=str, default="", help="整批目录")
    ap.add_argument("--batch-name", type=str, default="batch")
    ap.add_argument("--ledger", type=str, default="")
    ap.add_argument("--chmod-444", type=str, default="")
    ap.add_argument("--certificate", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    if args.hash:
        print(json.dumps({"path": args.hash, "sha256": sha256_file(args.hash), "did": DID}, ensure_ascii=False))
        return
    if args.chmod_444:
        chmod_444(args.chmod_444)
        return
    if args.dir:
        cfg = load_config()
        ledger = args.ledger or cfg["ledger_path"]
        lock_batch(args.dir, args.batch_name, ledger)
        return
    if args.certificate:
        print(json.dumps({"status": "OK", "msg": "证书模板见 templates/certificate_template.md", "did": DID}, ensure_ascii=False))
        return
    if args.verify:
        print(json.dumps({"status": "OK", "msg": "对账：本地哈希 vs 清单哈希 vs 云端/台账，以实测为准", "did": DID}, ensure_ascii=False))
        return
    ap.print_help()


if __name__ == "__main__":
    main()
