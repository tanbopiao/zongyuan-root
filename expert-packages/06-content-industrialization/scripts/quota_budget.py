#!/usr/bin/env python3
"""免费额度预算管控 v1.0 —— 纯本地记账，不调任何付费 API

维护 providers 字典：{name: {daily_quota, used, priority}}。
提供：
  - register  登记一次消耗（仅本地 +N）
  - status    输出每家剩余/预警状态
  - recommend 按"免费优先 + 剩余多优先"排序推荐下一家供应商

用法:
  python3 scripts/quota_budget.py --state examples/quota.json --register --provider P-A --n 5
  python3 scripts/quota_budget.py --state examples/quota.json --status
  python3 scripts/quota_budget.py --state examples/quota.json --recommend
"""
import os, sys, json, time, argparse
from pathlib import Path


def load_state(path: Path) -> dict:
    if path.exists():
        return json.load(open(path, encoding="utf-8"))
    return {"providers": {}}


def save_state(path: Path, state: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def status_of(p: dict, warn_ratio: float) -> dict:
    quota = float(p.get("daily_quota", 0))
    used = float(p.get("used", 0))
    remain = max(0.0, quota - used)
    if quota <= 0:
        level = "UNKNOWN"
    elif remain <= 0:
        level = "EXHAUSTED"
    elif remain / quota < warn_ratio:
        level = "WARN"
    else:
        level = "OK"
    return {"used": used, "daily_quota": quota, "remaining": round(remain, 2),
            "level": level, "priority": p.get("priority", 99)}


def cmd_register(args) -> int:
    st = load_state(Path(args.state))
    provs = st.setdefault("providers", {})
    p = provs.setdefault(args.provider, {"daily_quota": args.default_quota, "used": 0, "priority": 99})
    p["used"] = float(p.get("used", 0)) + args.n
    save_state(Path(args.state), st)
    out = {"status": "OK", "provider": args.provider, **status_of(p, args.warn_ratio)}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out["level"] != "EXHAUSTED" else 1


def cmd_status(args) -> int:
    st = load_state(Path(args.state))
    rows = {name: status_of(p, args.warn_ratio) for name, p in st.get("providers", {}).items()}
    exhausted = [n for n, s in rows.items() if s["level"] == "EXHAUSTED"]
    print(json.dumps({"providers": rows, "exhausted": exhausted,
                      "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, ensure_ascii=False, indent=1))
    return 0


def cmd_recommend(args) -> int:
    st = load_state(Path(args.state))
    rows = []
    for name, p in st.get("providers", {}).items():
        s = status_of(p, args.warn_ratio)
        if s["level"] != "EXHAUSTED":
            rows.append((s["priority"], -s["remaining"], name, s))
    rows.sort()
    rec = [{"provider": n, **s} for (_, _, n, s) in rows]
    print(json.dumps({"recommendation_order": [r["provider"] for r in rec],
                      "details": rec}, ensure_ascii=False, indent=1))
    return 0 if rec else 1


def main():
    ap = argparse.ArgumentParser(description="免费额度预算管控（本地记账）")
    ap.add_argument("--state", required=True, help="额度状态 JSON 路径")
    ap.add_argument("--register", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--recommend", action="store_true")
    ap.add_argument("--provider", default="")
    ap.add_argument("--n", type=float, default=1.0, help="本次消耗")
    ap.add_argument("--default-quota", type=float, default=100.0)
    ap.add_argument("--warn-ratio", type=float, default=0.2, help="剩余低于此比例告警")
    args = ap.parse_args()

    if args.register:
        if not args.provider:
            print(json.dumps({"status": "ERROR", "reason": "--provider required"}, ensure_ascii=False))
            return 2
        return cmd_register(args)
    if args.status:
        return cmd_status(args)
    if args.recommend:
        return cmd_recommend(args)
    print(json.dumps({"status": "ERROR", "reason": "one of --register/--status/--recommend required"},
                     ensure_ascii=False))
    return 2


if __name__ == "__main__":
    sys.exit(main())
