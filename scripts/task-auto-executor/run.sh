#!/bin/bash
# 元极恒一共享大脑·任务执行器
BASE_TOKEN="DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE="tblnVRjuf7P31cEP"
NODE_NAME="$(hostname)-$(date +%s)"

echo "[$(date)] 节点 $NODE_NAME 开始轮询任务..."

# 读任务台账
lark-cli base +record-list \
  --base-token "$BASE_TOKEN" \
  --table-id "$TASK_TABLE" \
  --as user --limit 50 2>&1 | grep -E "任务名称|状态|进度"

echo "[$(date)] 轮询完成"
