#!/bin/bash
# ZONGYUAN-ROOT 健康检查与自动修复脚本
# 每小时执行一次

LOG_FILE="/var/log/zongyuan-health.log"
ALERT_LOG="/var/log/zongyuan-alerts.log"

check_service() {
    local name=$1
    local url=$2
    local restart_cmd=$3
    
    if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
        echo "$(date): [OK] $name" >> "$LOG_FILE"
        return 0
    else
        echo "$(date): [FAIL] $name - 尝试重启..." >> "$ALERT_LOG"
        eval "$restart_cmd" 2>/dev/null
        sleep 3
        if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
            echo "$(date): [RECOVERED] $name - 重启成功" >> "$ALERT_LOG"
        else
            echo "$(date): [CRITICAL] $name - 重启失败，需要人工介入" >> "$ALERT_LOG"
        fi
        return 1
    fi
}

echo "$(date): === 健康检查开始 ===" >> "$LOG_FILE"

# 检查Nginx
if ! systemctl is-active --quiet nginx; then
    echo "$(date): [FAIL] Nginx未运行，重启中..." >> "$ALERT_LOG"
    systemctl restart nginx
fi

# 检查LOIP API
check_service "LOIP-API" "http://127.0.0.1:8001/api/v1/status" \
    "cd /opt/ZONGYUAN-ROOT && nohup python3 -m uvicorn loip.api_server:app --host 0.0.0.0 --port 8001 &"

# 检查ANCE API
check_service "ANCE-API" "http://127.0.0.1:8002/health" \
    "cd /opt/ZONGYUAN-ROOT/ai-native-ops && setsid python3 api_server.py > /var/log/ance-api.log 2>&1 < /dev/null &"

# 检查Ω-Brainμ
check_service "Omega-Brain" "http://127.0.0.1:8000/health" \
    "cd /opt/ZONGYUAN-ROOT && nohup python3 omega_brain_mu.py > /var/log/omega-brain.log 2>&1 &"

# 检查向量数据库
check_service "Vector-DB" "http://127.0.0.1:8003/health" \
    "cd /opt/ZONGYUAN-ROOT/ai-native-ops && setsid python3 vector_server.py > /var/log/vector-db.log 2>&1 < /dev/null &"

# 检查Redis
if ! systemctl is-active --quiet redis 2>/dev/null && ! systemctl is-active --quiet redis-server 2>/dev/null; then
    echo "$(date): [FAIL] Redis未运行，重启中..." >> "$ALERT_LOG"
    systemctl restart redis 2>/dev/null || systemctl restart redis-server 2>/dev/null
fi

# 检查磁盘空间
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 85 ]; then
    echo "$(date): [WARNING] 磁盘使用率 ${DISK_USAGE}%，超过85%阈值" >> "$ALERT_LOG"
fi

# 检查内存
MEM_AVAIL=$(free -m | awk '/Mem:/ {print $7}')
if [ "$MEM_AVAIL" -lt 150 ]; then
    echo "$(date): [WARNING] 可用内存 ${MEM_AVAIL}MB，低于150MB阈值" >> "$ALERT_LOG"
fi

echo "$(date): === 健康检查完成 ===" >> "$LOG_FILE"
