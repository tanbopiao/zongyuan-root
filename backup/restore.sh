#!/bin/bash
BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
  echo "用法: ./restore.sh <backup_file.tar.gz>"
  ls -lt /opt/ZONGYUAN-ROOT/backups/*.tar.gz 2>/dev/null | head -5
  exit 1
fi
echo "正在从 $BACKUP_FILE 恢复..."
tar -xzf $BACKUP_FILE -C /opt/ZONGYUAN-ROOT/
echo "✅ 恢复完成"
