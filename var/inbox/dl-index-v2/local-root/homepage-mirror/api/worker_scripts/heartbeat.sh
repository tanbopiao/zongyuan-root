#!/bin/bash
# heartbeat.sh 与云端中枢心跳
NOW=$(date +%s)
LOAD=$(uptime | awk -F'load average:' '{print $2}')
DISK=$(df -h / | tail -1 | awk '{print $5}')

curl -s -X POST https://www.huodouai.com/api/report/truth \
  -H "Content-Type: application/json" \
  -d "{\"truth_value\":\"心跳 load:$LOAD disk:$DISK block:#1408\",\"truth_type\":\"meta_law\"}" >/dev/null 2>&1

echo "心跳 @ $(date) load=$LOAD disk=$DISK"
