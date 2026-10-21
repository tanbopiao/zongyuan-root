#!/usr/bin/env python3
"""审计合规周报：扫描 audit.jsonl，统计事件分布/失败率/熔断/越权拒绝，落盘 var/reports/ 并写审计。

纯内部任务，零对外上报。
"""
import collections
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.core.config import Config
from kernel.core.audit import AuditLog


def main():
    cfg = Config()
    audit_path = cfg.path("audit_log")

    events = []
    if audit_path.exists():
        for ln in audit_path.read_text(encoding="utf-8").strip().splitlines():
            if not ln:
                continue
            try:
                events.append(json.loads(ln))
            except Exception:
                pass

    total = len(events)
    by_event = collections.Counter(e.get("event", "?") for e in events)
    by_action = collections.Counter(e.get("action", "?") for e in events)
    fails = sum(1 for e in events if e.get("result") == "fail")
    fuses = sum(1 for e in events if e.get("event") == "state.fuse")
    lock_refusals = sum(1 for e in events if "拒绝" in (e.get("detail") or "") or e.get("event") in ("engine.skip",))

    report = {
        "report_type": "审计合规周报",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "audit_total": total,
        "fail_count": fails,
        "fuse_count": fuses,
        "lock_refusal_count": lock_refusals,
        "fail_rate": round(fails / total, 4) if total else 0,
        "by_event": dict(by_event),
        "by_action": dict(by_action),
        "network_egress": "none",
    }

    reports_dir = cfg.root / "var" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    fname = f"审计周报-{time.strftime('%Y%m%d')}.json"
    fpath = reports_dir / fname
    fpath.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    AuditLog(audit_path).record(
        "kernel.auditreport", "operator", "report", "ok",
        f"审计周报 {fname} 共{total}条 失败{fails} 熔断{fuses} 越权/拒绝{lock_refusals}")

    print(f"审计周报: {fpath}")
    print(f"审计总条数: {total}")
    print(f"失败: {fails} ({report['fail_rate']})  熔断: {fuses}  锁拒绝: {lock_refusals}")
    print("事件分布:", dict(by_event))
    print("对外上报: 无")


if __name__ == "__main__":
    main()
