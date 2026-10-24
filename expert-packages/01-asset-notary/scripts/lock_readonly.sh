#!/bin/bash
# 只读锁档 v1.0 —— 目录文件 chmod 444 并校验无 writable 残留
set -u
DIR="${1:?用法: lock_readonly.sh <目录>}"
[ -d "$DIR" ] || { echo "ERR: 目录不存在 $DIR"; exit 1; }

LOCKED=0
find "$DIR" -type f -print0 | while IFS= read -r -d '' f; do
  case "$f" in
    */.git/*|*__pycache__*) continue ;;
  esac
  chmod 444 "$f" 2>/dev/null
done

WRITABLE=$(find "$DIR" -type f -perm /222 ! -path '*/.git/*' ! -path '*__pycache__*' 2>/dev/null)
COUNT=$(find "$DIR" -type f ! -path '*/.git/*' ! -path '*__pycache__*' 2>/dev/null | wc -l)
if [ -z "$WRITABLE" ]; then
  echo "[Lock] 只读锁档完成: $COUNT 个文件 444，writable 残留=0"
  exit 0
else
  echo "[Lock] 锁档失败，以下文件仍可写:"; echo "$WRITABLE"
  exit 1
fi
