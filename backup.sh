#!/bin/bash
# ZONGYUAN-ROOT 云端备份脚本
BACKUP_DIR="/opt/ZONGYUAN-ROOT/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/zongyuan_backup_$DATE.tar.gz"

echo "=== 开始备份 $(date) ==="

mkdir -p $BACKUP_DIR

# 备份配置和真值文件
tar -czf $BACKUP_FILE \
    /opt/ZONGYUAN-ROOT/*.json \
    /opt/ZONGYUAN-ROOT/.env \
    /opt/ZONGYUAN-ROOT/omega_brain/ \
    /opt/ZONGYUAN-ROOT/loip/ \
    /opt/ZONGYUAN-ROOT/truth_architecture/ \
    /opt/ZONGYUAN-ROOT/meta_laws/ \
    2>/dev/null

# 备份MySQL数据库（如果运行中）
if ss -tlnp | grep -q ":3306 "; then
    mysqldump -u root --all-databases > "$BACKUP_DIR/mysql_backup_$DATE.sql" 2>/dev/null
    gzip "$BACKUP_DIR/mysql_backup_$DATE.sql"
    echo "  MySQL数据库已备份"
fi

# 清理7天前的备份
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "  备份完成: $BACKUP_FILE"
echo "  备份大小: $(du -h $BACKUP_FILE | cut -f1)"
echo "=== 备份完成 ==="
