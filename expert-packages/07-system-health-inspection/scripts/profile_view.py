#!/usr/bin/env python3
"""健康档案查看器 v1.0 —— 输出连续轮次/停滞/自适应建议快照（纯标准库）

用法:
  python3 scripts/profile_view.py [--profile <health_profile.json>]
"""
import sys, json, argparse
from pathlib import Path

DEFAULT = {
    "consecutive_ok": 0, "consecutive_anomaly": 0, "last_score": None,
    "last_metric": None, "stall_rounds": 0, "history": [], "status": "INIT",
}


def main():
    ap = argparse.ArgumentParser(description="健康档案快照查看")
    ap.add_argument("--profile", default="health_profile.json", help="健康档案路径")
    args = ap.parse_args()
    p = Path(args.profile)
    prof = dict(DEFAULT)
    if p.exists():
        try:
            prof = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            print(json.dumps({"status": "ERROR", "reason": str(e)}, ensure_ascii=False))
            return 2
    print(json.dumps(prof, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
