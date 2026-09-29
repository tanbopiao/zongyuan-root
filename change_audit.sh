#!/bin/bash
# 变更审计日志 - 记录所有共享资源修改
# 用法: ./change_audit.sh <window_id> <resource> <action> <description>

WINDOW="$1"
RESOURCE="$2"
ACTION="$3"
DESC="$4"
LOG_FILE="/opt/ZONGYUAN-ROOT/logs/change_audit.log"

mkdir -p /opt/ZONGYUAN-ROOT/logs

TIMESTAMP=$(date -Iseconds)
SHA_BEFORE=""
SHA_AFTER=""

# 如果是文件，记录修改前后的SHA256
if [ -f "$RESOURCE" ]; then
    SHA_BEFORE=$(sha256sum "$RESOURCE" | cut -d' ' -f1)
fi

echo "[$TIMESTAMP] window=$WINDOW resource=$RESOURCE action=$ACTION desc=\"$DESC\" sha_before=$SHA_BEFORE" >> "$LOG_FILE"
echo "📝 审计记录已写入: $RESOURCE ($ACTION)"
