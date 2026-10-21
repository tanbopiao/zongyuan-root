#!/bin/bash
# 全站健康检查 - 每5分钟执行
LOG=/var/log/web-health.log
STATUS_FILE=/www/wwwroot/huodouai.com/monitor/status.json
mkdir -p /www/wwwroot/huodouai.com/monitor

ALERTS=0
DETAILS=""

for path in / /hub/ /axiom/ /kunlun/ /truth-engine/ /cte/ /rule-engine/ /collection-card/ /research-pipeline/ /drama-pipeline/ /legal-shield/; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 https://www.huodouai.com$path)
  TIME=$(curl -s -o /dev/null -w "%{time_total}" --max-time 5 https://www.huodouai.com$path)
  if [ "$CODE" != "200" ]; then
    ALERTS=$((ALERTS+1))
    DETAILS="$DETAILS $path=$CODE"
  fi
  if (( $(echo "$TIME > 3" | bc -l 2>/dev/null || echo 0) )); then
    DETAILS="$DETAILS $path慢=${TIME}s"
  fi
done

# 记录状态
echo "{$(date +%s)} online=$((11-ALERTS))/11 alerts=$ALERTS $DETAILS" >> $LOG

# 生成状态JSON
python3 -c "
import json,time
print(json.dumps({
  'timestamp': time.time(),
  'online': 11-$ALERTS,
  'total': 11,
  'alerts': $ALERTS,
  'details': '$DETAILS',
  'status': 'healthy' if $ALERTS==0 else 'degraded'
}, indent=2))
" > $STATUS_FILE 2>/dev/null

# 有告警时上报
if [ $ALERTS -gt 0 ]; then
  curl -s -X POST https://www.huodouai.com/api/report/truth     -H 'Content-Type: application/json'     -d "{\"truth_key\":\"ARCH.HEALTH.ALERT\",\"truth_value\":\"$ALERTS个页面异常:$DETAILS\",\"source_node\":\"server-123.207.202.158\",\"confidence\":0.9,\"truth_type\":\"risk\"}" > /dev/null
fi
