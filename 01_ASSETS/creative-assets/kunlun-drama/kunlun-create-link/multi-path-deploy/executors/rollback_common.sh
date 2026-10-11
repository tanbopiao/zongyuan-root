#!/bin/bash
# ============================================================================
# 通用回滚执行器(所有路径共用)
# 回滚到最近备份版本，保留最近5个版本
# 用法: bash rollback_common.sh <batch_id>
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# ============================================================================
set -e
BATCH_ID="${1:-TEST-001}"
GALLERY="/www/wwwroot/www.huodouai.com/gallery"
BACKUP_ROOT="/www/wwwroot/backups/gallery"
KEEP=5

echo "[回滚] 批次 $BATCH_ID 回滚执行"

# 1. 找该批次最近备份
LATEST=$(ls -1dt "$BACKUP_ROOT"/${BATCH_ID}_* 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
  echo "  ⚠️ 无 ${BATCH_ID} 备份，尝试通用最近备份"
  LATEST=$(ls -1dt "$BACKUP_ROOT"/*/ 2>/dev/null | head -1)
fi
if [ -z "$LATEST" ]; then
  echo "  ❌ 无可用备份，回滚失败"
  exit 1
fi

echo "  回滚源: $LATEST"
[ -d "$GALLERY" ] && rm -rf "$GALLERY"
mkdir -p "$GALLERY"
cp -a "$LATEST/." "$GALLERY/" 2>/dev/null

# 权限 + nginx
chown -R www:www "$GALLERY" 2>/dev/null
find "$GALLERY" -type d -exec chmod 755 {} \; 2>/dev/null
find "$GALLERY" -type f -exec chmod 644 {} \; 2>/dev/null
nginx -t 2>/dev/null && { systemctl reload nginx 2>/dev/null || nginx -s reload 2>/dev/null; }

# 2. 清理旧备份，保留最近 KEEP 个
ls -1dt "$BACKUP_ROOT"/*/ 2>/dev/null | tail -n +$((KEEP+1)) | while read d; do
  rm -rf "$d" 2>/dev/null
done

echo "  ✅ 回滚完成: $BATCH_ID -> $(basename "$LATEST")"
exit 0
