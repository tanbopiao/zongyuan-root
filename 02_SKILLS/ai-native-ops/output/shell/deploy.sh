#!/bin/bash
# ANCE 自动部署脚本
# 云厂商: tencent
# 软件栈: nginx, docker, certbot
# 域名: huodouai.com

set -e

echo "=== ANCE 部署开始 ==="

# 1. 系统更新
echo "[1/5] 更新系统..."
apt-get update -qq
apt-get upgrade -y -qq

# 2. 安装基础工具
echo "[2/5] 安装基础工具..."
apt-get install -y curl wget git unzip ufw

# 3. 安装软件栈
echo "[3/5] 安装软件栈..."
apt-get install -y nginx docker.io docker-compose certbot python3-certbot-nginx

# 4. 配置防火墙
echo "[4/5] 配置防火墙..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 5. 配置服务
echo "[5/5] 配置服务..."
systemctl enable --now docker
systemctl enable --now nginx
certbot --nginx -d huodouai.com --non-interactive --agree-tos -m admin@huodouai.com

echo "=== 部署完成 ==="
echo "服务器IP: $(curl -s ifconfig.me)"
