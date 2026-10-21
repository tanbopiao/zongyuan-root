#!/bin/bash
# supervisor 前台 wrapper：中枢受控 worker 循环（保持 worker_controlled.sh status 兼容）
ROOT="/home/user/ZONGYUAN-ROOT"
WID="worker-kernel-001"
PID_FILE="$ROOT/var/workers/$WID.pid"; HB_FILE="$ROOT/var/workers/$WID.heartbeat"
LOG="$ROOT/logs/worker_cns.log"
GW="https://www.huodouai.com/api/report/truth"; DID="DID-BR-000002"
mkdir -p "$ROOT/var/workers"
echo $$ > "$PID_FILE"; echo "$(date +%s)" > "$HB_FILE"
CYCLE=0
while true; do
  sleep 60
  echo "$(date +%s)" > "$HB_FILE"
  CYCLE=$((CYCLE+1))
  if [ $((CYCLE % 10)) -eq 0 ]; then
    curl -sS -m 15 -X POST "$GW" -H "X-DID: $DID" -H "Content-Type: application/json" \
      --data-binary "{\"key\":\"worker_heartbeat_${DID}_$(date +%s)\",\"value\":{\"event\":\"worker_heartbeat\",\"worker\":\"$WID\",\"mode\":\"cns_supervised\",\"pid\":$$,\"ts\":$(date +%s)}}" >> "$LOG" 2>&1 || true
    bash "$ROOT/scripts/worker_api_call.sh" "worker_api_auto_${WID}_$(date +%s)" >> "$LOG" 2>&1 || true
  fi
done
