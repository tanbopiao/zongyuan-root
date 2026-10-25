#!/bin/bash
# ZONGYUAN-ROOT AUTO-ARCHIVE V2.0 — 待同步队列 flush（续传）
# 遍历 meta/pending-rsync.list，逐项调用 auto_rsync_sync.sh 推送云端 gallery
# 成功后自动从队列移除；失败/未配置目标则保留，下次继续续传
set -uo pipefail
ROOT="/home/user/ZONGYUAN-ROOT"
PENDING_FILE="$ROOT/meta/pending-rsync.list"
SYNC_HOOK="$ROOT/hooks/auto_rsync_sync.sh"

[ -f "$PENDING_FILE" ] || { echo "无待同步队列"; exit 0; }
COUNT=$(wc -l < "$PENDING_FILE")
[ "$COUNT" -eq 0 ] && { echo "待同步队列为空"; exit 0; }

echo "[$(date)] === rsync 续传启动：$COUNT 项待同步 ==="
OK=0; FAIL=0
while IFS=, read -r AID KIND; do
  [ -z "$AID" ] && continue
  OUT=$("$SYNC_HOOK" "$AID" "$KIND" 2>&1)
  if echo "$OUT" | grep -q "rsync_ok"; then
    echo "OK: $AID"; OK=$((OK+1))
  else
    echo "保留: $AID（$OUT）"; FAIL=$((FAIL+1))
  fi
done < "$PENDING_FILE"
echo "[$(date)] === 续传结束：成功 $OK / 保留 $FAIL ==="
