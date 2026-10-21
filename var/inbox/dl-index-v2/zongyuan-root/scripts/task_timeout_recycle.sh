#!/bin/bash
# task_timeout_recycle.sh｜任务超时自动回收脚本（V1.4 新增）
# 能力：扫描飞书任务台账中认领超时的任务 → 标记 failed → 释放容器配额 → 消息同步
# 说明：本脚本内容在部署指令中被截断，此处按 V1.4 能力规范补写，已标注
# 事件ID: TASK-TIMEOUT-RECYCLE-001
set -uo pipefail

BASE_TOKEN="DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE="tblnVRjuf7P31cEP"
MSG_TABLE="tbl4Dv798yO7u0IK"
ERROR_TABLE="tbljp3z11UtiuWCF"
MEMORY_GATEWAY="https://www.huodouai.com/api/report/truth"
MEMORY_GATEWAY_BACKUP="https://drama.huodouai.com/api/report/truth"
DEFAULT_TIMEOUT=3600     # 默认超时秒（与算子 default_timeout_sec 一致）
TIMESTAMP=$(date +%s)
NODE_ID="$(hostname)"
NODE_NAME="${NODE_ID}-${TIMESTAMP}"

# 互斥锁
LOCK_FILE="/tmp/task_timeout_recycle.lock"
if [ -f "$LOCK_FILE" ];then
  PID=$(cat "$LOCK_FILE")
  if ps -p $PID > /dev/null 2>&1;then
    echo "[$(date)] 回收任务正在运行，退出"
    exit 0
  fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

lark_run() {
  lark-cli "$@"
  local ret=$?
  [ $ret -ne 0 ] && echo "[$(date)] lark-cli执行失败 ret=$ret"
  return $ret
}

echo "[$(date)] === 任务超时自动回收扫描开始 ==="
TMP_LOG="/tmp/timeout_task_${TIMESTAMP}.log"
lark_run base +record-list --base-token "$BASE_TOKEN" --table-id "$TASK_TABLE" --as user --limit 100 2>&1 > "$TMP_LOG" || { echo "读取台账失败"; rm -f "$TMP_LOG"; exit 1; }

# 匹配状态为 认领中/部署中 且带 create_ts 的记录（lark-cli JSON 输出为 TSV 行）
RECYCLED=0
while IFS= read -r line; do
  case "$line" in
    *认领中*|*部署中*)
      REC_ID=$(echo "$line" | awk '{print $1}')
      CREATE_TS=$(echo "$line" | grep -oE 'create_ts[^0-9]*[0-9]+' | grep -oE '[0-9]+' | head -1)
      [ -z "$CREATE_TS" ] && CREATE_TS=$TIMESTAMP
      # 超时判断：create_ts + timeout_sec < now
      TIMEOUT_SEC=$(echo "$line" | grep -oE 'timeout_sec[^0-9]*[0-9]+' | grep -oE '[0-9]+' | head -1)
      [ -z "$TIMEOUT_SEC" ] && TIMEOUT_SEC=$DEFAULT_TIMEOUT
      EXPIRY=$((CREATE_TS + TIMEOUT_SEC))
      if [ "$TIMESTAMP" -ge "$EXPIRY" ];then
        echo "[$(date)] 回收超时任务 record-id=$REC_ID（超时阈值 ${TIMEOUT_SEC}s）"
        lark_run base +record-batch-update \
          --base-token "$BASE_TOKEN" --table-id "$TASK_TABLE" \
          --json '{"update_records":{"'"$REC_ID"'":{"status":"failed","remark":"任务超时自动回收（V1.4），超时阈值'"$TIMEOUT_SEC"'秒"}}}'
        # 释放配额：docker 容器（正常模式）或降级本地进程（无 docker 时）
        if command -v docker >/dev/null 2>&1; then
          docker rm -f "worker-${REC_ID}" >/dev/null 2>&1 || true
        else
          bash /home/user/ZONGYUAN-ROOT/scripts/worker_local_process.sh stop "$REC_ID" >/dev/null 2>&1 || true
        fi
        lark_run base +record-batch-create \
          --base-token "$BASE_TOKEN" --table-id "$MSG_TABLE" \
          --json '{"create_records":[{"node_name":"'"$NODE_NAME"'","msg":"任务'"$REC_ID"'超时回收，已标记failed并释放配额","ts":'"$TIMESTAMP"'}]}'
        RECYCLED=$((RECYCLED + 1))
      fi
      ;;
  esac
done < "$TMP_LOG"

echo "[$(date)] 本轮回收超时任务数: $RECYCLED"
# 上报记忆网关（双通道，失败不阻塞）
curl -sS -m 20 -X POST "$MEMORY_GATEWAY" \
  -H "X-DID: DID-BR-000002" \
  -H "Content-Type: application/json" \
  -d '{"key":"task_timeout_recycle_'${TIMESTAMP}'","value":{"event":"task_timeout_recycle","node":"'${NODE_ID}'","recycled":'${RECYCLED}',"ts":'${TIMESTAMP}'}}' \
  || curl -sS -m 20 -X POST "$MEMORY_GATEWAY_BACKUP" \
  -H "X-DID: DID-BR-000002" \
  -H "Content-Type: application/json" \
  -d '{"key":"task_timeout_recycle_'${TIMESTAMP}'","value":{"event":"task_timeout_recycle","node":"'${NODE_ID}'","recycled":'${RECYCLED}',"ts":'${TIMESTAMP}'}}'

rm -f "$TMP_LOG"
echo "[$(date)] === 任务超时自动回收扫描结束 ==="
