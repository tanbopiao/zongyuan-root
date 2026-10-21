#!/bin/bash
# ZONGYUAN-ROOT 中枢受控 worker（CNS-Controlled）
# 遵循《worker进化模型与锁档边界》〇之一条款：
#   1) 接受中枢智能管控；2) 与中枢心跳同步；3) 中枢保有 kill-switch（fail-closed：中枢不可达→idle 不执行）
# 能力：上行心跳（真值网关）｜下行中枢指令拉取（飞书任务台账）｜受控执行（idle/executing）
# 用法：worker_controlled.sh {start|stop|status} <worker_id>
set -uo pipefail
ROOT="/home/user/ZONGYUAN-ROOT"
WORKER_DIR="$ROOT/var/workers"
mkdir -p "$WORKER_DIR"
DID="DID-BR-000002"
GW="https://www.huodouai.com/api/report/truth"
BASE="DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE="tblnVRjuf7P31cEP"
HB_INTERVAL=60
PULL_EVERY=5      # 每 5 次心跳拉取一次中枢指令

CMD="${1:-}"; WID="${2:-}"
[ -z "$CMD" ] || [ -z "$WID" ] && { echo "用法: worker_controlled.sh {start|stop|status} <worker_id>"; exit 2; }
PID_FILE="$WORKER_DIR/$WID.pid"
HB_FILE="$WORKER_DIR/$WID.heartbeat"
CNS_FILE="$WORKER_DIR/$WID.cns"
LOG_FILE="$ROOT/logs/worker_${WID}.log"

start() {
  # ---- 元内核加固自检：校验自身哈希与 worker-hardening.json 一致，防篡改 ----
  HARDENING="/home/user/ZONGYUAN-ROOT/meta-rules/worker-hardening.json"
  if [ -f "$HARDENING" ]; then
    SELF_SHA=$(sha256sum "$0" 2>/dev/null | awk '{print $1}')
    EXPECTED=$(python3 -c "import json;print(json.load(open('$HARDENING'))['scripts'].get('$(basename $0)',''))" 2>/dev/null || echo "")
    if [ -n "$EXPECTED" ] && [ "$SELF_SHA" != "$EXPECTED" ]; then
      echo "HARDENING_BLOCK: 脚本哈希与元内核不一致，拒绝启动（疑似篡改）"
      bash /home/user/ZONGYUAN-ROOT/scripts/worker_ntfy_alert.sh HARDENING_BLOCK "worker 哈希自检失败，拒绝启动（疑似篡改）" >> "$LOG" 2>&1 || true
      exit 3
    fi
  fi
  if [ -f "$PID_FILE" ] && ps -p "$(cat "$PID_FILE")" >/dev/null 2>&1; then
    echo "already_running: $WID (pid $(cat "$PID_FILE"))"; exit 0
  fi
  nohup bash /home/user/ZONGYUAN-ROOT/scripts/worker_daemon.sh "$WID" "$(dirname "$PID_FILE")" "$LOG_FILE" "$GW" "$DID" "$BASE" "$TASK_TABLE" >/dev/null 2>&1 &
  sleep 2
  if [ -f "$PID_FILE" ] && ps -p "$(cat "$PID_FILE")" >/dev/null 2>&1; then
    echo "started: $WID (pid $(cat "$PID_FILE"), 中枢受控模式)"
    bash /home/user/ZONGYUAN-ROOT/scripts/worker_ntfy_alert.sh WORKER_STARTED "受控 worker ${WID} 已启动（pid $(cat "$PID_FILE")）" >> /home/user/ZONGYUAN-ROOT/logs/worker_cns.log 2>&1 || true
  else
    echo "start_failed: $WID"; exit 1
  fi
}

stop() {
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" >/dev/null 2>&1; then kill "$PID" 2>/dev/null || true; fi
    rm -f "$PID_FILE" "$HB_FILE" "$CNS_FILE"
    echo "stopped: $WID"
  else
    echo "not_running: $WID"
  fi
}

status() {
  if [ -f "$PID_FILE" ] && ps -p "$(cat "$PID_FILE")" >/dev/null 2>&1; then
    NOW=$(date +%s); LAST=$(cat "$HB_FILE" 2>/dev/null || echo 0)
    AGE=$((NOW - LAST))
    CNS=$(cat "$CNS_FILE" 2>/dev/null || echo "{\"mode\":\"booting\"}")
    echo "healthy: $WID (pid $(cat "$PID_FILE"), 心跳 ${AGE}s 前) | 中枢态: $CNS"
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
