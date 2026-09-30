#!/bin/bash
# 白皮书自动部署脚本 - 云端Worker执行
set -e
WEBROOT="/www/wwwroot/huodouai.com"
echo "=== 部署白皮书 ==="
mkdir -p "$WEBROOT/whitepaper"
cp whitepaper/index.html "$WEBROOT/whitepaper/index.html"
cp whitepaper/aios-v1.html "$WEBROOT/whitepaper/aios-v1.html"
cp whitepaper/omega-brain-mu-v3.html "$WEBROOT/whitepaper/omega-brain-mu-v3.html"
chown -R www:www "$WEBROOT/whitepaper"
echo "=== 验证 ==="
curl -s -o /dev/null -w "whitepaper/: %{http_code}\n" https://www.huodouai.com/whitepaper/
echo "=== 部署完成 ==="
