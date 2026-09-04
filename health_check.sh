#!/bin/bash
# ZONGYUAN-ROOT 健康检查脚本
# 检查核心服务和端口，异常自动重启

LOG_FILE="/var/log/zongyuan-health.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 健康检查开始" >> $LOG_FILE

# 检查关键端口
check_port() {
    local port=$1
    local service=$2
    if ss -tlnp | grep -q ":$port "; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $service (端口$port) 正常" >> $LOG_FILE
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $service (端口$port) 异常，尝试重启" >> $LOG_FILE
        systemctl restart $service 2>/dev/null || true
    fi
}

check_port 8000 zongyuan-omega
check_port 8001 zongyuan-loip
check_port 8005 zongyuan-gov
check_port 8006 zongyuan-anchor

# 检查MySQL
if ss -tlnp | grep -q ":3306 "; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ MySQL 正常" >> $LOG_FILE
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  MySQL 异常，尝试启动" >> $LOG_FILE
    /www/server/mysql/bin/mysqld --defaults-file=/etc/my.cnf --user=mysql &
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 健康检查完成" >> $LOG_FILE
