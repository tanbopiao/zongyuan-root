#!/usr/bin/env python3
"""内核状态速览：熔断状态 / 审计摘要 / 基线状态 / 经验库 / 端口。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.core.config import Config
from kernel.core import merkle


def main():
    root_arg = sys.argv[1] if len(sys.argv) > 1 else None
    cfg = Config(root_arg)
    status, cur, exp = merkle.verify(cfg.path("meta_laws"), cfg.path("baseline_state"))

    print(f"内核: {cfg['name']}  根目录: {cfg.root}")
    print(f"哈希基线: {status}" + (f"  ({cur})" if cur else ""))
    print(f"端口: " + ", ".join(f"{k}={v}" for k, v in cfg['ports'].items()))
    print(f"允许动作: {cfg.get('allowed_actions', [])}")
    print(f"熔断开关: fuse_on_hash_mismatch={cfg.get('fuse_on_hash_mismatch', True)}")

    audit = cfg.path("audit_log")
    if audit.exists():
        lines = audit.read_text(encoding="utf-8").strip().splitlines()
        print(f"审计条目: {len(lines)}（最近3条）")
        for ln in lines[-3:]:
            print("  " + ln[:160])
    else:
        print("审计条目: 0")

    exp_db = cfg.path("experience_db")
    print(f"经验库: {exp_db.exists() and '存在' or '未创建'}")

    pid = cfg.path("pid_file")
    print(f"PID文件: {pid.read_text().strip() if pid.exists() else '(未运行)'}")


if __name__ == "__main__":
    main()
