#!/bin/bash
# ============================================
# JSON算子钩子：接收JSON，写入飞书台账，触发worker部署链路
# 确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 归属: OP-WORKER-TRIGGER-001
# META-RULE-014 钩子算子附录
# 用法: bash hook_trigger_worker.sh '<JSON载荷>'
# 修正: 使用 lark-cli +record-batch-create (实际可用命令，+record-add 不存在)
# ============================================
INPUT_JSON="$1"
TIMESTAMP=$(date +%s)
NODE_ID="$(hostname)"
BASE_TOKEN="DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE="tblnVRjuf7P31cEP"
OPERATOR_ID="OP-WORKER-TRIGGER-001"

# --- 校验输入JSON ---
if [ -z "$INPUT_JSON" ]; then
  echo "{\"operator_id\":\"$OPERATOR_ID\",\"status\":\"rejected\",\"msg\":\"缺少输入JSON\"}"
  exit 1
fi
if ! echo "$INPUT_JSON" | jq empty >/dev/null 2>&1; then
  echo "{\"operator_id\":\"$OPERATOR_ID\",\"status\":\"rejected\",\"msg\":\"JSON格式非法\"}"
  exit 1
fi

# --- 提取字段 ---
TASK_ID=$(echo "$INPUT_JSON" | jq -r '.task_id')
WORKER_NAME=$(echo "$INPUT_JSON" | jq -r '.worker_name')
IMAGE=$(echo "$INPUT_JSON" | jq -r '.image')
GPU=$(echo "$INPUT_JSON" | jq -r '.gpu')
CPU_CORES=$(echo "$INPUT_JSON" | jq -r '.cpu_cores')
MEMORY_MB=$(echo "$INPUT_JSON" | jq -r '.memory_mb')

# --- 写入飞书任务台账，状态置为【待处理】---
# 直接字段映射（无 fields 包装）；select 字段需传数组
BODY=$(jq -nc --arg name "$WORKER_NAME" --arg note "task_id=${TASK_ID}; 镜像=${IMAGE}; gpu=${GPU}; cpu=${CPU_CORES}核; mem=${MEMORY_MB}MB" \
  --arg status "待处理" --arg owner "云智中台" --arg pri "中" --arg prog "20" \
  '{create_records:[{"任务名称":$name,"备注":$note,"状态":[$status],"负责账号":[$owner],"优先级":[$pri],"进度":($prog|tonumber)}]}')
RECORD_OUT=$(lark-cli base +record-batch-create --base-token "$BASE_TOKEN" --table-id "$TASK_TABLE" --json "$BODY" --as user 2>&1)
RECORD_RET=$?

if [ $RECORD_RET -eq 0 ]; then
  # 尝试提取 record_id
  REC_ID=$(echo "$RECORD_OUT" | jq -r '.data.record_id_list[0] // .data.records[0].record_id // ""' 2>/dev/null)
  echo "{\"operator_id\":\"$OPERATOR_ID\",\"trigger_ts\":$TIMESTAMP,\"status\":\"accepted\",\"task_record_id\":\"${TASK_ID}\",\"msg\":\"任务已写入台账(record=${REC_ID})，扩容脚本轮询后自动认领部署\"}"
  # post_hook: ntfy 提醒
  if command -v curl >/dev/null 2>&1; then
    curl -s -H "Title: Worker部署触发" -d "{\"zr\":\"DID-BR-000002\",\"type\":\"ALERT\",\"node\":\"$NODE_ID\",\"payload\":{\"task\":\"$TASK_ID\",\"worker\":\"$WORKER_NAME\",\"status\":\"待部署\"}}" https://ntfy.sh/zongyuan-kunlun-2026 >/dev/null 2>&1 || true
  fi
  exit 0
else
  echo "{\"operator_id\":\"$OPERATOR_ID\",\"status\":\"rejected\",\"msg\":\"写入飞书Base失败: $(echo $RECORD_OUT | head -c 200)\"}"
  exit 1
fi
