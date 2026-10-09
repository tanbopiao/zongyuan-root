#!/bin/bash
# =============================================================================
# Worker自动部署定时任务｜元极恒一增强版 V2.1（本地适配）
# META-RULE-012 配额稳态保护 | META-RULE-014 Worker部署增强约束
# 事件ID: TASK-WORKER-AUTO-DEPLOY-002
# 适配修正: lark-cli命令(+record-upsert/+record-batch-create)、中文字段名、
#           心跳record_id硬编码、docker缺失优雅降级
# =============================================================================
set -u

BASE_TOKEN="DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE="tblnVRjuf7P31cEP"
NODE_HEARTBEAT_TABLE="tblOmIRJtTn2EsvM"
MSG_TABLE="tbl4Dv798yO7u0IK"
ERROR_TABLE="tbljp3z11UtiuWCF"
MEMORY_GATEWAY="https://www.huodouai.com/api/report/truth"
MEMORY_GATEWAY_BACKUP="https://drama.huodouai.com/api/report/truth"
NODE_HEARTBEAT_RECORD="recvw5OkCUCJvm"   # NODE-DEV-DOUBAO-WORK-001 心跳记录ID

# 业务配置
MAX_WORKER_COUNT=4
HEALTH_CHECK_RETRY=3
HEALTH_CHECK_INTERVAL=5
RETRY_MAX=2
TIMESTAMP=$(date +%s)
NOW_HUMAN=$(date '+%Y-%m-%d %H:%M:%S')
NODE_ID="NODE-DEV-DOUBAO-WORK-001"
NODE_NAME="${NODE_ID}-${TIMESTAMP}"
DEPLOY_RET=0
RESULT_MSG=""
TASK_STATUS=""
MSG_CONTENT=""
TASK_RECORD_ID=""

# 全局互斥锁
LOCK_FILE="/tmp/worker_auto_deploy.lock"
if [ -f "$LOCK_FILE" ]; then
  PID=$(cat "$LOCK_FILE" 2>/dev/null)
  if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
    echo "[$NOW_HUMAN] 检测到任务正在运行(PID=$PID)，直接退出"
    exit 0
  fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "[$NOW_HUMAN] === Worker自动部署定时任务【增强V2.1】启动 ==="

# ---- 工具函数 ----
lark_run() {
  lark-cli "$@" 2>&1
  local ret=$?
  if [ $ret -ne 0 ]; then
    echo "[$NOW_HUMAN] lark-cli命令执行失败 ret=$ret: $*"
  fi
  return $ret
}

# 心跳更新（upsert，中文本字段）
update_heartbeat() {
  local status="$1"
  lark_run base +record-upsert \
    --base-token "$BASE_TOKEN" \
    --table-id "$NODE_HEARTBEAT_TABLE" \
    --record-id "$NODE_HEARTBEAT_RECORD" \
    --json "{\"当前状态\":[\"$status\"],\"最后心跳时间\":\"$NOW_HUMAN\",\"备注\":\"worker调度器心跳 $NOW_HUMAN\"}" \
    --as user > /dev/null 2>&1
}

# 发跨节点消息（batch-create）
send_msg() {
  local content="$1"
  local payload="{\"create_records\":[{\"消息内容\":\"[$NOW_HUMAN] $content\",\"发送节点\":[\"昆仑洞天\"],\"接收节点\":[\"云端中枢\"],\"状态\":[\"已送达\"],\"发送时间\":\"$NOW_HUMAN\"}]}"
  lark_run base +record-batch-create \
    --base-token "$BASE_TOKEN" \
    --table-id "$MSG_TABLE" \
    --json "$payload" \
    --as user > /dev/null 2>&1
}

# 登记问题阻塞
log_error() {
  local err="$1"
  local payload="{\"create_records\":[{\"问题描述\":\"[$NOW_HUMAN] $err\",\"状态\":[\"待解决\"],\"提出账号\":[\"昆仑洞天\"],\"负责解决\":[\"云端中枢\"],\"时间\":\"$NOW_HUMAN\"}]}"
  lark_run base +record-batch-create \
    --base-token "$BASE_TOKEN" \
    --table-id "$ERROR_TABLE" \
    --json "$payload" \
    --as user > /dev/null 2>&1
}

