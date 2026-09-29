#!/bin/bash
# ZONGYUAN-ROOT 自我修复引擎 v2.0
# 配置回滚 + 端口处理 + 磁盘清理 + Key失效检测
LOG="/opt/ZONGYUAN-ROOT/self_heal.log"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

# 1. Nginx配置语法检查+自动回滚
nginx -t 2>&1 | grep -q "syntax is ok" || {
    log "NGINX配置语法错误，尝试回滚"
    if [ -f /www/server/panel/vhost/nginx/huodouai.com.conf.bak ]; then
        cp /www/server/panel/vhost/nginx/huodouai.com.conf.bak /www/server/panel/vhost/nginx/huodouai.com.conf
        nginx -s reload 2>/dev/null || nginx
        log "NGINX已回滚到上一版本"
    fi
}

# 2. 关键服务端口占用自动处理
for svc in zongyuan-aiproxy:8021 zongyuan-drift:8022 zongyuan-omega:8000; do
    name=${svc%:*}; port=${svc#*:}
    if ! systemctl is-active "$name" >/dev/null 2>&1; then
        log "$name 未运行，尝试重启"
        systemctl restart "$name" 2>/dev/null
    fi
    # 端口被占但服务没起来
    if ss -tlnp | grep -q ":$port " && ! systemctl is-active "$name" >/dev/null 2>&1; then
        log "端口$port被占用但$name未运行"
    fi
done

# 3. 磁盘清理（>85%触发）
USAGE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$USAGE" -gt 85 ]; then
    log "磁盘使用率${USAGE}%，执行清理"
    find /opt/ZONGYUAN-ROOT/drama_output/logs -name "*.log" -mtime +7 -delete 2>/dev/null
    find /opt/ZONGYUAN-ROOT -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
    journalctl --vacuum-size=50M 2>/dev/null
    log "清理完成，当前使用率: $(df / | tail -1 | awk '{print $5}')"
fi

# 4. API Key失效检测（调用失败率>50%告警）
# 简化版：检查AI Proxy健康
if ! curl -s http://127.0.0.1:8021/health >/dev/null 2>&1; then
    log "AI Proxy无响应，重启"
    systemctl restart zongyuan-aiproxy
fi

echo "自我修复检查完成: $(date '+%Y-%m-%d %H:%M:%S')"
