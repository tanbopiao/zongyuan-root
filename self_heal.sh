#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
# ZONGYUAN-ROOT 自我修复引擎 v2.0（全覆盖版）
# 功能：16服务健康检查+自动重启 + 内存监控 + 磁盘清理 + SSH守护 + 配置回滚
LOG="/opt/ZONGYUAN-ROOT/self_heal.log"
HEAL_LOG="/opt/ZONGYUAN-ROOT/logs/self_heal_actions.log"

log() { echo "[$(date "+%Y-%m-%d %H:%M:%S")] $1" >> "$LOG"; }
heal_log() { echo "[$(date "+%Y-%m-%d %H:%M:%S")] [HEAL] $1" >> "$HEAL_LOG"; }

mkdir -p $(dirname "$HEAL_LOG")
touch "$HEAL_LOG"

# === 1. 16个ZONGYUAN核心服务健康检查 + 自动重启 ===
ZONGYUAN_SERVICES=(
    "zongyuan-omega"
    "zongyuan-loip"
    "zongyuan-vector"
    "zongyuan-meta"
    "zongyuan-platform"
    "zongyuan-smartai"
    "zongyuan-gov"
    "zongyuan-ance"
    "zongyuan-event"
    "zongyuan-federation"
    "zongyuan-drift"
    "zongyuan-monitor"
    "zongyuan-license"
    "zongyuan-idle-engine"
    "zongyuan-aiproxy"
    "zongyuan-deploy-api"
)

HEALED_COUNT=0
FAILED_COUNT=0

for svc in "${ZONGYUAN_SERVICES[@]}"; do
    if ! systemctl is-active "$svc" >/dev/null 2>&1; then
        log "$svc 未运行，尝试重启"
        if systemctl restart "$svc" 2>/dev/null; then
            sleep 2
            if systemctl is-active "$svc" >/dev/null 2>&1; then
                heal_log "$svc 已自动重启成功"
                HEALED_COUNT=$((HEALED_COUNT+1))
            else
                heal_log "$svc 重启失败，需要人工介入"
                FAILED_COUNT=$((FAILED_COUNT+1))
            fi
        else
            heal_log "$svc 重启命令执行失败"
            FAILED_COUNT=$((FAILED_COUNT+1))
        fi
    fi
done

# === 2. 其他关键服务检查 ===
OTHER_SERVICES=("aios" "drama-api" "frps" "site_total" "redis" "mysqld" "docker")
for svc in "${OTHER_SERVICES[@]}"; do
    if systemctl is-enabled "$svc" >/dev/null 2>&1; then
        if ! systemctl is-active "$svc" >/dev/null 2>&1; then
            log "$svc 未运行，尝试重启"
            systemctl restart "$svc" 2>/dev/null
            HEALED_COUNT=$((HEALED_COUNT+1))
        fi
    fi
done

# === 3. 内存监控与预警 ===
MEM_TOTAL=$(free -m | awk "/^Mem:/ {print \$2}")
MEM_USED=$(free -m | awk "/^Mem:/ {print \$3}")
MEM_PERCENT=$((MEM_USED * 100 / MEM_TOTAL))

if [ $MEM_PERCENT -ge 90 ]; then
    log "内存使用率${MEM_PERCENT}%，触发紧急清理"
    sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null
    heal_log "内存紧急清理已执行（使用率${MEM_PERCENT}%）"
elif [ $MEM_PERCENT -ge 80 ]; then
    log "内存使用率${MEM_PERCENT}%，接近警戒线"
fi

# === 4. 磁盘清理（>85%触发） ===
DISK_USAGE=$(df / | awk "NR==2 {print \$5}" | tr -d "%")
if [ "$DISK_USAGE" -ge 85 ]; then
    log "磁盘使用率${DISK_USAGE}%，执行清理"
    find /var/log -name "*.log" -mtime +7 -delete 2>/dev/null
    find /tmp -type f -mtime +3 -delete 2>/dev/null
    journalctl --vacuum-time=7d 2>/dev/null
    heal_log "磁盘清理已执行（使用率${DISK_USAGE}%）"
fi

# === 5. SSH authorized_keys守护 ===
BACKUP="/opt/ZONGYUAN-ROOT/backups/ssh/authorized_keys.latest"
TARGET="/root/.ssh/authorized_keys"
if [ -f "$BACKUP" ]; then
    if ! grep -q "zongyuan" "$TARGET" 2>/dev/null; then
        log "authorized_keys异常，从备份恢复"
        cp "$BACKUP" "$TARGET"
        chmod 600 "$TARGET"
        chmod 70 /root/.ssh
        heal_log "SSH authorized_keys已恢复"
    fi
    cp "$TARGET" "$BACKUP" 2>/dev/null
fi

# === 6. 输出汇总 ===
TOTAL_SERVICES=${#ZONGYUAN_SERVICES[@]}
log "自我修复检查完成: 检查${TOTAL_SERVICES}个ZONGYUAN服务, 修复${HEALED_COUNT}个, 失败${FAILED_COUNT}个, 内存${MEM_PERCENT}%, 磁盘${DISK_USAGE}%"
echo "[$(date "+%Y-%m-%d %H:%M:%S")] 自我修复v2.0完成: 修复${HEALED_COUNT}个, 失败${FAILED_COUNT}个, 内存${MEM_PERCENT}%, 磁盘${DISK_USAGE}%"
