#!/usr/bin/env python3
"""因果图快照：导出 CausalDAG 动作依赖，归档到 var/reports/ 并写审计。

纯内部任务，零对外上报。
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.core.config import Config
from kernel.core.causal import CausalDAG
from kernel.core.audit import AuditLog


def main():
    cfg = Config()
    dag = CausalDAG()

    snap = {
        "snapshot_type": "因果图快照",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "edges": {a: deps for a, deps in dag.edges.items()},
        "node_count": len(dag.edges),
        "network_egress": "none",
    }

    reports_dir = cfg.root / "var" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    fname = f"因果图快照-{time.strftime('%Y%m%d-%H%M%S')}.json"
    fpath = reports_dir / fname
    fpath.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")

    AuditLog(cfg.path("audit_log")).record(
        "kernel.causal", "operator", "snapshot", "ok",
        f"因果图快照 {fname} 节点={snap['node_count']}")

    print(f"因果图快照: {fpath}")
    for a, deps in dag.edges.items():
        print(f"  {a} -> {deps}")
    print("对外上报: 无")


if __name__ == "__main__":
    main()
