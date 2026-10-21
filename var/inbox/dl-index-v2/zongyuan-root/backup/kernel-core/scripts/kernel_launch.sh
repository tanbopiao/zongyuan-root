#!/bin/bash
# zongyuan-kernel 守护进程启动/停止/状态（端口避开 nginx 8081，用 9081/9082/9092）
# 用法: kernel_launch.sh {start|stop|status}
ROOT="/home/user/Doubao/chats/38412149511142658/zongyuan-kernel"
PID_FILE="$ROOT/var/run/kernel.pid"
export ZONGYUAN_PORT_BRAIN_PROXY=9081
export ZONGYUAN_PORT_BRAIN_ROUTER=9082
export ZONGYUAN_PORT_CAUSAL=9092
case "${1:-status}" in
  start)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "already_running: pid $(cat "$PID_FILE")"; exit 0
    fi
    nohup /usr/bin/python3 "$ROOT/kernel/main.py" > "$ROOT/var/run/kernel.log" 2>&1 &
    sleep 3
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "started: pid $(cat "$PID_FILE")"
    else
      echo "start_failed: $(tail -3 "$ROOT/var/run/kernel.log")"; exit 1
    fi
    ;;
  stop)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      kill "$(cat "$PID_FILE")"; rm -f "$PID_FILE"; echo "stopped"
    else
      echo "not_running"
    fi
    ;;
  status)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "running: pid $(cat "$PID_FILE")"
    else
      echo "down"
    fi
    ;;
esac
