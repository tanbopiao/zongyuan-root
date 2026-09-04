#!/bin/bash
# ZONGYUAN-ROOT 服务器监控脚本
# 用法: ./monitor.sh  或加入crontab

LOG_FILE="/opt/ZONGYUAN-ROOT/monitor.log"
THRESHOLD_CPU=80
THRESHOLD_MEM=85
THRESHOLD_DISK=90

get_cpu() { top -bn1 | grep "Cpu(s)" | awk '{print 100-$8}' | cut -d. -f1; }
get_mem() { free | awk '/Mem:/ {printf "%.0f", $3/$2*100}'; }
get_disk() { df / | awk 'NR==2 {print $5}' | tr -d '%'; }

CPU=$(get_cpu)
MEM=$(get_mem)
DISK=$(get_disk)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

ALERTS=""
[ "$CPU" -gt "$THRESHOLD_CPU" ] && ALERTS="$ALERTS [CPU高:${CPU}%]"
[ "$MEM" -gt "$THRESHOLD_MEM" ] && ALERTS="$ALERTS [内存高:${MEM}%]"
[ "$DISK" -gt "$THRESHOLD_DISK" ] && ALERTS="$ALERTS [磁盘高:${DISK}%]"

# 检查关键服务
SERVICES="zongyuan-aiproxy zongyuan-omega frps"
for svc in $SERVICES; do
  if ! systemctl is-active --quiet $svc 2>/dev/null; then
    ALERTS="$ALERTS [服务异常:$svc]"
    # 自动重启
    systemctl restart $svc 2>/dev/null && ALERTS="$ALERTS(已重启)"
  fi
done
# nginx由宝塔管理，用pgrep检测
if ! pgrep -x nginx > /dev/null 2>&1; then
    ALERTS="$ALERTS [服务异常:nginx]"
    nginx 2>/dev/null && ALERTS="$ALERTS(已重启)"
fi

LOG_LINE="$TIMESTAMP | CPU:${CPU}% MEM:${MEM}% DISK:${DISK}%$ALERTS"
echo "$LOG_LINE" >> "$LOG_FILE"

# 保留最近1000行
tail -1000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"

if [ -n "$ALERTS" ]; then
  echo "⚠️  ALERT: $LOG_LINE"
else
  echo "✅ OK: CPU:${CPU}% MEM:${MEM}% DISK:${DISK}%"
fi
