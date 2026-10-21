#!/bin/bash
# 中枢受控 worker 保活（开机自启 + 周期拉起）
# 语义：CNS-DEMO-001 未健康运行（down/stale）时自动 start；已健康则跳过
set -uo pipefail
CTRL="/home/user/ZONGYUAN-ROOT/scripts/worker_controlled.sh"
if bash "$CTRL" status CNS-DEMO-001 2>/dev/null | grep -q "healthy"; then
  echo "[$(date)] CNS-DEMO-001 健康运行，无需拉起"
else
  echo "[$(date)] CNS-DEMO-001 未运行/失联，执行拉起"
  bash "$CTRL" start CNS-DEMO-001
fi
