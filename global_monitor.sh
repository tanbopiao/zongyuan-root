#!/bin/bash
# ZONGYUAN-ROOT 全域监控告警脚本
# 功能：服务健康检查、内存/磁盘监控、自动恢复、告警记录
# 溯源：Ω₀⊂⊙∞⊂Ω | DID-BR-000002

LOG_FILE="/var/log/global_monitor.log"
ALERT_DIR="/opt/ZONGYUAN-ROOT/alerts"
MEMORY_THRESHOLD=85  # 内存告警阈值(%)
DISK_THRESHOLD=85    # 磁盘告警阈值(%)

# 确保告警目录存在
mkdir -p "$ALERT_DIR" 2>/dev/null

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 告警函数
alert() {
    local level=$1  # warning/critical
    local category=$2
    local message=$3
    log "⚠️ [$level] [$category] $message"
    echo "{\"level\":\"$level\",\"category\":\"$category\",\"message\":\"$message\",\"timestamp\":\"$(date -Iseconds)\"}" >> "$ALERT_DIR/global_alerts.json" 2>/dev/null
}

# 检查服务状态
check_service() {
    local name=$1
    local check_cmd=$2
    local restart_cmd=$3
    
    if eval "$check_cmd" > /dev/null 2>&1; then
        log "✅ $name: 运行正常"
        return 0
    else
        log "❌ $name: 未运行，尝试自动恢复..."
        alert "critical" "service" "$name 未运行，尝试自动恢复"
        
        if [ -n "$restart_cmd" ]; then
            eval "$restart_cmd" > /dev/null 2>&1
            sleep 3
            if eval "$check_cmd" > /dev/null 2>&1; then
                log "✅ $name: 自动恢复成功"
                alert "warning" "service" "$name 自动恢复成功"
                return 0
            else
                log "❌ $name: 自动恢复失败，需要人工干预"
                alert "critical" "service" "$name 自动恢复失败，需要人工干预"
                return 1
            fi
        fi
        return 1
    fi
}

# 主流程
log "========================================"
log "  ZONGYUAN-ROOT 全域监控告警"
log "  溯源: Ω₀⊂⊙∞⊂Ω | DID-BR-000002"
log "========================================"
log ""

# 1. 系统资源监控
log "=== 1. 系统资源监控 ==="

# 内存检查
mem_total=$(free -m | awk '/^Mem:/{print $2}')
mem_used=$(free -m | awk '/^Mem:/{print $3}')
mem_percent=$((mem_used * 100 / mem_total))
log "内存: ${mem_used}MB / ${mem_total}MB (${mem_percent}%)"
if [ "$mem_percent" -ge "$MEMORY_THRESHOLD" ]; then
    alert "warning" "memory" "内存使用率 ${mem_percent}% 超过阈值 ${MEMORY_THRESHOLD}%"
fi

# 磁盘检查
disk_usage=$(df -h / | awk 'NR==2{print $5}' | tr -d '%')
log "磁盘: ${disk_usage}%"
if [ "$disk_usage" -ge "$DISK_THRESHOLD" ]; then
    alert "warning" "disk" "磁盘使用率 ${disk_usage}% 超过阈值 ${DISK_THRESHOLD}%"
fi

# 负载检查
load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
log "系统负载: $load_avg"
log ""

# 2. 核心服务监控
log "=== 2. 核心服务监控 ==="

# Nginx
check_service "Nginx" "pgrep -x nginx" "nginx -s reload || systemctl restart nginx"

# MySQL
check_service "MySQL" "pgrep -x mysqld" "systemctl start mysqld"

# Redis
check_service "Redis" "redis-cli ping | grep -q PONG" "systemctl start redis || redis-server --daemonize yes"

# AI工作台后端
check_service "AI工作台后端(8765)" "curl -s http://127.0.0.1:8765/health | grep -q ok" "systemctl restart aios"

# frp服务端
check_service "frp服务端(7100)" "ss -tlnp | grep -q 7100" "systemctl restart frps"

log ""

# 3. 云内核服务监控
log "=== 3. 云内核服务监控 ==="

# Ω-Brainμ (8000)
check_service "Ω-Brainμ(8000)" "curl -s http://127.0.0.1:8000/health | grep -q healthy" "cd /opt/ZONGYUAN-ROOT && nohup python3 omega_brain/health_endpoint.py --host 0.0.0.0 --port 8000 > /var/log/omega-brain.log 2>&1 &"

# LOIP API (8001)
check_service "LOIP API(8001)" "curl -s http://127.0.0.1:8001/api/v1/status | grep -q ok" "cd /opt/ZONGYUAN-ROOT && nohup python3 -m uvicorn loip.api_server:app --host 0.0.0.0 --port 8001 --workers 1 > /var/log/loip-api.log 2>&1 &"

# Anchor同步API (8006)
check_service "Anchor同步API(8006)" "curl -s http://127.0.0.1:8006/api/v1/sync/handshake | grep -q truth_version" "echo 'Anchor服务需要手动重启'"

log ""

# 4. 端口监听检查
log "=== 4. 关键端口监听检查 ==="
CRITICAL_PORTS=("80" "443" "8765" "3306" "6379" "7100" "8000" "8001" "8006")
for port in "${CRITICAL_PORTS[@]}"; do
    if ss -tlnp | grep -q ":$port "; then
        log "✅ 端口 $port: 监听中"
    else
        log "❌ 端口 $port: 未监听"
        alert "critical" "port" "关键端口 $port 未监听"
    fi
done
log ""

# 5. 总结
log "=== 5. 监控总结 ==="
alert_count=$(wc -l < "$ALERT_DIR/global_alerts.json" 2>/dev/null || echo 0)
log "告警记录: $alert_count 条"
log "监控完成: $(date '+%Y-%m-%d %H:%M:%S')"
log ""

exit 0
