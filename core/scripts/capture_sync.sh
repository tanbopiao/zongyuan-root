#!/bin/bash
# 捕获同步: 本地归档 → 云端(HTTP上传,Token鉴权,图片/视频分桶,幂等)
CAPTURE_BOX=${CAPTURE_BOX:-$HOME/capture-box}
LOCAL_ASSETS=${LOCAL_ASSETS:-$HOME/kunlun-assets}
LOG=$HOME/capture_sync.log
UPLOAD_URL='https://drama.huodouai.com/api/upload'
TOKEN='ZR-CAPTURE-2026-OMEGA'
for f in "$CAPTURE_BOX"/*; do
  [ -f "$f" ] || continue
  case "$f" in
    *.png|*.jpg|*.jpeg|*.webp|*.mp4|*.mov|*.gif)
      DEST="$LOCAL_ASSETS/$(date +%Y-%m-%d)"
      mkdir -p "$DEST"
      mv -n "$f" "$DEST/" 2>/dev/null
      echo "[$(date '+%F %T')] 归档: $(basename "$f")" >> "$LOG"
      ;;
  esac
done
FAILED="$LOCAL_ASSETS/.pending_upload"
: > "$FAILED"
for f in "$LOCAL_ASSETS"/*/*; do
  [ -f "$f" ] || continue
  case "$f" in
    *.uploaded) continue ;;   # 跳过标记文件
  esac
  base=$(basename "$f")
  [ -f "$f.uploaded" ] && continue
  case "$f" in
    *.mp4|*.mov) bucket=videos ;;
    *) bucket=images ;;
  esac
  ok=0
  for attempt in 1 2 3; do
    resp=$(curl -s -o /dev/null -w '%{http_code}' --max-time 120 -H "X-Capture-Token: $TOKEN" -F "file=@$f" -F "bucket=$bucket" -F "subdir=$(basename "$(dirname "$f")")" "$UPLOAD_URL")
    if [ "$resp" = '200' ]; then ok=1; break; fi
    sleep 5
  done
  if [ "$ok" = '1' ]; then
    touch "$f.uploaded"
    echo "[$(date '+%F %T')] 上传成功: $base → $bucket" >> "$LOG"
  else
    echo "$f" >> "$FAILED"
    echo "[$(date '+%F %T')] 上传失败: $base" >> "$LOG"
  fi
done
echo "[$(date '+%F %T')] 同步完成" >> "$LOG"
