#!/usr/bin/env bash
# cloud-hub-deploy/zhongshu-server/run.sh
# 启动/停止 云端中枢元内核三服务（网关 + 调度）
set -e
cd "$(dirname "$0")"
NAME="zhongshu"
PY=${PY:-python3}

case "${1:-start}" in
  start)
    echo "[$NAME] 启动真值网关 :9001"
    nohup $PY gateway_server.py --port 9001 > ../data/gateway.log 2>&1 &
    echo $! > ../data/gateway.pid
    echo "[$NAME] 启动调度 worker"
    nohup $PY scheduler.py --interval 300 > ../data/scheduler.log 2>&1 &
    echo $! > ../data/scheduler.pid
    sleep 1
    echo "[$NAME] 已启动 pid=$(cat ../data/gateway.pid) / $(cat ../data/scheduler.pid)"
    ;;
  stop)
    for f in ../data/gateway.pid ../data/scheduler.pid; do
      [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null && rm -f "$f" && echo "[$NAME] 停止 $f"
    done
    ;;
  status)
    echo "网关: $(curl -s -m 5 http://127.0.0.1:9001/api/status || echo DOWN)"
    ;;
  *) echo "用法: $0 {start|stop|status}"; exit 1;;
esac