# 容器健康探测（docker可用时）
health_check_container() {
  local container_name=$1
  for ((i=1; i<=HEALTH_CHECK_RETRY; i++)); do
    if docker inspect --format '{{.State.Health.Status}}' "$container_name" 2>/dev/null | grep -q "healthy"; then
      return 0
    fi
    echo "[$NOW_HUMAN] 健康探测第$i次未就绪，等待${HEALTH_CHECK_INTERVAL}s"
    sleep $HEALTH_CHECK_INTERVAL
  done
  return 1
}

# ---- 步骤1：读取任务台账 ----
echo "[$NOW_HUMAN] 读取任务台账"
TMP_LOG="/tmp/worker_task_${TIMESTAMP}.log"
lark_run base +record-list \
  --base-token "$BASE_TOKEN" \
  --table-id "$TASK_TABLE" \
  --as user --limit 200 > "$TMP_LOG" 2>&1
if [ $? -ne 0 ]; then
  echo "[$NOW_HUMAN] 读取台账失败"
  update_heartbeat "维护中"
  rm -f "$TMP_LOG"
  exit 1
fi

# ---- 步骤2：本机worker配额检查（docker不可用时跳过） ----
if command -v docker > /dev/null 2>&1; then
  RUNNING_WORKER=$(docker ps --filter "name=worker-" --filter "status=running" -q 2>/dev/null | wc -l)
  echo "[$NOW_HUMAN] 当前运行worker: $RUNNING_WORKER / 上限$MAX_WORKER_COUNT"
  if [ "$RUNNING_WORKER" -ge "$MAX_WORKER_COUNT" ]; then
    echo "[$NOW_HUMAN] worker配额已满"
    update_heartbeat "在线"
    send_msg "节点worker配额已满($RUNNING_WORKER/$MAX_WORKER_COUNT)"
    rm -f "$TMP_LOG"
    exit 0
  fi
else
  echo "[$NOW_HUMAN] docker未安装，跳过配额检查（调度框架模式）"
fi

# ---- 步骤3：docker可用性前置检查 ----
# docker不可用时，部署类任务必然失败，直接idle，不认领任务
if ! command -v docker > /dev/null 2>&1; then
  echo "[$NOW_HUMAN] docker未安装，本机仅调度框架模式，跳过部署任务认领"
  update_heartbeat "在线"
  send_msg "docker未安装，worker调度器运行于框架模式（仅心跳+消息+上报，不执行部署）"
  rm -f "$TMP_LOG"
  echo "[$NOW_HUMAN] === Worker自动部署任务结束（框架模式idle） ==="
  exit 0
fi

# ---- 步骤4：筛选待部署任务 ----
# 任务台账状态选项：待开始|进行中|已完成|已阻塞；筛选"待开始"且名称含worker/部署
TASK_RAW=$(grep -E "待开始" "$TMP_LOG" 2>/dev/null | grep -iE "worker|部署|deploy" || true)
if [ -z "$TASK_RAW" ]; then
  echo "[$NOW_HUMAN] 无待部署worker任务，节点空闲"
  update_heartbeat "在线"
  send_msg "无worker待部署任务，节点空闲（调度框架正常）"
  rm -f "$TMP_LOG"
  echo "[$NOW_HUMAN] === Worker自动部署任务结束（idle） ==="
  exit 0
fi

# 提取第一条任务的 record_id（飞书记录ID格式 recv...）
TASK_RECORD_ID=$(echo "$TASK_RAW" | head -n1 | grep -oE 'rec[a-zA-Z0-9]+' | head -1)
if [ -z "$TASK_RECORD_ID" ]; then
  echo "[$NOW_HUMAN] 无法解析任务record_id"
  update_heartbeat "在线"
  rm -f "$TMP_LOG"
  exit 1
fi
echo "[$NOW_HUMAN] 原子认领任务 record_id: $TASK_RECORD_ID"

# 原子认领：状态改为进行中
lark_run base +record-upsert \
  --base-token "$BASE_TOKEN" \
  --table-id "$TASK_TABLE" \
  --record-id "$TASK_RECORD_ID" \
  --json "{\"状态\":[\"进行中\"],\"备注\":\"节点$NODE_ID已认领，开始部署 $NOW_HUMAN\"}" \
  --as user > /dev/null 2>&1

# ---- 步骤4：部署执行 ----
COMPOSE_FILE="/home/user/ZONGYUAN-ROOT/docker/worker-compose.yml"
if ! command -v docker > /dev/null 2>&1; then
  RESULT_MSG="worker部署阻塞：本机未安装docker/docker-compose，仅调度框架运行"
  TASK_STATUS="已阻塞"
  DEPLOY_RET=1
