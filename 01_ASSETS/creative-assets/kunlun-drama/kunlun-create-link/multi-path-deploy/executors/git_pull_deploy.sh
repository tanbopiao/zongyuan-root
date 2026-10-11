#!/bin/bash
# ============================================================================
# 路径P0: Git 仓库拉取部署执行器
# 云端服务器主动 git pull 发布仓，无需入站 SSH
# 用法: bash git_pull_deploy.sh <batch_id>
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# ============================================================================
set -e
BATCH_ID="${1:-TEST-001}"
GIT_REMOTE_URL="${GIT_REMOTE_URL:-}"
WEB_ROOT="/www/wwwroot/www.huodouai.com/"
GALLERY="${WEB_ROOT}gallery/"
TAG="${2:-$BATCH_ID}"

echo "[Git路径] 批次 $BATCH_ID 部署开始"

# 1. 校验配置
if [ -z "$GIT_REMOTE_URL" ]; then
  echo "  ⚠️ GIT_REMOTE_URL 未配置，跳过"
  exit 1
fi

# 2. 备份当前线上
TS=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/www/wwwroot/backups/gallery/${BATCH_ID}_${TS}"
mkdir -p "$BACKUP_DIR"
[ -d "$GALLERY" ] && cp -a "$GALLERY/." "$BACKUP_DIR/" 2>/dev/null && echo "  已备份 -> $BACKUP_DIR"

# 3. 拉取发布仓
REPO_DIR="/www/wwwroot/gallery-repo"
if [ ! -d "$REPO_DIR/.git" ]; then
  echo "  首次拉取仓库..."
  git clone --depth 1 "$GIT_REMOTE_URL" "$REPO_DIR"
else
  echo "  增量拉取..."
  cd "$REPO_DIR" && git fetch origin && git checkout "$TAG" 2>/dev/null || git reset --hard origin/HEAD
fi

# 4. 同步静态资源到网站目录
echo "  同步静态资源..."
rsync -a --delete "$REPO_DIR/" "$GALLERY/" 2>/dev/null || cp -a "$REPO_DIR/." "$GALLERY/"

# 5. 权限
chown -R www:www "$GALLERY" 2>/dev/null
find "$GALLERY" -type d -exec chmod 755 {} \; 2>/dev/null
find "$GALLERY" -type f -exec chmod 644 {} \; 2>/dev/null

# 6. nginx 校验重载
nginx -t 2>/dev/null && { systemctl reload nginx 2>/dev/null || nginx -s reload 2>/dev/null; }
echo "  ✅ Git路径部署完成: $BATCH_ID"
exit 0
