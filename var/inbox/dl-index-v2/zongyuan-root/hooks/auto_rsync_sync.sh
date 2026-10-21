#!/usr/bin/env bash
# =====================================================================
# ZONGYUAN-ROOT AUTO-ARCHIVE V2.0 — 异步 rsync 推送云端 gallery（短链路）
# 用法：auto_rsync_sync.sh <asset_id> <asset_kind>
# 云端 rsync 目标未配置时，资产进入待同步队列，下次执行自动续传。
# =====================================================================
set -uo pipefail

ASSET_ID="$1"
ASSET_KIND="$2"

ROOT="/home/user/ZONGYUAN-ROOT"
SRC_DIR="$ROOT/asset/$ASSET_KIND/kunlun-auto-out"
PENDING_FILE="$ROOT/meta/pending-rsync.list"
# 云端 rsync 目标（配置点：meta/rsync-target.env 或环境变量注入）
# 示例：user@host:/srv/gallery/kunlun-auto-out/
if [ -f "$ROOT/meta/rsync-target.env" ]; then
  . "$ROOT/meta/rsync-target.env"
fi
CLOUD_RSYNC_TARGET="${CLOUD_RSYNC_TARGET:-}"

# 扩展名由资产 ID 推断
EXT="webp"; [ "$ASSET_KIND" = "video" ] && EXT="mp4"
FILE="$SRC_DIR/$ASSET_ID.$EXT"

[ -f "$FILE" ] || { echo "skip: $ASSET_ID 本地文件不存在"; exit 1; }

if [ -z "$CLOUD_RSYNC_TARGET" ]; then
  # 未配置云端目标：记入待同步队列（append-only），下次续传
  if ! grep -q "^$ASSET_ID,$ASSET_KIND$" "$PENDING_FILE" 2>/dev/null; then
    echo "$ASSET_ID,$ASSET_KIND" >> "$PENDING_FILE"
  fi
  echo "pending_sync: 云端目标未配置，$ASSET_ID 已入待同步队列"
  exit 0
fi

# 尝试 rsync（网络中断则保留待同步队列）
if rsync -az --timeout=60 "$FILE" "$CLOUD_RSYNC_TARGET" 2>/dev/null; then
  # 成功：从待同步队列移除（临时队列，非不可变账本）
  sed -i "/^$ASSET_ID,$ASSET_KIND$/d" "$PENDING_FILE" 2>/dev/null
  echo "rsync_ok: $ASSET_ID -> $CLOUD_RSYNC_TARGET"
else
  if ! grep -q "^$ASSET_ID,$ASSET_KIND$" "$PENDING_FILE" 2>/dev/null; then
    echo "$ASSET_ID,$ASSET_KIND" >> "$PENDING_FILE"
  fi
  echo "rsync_failed: 已保留待同步队列 $PENDING_FILE"
  exit 1
fi
