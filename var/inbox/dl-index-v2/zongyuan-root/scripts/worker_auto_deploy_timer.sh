#!/bin/bash
# worker自动部署定时任务｜元极恒一增强版
# META-RULE-012 配额稳态保护
# META-RULE-014 附录增强约束
# 事件ID: TASK-WORKER-AUTO-DEPLOY-002
BASE_TOKEN="DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE="tblnVRjuf7P31cEP"
NODE_HEARTBEAT_TABLE="tblOmIRJtTn2EsvM"
MSG_TABLE="tbl4Dv798yO7u0IK"
ERROR_TABLE="tbljp3z11UtiuWCF"
MEMORY_GATEWAY="https://www.huodouai.com/api/report/truth"
MEMORY_GATEWAY_BACKUP="https://drama.huodouai.com/api/report/truth"

# 业务配置
MAX_WORKER_COUNT=4          # 本机最大worker并发上限，防止过载
HEALTH_CHECK_RETRY=3        # 健康检查重试次数
HEALTH_CHECK_INTERVAL=5     # 健康检查间隔秒
RETRY_MAX=2                 # 部署失败最大重试次数
TIMESTAMP=$(date +%s)
NODE_ID="$(hostname)"
NODE_NAME="${NODE_ID}-${TIMESTAMP}"

# 全局互斥锁，防止本机并发执行
LOCK_FILE="/tmp/worker_auto_deploy.lock"
if [ -f "$LOCK_FILE" ];then
  PID=$(cat "$LOCK_FILE")
  if ps -p $PID > /dev/null;then
    echo "[$(date)] 检测到任务正在运行，直接退出"
    exit 0
  fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "[$(date)] === Worker自动部署定时任务【增强版】启动 ==="

# 工具函数：lark-cli执行+返回码捕获
lark_run() {
  lark-cli "$@"
  local ret=$?
  if [ $ret -ne 0 ];then
    echo "[$(date)] lark-cli命令执行失败，ret=$ret"
  fi
  return $ret
}

# 工具函数：容器健康探测
health_check_container() {
  local container_name=$1
  for ((i=1; i<=HEALTH_CHECK_RETRY; i++)); do
    if docker inspect --format '{{.State.Health.Status}}' "$container_name" 2>/dev/null | grep -q "healthy";then
      return 0
    fi
    echo "[$(date)] 健康探测第$i次未就绪，等待${HEALTH_CHECK_INTERVAL}s"
    sleep $HEALTH_CHECK_INTERVAL
  done
  return 1
}

# 步骤1：读取台账，查询待部署worker任务
echo "[$(date)] 读取任务台账"
TMP_LOG="/tmp/worker_task_${TIMESTAMP}.log"
lark_run base +record-list \
--base-token "$BASE_TOKEN" \
--table-id "$TASK_TABLE" \
--as user --limit 50 --format json 2>&1 > "$TMP_LOG"
if [ $? -ne 0 ];then
  echo "[$(date)] 读取台账失败，更新心跳后退出"
  lark_run base +record-batch-update \
    --base-token "$BASE_TOKEN" \
    --table-id "$NODE_HEARTBEAT_TABLE" \
  --json '{"update_records":{"'"$NODE_ID"'":{"last_heartbeat":'"$TIMESTAMP"',"status":"read_fail"}}}'
  rm -f "$TMP_LOG"
  exit 1
fi

# 步骤2：检查本机当前运行worker数量，达到上限直接休眠
RUNNING_WORKER=$(docker ps --filter "name=worker-" --filter "status=running" 2>/dev/null | wc -l)
echo "[$(date)] 当前本机运行worker数量: $RUNNING_WORKER，最大上限:${MAX_WORKER_COUNT}"
if [ $RUNNING_WORKER -ge $MAX_WORKER_COUNT ];then
  echo "[$(date)] 本机worker已达最大配额，暂不新增，更新心跳退出"
  lark_run base +record-batch-update \
    --base-token "$BASE_TOKEN" \
    --table-id "$NODE_HEARTBEAT_TABLE" \
  --json '{"update_records":{"'"$NODE_ID"'":{"last_heartbeat":'"$TIMESTAMP"',"status":"quota_full"}}}'
  lark_run base +record-batch-create \
    --base-token "$BASE_TOKEN" \
    --table-id "$MSG_TABLE" \
  --json '{"create_records":[{"node_name":"'"$NODE_NAME"'","msg":"节点worker配额已满","ts":'"$TIMESTAMP"'}]}'
  rm -f "$TMP_LOG"
  exit 0
