#!/bin/bash
# ZONGYUAN-ROOT 自动备份脚本
# 每日凌晨3点执行

BACKUP_DIR="/opt/backups/$(date +%Y%m%d)"
LOG_FILE="/var/log/zongyuan-backup.log"

mkdir -p "$BACKUP_DIR"

echo "$(date): === 开始自动备份 ===" >> "$LOG_FILE"

# 1. 备份网站文件
tar -czf "$BACKUP_DIR/www.tar.gz" /www/wwwroot/ 2>/dev/null
echo "$(date): 网站文件备份完成" >> "$LOG_FILE"

# 2. 备份Nginx配置
tar -czf "$BACKUP_DIR/nginx-config.tar.gz" /www/server/panel/vhost/nginx/ 2>/dev/null
echo "$(date): Nginx配置备份完成" >> "$LOG_FILE"

# 3. 备份ZONGYUAN-ROOT核心（排除大文件）
tar -czf "$BACKUP_DIR/zongyuan-root.tar.gz" \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  --exclude='*/output/*' \
  --exclude='*/vector_db/*' \
  /opt/ZONGYUAN-ROOT/ 2>/dev/null
echo "$(date): ZONGYUAN-ROOT备份完成" >> "$LOG_FILE"

# 4. 备份.env（加密）
if [ -f /opt/ZONGYUAN-ROOT/.env ]; then
  cp /opt/ZONGYUAN-ROOT/.env "$BACKUP_DIR/env.backup"
  chmod 600 "$BACKUP_DIR/env.backup"
  echo "$(date): 环境变量备份完成" >> "$LOG_FILE"
fi

# 5. 备份MySQL（如果启用）
if systemctl is-active --quiet mysqld 2>/dev/null; then
  mysqldump --all-databases -u root > "$BACKUP_DIR/mysql-all.sql" 2>/dev/null
  echo "$(date): MySQL备份完成" >> "$LOG_FILE"
fi

# 6. 生成备份清单
ls -lh "$BACKUP_DIR/" > "$BACKUP_DIR/MANIFEST.txt"
echo "$(date): 备份清单生成完成" >> "$LOG_FILE"

# 7. 清理7天前的备份
find /opt/backups -type d -mtime +7 -exec rm -rf {} + 2>/dev/null
echo "$(date): 旧备份清理完成" >> "$LOG_FILE"

# 8. 计算总大小
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "$(date): === 备份完成，总大小: $TOTAL_SIZE ===" >> "$LOG_FILE"
