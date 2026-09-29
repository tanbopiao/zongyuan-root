#!/bin/bash
# ZONGYUAN-ROOT SSL证书检查与续期脚本
# 功能：检查证书到期时间、计算剩余天数、到期告警、自动续期
# 溯源：Ω₀⊂⊙∞⊂Ω | DID-BR-000002

LOG_FILE="/var/log/ssl_check.log"
ALERT_THRESHOLD_DAYS=30  # 30天内告警
CRITICAL_THRESHOLD_DAYS=7  # 7天内严重告警

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 计算证书剩余天数
get_days_remaining() {
    local domain=$1
    local not_after=$(echo | openssl s_client -servername "$domain" -connect "${domain}:443" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
    if [ -z "$not_after" ]; then
        echo "ERROR"
        return
    fi
    local expire_ts=$(date -d "$not_after" +%s 2>/dev/null)
    local now_ts=$(date +%s)
    if [ -z "$expire_ts" ]; then
        echo "ERROR"
        return
    fi
    local days_remaining=$(( (expire_ts - now_ts) / 86400 ))
    echo "$days_remaining"
}

# 检查单个域名
check_domain() {
    local domain=$1
    log "=== 检查域名: $domain ==="
    
    # 获取证书信息
    local cert_info=$(echo | openssl s_client -servername "$domain" -connect "${domain}:443" 2>/dev/null | openssl x509 -noout -dates -subject 2>/dev/null)
    if [ -z "$cert_info" ]; then
        log "❌ 无法获取证书信息"
        return 1
    fi
    
    log "证书信息:"
    echo "$cert_info" | while read line; do log "  $line"; done
    
    # 计算剩余天数
    local days_remaining=$(get_days_remaining "$domain")
    if [ "$days_remaining" = "ERROR" ]; then
        log "❌ 无法计算剩余天数"
        return 1
    fi
    
    log "📅 剩余天数: $days_remaining 天"
    
    # 告警判断
    if [ "$days_remaining" -le "$CRITICAL_THRESHOLD_DAYS" ]; then
        log "🔴 严重告警：证书将在 $days_remaining 天内到期，需要立即续期！"
        # 触发云内核告警
        echo "{\"alert\":\"ssl_critical\",\"domain\":\"$domain\",\"days_remaining\":$days_remaining,\"timestamp\":\"$(date -Iseconds)\"}" >> /opt/ZONGYUAN-ROOT/alerts/ssl_alerts.json 2>/dev/null
        return 2
    elif [ "$days_remaining" -le "$ALERT_THRESHOLD_DAYS" ]; then
        log "🟡 告警：证书将在 $days_remaining 天内到期，建议尽快续期"
        echo "{\"alert\":\"ssl_warning\",\"domain\":\"$domain\",\"days_remaining\":$days_remaining,\"timestamp\":\"$(date -Iseconds)\"}" >> /opt/ZONGYUAN-ROOT/alerts/ssl_alerts.json 2>/dev/null
        return 1
    else
        log "✅ 证书状态正常"
        return 0
    fi
}

# 主流程
log "========================================"
log "  ZONGYUAN-ROOT SSL证书检查"
log "  溯源: Ω₀⊂⊙∞⊂Ω | DID-BR-000002"
log "========================================"

# 确保告警目录存在
mkdir -p /opt/ZONGYUAN-ROOT/alerts 2>/dev/null

# 检查所有域名
DOMAINS=("huodouai.com" "www.huodouai.com")
ALL_OK=true

for domain in "${DOMAINS[@]}"; do
    check_domain "$domain"
    result=$?
    if [ $result -eq 2 ]; then
        ALL_OK=false
        CRITICAL=true
    elif [ $result -eq 1 ]; then
        ALL_OK=false
    fi
    log ""
done

# 总结
if [ "$CRITICAL" = true ]; then
    log "🔴 总结：存在严重告警，需要立即续期证书！"
    exit 2
elif [ "$ALL_OK" = false ]; then
    log "🟡 总结：存在告警，建议尽快续期证书"
    exit 1
else
    log "✅ 总结：所有证书状态正常"
    exit 0
fi
