#!/usr/bin/env bash
# intent-drift-guard 启动脚本 —— 拉起可观测面板接口(metrics) + 运行态信息
# 用法: bash scripts/start.sh [工作目录] [端口]     默认: ./var  8120
set -euo pipefail
cd "$(dirname "$0")/.."

WORKDIR="${1:-./var}"
PORT="${2:-8120}"
GOAL="${GOAL:-生成2026年四季度市场分析报告；必须覆盖出货量与价格趋势；不得超过50页；截止2026-12-31；交付标准为结构完整、结论可溯源}"

mkdir -p "$WORKDIR"
echo "启动 intent-drift-guard (挂载形态: 服务常驻 = 面板接口 + 防控就绪)"
PYTHONPATH=. WORKDIR="$WORKDIR" PORT="$PORT" GOAL="$GOAL" python3 - <<'PY'
import os, sys, time
from intent_drift_guard import IntentDriftGuard

workdir = os.environ["WORKDIR"]
port = int(os.environ["PORT"])
guard = IntentDriftGuard("service-default", os.environ["GOAL"], workdir=workdir)
thread = guard.metrics.serve(port=port)
snap = guard.stats()
print(f"[OK] metrics endpoint: http://127.0.0.1:{port}/metrics (daemon={thread.is_alive()})")
print(f"[OK] anchor locked: {snap['anchor']['core_target'][:40]}...")
print(f"[OK] embedding backend: {snap['semantic'].get('embedding_backend', 'lazy')}")
print(f"[OK] circuit state: {snap['circuit']['state']}")
print("[..] 常驻运行, Ctrl+C 停止")
try:
    while True:
        time.sleep(3600)
except KeyboardInterrupt:
    print("stopped.")
    sys.exit(0)
PY
