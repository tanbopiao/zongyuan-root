#!/bin/bash
# ZONGYUAN-ROOT 内核写入锁
# 用法: ./kernel_write_lock.sh "<python命令或脚本>" "<窗口标识>"
# 所有写kernel.json的操作必须通过此脚本

LOCK_FILE="/var/lock/zongyuan/kernel_write.lock"
TIMEOUT=60
WINDOW_ID="${2:-unknown}"
CMD="$1"

if [ -z "$CMD" ]; then
  echo "用法: $0 \"<命令>\" \"<窗口标识>\""
  exit 1
fi

exec 200>"$LOCK_FILE"
if flock -w $TIMEOUT 200; then
  echo "$WINDOW_ID $(date '+%Y-%m-%d %H:%M:%S')" > "$LOCK_FILE.owner"
  eval "$CMD"
  RET=$?
  rm -f "$LOCK_FILE.owner"
  exit $RET
else
  echo "内核写入锁超时(${TIMEOUT}s)，持有者: $(cat $LOCK_FILE.owner 2>/dev/null || echo '未知')"
  exit 1
fi
