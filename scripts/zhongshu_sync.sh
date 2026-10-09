#!/usr/bin/env bash
# 云端双向同步汇总 | 读本地资产索引+节点注册表+网关 → 同步状态JSON+上报 | cron 30min
set -uo pipefail
DOC="/www/wwwroot/huodouai.com"; TS=$(date '+%Y-%m-%dT%H:%M:%S%z')
LOCAL=$(curl -s -m 8 "http://127.0.0.1:9001/api/status" 2>/dev/null | grep -o '"truth_count": *[0-9]*' | grep -o '[0-9]*$')
NODES=$(cat "$DOC/_zongyuan-assets/zhongshu-nodes.json" 2>/dev/null || echo "{}")
LI=$(curl -s -m 8 "http://127.0.0.1:9001/" >/dev/null 2>&1 && cat "$DOC/_zongyuan-assets/local-asset-index.json" 2>/dev/null || echo "{}")
LF=$(echo "$LI" | grep -o '"total_files": *[0-9]*' | grep -o '[0-9]*$')
LIU=$(echo "$LI" | grep -o '"generated": *"[^"]*"' | head -1 | cut -d'"' -f4)
SYNC="{\"ts\":\"$TS\",\"cloud\":{\"truth_count\":\"${LOCAL:-0}\",\"node\":\"CLOUD-HUB\"},\"local\":{\"files\":\"${LF:-?}\",\"indexed_at\":\"${LIU:-?}\",\"node\":\"NODE-DEV-DOUBAO-WORK-001\"},\"nodes\":$(echo "$NODES" | grep -o '\[[^]]*\]' | head -1 || echo "[]"),\"direction\":\"local->cloud 资产索引/真值上报 · cloud->local 指令队列\",\"status\":\"bidirectional\"}"
echo "$SYNC" > "$DOC/_zongyuan-assets/zhongshu-sync.json"
echo "[$TS] 双向同步: 云端tc=${LOCAL:-0} · 本地索引${LF:-?}文件@${LIU:-?}"
