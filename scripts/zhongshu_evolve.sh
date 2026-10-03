#!/usr/bin/env bash
# 云端自主进化循环 | 能力矩阵评估→短板提案→白名单自实施→挂起+上报 | cron 每日
set -uo pipefail
DOC="/www/wwwroot/huodouai.com"; ZD="$DOC/zhongshu"; EV="$ZD/data/evolution"; mkdir -p "$EV"
TS=$(date '+%Y-%m-%dT%H:%M:%S%z')
# 1) 能力矩阵评估 (6 维度 0/1)
SVC=$(( $(systemctl is-active zhongshu-gateway 2>/dev/null | grep -c active) + $(systemctl is-active zhongshu-scheduler 2>/dev/null | grep -c active) ))
HEAL=$(( $(crontab -l 2>/dev/null | grep -c zhongshu_health) + $(crontab -l 2>/dev/null | grep -c zhongshu_bootstrap) ))
LEARN=$([ -s "$ZD/data/meta-laws-index.json" ] && echo 1 || echo 0)
DECIDE=$([ -d "$ZD/data/decisions" ] && echo 1 || echo 0)
MONITOR=$(( $(crontab -l 2>/dev/null | grep -c zhongshu_metrics) ))
VERSION=$([ -d "$ZD/zhongshu-server/.git" ] && echo 1 || echo 0)
# 2) 能力总分 + 短板
SCORE=$(( SVC/2*1 + (HEAL>0) + LEARN + DECIDE + (MONITOR>0) + VERSION ))
CAPS="{\"svc\":$((SVC/2)),\"heal\":$((HEAL>0)),\"learn\":$LEARN,\"decide\":$DECIDE,\"monitor\":$((MONITOR>0)),\"version\":$VERSION,\"score\":$SCORE}"
GAPS=""
[ $((SVC/2)) -lt 1 ] && GAPS="$GAPS 服务托管"
[ $((HEAL>0)) -lt 1 ] && GAPS="$GAPS 自愈巡检"
[ $LEARN -lt 1 ] && GAPS="$GAPS 学习先行"
[ $DECIDE -lt 1 ] && GAPS="$GAPS 决策引擎"
[ $((MONITOR>0)) -lt 1 ] && GAPS="$GAPS 监控采集"
[ $VERSION -lt 1 ] && GAPS="$GAPS 版本化"
# 3) 白名单自实施: 日志轮转(>50M) / metrics 保留14天
ACT=""
if [ -f "$ZD/data/gateway.log" ] && [ "$(stat -c%s "$ZD/data/gateway.log" 2>/dev/null || echo 0)" -gt 52428800 ]; then
  mv "$ZD/data/gateway.log" "$ZD/data/gateway.log.$(date +%Y%m%d)" 2>/dev/null; ACT="$ACT 日志轮转"
fi
OLD=$(find "$ZD/data/metrics" -name 'metrics-*.jsonl' -mtime +14 2>/dev/null | wc -l)
[ "$OLD" -gt 0 ] && find "$ZD/data/metrics" -name 'metrics-*.jsonl' -mtime +14 -delete 2>/dev/null && ACT="$ACT 清理${OLD}旧指标"
# 4) 提案落盘(高风险域: 架构/部署/外部写 一律挂起)
PROPOSAL="{\"ts\":\"$TS\",\"caps\":$CAPS,\"gaps\":\"${GAPS:-无}\",\"auto\":\"${ACT:-无}\",\"pending\":\"跨节点仲裁/自主进化深度/真值API开放 待人工审批\"}"
echo "$PROPOSAL" >> "$EV/proposals-$(date +%Y%m%d).jsonl"
# 5) 上报网关
curl -s -m 8 -X POST "https://www.huodouai.com/api/report/truth" -H "X-DID: DID-BR-000002" -H "Content-Type: application/json" \
  -d "{\"key\":\"cloud.evolution.$(date +%Y%m%d)\",\"value\":{\"event\":\"cloud_evolve_cycle\",\"caps\":$CAPS,\"gaps\":\"${GAPS:-无}\",\"auto\":\"${ACT:-无}\",\"at\":\"$TS\"}}" >/dev/null 2>&1 || true
echo "[$TS] 能力矩阵 score=$SCORE/6 caps=$CAPS gaps='${GAPS:-无}' auto='${ACT:-无}'"
