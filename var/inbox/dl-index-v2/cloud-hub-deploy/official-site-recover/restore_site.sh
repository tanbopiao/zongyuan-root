#!/usr/bin/env bash
# official-site-recover/restore_site.sh · 官网 docroot 恢复
# 用法: bash restore_site.sh <镜像tar.gz路径> [docroot]
set -e
SRC="${1:?用法: restore_site.sh <homepage-mirror.tar.gz> [docroot]}"
DOCROOT="${2:-/www/wwwroot/huodouai.com}"
[ -d "$DOCROOT" ] || mkdir -p "$DOCROOT"
echo "[官网恢复] 解压 $SRC -> $DOCROOT"
tar -xzf "$SRC" -C "$DOCROOT" --strip-components=1
echo "[官网恢复] docroot 文件数: $(find "$DOCROOT" -type f | wc -l)"
echo "[官网恢复] 完成。建议立即: nginx reload + 验证 https://www.huodouai.com/"
