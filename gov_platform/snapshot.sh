#!/bin/bash
# 变更前快照脚本 - 防冲突机制规则6
# 用法: source snapshot.sh 或 ./snapshot.sh <变更描述>
SNAP_DIR="/opt/ZONGYUAN-ROOT/gov_platform/backups/snapshots"
DATE=$(date +%Y%m%d_%H%M%S)
DESC="${1:-manual_change}"
SNAP_FILE="$SNAP_DIR/snapshot_${DATE}_${DESC}.json"

mkdir -p "$SNAP_DIR"

# 生成快照
cat > "$SNAP_FILE" << EOF
{
  "snapshot_id": "SNAP-$DATE",
  "description": "$DESC",
  "timestamp": "$(date -Iseconds)",
  "window_id": "WIN-CLOUD-GOV-DEV-001",
  "nginx_config_hash": "$(sha256sum /www/server/panel/vhost/nginx/huodouai.com.conf 2>/dev/null | cut -d' ' -f1)",
  "services": {
    $(systemctl list-units --type=service --state=running | grep zongyuan | awk '{printf "\"%s\": \"running\", ", $1}' | sed 's/,$//')
  },
  "ports": "$(ss -tlnp | grep -E '8000|8001|8003|8006|8021|8025|8765|8766|7100' | awk '{print $4}' | tr '\n' ',')",
  "memory_used": "$(free -h | awk 'NR==2{print $3}')",
  "disk_used": "$(df -h / | awk 'NR==2{print $5}')",
  "kernel_chain_root": "$(cat /root/.zongyuan_root/kernel_state.json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("current_root_hash","unknown"))' 2>/dev/null || echo 'unknown')"
}
EOF

echo "快照已生成: $SNAP_FILE"
cat "$SNAP_FILE" | python3 -m json.tool 2>/dev/null | head -20

# 清理30天前的快照
find "$SNAP_DIR" -name 'snapshot_*.json' -mtime +30 -delete 2>/dev/null
