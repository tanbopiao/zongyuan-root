#!/bin/bash
# ZONGYUAN-ROOT SSL 证书一键申请/部署脚本（Let's Encrypt 免费证书）
# 前置条件（外部）：1) DNS 已配置 A 记录 zyr.huodouai.com → 本机公网IP  2) 公网 80 可达（HTTP-01 验证）
# 本脚本：预检 DNS → 签发（certbot standalone）→ 部署至 nginx → 重载
set -uo pipefail
ROOT="/home/user/ZONGYUAN-ROOT"
DOMAIN="kunlun.huodouai.com"
CERT_DIR="$ROOT/var/nginx/certs"
mkdir -p "$CERT_DIR"
PUB_IP=$(python3 -c "import json;print(json.load(open('$ROOT/var/network/ip-state.json'))['current_ip'])" 2>/dev/null || echo "unknown")

echo "[ssl] 域名: $DOMAIN | 本机公网IP: $PUB_IP"

# 1) DNS 预检
RESOLVED=$(python3 -c "
import socket
try: print(socket.gethostbyname('$DOMAIN'))
except Exception: print('')
" 2>/dev/null)
if [ -z "$RESOLVED" ]; then
  echo "[ssl] BLOCK: $DOMAIN 尚无 DNS 记录。请在 huodouai.com DNS 控制台添加 A 记录指向 $PUB_IP 后重跑本脚本。"
  exit 1
fi
if [ "$RESOLVED" != "$PUB_IP" ]; then
  echo "[ssl] BLOCK: DNS 指向 $RESOLVED，与本机公网IP $PUB_IP 不一致（NAT 或记录未生效）。"
  exit 1
fi
echo "[ssl] DNS OK: $DOMAIN → $RESOLVED（与本机一致）"

# 2) 签发（certbot standalone，需公网 80 空闲且可达）
if ! command -v certbot >/dev/null 2>&1; then
  echo "[ssl] BLOCK: certbot 未安装（apt 无权限）。可手动安装后重跑：sudo apt install certbot"
  exit 2
fi
echo "[ssl] 开始签发（HTTP-01 challenge，standalone 模式）..."
certbot certonly --standalone --preferred-challenges http -d "$DOMAIN" -d zyr.huodouai.com \
  --non-interactive --agree-tos --email zr-node@huodouai.com \
  --cert-path "$CERT_DIR/fullchain.pem" --key-path "$CERT_DIR/privkey.pem" 2>&1 | tail -3

# 3) 部署（更新 nginx TLS 配置并重载）
if [ -f "$CERT_DIR/fullchain.pem" ] && [ -f "$CERT_DIR/privkey.pem" ]; then
  echo "[ssl] 证书已就位，重载 nginx..."
  nginx -s reload -c "$ROOT/var/nginx/zyr_nginx.conf" 2>/dev/null || nginx -c "$ROOT/var/nginx/zyr_nginx.conf" &
  echo "[ssl] 部署完成：https://$DOMAIN:8443 （经令牌鉴权访问）"
else
  echo "[ssl] 证书文件缺失，部署未完成。"
fi
