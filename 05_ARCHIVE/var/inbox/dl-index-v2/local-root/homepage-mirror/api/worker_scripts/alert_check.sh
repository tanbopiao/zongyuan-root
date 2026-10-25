#!/bin/bash
# alert_check.sh 异常自动告警
LAST=$(tail -1 /tmp/heartbeat.log 2>/dev/null)
if [ -z "$LAST" ]; then
  curl -s -X POST https://ntfy.sh/zongyuan-kunlun-2026-result \
    -H "Title: 心跳丢失告警" \
    -d "本地心跳中断，请检查" >/dev/null 2>&1
fi
echo "告警检查完成"
