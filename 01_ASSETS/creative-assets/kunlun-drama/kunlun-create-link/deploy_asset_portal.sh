#!/usr/bin/env bash
# ============================================================================
# ZONGYUAN-ROOT 对外资产检索台 一键部署脚本（P3）
# 在云服务器执行：静态托管检索台 + nginx 配置 + 启动
# 确权 DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# 用法: bash deploy_asset_portal.sh [PORT=8080] [DOMAIN=]
# ============================================================================
set -euo pipefail

PORT="${1:-8080}"
DOMAIN="${2:-}"
SITE_DIR="/var/www/asset-portal"
NGINX_CONF="/etc/nginx/conf.d/asset-portal.conf"
HTML_SRC="${HTML_SRC:-/tmp/对外资产检索台_20260929.html}"

echo "🔧 ZONGYUAN-ROOT 资产检索台部署 | 端口 $PORT"

# 1. 准备站点目录并放置检索台
echo "📁 创建站点目录: $SITE_DIR"
sudo mkdir -p "$SITE_DIR"
if [ -f "$HTML_SRC" ]; then
    sudo cp "$HTML_SRC" "$SITE_DIR/index.html"
    echo "   ✅ 检索台已复制到 $SITE_DIR/index.html"
else
    echo "   ⚠️ 未找到 $HTML_SRC，请先上传检索台 HTML 到该路径"
    exit 1
fi

# 2. nginx 配置
echo "📝 写入 nginx 配置: $NGINX_CONF"
sudo tee "$NGINX_CONF" > /dev/null <<EOF
server {
    listen $PORT;
    server_name $DOMAIN;
    root $SITE_DIR;
    index index.html;
    location / {
        try_files \$uri \$uri/ =404;
    }
    add_header X-DID "DID-BR-000002" always;
}
EOF
echo "   ✅ nginx 配置完成"

# 3. 校验并重载
echo "🔄 校验 nginx 配置"
sudo nginx -t
echo "🚀 重载 nginx"
sudo systemctl reload nginx || sudo nginx -s reload

# 4. 验证
echo ""
echo "═══════ 部署结果 ═══════"
if command -v curl > /dev/null; then
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/")
    echo "  HTTP 状态: $code"
    if [ "$code" = "200" ]; then echo "  ✅ 检索台可访问"; else echo "  ⚠️ 状态异常，请检查"; fi
fi
echo "  站点: http://$DOMAIN:$PORT/  (或 http://<服务器IP>:$PORT/)"
echo "  确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω"
