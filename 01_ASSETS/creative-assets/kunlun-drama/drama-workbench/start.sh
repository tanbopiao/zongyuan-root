#!/usr/bin/env bash
# 启动/守护 昆仑洞天量产 HTTP 接入层
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$DIR/live/server.pid"
LOGFILE="$DIR/live/server.log"

cd "$DIR"

# 已在跑则不重复起
if [ -f "$PIDFILE" ]; then
  OLDPID=$(cat "$PIDFILE" 2>/dev/null || echo "")
  if [ -n "$OLDPID" ] && kill -0 "$OLDPID" 2>/dev/null; then
    echo "[start.sh] 服务已在运行 pid=$OLDPID"
    exit 0
  fi
fi

mkdir -p live/tasks artifacts_live
nohup python3 drama_production_server.py >> "$LOGFILE" 2>&1 &
NEWPID=$!
echo "$NEWPID" > "$PIDFILE"
sleep 1.5
if kill -0 "$NEWPID" 2>/dev/null; then
  echo "[start.sh] 服务已启动 pid=$NEWPID  log=$LOGFILE"
else
  echo "[start.sh] 启动失败，请看 $LOGFILE"
  exit 1
fi
