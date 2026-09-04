#!/bin/bash
# ZONGYUAN-ROOT 云服务器端健康检查脚本
# 检查本地服务 + 通过frp检查本地Windows服务
# 每5分钟执行一次

LOG_FILE="/opt/ZONGYUAN-ROOT/logs/cloud_health_check.log"
ALERT_FILE="/opt/ZONGYUAN-ROOT/logs/cloud_health_alerts.log"
LOCAL_IP="127.0.0.1"
FRP_PORTS="8000 8001 8004 8005 8006"
REMOTE_PORTS="8017 8020 8899"
REMOTE_NAME="local-win-001"

echo "=== Health Check $(date) ===" >> "$LOG_FILE"

# 1. Check local cloud services
ALL_OK=true
for port in $FRP_PORTS; do
    if curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://$LOCAL_IP:$port/health" 2>/dev/null | grep -q "200"; then
        echo "  [OK] Cloud service port $port" >> "$LOG_FILE"
    elif curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://$LOCAL_IP:$port/" 2>/dev/null | grep -q "200"; then
        echo "  [OK] Cloud service port $port (root)" >> "$LOG_FILE"
    else
        echo "  [ALERT] Cloud service port $port NOT responding" >> "$LOG_FILE"
        echo "[$(date)] ALERT: Cloud service port $port down" >> "$ALERT_FILE"
        ALL_OK=false
    fi
done

# 2. Check remote Windows services via frp
for port in $REMOTE_PORTS; do
    if curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://$LOCAL_IP:$port/api/health" 2>/dev/null | grep -q "200"; then
        echo "  [OK] Remote $REMOTE_NAME port $port" >> "$LOG_FILE"
    elif curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://$LOCAL_IP:$port/" 2>/dev/null | grep -q "200"; then
        echo "  [OK] Remote $REMOTE_NAME port $port (root)" >> "$LOG_FILE"
    else
        echo "  [ALERT] Remote $REMOTE_NAME port $port NOT responding" >> "$LOG_FILE"
        echo "[$(date)] ALERT: Remote $REMOTE_NAME port $port down" >> "$ALERT_FILE"
        ALL_OK=false
    fi
done

# 3. Check frps status
if systemctl is-active --quiet frps; then
    echo "  [OK] frps service running" >> "$LOG_FILE"
else
    echo "  [ALERT] frps service NOT running" >> "$LOG_FILE"
    echo "[$(date)] ALERT: frps service down" >> "$ALERT_FILE"
    systemctl restart frps
    echo "  [RECOVER] frps restarted" >> "$LOG_FILE"
    ALL_OK=false
fi

# 4. Summary
if [ "$ALL_OK" = true ]; then
    echo "  [SUMMARY] ALL SERVICES HEALTHY" >> "$LOG_FILE"
else
    echo "  [SUMMARY] SOME SERVICES NEED ATTENTION" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
