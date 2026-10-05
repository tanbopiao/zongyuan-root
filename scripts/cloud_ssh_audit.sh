#!/usr/bin/env bash
# 云内核SSH登录审计 | 新登录检测→告警 | cron 每5分钟
set -uo pipefail
AUD="/www/wwwroot/huodouai.com/zhongshu/data/audit"; mkdir -p "$AUD"
TS=$(date '+%Y-%m-%dT%H:%M:%S%z'); SEEN="$AUD/.seen-last"
LAST=$(tail -c 200000 /var/log/secure 2>/dev/null | grep -E "Accepted|Failed password" | tail -20 || true)
NEW=$(echo "$LAST" | grep -vFf "$SEEN" 2>/dev/null || echo "$LAST" | head -1)
echo "$LAST" > "$SEEN"
if [ -n "$NEW" ]; then
  # 失败登录阈值告警(疑似爆破)
  FAIL=$(echo "$NEW" | grep -c "Failed password" || true)
  ACC=$(echo "$NEW" | grep -c "Accepted" || true)
  echo "[$TS] ssh_audit: accepted=$ACC failed=$FAIL" >> "$AUD/ssh-$(date +%Y%m%d).log"
  [ "$FAIL" -gt 5 ] && curl -s -m 8 -X POST "https://zrntfy.huodouai.com/zongyuan-did-br-000002-7f3a9c2e-alert" -H "X-DID: DID-BR-000002" -d "{\"event\":\"ssh_brute_alert\",\"failed\":$FAIL,\"ts\":\"$TS\"}" >/dev/null 2>&1
  [ "$ACC" -gt 0 ] && echo "$NEW" | grep "Accepted" | head -5 >> "$AUD/ssh-logins.log"
fi
echo "[$TS] ssh审计巡检 done" >> "$AUD/audit-run.log"
