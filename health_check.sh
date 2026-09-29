#!/bin/bash
# ZONGYUAN-ROOT AIOS 健康检查与自动恢复脚本
# 功能：定期检查所有服务健康状态，异常自动重启
# 用法: ./health_check.sh [--fix] [--verbose]

BASE_DIR="/opt/ZONGYUAN-ROOT"
LOG_DIR="$BASE_DIR/logs"
LOG_FILE="$LOG_DIR/health_check.log"
FIX_MODE=false
VERBOSE=false

# 解析参数
for arg in "$@"; do
    case $arg in
        --fix) FIX_MODE=true ;;
        --verbose) VERBOSE=true ;;
    esac
done

# 服务列表（名称:端口:描述）
SERVICES=(
    "zongyuan-ai-proxy:8021:AI Proxy"
    "zongyuan-agent-hub:8023:Agent Hub"
    "zongyuan-gov-api:8025:Gov API"
    "zongyuan-handshake:8008:Handshake API"
    "zongyuan-self-learning::Self-Learning"
)

# 日志函数
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
    if [ "$VERBOSE" = true ] || [ "$level" = "ERROR" ] || [ "$level" = "WARN" ]; then
        echo "[$timestamp] [$level] $message"
    fi
}

# 确保日志目录存在
mkdir -p "$LOG_DIR"

log "INFO" "========== 健康检查开始 =========="
log "INFO" "修复模式: $FIX_MODE"

healthy_count=0
unhealthy_count=0
restarted_count=0

for service_def in "${SERVICES[@]}"; do
    IFS=':' read -r name port desc <<< "$service_def"
    
    # 检查systemd服务状态
    status=$(systemctl is-active "$name" 2>/dev/null)
    
    if [ "$status" = "active" ]; then
        # 服务运行中，检查端口（如果有端口）
        if [ -n "$port" ]; then
            if ss -tlnp | grep -q ":$port "; then
                log "INFO" "✅ $desc ($name): 运行正常，端口$port监听中"
                healthy_count=$((healthy_count + 1))
            else
                log "WARN" "⚠️  $desc ($name): 服务运行中但端口$port未监听"
                unhealthy_count=$((unhealthy_count + 1))
                if [ "$FIX_MODE" = true ]; then
                    log "INFO" "🔧 自动重启 $name..."
                    systemctl restart "$name"
                    sleep 3
                    new_status=$(systemctl is-active "$name" 2>/dev/null)
                    if [ "$new_status" = "active" ]; then
                        log "INFO" "✅ $name 重启成功"
                        restarted_count=$((restarted_count + 1))
                    else
                        log "ERROR" "❌ $name 重启失败"
                    fi
                fi
            fi
        else
            log "INFO" "✅ $desc ($name): 运行正常"
            healthy_count=$((healthy_count + 1))
        fi
    else
        log "ERROR" "❌ $desc ($name): 服务未运行 (状态: $status)"
        unhealthy_count=$((unhealthy_count + 1))
        if [ "$FIX_MODE" = true ]; then
            log "INFO" "🔧 自动启动 $name..."
            systemctl start "$name"
            sleep 3
            new_status=$(systemctl is-active "$name" 2>/dev/null)
            if [ "$new_status" = "active" ]; then
                log "INFO" "✅ $name 启动成功"
                restarted_count=$((restarted_count + 1))
            else
                log "ERROR" "❌ $name 启动失败"
            fi
        fi
    fi
done

# 检查系统资源
log "INFO" "--- 系统资源状态 ---"
mem_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100}')
disk_usage=$(df -h / | tail -1 | awk '{print $5}')
log "INFO" "内存使用率: ${mem_usage}%"
log "INFO" "磁盘使用率: $disk_usage"

if (( $(echo "$mem_usage > 85" | bc -l) )); then
    log "WARN" "⚠️  内存使用率过高 (${mem_usage}%)，建议清理缓存"
    if [ "$FIX_MODE" = true ]; then
        log "INFO" "🔧 自动清理内存缓存..."
        sync && echo 3 > /proc/sys/vm/drop_caches
        log "INFO" "✅ 内存缓存已清理"
    fi
fi

# 汇总
log "INFO" "========== 健康检查汇总 =========="
log "INFO" "健康服务: $healthy_count"
log "INFO" "异常服务: $unhealthy_count"
log "INFO" "已重启/启动: $restarted_count"

if [ $unhealthy_count -gt 0 ] && [ "$FIX_MODE" = false ]; then
    log "WARN" "提示: 使用 --fix 参数自动修复异常服务"
fi

log "INFO" "========== 健康检查结束 =========="
echo ""
