#!/bin/bash
# auto_claim.sh 自动认领飞书Base任务
BASE_TOKEN="DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE="tblnVRjuf7P31cEP"

# 查询待处理任务
lark-cli base +record-list --base-token "$BASE_TOKEN" --table-id "$TASK_TABLE" --as user --page-size 5 2>/dev/null | jq -r '.items[]? | select(.fields.status=="待部署") | .record_id' | while read rid; do
  echo "认领任务: $rid"
  # 更新状态为部署中
  lark-cli base +record-update --base-token "$BASE_TOKEN" --table-id "$TASK_TABLE" --record-id "$rid" --fields '{"status":"运行中"}' --as user 2>/dev/null
done

echo "轮询完成 $(date)"
