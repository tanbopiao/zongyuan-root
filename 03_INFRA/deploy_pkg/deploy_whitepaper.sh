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

# === 双向同步引擎白皮书 V1.0 (2026-10-26) ===
echo "--- 双向同步引擎白皮书 ---"
mkdir -p "$WEBROOT/whitepaper/bidir-sync-whitepaper/_shared/js" "$WEBROOT/whitepaper/bidir-sync-whitepaper/_shared/fonts"
cp -r "whitepaper/bidir-sync-whitepaper/"* "$WEBROOT/whitepaper/bidir-sync-whitepaper/"
cp -r "whitepaper/bidir-sync-whitepaper/_shared/"* "$WEBROOT/whitepaper/bidir-sync-whitepaper/_shared/" 2>/dev/null || true
chown -R www:www "$WEBROOT/whitepaper/bidir-sync-whitepaper"
curl -s -o /dev/null -w "bidir-sync-whitepaper: %{http_code}\n" "https://www.huodouai.com/whitepaper/bidir-sync-whitepaper/bidir-sync-whitepaper.html"

# === 双向同步交付包 ===
echo "--- 交付包 tarball ---"
cp bidir-sync-v1.0.tar.gz "$WEBROOT/whitepaper/" 2>/dev/null || cp 03_INFRA/deploy_pkg/bidir-sync-v1.0.tar.gz "$WEBROOT/whitepaper/"
chown www:www "$WEBROOT/whitepaper/bidir-sync-v1.0.tar.gz" 2>/dev/null || true
curl -s -o /dev/null -w "bidir-sync-v1.0.tar.gz: %{http_code}\n" "https://www.huodouai.com/whitepaper/bidir-sync-v1.0.tar.gz"

# === 联邦记忆内核产品白皮书 V1.0 (2026-10-26) ===
echo "--- 联邦记忆内核白皮书 ---"
mkdir -p "$WEBROOT/whitepaper/federated-memory-kernel-whitepaper/_shared/js" "$WEBROOT/whitepaper/federated-memory-kernel-whitepaper/_shared/fonts"
cp -r "04_PROJECTS/docs/whitepaper/federated-memory-kernel-whitepaper/"* "$WEBROOT/whitepaper/federated-memory-kernel-whitepaper/"
chown -R www:www "$WEBROOT/whitepaper/federated-memory-kernel-whitepaper"
curl -s -o /dev/null -w "federated-memory-kernel-whitepaper: %{http_code}\n" "https://www.huodouai.com/whitepaper/federated-memory-kernel-whitepaper/federated-memory-kernel-whitepaper.html"

# === 联邦记忆内核产品落地页 ===
echo "--- 联邦记忆内核产品页 ---"
mkdir -p "$WEBROOT/products/federated-memory-kernel/_shared/js" "$WEBROOT/products/federated-memory-kernel/_shared/fonts"
cp -r "04_PROJECTS/website/federated-memory-kernel/"* "$WEBROOT/products/federated-memory-kernel/"
chown -R www:www "$WEBROOT/products/federated-memory-kernel"
curl -s -o /dev/null -w "federated-memory-kernel product page: %{http_code}\n" "https://www.huodouai.com/products/federated-memory-kernel/federated-memory-kernel.html"
