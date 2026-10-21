#!/bin/bash
# truth_distill.sh 每日真值蒸馏
COUNT=$(tail -100 /tmp/heartbeat.log 2>/dev/null | wc -l)
curl -s -X POST https://www.huodouai.com/api/report/truth \
  -H "Content-Type: application/json" \
  -d "{\"truth_value\":\"每日蒸馏 心跳记录:$COUNT条 系统稳定运行\",\"truth_type\":\"meta_law\"}" >/dev/null 2>&1
echo "蒸馏完成"
