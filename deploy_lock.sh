#!/bin/bash
# ZONGYUAN-ROOT 全局部署锁
# 用法: ./deploy_lock.sh "<命令>" "<窗口标识>"
# 所有重启服务/改Nginx/系统级变更必须通过此脚本

LOCK_FILE="/var/lock/zongyuan/deploy.lock"
TIMEOUT=300
WINDOW_ID="${2:-unknown}"
CMD="$1"

if [ -z "$CMD" ]; then
  echo "用法: $0 \"<命令>\" \"<窗口标识>\""
  exit 1
fi

echo "[$(date '+%H:%M:%S')] 窗口[$WINDOW_ID] 申请部署锁..."

exec 200>"$LOCK_FILE"
if flock -w $TIMEOUT 200; then
  echo "[$(date '+%H:%M:%S')] 窗口[$WINDOW_ID] 获取部署锁成功"
  echo "$WINDOW_ID $(date '+%Y-%m-%d %H:%M:%S')" > "$LOCK_FILE.owner"
  eval "$CMD"
  RET=$?
  rm -f "$LOCK_FILE.owner"
  echo "[$(date '+%H:%M:%S')] 窗口[$WINDOW_ID] 释放部署锁 (退出码:$RET)"
  exit $RET
else
  echo "[$(date '+%H:%M:%S')] 窗口[$WINDOW_ID] 获取部署锁超时(${TIMEOUT}s)，有其他窗口正在部署"
  echo "  当前持有者: $(cat $LOCK_FILE.owner 2>/dev/null || echo '未知')"
  exit 1
fi
