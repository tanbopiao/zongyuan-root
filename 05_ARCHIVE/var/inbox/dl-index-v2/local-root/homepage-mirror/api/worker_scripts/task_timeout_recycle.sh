#!/bin/bash
# task_timeout_recycle.sh V1.5 超时回收
BASE_TOKEN="DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE="tblnVRjuf7P31cEP"
NOW=$(date +%s)
echo "=== 超时回收扫描 $(date) ==="

# 本机docker状态
RUNNING=$(docker ps --filter "name=worker-" --filter "status=running" 2>/dev/null | wc -l)
echo "运行中worker: $RUNNING"

# 清理僵尸进程
pkill -9 -f "produce.py.*stuck" 2>/dev/null

# 上报
curl -s -X POST https://www.huodouai.com/api/report/truth \
  -H "Content-Type: application/json" \
  -d "{\"truth_value\":\"超时回收扫描完成 running=$RUNNING\",\"truth_type\":\"meta_law\"}" >/dev/null 2>&1

echo "=== 完成 ==="
