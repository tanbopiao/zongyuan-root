#!/usr/bin/env bash
# 云端中枢监控指标采集 | DID-BR-000002 | cron */10
set -uo pipefail
DIR="/www/wwwroot/huodouai.com/zhongshu/data/metrics"
DOCROOT="/www/wwwroot/huodouai.com"
mkdir -p "$DIR"
TS=$(date '+%Y-%m-%dT%H:%M:%S%z'); EPOCH=$(date +%s)
START=$(date +%s%N)
RESP=$(curl -s -m 8 http://127.0.0.1:9001/api/status 2>/dev/null)
END=$(date +%s%N); LATENCY_MS=$(( (END-START)/1000000 ))
TC=$(echo "$RESP" | grep -o '"truth_count": *[0-9]*' | grep -o '[0-9]*$')
MERKLE=$(echo "$RESP" | grep -o '"merkle_root": *"[a-f0-9]\{64\}"' | grep -o '[a-f0-9]\{16\}' | head -1)
GW_OK=0; [ -n "$TC" ] && GW_OK=1
DISK=$(df -P "$DOCROOT" 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
MEM=$(free -m 2>/dev/null | awk '/Mem:/{printf "%.0f", $3/$2*100}')
GP=$(pgrep -f gateway_server.py >/dev/null && echo 1 || echo 0)
SP=$(pgrep -f "scheduler.py --interval" >/dev/null && echo 1 || echo 0)
ERR=$(tail -200 "$DIR/../gateway.log" 2>/dev/null | grep -cE '"status": ?[45][0-9][0-9]' || true)
printf '{"ts":"%s","epoch":%s,"gateway_ok":%s,"truth_count":"%s","merkle":"%s","latency_ms":%s,"disk_pct":%s,"mem_pct":%s,"gw_proc":%s,"sch_proc":%s,"err_10m":%s}\n' \
  "$TS" "$EPOCH" "$GW_OK" "$TC" "$MERKLE" "$LATENCY_MS" "${DISK:-0}" "${MEM:-0}" "$GP" "$SP" "${ERR:-0}" >> "$DIR/metrics-$(date +%Y%m%d).jsonl"
printf '{"last":{"ts":"%s","gateway_ok":%s,"truth_count":"%s","merkle":"%s","latency_ms":%s,"disk_pct":%s,"mem_pct":%s},"updated_at":"%s"}\n' \
  "$TS" "$GW_OK" "$TC" "$MERKLE" "$LATENCY_MS" "${DISK:-0}" "${MEM:-0}" "$TS" > /www/wwwroot/huodouai.com/_zongyuan-assets/zhongshu-metrics.json
ALERT=""
[ "$GW_OK" != "1" ] && ALERT="$ALERT 网关无响应"
[ -n "$DISK" ] && [ "$DISK" -gt 85 ] && ALERT="$ALERT 磁盘${DISK}%"
[ -n "$MEM" ] && [ "$MEM" -gt 90 ] && ALERT="$ALERT 内存${MEM}%"
[ "$LATENCY_MS" -gt 2000 ] && ALERT="$ALERT 延迟${LATENCY_MS}ms"
if [ -n "$ALERT" ]; then
  echo "[$TS] ALERT:$ALERT" >> "$DIR/alert.log"
  curl -s -m 8 -X POST "https://zrntfy.huodouai.com/zongyuan-did-br-000002-7f3a9c2e-alert" -H "X-DID: DID-BR-000002" -d "{\"event\":\"zhongshu_metrics_alert\",\"msg\":\"$ALERT\",\"ts\":\"$TS\"}" >/dev/null 2>&1 || true
fi
echo "[$TS] gw=$GW_OK tc=$TC dsk=${DISK}% mem=${MEM}% lat=${LATENCY_MS}ms err=${ERR}"
