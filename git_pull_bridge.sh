#!/bin/bash
# ZONGYUAN-ROOT 云内核从Git桥接拉取本地资产
set -e
LOG_FILE="/opt/ZONGYUAN-ROOT/logs/git_pull_bridge.log"
log() { echo "[$(date "+%Y-%m-%d %H:%M:%S")] $1" >> "$LOG_FILE"; }

cd /opt/ZONGYUAN-ROOT
log "=== 从Gitee拉取最新 ==="
git pull gitee master --no-rebase 2>&1 | tail -5 >> "$LOG_FILE" 2>&1

# 检查是否有新的local_bridge资产
if [ -d "local_bridge/workbench_deliverables" ]; then
    COUNT=$(ls local_bridge/workbench_deliverables/*.md 2>/dev/null | wc -l)
    log "本地桥接资产数: $COUNT"
    # 复制到incoming_sync供内核处理
    cp -u local_bridge/workbench_deliverables/*.md incoming_sync/ 2>/dev/null || true
fi
log "✅ Pull完成"
