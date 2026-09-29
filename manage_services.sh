#!/bin/bash
# ZONGYUAN-ROOT AIOS 统一服务管理脚本
# 用法: ./manage_services.sh {start|stop|restart|status|logs|enable|disable} [服务名]

BASE_DIR="/opt/ZONGYUAN-ROOT"
LOG_DIR="$BASE_DIR/logs"

# 服务列表
SERVICES=(
    "zongyuan-ai-proxy"
    "zongyuan-agent-hub"
    "zongyuan-gov-api"
    "zongyuan-handshake"
    "zongyuan-self-learning"
)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示用法
usage() {
    echo "ZONGYUAN-ROOT AIOS 统一服务管理脚本"
    echo ""
    echo "用法: $0 {start|stop|restart|status|logs|enable|disable} [服务名]"
    echo ""
    echo "命令:"
    echo "  start    - 启动所有服务（或指定服务）"
    echo "  stop     - 停止所有服务（或指定服务）"
    echo "  restart  - 重启所有服务（或指定服务）"
    echo "  status   - 查看所有服务状态"
    echo "  logs     - 查看服务日志（指定服务名）"
    echo "  enable   - 设置开机自启（所有服务）"
    echo "  disable  - 取消开机自启（所有服务）"
    echo ""
    echo "服务列表:"
    for svc in "${SERVICES[@]}"; do
        echo "  - $svc"
    done
    echo ""
}

# 执行命令
execute_cmd() {
    local cmd="$1"
    local target="$2"
    
    if [ -n "$target" ]; then
        # 操作指定服务
        if [[ " ${SERVICES[@]} " =~ " ${target} " ]]; then
            echo -e "${BLUE}[执行]${NC} $cmd $target"
            systemctl $cmd $target
            systemctl status $target --no-pager -l | head -5
        else
            echo -e "${RED}[错误]${NC} 未知服务: $target"
            echo "可用服务: ${SERVICES[*]}"
            exit 1
        fi
    else
        # 操作所有服务
        for svc in "${SERVICES[@]}"; do
            echo -e "${BLUE}[执行]${NC} $cmd $svc"
            systemctl $cmd $svc
        done
        echo ""
        echo -e "${GREEN}[完成]${NC} 所有服务已执行 $cmd"
        echo ""
        $0 status
    fi
}

# 查看状态
show_status() {
    echo ""
    echo "=========================================="
    echo "  ZONGYUAN-ROOT AIOS 服务状态"
    echo "=========================================="
    echo ""
    printf "%-30s %-10s %-10s %-15s\n" "服务名称" "状态" "开机自启" "内存使用"
    echo "------------------------------------------------------------"
    
    for svc in "${SERVICES[@]}"; do
        status=$(systemctl is-active "$svc" 2>/dev/null)
        enabled=$(systemctl is-enabled "$svc" 2>/dev/null)
        
        # 获取内存使用
        mem_usage=$(systemctl show "$svc" --property=MemoryCurrent --value 2>/dev/null)
        if [ -n "$mem_usage" ] && [ "$mem_usage" != "[not set]" ]; then
            mem_mb=$((mem_usage / 1024 / 1024))
            mem_str="${mem_mb}MB"
        else
            mem_str="-"
        fi
        
        # 状态颜色
        if [ "$status" = "active" ]; then
            status_str="${GREEN}● active${NC}"
        else
            status_str="${RED}● $status${NC}"
        fi
        
        if [ "$enabled" = "enabled" ]; then
            enabled_str="${GREEN}enabled${NC}"
        else
            enabled_str="${YELLOW}$enabled${NC}"
        fi
        
        printf "%-30s %-10s %-10s %-15s\n" "$svc" "$status_str" "$enabled_str" "$mem_str"
    done
    
    echo ""
    echo "=========================================="
    echo ""
}

# 查看日志
show_logs() {
    local target="$1"
    if [ -z "$target" ]; then
        echo -e "${RED}[错误]${NC} 请指定服务名查看日志"
        echo "用法: $0 logs <服务名>"
        exit 1
    fi
    
    if [[ " ${SERVICES[@]} " =~ " ${target} " ]]; then
        log_file="$LOG_DIR/${target}.log"
        if [ -f "$log_file" ]; then
            echo -e "${BLUE}[日志]${NC} $target (最后50行)"
            echo "----------------------------------------"
            tail -50 "$log_file"
        else
            echo -e "${YELLOW}[提示]${NC} 日志文件不存在: $log_file"
            echo "查看systemd日志:"
            journalctl -u "$target" -n 50 --no-pager
        fi
    else
        echo -e "${RED}[错误]${NC} 未知服务: $target"
        exit 1
    fi
}

# 主逻辑
case "$1" in
    start|stop|restart|enable|disable)
        execute_cmd "$1" "$2"
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    *)
        usage
        exit 1
        ;;
esac