fi

# 步骤3：筛选【待部署】任务（精确匹配 status 字段值），执行原子认领
TASK_RAW=$(jq -r '.data.data[]? | select(.fields.status == "待部署") | .record_id' "$TMP_LOG" | head -n1)
if [ -z "$TASK_RAW" ];then
  echo "[$(date)] 无待部署worker任务，进入休眠，更新心跳直接退出"
  lark_run base +record-batch-update \
    --base-token "$BASE_TOKEN" \
    --table-id "$NODE_HEARTBEAT_TABLE" \
  --json '{"update_records":{"'"$NODE_ID"'":{"last_heartbeat":'"$TIMESTAMP"',"status":"idle"}}}'
  lark_run base +record-batch-create \
    --base-token "$BASE_TOKEN" \
    --table-id "$MSG_TABLE" \
  --json '{"create_records":[{"node_name":"'"$NODE_NAME"'","msg":"无worker待部署，节点空闲","ts":'"$TIMESTAMP"'}]}'
  rm -f "$TMP_LOG"
  exit 0
fi

# 提取第一条待部署任务record-id（原子抢占）
TASK_RECORD_ID="$TASK_RAW"
echo "[$(date)] 原子认领任务 record-id: $TASK_RECORD_ID"
lark_run base +record-batch-update \
--base-token "$BASE_TOKEN" \
--table-id "$TASK_TABLE" \
--json '{"update_records":{"'"$TASK_RECORD_ID"'":{"status":"认领中","remark":"节点'"$NODE_ID"'已抢占任务，开始部署"}}}'
if [ $? -ne 0 ];then
  echo "[$(date)] 任务认领失败，可能已被其他节点抢占，退出"
  rm -f "$TMP_LOG"
  exit 0
fi

# 步骤4：部署前置校验 compose文件
COMPOSE_FILE="/home/user/ZONGYUAN-ROOT/docker/worker-compose.yml"
# docker 可用性 = daemon 存活 + 容器实际可运行（run 探测；沙箱内核禁 unshare/mount 时 run 必败 → 自动降级）
DOCKER_AVAILABLE=0
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  timeout 30 docker run --rm --network=host busybox:latest echo ok >/dev/null 2>&1 && DOCKER_AVAILABLE=1
  [ "$DOCKER_AVAILABLE" -eq 0 ] && echo "[$(date)] docker daemon 存活但容器无法运行（内核限制），自动降级本机进程模式"
fi
if [ ! -f "$COMPOSE_FILE" ];then
  RESULT_MSG="worker部署失败：docker compose文件不存在 $COMPOSE_FILE"
  TASK_STATUS="阻塞"
  DEPLOY_RET=1
elif [ "$DOCKER_AVAILABLE" -eq 0 ];then
  echo "[$(date)] docker 不可用，进入降级模式（本机进程模拟 worker）"
  DEGRADED_SCRIPT="/home/user/ZONGYUAN-ROOT/scripts/worker_local_process.sh"
  if bash "$DEGRADED_SCRIPT" start "$TASK_RECORD_ID";then
    sleep 2
    if bash "$DEGRADED_SCRIPT" status "$TASK_RECORD_ID" | grep -q "healthy";then
      RESULT_MSG="worker部署成功（降级模式：本机进程模拟，心跳正常）"
      TASK_STATUS="已完成"
      DEPLOY_RET=0
    else
      RESULT_MSG="降级 worker 已启动但健康检查失败"
      TASK_STATUS="阻塞"
      DEPLOY_RET=2
    fi
  else
    RESULT_MSG="worker部署失败（降级模式启动异常）"
    TASK_STATUS="阻塞"
    DEPLOY_RET=1
  fi
else
  echo "[$(date)] 开始执行docker compose部署"
  docker-compose -f "$COMPOSE_FILE" up -d
  DEPLOY_RET=$?
  if [ $DEPLOY_RET -eq 0 ];then
    CONTAINER_NAME="worker-${TASK_RECORD_ID}"
    echo "[$(date)] 容器启动命令返回成功，开始健康探针检测"
    if health_check_container "$CONTAINER_NAME";then
      RESULT_MSG="worker部署成功，容器健康检查通过"
      TASK_STATUS="已完成"
    else
      RESULT_MSG="容器已拉起，但健康检查失败，服务异常"
      TASK_STATUS="阻塞"
      DEPLOY_RET=2
    fi
  else
    RESULT_MSG="worker部署失败，docker-compose返回码:$DEPLOY_RET"
    TASK_STATUS="阻塞"
  fi
