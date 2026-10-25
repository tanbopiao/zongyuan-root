#!/bin/bash
# frp 隧道保活脚本：frpc 守护（连真实服务器 frps，IP 变动无感）
# @reboot + */10；frpc 未运行则拉起；日志 logs/frp_tunnel.log
set -uo pipefail
ROOT="/home/user/ZONGYUAN-ROOT"
FRPC="$ROOT/var/frp/frpc"
CONF="$ROOT/var/frp/frpc.toml"
LOG="$ROOT/logs/frp_tunnel.log"
mkdir -p "$(dirname "$LOG")"

if pgrep -f "$FRPC.*$CONF" >/dev/null 2>&1; then
  echo "[frp-keepalive] $(date '+%F %T') frpc 已在运行，跳过" >> "$LOG"
  exit 0
fi

echo "[frp-keepalive] $(date '+%F %T') frpc 未运行，拉起" >> "$LOG"
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy nohup "$FRPC" -c "$CONF" >> "$LOG" 2>&1 &
disown
sleep 3
if pgrep -f "$FRPC.*$CONF" >/dev/null 2>&1; then
  echo "[frp-keepalive] $(date '+%F %T') frpc 已启动" >> "$LOG"
else
  echo "[frp-keepalive] $(date '+%F %T') frpc 启动失败（frps 未就绪时属正常，将自动重试）" >> "$LOG"
fi
exit 0
