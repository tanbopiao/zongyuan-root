#!/usr/bin/env bash
# 云端中枢探活自愈：进程在但服务异常/API无响应 → 自动拉起
set -u
API="http://127.0.0.1:9001/api/status"
OK=$(curl -s -m 5 "$API" 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print('1' if d.get('status')=='ok' else '0')" 2>/dev/null || echo 0)
if [ "$OK" != "1" ]; then
  echo "$(date '+%F %T') health: gateway 异常, 尝试重启" >> /www/wwwroot/huodouai.com/zhongshu/data/health.log
  systemctl restart zhongshu-gateway 2>/dev/null || {
    cd /www/wwwroot/huodouai.com/zhongshu/zhongshu-server && bash run.sh start
  }
fi
# scheduler 进程存活检查（systemd 应托管, 兜底）
systemctl is-active --quiet zhongshu-scheduler || systemctl restart zhongshu-scheduler 2>/dev/null
