#!/bin/bash
# 静默自治监控脚本 - 每15分钟执行一次
LOG_FILE="/opt/ZONGYUAN-ROOT/logs/autonomous_monitor.log"
mkdir -p "$(dirname $LOG_FILE)"

echo "[$(date "+%Y-%m-%d %H:%M:%S")] 静默自治监控启动" >> "$LOG_FILE"

# 1. AI Proxy健康检查
if ! systemctl is-active --quiet zongyuan-aiproxy; then
    echo "[$(date "+%Y-%m-%d %H:%M:%S")] AI Proxy未运行，自动重启..." >> "$LOG_FILE"
    systemctl restart zongyuan-aiproxy
    sleep 5
fi

# 2. 磁盘空间检查
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | tr -d "%")
if [ "$DISK_USAGE" -gt 85 ]; then
    echo "[$(date "+%Y-%m-%d %H:%M:%S")] 磁盘${DISK_USAGE}%，清理..." >> "$LOG_FILE"
    journalctl --vacuum-size=50M 2>/dev/null
    find /opt/ZONGYUAN-ROOT/backups/ -name "*.tar.gz" -mtime +7 -delete 2>/dev/null
fi

# 3. 内存检查
MEM_AVAILABLE=$(free -m | grep Mem | awk '{print $7}')
if [ "$MEM_AVAILABLE" -lt 100 ]; then
    sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null
fi

# 4. 任务队列超时清理
python3 /opt/ZONGYUAN-ROOT/clean_timeout_tasks.py 2>/dev/null

# 5. API健康检查
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8021/health --max-time 5 2>/dev/null)
if [ "$API_STATUS" != "200" ]; then
    echo "[$(date "+%Y-%m-%d %H:%M:%S")] API健康检查失败($API_STATUS)，重启AI Proxy..." >> "$LOG_FILE"
    systemctl restart zongyuan-aiproxy
fi

# 6. 日志轮转（超过10MB截断）
if [ -f "$LOG_FILE" ] && [ $(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0) -gt 10485760 ]; then
    tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
    echo "[$(date "+%Y-%m-%d %H:%M:%S")] 日志已轮转" >> "$LOG_FILE"
fi

# 7. 作品库0字节文件清理
find /www/wwwroot/huodouai.com/drama/videos/ -name "*.mp4" -size 0 -delete 2>/dev/null

echo "[$(date "+%Y-%m-%d %H:%M:%S")] 静默自治监控完成(API健康+日志轮转+0字节清理)" >> "$LOG_FILE"
