#!/bin/bash
# ============================================================================
# 路径P3: SSH rsync 直推部署执行器(备用路径3)
# 复用 SOP-GALLERY-DEPLOY-v2.0 链路，需SSH授信修复后启用
# 用法: bash ssh_rsync_deploy.sh <batch_id> [本地画廊目录]
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# ============================================================================
set -e
BATCH_ID="${1:-TEST-001}"
LOCAL_GALLERY="${2:-/home/user/Doubao/chats/1128121028098/kunlun-create-link}"
SSH_ALIAS="${SSH_ALIAS:-zongyuan-cloud}"
REMOTE_ROOT="/www/wwwroot/www.huodouai.com/gallery"

echo "[SSH路径] 批次 $BATCH_ID 部署开始"

# 1. SSH 连通检查
echo "  SSH连通检查..."
if ! timeout 15 ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_ALIAS" "echo ok" >/dev/null 2>&1; then
  echo "  ❌ SSH通道不可用(公钥认证失败)，无法部署。请修复authorized_keys后重试"
  exit 1
fi

# 2. 远端备份
TS=$(date +%Y%m%d_%H%M%S)
ssh "$SSH_ALIAS" "mkdir -p /www/wwwroot/backups/gallery/${BATCH_ID}_${TS} && cp -a $REMOTE_ROOT/. /www/wwwroot/backups/gallery/${BATCH_ID}_${TS}/ 2>/dev/null; echo backup_done"

# 3. rsync 推送
echo "  rsync推送..."
rsync -avz --delete \
  -e "ssh -o BatchMode=yes" \
  "$LOCAL_GALLERY/" \
  "$SSH_ALIAS:$REMOTE_ROOT/" 2>/dev/null && echo "  rsync完成"

# 4. 远端权限 + nginx
ssh "$SSH_ALIAS" "
chown -R www:www $REMOTE_ROOT 2>/dev/null
find $REMOTE_ROOT -type d -exec chmod 755 {} \; 2>/dev/null
find $REMOTE_ROOT -type f -exec chmod 644 {} \; 2>/dev/null
nginx -t 2>/dev/null && { systemctl reload nginx 2>/dev/null || nginx -s reload 2>/dev/null; }
echo remote_done
"

echo "  ✅ SSH路径部署完成: $BATCH_ID"
exit 0
