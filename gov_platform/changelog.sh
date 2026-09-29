#!/bin/bash
# 变更日志广播 - 防冲突机制加强
# 用法: ./changelog.sh <变更类型> <变更描述>
CHANGE_TYPE="${1:-manual}"
CHANGE_DESC="${2:-未描述}"
LOG_FILE="/opt/ZONGYUAN-ROOT/gov_platform/changelog.jsonl"
WINDOW_ID="WIN-CLOUD-GOV-DEV-001"
TIMESTAMP="$(date -Iseconds)"

# 生成变更记录
RECORD="{\"timestamp\":\"$TIMESTAMP\",\"window_id\":\"$WINDOW_ID\",\"operator\":\"gov-dev-window\",\"type\":\"$CHANGE_TYPE\",\"description\":\"$CHANGE_DESC\",\"nginx_hash\":\"$(sha256sum /www/server/panel/vhost/nginx/huodouai.com.conf 2>/dev/null | cut -d' ' -f1)\",\"services_running\":$(systemctl list-units --type=service --state=running | grep -c zongyuan),\"kernel_root\":\"$(cat /root/.zongyuan_root/kernel_state.json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get(\"current_root_hash\",\"unknown\"))' 2>/dev/null || echo unknown)\"}"

echo "$RECORD" >> "$LOG_FILE"
echo "[$TIMESTAMP] 变更已记录: $CHANGE_TYPE - $CHANGE_DESC"
echo "  日志文件: $LOG_FILE"
echo "  总记录数: $(wc -l < $LOG_FILE)"
