#!/bin/bash
# ZONGYUAN-ROOT 能量调度器 v1.0
# 内存清理 + 带宽监控 + 服务优先级
LOG="/opt/ZONGYUAN-ROOT/energy.log"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

# 1. 内存监控（>80%清理）
MEM_PCT=$(free | awk '/Mem:/{printf "%.0f", $3/$2*100}')
if [ "$MEM_PCT" -gt 80 ]; then
    log "内存${MEM_PCT}%，执行清理"
    sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null
    # 重启低优先级服务释放内存
    for svc in zongyuan-gov zongyuan-license zongyuan-meta; do
        systemctl restart "$svc" 2>/dev/null
    done
    log "内存清理后: $(free | awk '/Mem:/{printf "%.0f%%", $3/$2*100}')"
fi

# 2. 带宽监控（3Mbps上限，视频生成限速）
BW=$(cat /proc/net/dev | grep eth0 | awk '{print $10}')
# 简化：如果有大文件下载，记录日志
log "带宽监控: 接收${BW}字节, 内存${MEM_PCT}%"

# 3. CPU监控
CPU_PCT=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d. -f1)
if [ "$CPU_PCT" -gt 90 ]; then
    log "CPU${CPU_PCT}%，降低非核心服务优先级"
    for pid in $(pgrep -f "zongyuan-gov\|zongyuan-license"); do
        renice +10 -p "$pid" 2>/dev/null
    done
fi

echo "能量调度完成: CPU=${CPU_PCT}% MEM=${MEM_PCT}%"
