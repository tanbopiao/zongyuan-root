#!/bin/bash
# ============================================================================
# 路径P2: 对象存储中转部署执行器(备用路径2)
# 火山TOS/阿里云OSS中转，需配置 OSS_ENDPOINT/OSS_BUCKET/OSS_KEY/OSS_SECRET
# 用法: bash oss_pull_deploy.sh <batch_id>
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# ============================================================================
set -e
BATCH_ID="${1:-TEST-001}"
OSS_ENDPOINT="${OSS_ENDPOINT:-}"
OSS_BUCKET="${OSS_BUCKET:-}"
OSS_KEY="${OSS_KEY:-}"
OSS_SECRET="${OSS_SECRET:-}"
WEB_ROOT="/www/wwwroot/www.huodouai.com/"
GALLERY="${WEB_ROOT}gallery/"
STAGE="/tmp/gallery_deploy_${BATCH_ID}"

echo "[对象存储路径] 批次 $BATCH_ID 部署开始"

# 1. 校验配置
if [ -z "$OSS_ENDPOINT" ] || [ -z "$OSS_BUCKET" ]; then
  echo "  ⚠️ OSS配置未就绪(需OSS_ENDPOINT/OSS_BUCKET/OSS_KEY/OSS_SECRET)，跳过"
  exit 1
fi

# 2. 备份
TS=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/www/wwwroot/backups/gallery/${BATCH_ID}_${TS}"
mkdir -p "$BACKUP_DIR"
[ -d "$GALLERY" ] && cp -a "$GALLERY/." "$BACKUP_DIR/" 2>/dev/null

# 3. 从对象存储下载部署包
echo "  从对象存储下载..."
mkdir -p "$STAGE"
# 阿里云OSS / 火山TOS 通用: 用预签名URL或CLI
if command -v ossutil >/dev/null 2>&1; then
  ossutil config --endpoint "$OSS_ENDPOINT" --access-key-id "$OSS_KEY" --access-key-secret "$OSS_SECRET" 2>/dev/null
  ossutil cp "oss://$OSS_BUCKET/gallery-deploy/${BATCH_ID}/" "$STAGE/" -r 2>/dev/null && echo "  ossutil下载完成"
elif command -v tos >/dev/null 2>&1; then
  tos cp "tos://$OSS_BUCKET/gallery-deploy/${BATCH_ID}/" "$STAGE/" -r 2>/dev/null && echo "  tos下载完成"
else
  echo "  ⚠️ 无ossutil/tos客户端，需安装或改用预签名URL"
  exit 1
fi

# 4. 同步到网站目录
[ -d "$STAGE" ] && cp -a "$STAGE/." "$GALLERY/" 2>/dev/null
chown -R www:www "$GALLERY" 2>/dev/null
find "$GALLERY" -type d -exec chmod 755 {} \; 2>/dev/null
find "$GALLERY" -type f -exec chmod 644 {} \; 2>/dev/null

# 5. nginx
nginx -t 2>/dev/null && { systemctl reload nginx 2>/dev/null || nginx -s reload 2>/dev/null; }
echo "  ✅ 对象存储路径部署完成: $BATCH_ID"
exit 0
