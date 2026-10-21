#!/bin/bash
# ZONGYUAN-ROOT nginx 持久守护脚本（鉴权入口 8089/8443）
# 未监听 → 拉起；已监听 → 跳过。供 @reboot 与 */10 保活。
set -uo pipefail
ROOT="/home/user/ZONGYUAN-ROOT"
CONF="$ROOT/var/nginx/zyr_nginx.conf"
if ss -tln | grep -qE ":8089|:8443"; then
  echo "[nginx-keepalive] 入口已在监听，跳过"
  exit 0
fi
nginx -t -c "$CONF" >/dev/null 2>&1 && {
  nginx -c "$CONF"
  sleep 1
  if ss -tln | grep -qE ":8089|:8443"; then
    echo "[nginx-keepalive] 已拉起 8089/8443"
  else
    echo "[nginx-keepalive] 拉起失败"
    exit 1
  fi
} || echo "[nginx-keepalive] 配置校验失败"
