#!/usr/bin/env bash
# ============================================================
# 云端自治巡检 Watchdog ｜ 元极恒一小模型 + 官网全链路
# 功能：每5分钟巡检 → 异常自动自愈 → 真值上报网关（X-DID 单头）
#   1. api_server 进程/端口健康检查，异常自动重启（@reboot 同款命令）
#   2. 系统负载/内存/CPU 异常检测（load 超阈值 → 上报 + 清理失控进程）
#   3. nginx 存活检查（挂了尝试拉起）
#   4. 异常事件 → 本地日志 + 云端直连网关上报（DID-BR-000002 单头）
# 锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-10-05
# ============================================================
set -u
DID="DID-BR-000002"
GATEWAY="https://www.huodouai.com/api/report/truth"
LOG="/root/zongyuan-yuanji/logs/watchdog.log"
STAMP=$(date +%Y%m%d-%H%M%S)
EVENTS=()

say() { echo "[$STAMP] $*" >> "$LOG"; }

# 1) api_server 进程/端口自愈
API_PID=$(pgrep -f "api_serve[r].py" | head -1)
if [ -z "$API_PID" ]; then
  say "api_server 进程缺失 → 重启"
  cd /root/zongyuan-yuanji/src && setsid nohup python3 api_server.py >> /root/zongyuan-yuanji/logs/api_server.log 2>&1 < /dev/null &
  EVENTS+=("api_server_restarted:process_missing")
elif ! ss -tln 2>/dev/null | grep -q ":18080 "; then
  say "api_server 端口18080未监听(进程在,加载期或卡死) → 记录,30s后复查"
  sleep 30
  if ! ss -tln 2>/dev/null | grep -q ":18080 "; then
    kill -9 "$API_PID" 2>/dev/null
    cd /root/zongyuan-yuanji/src && setsid nohup python3 api_server.py >> /root/zongyuan-yuanji/logs/api_server.log 2>&1 < /dev/null &
    EVENTS+=("api_server_restarted:port_down")
  fi
fi

# 2) 系统负载/内存异常检测
LOAD1=$(cut -d' ' -f1 /proc/loadavg)
NCPU=$(nproc)
THRESH=$(awk "BEGIN{printf \"%.1f\", $NCPU*3}")
if awk "BEGIN{exit !($LOAD1 > $THRESH)}"; then
  say "load 异常: ${LOAD1} (阈值${THRESH}) → 检查失控进程"
  # 找出并清理非体系的高CPU python（保留 api_server 最新实例与官网服务）
  ps aux | awk '$3>150 && $11 ~ /python3/ && $0 !~ /api_serve[r]/ {print $2}' | while read -r p; do
    kill -9 "$p" 2>/dev/null && say "清理失控python pid=$p"
  done
  EVENTS+=("load_high:${LOAD1}_cleaned")
fi

MEM=$(free -m | awk '/Mem:/{printf "%d", $3*100/$2}')
if [ "$MEM" -gt 88 ]; then
  EVENTS+=("mem_high:${MEM}%")
fi

# 3) nginx 存活
if ! pgrep -x nginx >/dev/null; then
  /usr/local/nginx/sbin/nginx 2>/dev/null && EVENTS+=("nginx_restarted") || EVENTS+=("nginx_restart_failed")
fi

# 4) 异常上报网关（仅X-DID单头，无尾斜杠端点）
if [ ${#EVENTS[@]} -gt 0 ]; then
  EV=$(IFS=","; echo "${EVENTS[*]}")
  say "事件: $EV"
  curl -s -m 10 -X POST "$GATEWAY" \
    -H "X-DID: $DID" -H "Content-Type: application/json" \
    -d "{\"key\":\"watchdog.$STAMP\",\"value\":{\"event\":\"cloud_watchdog\",\"did\":\"$DID\",\"events\":\"$EV\",\"load1\":\"$LOAD1\",\"mem\":\"${MEM}%\",\"ts\":\"$STAMP\"}}" >> "$LOG" 2>&1
fi

say "巡检完成: load=$LOAD1 mem=${MEM}% events=${#EVENTS[@]}"
exit 0
