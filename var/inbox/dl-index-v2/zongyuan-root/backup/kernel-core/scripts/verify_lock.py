#!/usr/bin/env python3
"""每日锁档复核：verify 元法则 Merkle 基线，结果写审计 + 复核凭证。

纯内部任务，零对外上报。
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.core.config import Config
from kernel.core import merkle
from kernel.core.audit import AuditLog


def main():
    cfg = Config()
    status, cur, exp = merkle.verify(cfg.path("meta_laws"), cfg.path("baseline_state"))

    cert = {
        "cert_type": "锁档复核凭证",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "baseline_status": status,
        "current_hash": cur,
        "expected_hash": exp,
        "scope": "meta_laws",
    }

    lock_dir = cfg.root / "var" / "lock"
    lock_dir.mkdir(parents=True, exist_ok=True)
    fname = f"锁档复核-{time.strftime('%Y%m%d-%H%M%S')}.json"
    fpath = lock_dir / fname
    fpath.write_text(json.dumps(cert, ensure_ascii=False, indent=2), encoding="utf-8")

    AuditLog(cfg.path("audit_log")).record(
        "kernel.lockcheck", "operator", "verify", "ok" if status == "ok" else "fail",
        f"锁档复核 {status} 凭证={fname}")

    print(f"复核状态: {status}")
    print(f"凭证: {fpath}")
    if status != "ok":
        sys.exit(1)


if __name__ == "__main__":
    main()