elif [ ! -f "$COMPOSE_FILE" ]; then
  RESULT_MSG="worker部署阻塞：compose文件不存在 $COMPOSE_FILE"
  TASK_STATUS="已阻塞"
  DEPLOY_RET=1
else
  echo "[$NOW_HUMAN] 执行docker compose部署"
  docker-compose -f "$COMPOSE_FILE" up -d
  DEPLOY_RET=$?
  if [ $DEPLOY_RET -eq 0 ]; then
    CONTAINER_NAME="worker-${TASK_RECORD_ID}"
    if health_check_container "$CONTAINER_NAME"; then
      RESULT_MSG="worker部署成功，容器健康检查通过"
      TASK_STATUS="已完成"
    else
      RESULT_MSG="容器已拉起但健康检查失败"
      TASK_STATUS="已阻塞"
      DEPLOY_RET=2
    fi
  else
    RESULT_MSG="worker部署失败，docker-compose返回码:$DEPLOY_RET"
    TASK_STATUS="已阻塞"
  fi
fi

# ---- 步骤5：失败重试/死信 ----
if [ $DEPLOY_RET -ne 0 ]; then
  RETRY_COUNT=$(grep -c "retry_count" "$TMP_LOG" 2>/dev/null || true)
  RETRY_COUNT=${RETRY_COUNT:-0}
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ "$RETRY_COUNT" -le "$RETRY_MAX" ]; then
    lark_run base +record-upsert \
      --base-token "$BASE_TOKEN" --table-id "$TASK_TABLE" \
      --record-id "$TASK_RECORD_ID" \
      --json "{\"状态\":[\"待开始\"],\"备注\":\"$RESULT_MSG，重试$RETRY_COUNT/$RETRY_MAX $NOW_HUMAN\"}" \
      --as user > /dev/null 2>&1
    MSG_CONTENT="任务$TASK_RECORD_ID部署失败，剩余重试$((RETRY_MAX - RETRY_COUNT))"
  else
    lark_run base +record-upsert \
      --base-token "$BASE_TOKEN" --table-id "$TASK_TABLE" \
      --record-id "$TASK_RECORD_ID" \
      --json "{\"状态\":[\"已阻塞\"],\"备注\":\"$RESULT_MSG，重试耗尽移入死信 $NOW_HUMAN\"}" \
      --as user > /dev/null 2>&1
    MSG_CONTENT="任务$TASK_RECORD_ID重试耗尽，移入死信队列"
  fi
  log_error "$RESULT_MSG (task=$TASK_RECORD_ID)"
else
  lark_run base +record-upsert \
    --base-token "$BASE_TOKEN" --table-id "$TASK_TABLE" \
    --record-id "$TASK_RECORD_ID" \
    --json "{\"状态\":[\"$TASK_STATUS\"],\"进度\":100,\"备注\":\"$RESULT_MSG $NOW_HUMAN\"}" \
    --as user > /dev/null 2>&1
  MSG_CONTENT="任务$TASK_RECORD_ID部署成功"
fi

# ---- 步骤6：心跳 ----
update_heartbeat "在线"

# ---- 步骤7：跨节点消息 ----
send_msg "$MSG_CONTENT"

# ---- 步骤8：记忆网关双通道上报 ----
GW_PAYLOAD="{\"key\":\"worker_auto_deploy_$(date +%Y%m%d)\",\"truth_value\":\"event=worker_auto_deploy node=$NODE_ID task_id=$TASK_RECORD_ID ret=$DEPLOY_RET msg=$RESULT_MSG\",\"node_id\":\"$NODE_ID\",\"DID\":\"DID-BR-000002\",\"ROOT_OMEGA\":\"Ω-TAN-7-001\",\"truth_type\":\"operation_log\"}"
curl -s -m 8 -X POST "$MEMORY_GATEWAY" \
  -H "Content-Type: application/json" \
  -d "$GW_PAYLOAD" > /dev/null 2>&1 || \
curl -s -m 8 -X POST "$MEMORY_GATEWAY_BACKUP" \
  -H "X-Capture-Token: ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d" \
  -H "Content-Type: application/json" \
  -d "$GW_PAYLOAD" > /dev/null 2>&1

rm -f "$TMP_LOG"
echo "[$NOW_HUMAN] === Worker自动部署任务结束 ret=$DEPLOY_RET ==="
exit $DEPLOY_RET
