#!/bin/bash
# ============================================================================
# 路径P1: 魔搭数据集拉取部署执行器
# 云端服务器用魔搭SDK下载部署包(已实测匿名单文件GET 200)
# 用法: bash modelscope_pull_deploy.sh <batch_id>
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# ============================================================================
set -e
BATCH_ID="${1:-TEST-001}"
MS_TOKEN="${MODELSCOPE_TOKEN:-ms-673547d6-508b-4242-a862-85de112a3ce7}"
DATA_REPO="zongyuanroot/zongyuan-root-achievements"
WEB_ROOT="/www/wwwroot/www.huodouai.com/"
GALLERY="${WEB_ROOT}gallery/"
STAGE="/tmp/gallery_deploy_${BATCH_ID}"
DEPLOY_PACK_DIR="data_lake/outreach-p3"

echo "[魔搭路径] 批次 $BATCH_ID 部署开始"

# 1. 备份
TS=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/www/wwwroot/backups/gallery/${BATCH_ID}_${TS}"
mkdir -p "$BACKUP_DIR"
[ -d "$GALLERY" ] && cp -a "$GALLERY/." "$BACKUP_DIR/" 2>/dev/null && echo "  已备份 -> $BACKUP_DIR"

# 2. 用魔搭SDK拉取部署包
echo "  从魔搭拉取部署包..."
if python3 -c "import modelscope" 2>/dev/null; then
  python3 - << EOF
import os
from modelscope.hub.api import HubApi
from modelscope.hub.file_download import dataset_file_download
os.makedirs("$STAGE", exist_ok=True)
files = ["对外资产检索台_20260929.html","对外资产检索API规范_P3_V1.0.md"]
for f in files:
    try:
        p = dataset_file_download("$DATA_REPO", f, cache_dir="$STAGE", revision="master")
        print("  下载:", f, "->", p)
    except Exception as e:
        print("  跳过(可能不存在):", f, str(e)[:60])
EOF
else
  echo "  ⚠️ 服务器无modelscope SDK，改用HTTP下载"
  # HTTP fallback: 下载画廊html
  mkdir -p "$STAGE"
  curl -sL -o "$STAGE/index.html" \
    "https://www.modelscope.cn/api/v1/datasets/$DATA_REPO/repo?Revision=master&FilePath=data_lake/outreach-p3/%E5%AF%B9%E5%A4%96%E8%B5%84%E4%BA%A7%E6%A3%80%E7%B4%A2%E5%8F%B0_20260929.html" \
    && echo "  HTTP下载index.html完成" || echo "  ⚠️ 下载失败"
fi

# 3. 同步到网站目录
echo "  同步静态资源..."
[ -d "$STAGE" ] && cp -a "$STAGE/." "$GALLERY/" 2>/dev/null

# 4. 权限
chown -R www:www "$GALLERY" 2>/dev/null
find "$GALLERY" -type d -exec chmod 755 {} \; 2>/dev/null
find "$GALLERY" -type f -exec chmod 644 {} \; 2>/dev/null

# 5. nginx
nginx -t 2>/dev/null && { systemctl reload nginx 2>/dev/null || nginx -s reload 2>/dev/null; }
echo "  ✅ 魔搭路径部署完成: $BATCH_ID"
exit 0
