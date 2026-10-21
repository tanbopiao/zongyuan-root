#!/bin/bash
# ZONGYUAN-ROOT 降级模式 worker 本体（无 docker 时模拟容器 worker）
# 能力：start/stop/status 子命令；后台进程每 60s 更新本地心跳文件；每 10 次心跳上报真值网关
# 用法：
#   worker_local_process.sh start <worker_id>     # 启动降级 worker
#   worker_local_process.sh stop  <worker_id>     # 停止降级 worker
#   worker_local_process.sh status <worker_id>    # 进程存活 + 心跳新鲜度
set -uo pipefail
ROOT="/home/user/ZONGYUAN-ROOT"
WORKER_DIR="$ROOT/var/workers"
mkdir -p "$WORKER_DIR"
DID="DID-BR-000002"
GW="https://www.huodouai.com/api/report/truth"
HEARTBEAT_INTERVAL=60
STALE_AFTER=180   # 心跳超过 180s 视为失联

CMD="${1:-}"; WID="${2:-}"
[ -z "$CMD" ] || [ -z "$WID" ] && { echo "用法: worker_local_process.sh {start|stop|status} <worker_id>"; exit 2; }
PID_FILE="$WORKER_DIR/$WID.pid"
HB_FILE="$WORKER_DIR/$WID.heartbeat"
LOG_FILE="$ROOT/logs/worker_${WID}.log"

start() {
  # ---- 元内核加固自检：校验自身哈希与 worker-hardening.json 一致，防篡改 ----
  HARDENING="/home/user/ZONGYUAN-ROOT/meta-rules/worker-hardening.json"
  if [ -f "$HARDENING" ]; then
    SELF_SHA=$(sha256sum "$0" 2>/dev/null | awk '{print $1}')
    EXPECTED=$(python3 -c "import json;print(json.load(open('$HARDENING'))['scripts'].get('$(basename $0)',''))" 2>/dev/null || echo "")
    if [ -n "$EXPECTED" ] && [ "$SELF_SHA" != "$EXPECTED" ]; then
      echo "HARDENING_BLOCK: 脚本哈希与元内核不一致，拒绝启动（疑似篡改）"
      exit 3
    fi
  fi
  if [ -f "$PID_FILE" ] && ps -p "$(cat "$PID_FILE")" >/dev/null 2>&1; then
    echo "already_running: $WID (pid $(cat "$PID_FILE"))"; exit 0
  fi
  nohup bash -c '
    WID="$1"; PID_FILE="$2"; HB_FILE="$3"; LOG="$4"; GW="$5"; DID="$6"
    echo $$ > "$PID_FILE"
    echo "$(date +%s)" > "$HB_FILE"
    echo "[$(date)] worker $WID 降级模式启动 (pid $$)" >> "$LOG"
    CYCLE=0
    while true; do
      sleep 60
      echo "$(date +%s)" > "$HB_FILE"
      CYCLE=$((CYCLE + 1))
      if [ $((CYCLE % 10)) -eq 0 ]; then
        # 每 10 次心跳上报一次网关（失败不阻塞循环）
        curl -sS -m 15 -X POST "$GW" -H "X-DID: $DID" -H "Content-Type: application/json" \
          --data-binary "{\"key\":\"worker_heartbeat_${DID}_$(date +%s)\",\"value\":{\"event\":\"worker_heartbeat\",\"worker\":\"$WID\",\"mode\":\"degraded_local\",\"pid\":$$,\"ts\":$(date +%s)}}" >> "$LOG" 2>&1 || true
      fi
    done
  ' _ "$WID" "$PID_FILE" "$HB_FILE" "$LOG_FILE" "$GW" "$DID" >/dev/null 2>&1 &
  sleep 2
  if [ -f "$PID_FILE" ] && ps -p "$(cat "$PID_FILE")" >/dev/null 2>&1; then
    echo "started: $WID (pid $(cat "$PID_FILE"), 降级模式)"
  else
    echo "start_failed: $WID"; exit 1
  fi
}

stop() {
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" >/dev/null 2>&1; then kill "$PID" 2>/dev/null || true; fi
    rm -f "$PID_FILE" "$HB_FILE"
    echo "stopped: $WID"
  else
    echo "not_running: $WID"
  fi
}

status() {
  if [ -f "$PID_FILE" ] && ps -p "$(cat "$PID_FILE")" >/dev/null 2>&1; then
    NOW=$(date +%s); LAST=$(cat "$HB_FILE" 2>/dev/null || echo 0)
    AGE=$((NOW - LAST))
    if [ "$AGE" -lt "$STALE_AFTER" ]; then
      echo "healthy: $WID (pid $(cat "$PID_FILE"), 心跳 ${AGE}s 前)"
    else
      echo "stale: $WID (pid $(cat "$PID_FILE"), 心跳 ${AGE}s 前 > ${STALE_AFTER}s)"
    fi
  else
    echo "down: $WID"
  fi
}

case "$CMD" in
  start) start ;;
  stop) stop ;;
  status) status ;;
  *) echo "未知命令: $CMD"; exit 2 ;;
esac
