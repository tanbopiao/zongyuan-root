#!/bin/bash
# OpenAI 网关保活（:9120/v1）；@reboot + */10；未运行则拉起
set -uo pipefail
ROOT="/home/user/ZONGYUAN-ROOT"
PIDFILE="$ROOT/var/gateway/gateway.pid"
LOG="$ROOT/logs/gateway.log"
mkdir -p "$(dirname "$LOG")"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "[gateway-keepalive] $(date '+%F %T') 网关已在运行" >> "$LOG"
  exit 0
fi
echo "[gateway-keepalive] $(date '+%F %T') 网关未运行，拉起" >> "$LOG"
cd "$ROOT" && nohup python3 scripts/openai_gateway.py >> "$LOG" 2>&1 &
echo $! > "$PIDFILE"
sleep 2
if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "[gateway-keepalive] $(date '+%F %T') 网关已启动 pid=$(cat "$PIDFILE")" >> "$LOG"
else
  echo "[gateway-keepalive] $(date '+%F %T') 网关启动失败" >> "$LOG"
fi
exit 0
