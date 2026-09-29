#!/bin/bash
# ZONGYUAN-ROOT 自动备份脚本
# 备份：MySQL数据库 + 关键配置 + 代码快照
BACKUP_DIR="/opt/ZONGYUAN-ROOT/backups"
DATE=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=7

# 1. MySQL备份
mysqldump -u root --all-databases --single-transaction 2>/dev/null | gzip > "$BACKUP_DIR/mysql_$DATE.sql.gz" 2>/dev/null

# 2. Nginx配置备份
tar czf "$BACKUP_DIR/nginx_conf_$DATE.tar.gz" /www/server/panel/vhost/nginx/ 2>/dev/null

# 3. systemd服务备份
tar czf "$BACKUP_DIR/systemd_$DATE.tar.gz" /etc/systemd/system/zongyuan-*.service 2>/dev/null

# 4. 政务API数据备份
tar czf "$BACKUP_DIR/gov_data_$DATE.tar.gz" /opt/ZONGYUAN-ROOT/gov_api/data/ 2>/dev/null

# 5. 内核状态备份
cp /root/.zongyuan_root/kernel_state.json "$BACKUP_DIR/kernel_state_$DATE.json" 2>/dev/null

# 清理旧备份
find "$BACKUP_DIR" -name "*.gz" -mtime +$KEEP_DAYS -delete 2>/dev/null
find "$BACKUP_DIR" -name "*.json" -mtime +$KEEP_DAYS -delete 2>/dev/null

echo "[$(date)] 备份完成: $DATE" >> /opt/ZONGYUAN-ROOT/logs/backup.log