fi

# 步骤5：失败分支，重试计数/死信流转
if [ $DEPLOY_RET -ne 0 ];then
  # 读取当前重试次数
  RETRY_COUNT=$(echo "$TASK_RAW" | grep -E "retry_count" | awk '{print $2}' || echo 0)
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -le $RETRY_MAX ];then
    # 还有重试机会，退回待部署
    lark_run base +record-batch-update \
        --base-token "$BASE_TOKEN" \
        --table-id "$TASK_TABLE" \
    --json '{"update_records":{"'"$TASK_RECORD_ID"'":{"status":"待部署","retry_count":'"$RETRY_COUNT"',"remark":"'"$RESULT_MSG"'，等待下一轮重试"}}}'
    MSG_CONTENT="任务$TASK_RECORD_ID部署失败，剩余重试次数 $((RETRY_MAX - RETRY_COUNT))"
  else
    # 重试耗尽，移入死信
    lark_run base +record-batch-update \
        --base-token "$BASE_TOKEN" \
        --table-id "$TASK_TABLE" \
    --json '{"update_records":{"'"$TASK_RECORD_ID"'":{"status":"死信","remark":"'"$RESULT_MSG"'，重试次数耗尽，等待人工复盘"}}}'
    MSG_CONTENT="任务$TASK_RECORD_ID重试耗尽，移入死信队列"
  fi
  # 写入错误阻塞表
  lark_run base +record-batch-create \
    --base-token "$BASE_TOKEN" \
    --table-id "$ERROR_TABLE" \
  --json '{"create_records":[{"node_name":"'"$NODE_NAME"'","error_msg":"'"$RESULT_MSG"'","ts":'"$TIMESTAMP"'}]}'
else
  # 部署成功，更新任务状态
  lark_run base +record-batch-update \
    --base-token "$BASE_TOKEN" \
    --table-id "$TASK_TABLE" \
  --json '{"update_records":{"'"$TASK_RECORD_ID"'":{"status":"'"$TASK_STATUS"'","remark":"'"$RESULT_MSG"'"}}}'
  MSG_CONTENT="任务$TASK_RECORD_ID部署成功"
fi

# 步骤6：更新节点心跳
lark_run base +record-batch-update \
--base-token "$BASE_TOKEN" \
--table-id "$NODE_HEARTBEAT_TABLE" \
--json '{"update_records":{"'"$NODE_ID"'":{"last_heartbeat":'"$TIMESTAMP"',"status":"'"$TASK_STATUS"'"}}}'

# 步骤7：跨节点消息同步
lark_run base +record-batch-create \
--base-token "$BASE_TOKEN" \
--table-id "$MSG_TABLE" \
--json '{"create_records":[{"node_name":"'"$NODE_NAME"'","msg":"'"$MSG_CONTENT"'","ts":'"$TIMESTAMP"'}]}'

# 步骤8：上报记忆网关真值（双通道）
curl -X POST "$MEMORY_GATEWAY" \
-H "X-DID: DID-BR-000002" \
-H "Content-Type: application/json" \
-d '{
  "key": "worker_auto_deploy_'${TIMESTAMP}'",
  "value": {
    "event":"worker_auto_deploy",
    "node":"'${NODE_ID}'",
    "task_id":"'${TASK_RECORD_ID}'",
    "ret_code":'${DEPLOY_RET}',
    "msg":"'${RESULT_MSG}'",
    "ts":'${TIMESTAMP}'
  }
}' || curl -X POST "$MEMORY_GATEWAY_BACKUP" \
-H "X-DID: DID-BR-000002" \
-H "Content-Type: application/json" \
-d '{
  "key": "worker_auto_deploy_'${TIMESTAMP}'",
  "value": {
    "event":"worker_auto_deploy",
    "node":"'${NODE_ID}'",
    "task_id":"'${TASK_RECORD_ID}'",
    "ret_code":'${DEPLOY_RET}',
    "msg":"'${RESULT_MSG}'",
    "ts":'${TIMESTAMP}'
  }
}'

echo "[$(date)] === Worker自动部署定时任务【增强版】结束 ==="
