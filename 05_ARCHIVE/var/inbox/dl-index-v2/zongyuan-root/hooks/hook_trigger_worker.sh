#!/bin/bash
# JSON算子钩子V1.4：同步/异步 + 并发保护 + 优先级 + 超时配置
# META-RULE-014 钩子算子附录 V1.4
# 事件ID: HOOK-JSON-OPERATOR-WORKER-TRIGGER-003（V1.2升级）→ V1.4 新增 priority/timeout_sec
INPUT_JSON="$1"
TIMESTAMP=$(date +%s)
NODE_ID="$(hostname)"
BASE_TOKEN="DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE="tblnVRjuf7P31cEP"
DEPLOY_SCRIPT="/home/user/ZONGYUAN-ROOT/scripts/worker_auto_deploy_timer.sh"
MAX_WORKER_COUNT=4
DEFAULT_TIMEOUT=3600

# 校验输入JSON
if ! echo "$INPUT_JSON" | jq empty >/dev/null 2>&1;then
  echo "{\"status\":\"rejected\",\"msg\":\"JSON格式非法\"}"
  exit 1
fi

# 提取字段
TASK_ID=$(echo "$INPUT_JSON" | jq -r '.task_id')
WORKER_NAME=$(echo "$INPUT_JSON" | jq -r '.worker_name')
IMAGE=$(echo "$INPUT_JSON" | jq -r '.image')
GPU=$(echo "$INPUT_JSON" | jq -r '.gpu')
RUN_MODE=$(echo "$INPUT_JSON" | jq -r '.run_mode // "async"')
PRIORITY=$(echo "$INPUT_JSON" | jq -r '.priority // "P2"')
TIMEOUT_SEC=$(echo "$INPUT_JSON" | jq -r '.timeout_sec // '"${DEFAULT_TIMEOUT}"'')

# 校验优先级枚举合法
ALLOW_PRIORITY=("P0" "P1" "P2" "P3")
if [[ ! " ${ALLOW_PRIORITY[@]} " =~ " ${PRIORITY} " ]];then
  echo "{
    \"operator_id\":\"OP-WORKER-TRIGGER-001\",
    \"trigger_ts\":$TIMESTAMP,
    \"status\":\"rejected\",
    \"task_record_id\":\"$TASK_ID\",
    \"run_mode\":\"$RUN_MODE\",
    \"priority\":\"$PRIORITY\",
    \"timeout_sec\":$TIMEOUT_SEC,
    \"current_running_workers\":0,
    \"max_worker_limit\":$MAX_WORKER_COUNT,
    \"msg\":\"priority参数非法，仅支持P0/P1/P2/P3\"
  }"
  exit 1
fi

# 校验超时时间
if ! [[ "$TIMEOUT_SEC" =~ ^[0-9]+$ ]];then
  echo "{
    \"operator_id\":\"OP-WORKER-TRIGGER-001\",
    \"trigger_ts\":$TIMESTAMP,
    \"status\":\"rejected\",
    \"task_record_id\":\"$TASK_ID\",
    \"run_mode\":\"$RUN_MODE\",
    \"priority\":\"$PRIORITY\",
    \"timeout_sec\":$TIMEOUT_SEC,
    \"current_running_workers\":0,
    \"max_worker_limit\":$MAX_WORKER_COUNT,
    \"msg\":\"timeout_sec必须为正整数秒\"
  }"
  exit 1
fi

# 统计当前正在运行的worker容器
CURRENT_RUNNING_WORKERS=$(docker ps --filter "name=worker-" --filter "status=running" 2>/dev/null | wc -l)

# 并发阈值前置校验
if [ "${CURRENT_RUNNING_WORKERS}" -ge "${MAX_WORKER_COUNT}" ];then
  echo "{
    \"operator_id\":\"OP-WORKER-TRIGGER-001\",
    \"trigger_ts\":$TIMESTAMP,
    \"status\":\"rejected\",
    \"task_record_id\":\"$TASK_ID\",
    \"run_mode\":\"$RUN_MODE\",
    \"priority\":\"$PRIORITY\",
    \"timeout_sec\":$TIMEOUT_SEC,
    \"current_running_workers\":$CURRENT_RUNNING_WORKERS,
    \"max_worker_limit\":$MAX_WORKER_COUNT,
    \"msg\":\"并发上限保护拒绝：当前运行worker(${CURRENT_RUNNING_WORKERS}) ≥ 最大配额(${MAX_WORKER_COUNT})，任务入队失败\"
  }"
  exit 1
fi

# 写入飞书任务台账，新增timeout_sec字段
lark-cli base +record-batch-create \
--base-token "$BASE_TOKEN" \
--table-id "$TASK_TABLE" \
--json '{"create_records":[{
  "任务名称":"'"${WORKER_NAME}"'",
  "task_id":"'"${TASK_ID}"'",
  "镜像":"'"${IMAGE}"'",
  "gpu_enable":'"${GPU}"',
  "status":"待部署",
  "create_ts":'"${TIMESTAMP}"',
  "run_mode":"'"${RUN_MODE}"'",
  "priority":"'"${PRIORITY}"'",
  "timeout_sec":'"${TIMEOUT_SEC}"]}'
}'

RECORD_RET=$?
if [ $RECORD_RET -ne 0 ];then
  echo "{\"status\":\"rejected\",\"msg\":\"写入飞书Base失败\"}"
  exit 1
fi

# 同步模式：直接调用扩容脚本执行部署
if [ "${RUN_MODE}" = "sync" ];then
  echo "=== 同步模式，立即执行部署脚本 ==="
  ${DEPLOY_SCRIPT}
  DEPLOY_EXIT=$?
  if [ ${DEPLOY_EXIT} -eq 0 ];then
    MSG="任务已入队并同步执行部署，超时限制${TIMEOUT_SEC}秒"
  else
    MSG="任务已入队，但同步部署脚本执行异常 code:${DEPLOY_EXIT}"
  fi
else
  MSG="任务已写入台账，等待定时轮询部署，优先级:${PRIORITY},超时限制${TIMEOUT_SEC}秒"
fi

echo "{
  \"operator_id\":\"OP-WORKER-TRIGGER-001\",
  \"trigger_ts\":$TIMESTAMP,
  \"status\":\"accepted\",
  \"task_record_id\":\"${TASK_ID}\",
  \"run_mode\":\"${RUN_MODE}\",
  \"priority\":\"${PRIORITY}\",
  \"timeout_sec\":${TIMEOUT_SEC},
  \"current_running_workers\":${CURRENT_RUNNING_WORKERS},
  \"max_worker_limit\":${MAX_WORKER_COUNT},
  \"msg\":\"${MSG}\"
}"
