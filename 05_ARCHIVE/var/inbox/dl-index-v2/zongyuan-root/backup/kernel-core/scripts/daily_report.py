#!/usr/bin/env python3
"""每日健康巡检日报：汇总内核关键状态，落盘 var/reports/ 并写审计。

覆盖：基线状态 / 熔断开关 / 审计规模 / 经验库 / 端口 / 最近审计事件。
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
from kernel.engines.experience import ExperienceDB


def main():
    cfg = Config()
    status, cur, exp = merkle.verify(cfg.path("meta_laws"), cfg.path("baseline_state"))

    report = {
        "report_type": "内核健康巡检日报",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "root": str(cfg.root),
        "baseline_status": status,
        "current_hash": cur,
        "expected_hash": exp,
        "fuse_on_mismatch": cfg.get("fuse_on_hash_mismatch", True),
        "ports": cfg["ports"],
        "allowed_actions": cfg.get("allowed_actions", []),
        "network_egress": "none",
    }

    audit = cfg.path("audit_log")
    if audit.exists():
        lines = audit.read_text(encoding="utf-8").strip().splitlines()
        report["audit_entries"] = len(lines)
        report["recent_audit"] = [json.loads(l) for l in lines[-3:] if l]
    else:
        report["audit_entries"] = 0
        report["recent_audit"] = []

    exp_db = cfg.path("experience_db")
    report["experience_db"] = "present" if exp_db.exists() else "absent"
    if exp_db.exists():
        try:
            report["experience_count"] = ExperienceDB(exp_db).recent(1) and "writable" or "empty"
        except Exception as e:
            report["experience_count"] = f"error:{e}"

    reports_dir = cfg.root / "var" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    fname = f"健康日报-{time.strftime('%Y%m%d')}.json"
    rpath = reports_dir / fname
    rpath.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # 经验沉淀（等价于 reflection 的当日摘要写入经验库）
    exp = ExperienceDB(exp_db)
    exp.add("daily_report", "ok",
            outcome=f"基线={status} 审计={report['audit_entries']}条",
            tags=["daily", "health"], note=rpath.name)

    AuditLog(audit).record("kernel.health", "operator", "report", "ok",
                           f"健康日报 {fname} 基线={status} 审计={report['audit_entries']}条")

    print(f"健康日报: {rpath}")
    print(f"基线: {status}")
    print(f"审计条目: {report['audit_entries']}")
    print(f"经验库: {report['experience_db']}")
    print("对外上报: 无")


if __name__ == "__main__":
    main()
