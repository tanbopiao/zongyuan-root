#!/bin/bash
# 昆仑洞天全自动捕获机制 · HTTP版一键搭建(零SSH零密钥)
# 用途: 云电脑销毁重建后自动重建捕获链路
# 用法: curl -sL https://drama.huodouai.com/assets/capture/setup_capture.sh | bash
set -e
echo '═══════ 昆仑洞天捕获机制自动搭建(HTTP版) ═══════'
# 1. 建捕获箱+本地归档目录
CAPTURE_BOX=${CAPTURE_BOX:-$HOME/capture-box}
LOCAL_ASSETS=${LOCAL_ASSETS:-$HOME/kunlun-assets}
mkdir -p "$CAPTURE_BOX" "$LOCAL_ASSETS"
echo "✅ 捕获箱: $CAPTURE_BOX"
echo "✅ 归档目录: $LOCAL_ASSETS"
# 2. 安装捕获同步脚本(HTTP上传,零SSH)
cat > $HOME/capture_sync.sh << 'SYNC'
#!/bin/bash
# 捕获同步: 本地归档 → 云端(HTTP上传,Token鉴权,图片/视频分桶,幂等)
CAPTURE_BOX=${CAPTURE_BOX:-$HOME/capture-box}
LOCAL_ASSETS=${LOCAL_ASSETS:-$HOME/kunlun-assets}
LOG=$HOME/capture_sync.log
UPLOAD_URL='https://drama.huodouai.com/api/upload'
TOKEN='ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d'
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
    *.uploaded) continue ;;
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
SYNC
chmod +x $HOME/capture_sync.sh
echo "✅ 同步脚本: $HOME/capture_sync.sh (HTTP上传)"
# 3. 注册常驻监控(cron优先,无cron用守护进程)
if command -v crontab >/dev/null 2>&1 && [ -x /usr/sbin/cron ]; then
  (crontab -l 2>/dev/null | grep -v capture_sync; echo '* * * * * $HOME/capture_sync.sh >/dev/null 2>&1') | crontab -
  echo '✅ 已注册cron每分钟自动捕获'
else
  cat > $HOME/capture_daemon.sh << 'DAEMON'
#!/bin/bash
while true; do
  bash $HOME/capture_sync.sh >/dev/null 2>&1
  sleep 60
done
DAEMON
  chmod +x $HOME/capture_daemon.sh
  nohup $HOME/capture_daemon.sh >/dev/null 2>&1 &
  echo '✅ 已启动守护进程(每60秒自动捕获)'
fi
echo '═══════ 搭建完成 ═══════'
echo '使用: 把豆包App生成的图片/视频放入' $CAPTURE_BOX '/，自动归档并HTTP上传到云端'
