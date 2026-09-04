#!/bin/bash
# ZONGYUAN-ROOT 自动备份脚本 v2.0
# 7天滚动保留 + SHA256校验 + 飞书云盘待上传标记
BACKUP_DIR=/opt/ZONGYUAN-ROOT/backups
SOURCE_DIR=/opt/ZONGYUAN-ROOT
DATE=$(date '+%Y%m%d_%H%M%S')
KEEP_DAYS=7

mkdir -p $BACKUP_DIR

# 1. 排除大文件和日志，备份核心资产
tar czf $BACKUP_DIR/zongyuan_backup_${DATE}.tar.gz \
  --exclude='backups' \
  --exclude='logs' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='node_modules' \
  -C $(dirname $SOURCE_DIR) $(basename $SOURCE_DIR) 2>/dev/null

# 2. SHA256校验
SHA256=$(sha256sum $BACKUP_DIR/zongyuan_backup_${DATE}.tar.gz | awk '{print $1}')
SIZE=$(du -h $BACKUP_DIR/zongyuan_backup_${DATE}.tar.gz | awk '{print $1}')

# 3. 生成清单
cat > $BACKUP_DIR/zongyuan_backup_${DATE}_meta.json << META
{
  "backup_id": "ZONGYUAN-BACKUP-$DATE",
  "timestamp": "$(date -Iseconds)",
  "filename": "zongyuan_backup_${DATE}.tar.gz",
  "size": "$SIZE",
  "sha256": "$SHA256",
  "source": "/opt/ZONGYUAN-ROOT",
  "keep_days": $KEEP_DAYS,
  "feishu_upload": "pending",
  "did": "DID-BR-000002"
}
META

# 4. 清理7天前备份
find $BACKUP_DIR -name "zongyuan_backup_*.tar.gz" -mtime +$KEEP_DAYS -delete 2>/dev/null
find $BACKUP_DIR -name "zongyuan_backup_*_meta.json" -mtime +$KEEP_DAYS -delete 2>/dev/null

# 5. 记录日志
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份完成: zongyuan_backup_${DATE}.tar.gz ($SIZE) SHA256=${SHA256:0:16}..." >> $BACKUP_DIR/backup_log.txt

echo "备份完成: zongyuan_backup_${DATE}.tar.gz ($SIZE)"
echo "SHA256: ${SHA256:0:32}..."
echo "保留策略: ${KEEP_DAYS}天滚动"
