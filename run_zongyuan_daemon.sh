#!/bin/bash
# ZONGYUAN-ROOT 自治守护 supervisord 启动脚本 (V3 自愈增强)
# 独立supervisord，不依赖/不侵入系统supervisord
# V2进化: 崩溃自愈+stale socket检测+强制重启+进程存活校验(E-001)
# V3进化: 释放托管端口残留进程(根治api-server FATAL/端口占用冲突)
DIR="/home/user/Doubao/chats/38418284746129666"
CFG="$DIR/supervisord.zongyuan.conf"
SOCK="$DIR/run/zongyuan-supervisor.sock"
PIDF="$DIR/run/zongyuan-supervisord.pid"
mkdir -p "$DIR/run" "$DIR/logs"

is_supervisord_alive() {
  [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null && return 0
  return 1
}

cleanup_stale() {
  # 清理残留socket(进程已死但socket残留导致refused)
  rm -f "$SOCK" "$PIDF"
}

# V3: 释放托管端口残留进程(根治api-server FATAL/端口占用冲突)
release_ports() {
  local port pid
  for port in 8765; do
    pid=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' | head -1)
    [ -n "$pid" ] && kill "$pid" 2>/dev/null && echo "释放端口$port残留进程$pid"
  done
  sleep 1
}

start() {
  release_ports  # V3进化: 启动前释放残留端口进程
  if is_supervisord_alive; then
    echo "supervisord存活"
  else
    cleanup_stale
    supervisord -c "$CFG"
    for i in 1 2 3 4 5 6 7 8 9 10; do
      sleep 1
      supervisorctl -c "$CFG" status >/dev/null 2>&1 && break
    done
    echo "supervisord启动完成"
  fi
  # 校验托管程序存活,失败则重启
  if supervisorctl -c "$CFG" status 2>/dev/null | grep -q "FATAL\|EXITED\|BACKOFF"; then
    echo "检测到服务异常,释放端口并重启全部"
    release_ports
    supervisorctl -c "$CFG" restart all >/dev/null 2>&1
    sleep 3
  fi
  supervisorctl -c "$CFG" status
}

case "${1:-start}" in
  start)  start ;;
  stop)   supervisorctl -c "$CFG" shutdown 2>/dev/null && sleep 1 && cleanup_stale || echo "未运行" ;;
  status) supervisorctl -c "$CFG" status 2>/dev/null || echo "未运行" ;;
  *)
    echo "用法: $0 {start|stop|status}"
    ;;
esac
