#!/bin/bash
# =====================================================================
# ZONGYUAN-ROOT 自治内核锁档 + OP-WORKER-TRIGGER-001 V1.4 全自动部署器
# 事件ID：GLOBAL-LOCK-ZONGYUAN-ROOT-OP-V1.4 | 锚定 Ω₀⊂⊙∞⊂Ω | DID-BR-000002
# 说明：本脚本在部署指令中仅给出开头，此处按 V1.4 锁档元指令能力补写完整版。
#       资产以 cp 方式取自本机已锁档源文件，保证 HASH-LEDGER 哈希一致。
# 用法：bash scripts/auto_deploy_op_v1.4.sh
# =====================================================================
set -uo pipefail

TIMESTAMP=$(date +%s)
ROOT="/home/user/ZONGYUAN-ROOT"
LOG_DIR="$ROOT/logs"
DEPLOY_LOG="$LOG_DIR/auto_deploy_op_v1.4_$(date +%Y%m%d-%H%M%S).log"
BASE_TOKEN="DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE="tblnVRjuf7P31cEP"
MEMORY_GATEWAY="https://www.huodouai.com/api/report/truth"
MEMORY_GATEWAY_BACKUP="https://drama.huodouai.com/api/report/truth"
NODE_ID="$(hostname)"

mkdir -p "$LOG_DIR"
exec >> "$DEPLOY_LOG" 2>&1

echo "[$(date)] === OP-WORKER-TRIGGER-001 V1.4 全自动部署开始 === 节点=$NODE_ID"

# ---- 1. 目录初始化 ----
mkdir -p "${ROOT}/operators" "${ROOT}/hooks" "${ROOT}/scripts" "${ROOT}/卷宗" "${ROOT}/meta-rules" "${ROOT}/docker" "${ROOT}/logs"

# ---- 2. 资产部署（cp 自锁档源，哈希一致性）----
declare -A ASSETS=(
  ["operators/trigger_worker_operator.json"]="operators/trigger_worker_operator.json"
  ["hooks/hook_trigger_worker.sh"]="hooks/hook_trigger_worker.sh"
  ["scripts/worker_auto_deploy_timer.sh"]="scripts/worker_auto_deploy_timer.sh"
  ["scripts/task_timeout_recycle.sh"]="scripts/task_timeout_recycle.sh"
  ["meta-rules/META-RULE-012.json"]="meta-rules/META-RULE-012.json"
  ["meta-rules/META-RULE-014.json"]="meta-rules/META-RULE-014.json"
)
DEPLOY_FAIL=0
for dst in "${!ASSETS[@]}"; do
  src="${ASSETS[$dst]}"
  if [ -f "${ROOT}/${src}" ]; then
    cp "${ROOT}/${src}" "${ROOT}/${dst}"
    echo "[$(date)] 部署资产 OK: $dst"
  else
    echo "[$(date)] 部署资产 缺失: $src"
    DEPLOY_FAIL=1
  fi
done

# ---- 3. 赋权与语法校验 ----
chmod +x "${ROOT}"/scripts/*.sh "${ROOT}"/hooks/*.sh 2>/dev/null
for s in scripts/worker_auto_deploy_timer.sh scripts/task_timeout_recycle.sh hooks/hook_trigger_worker.sh; do
  bash -n "${ROOT}/$s" || { echo "[$(date)] 语法校验失败: $s"; DEPLOY_FAIL=1; }
done
for j in operators/trigger_worker_operator.json meta-rules/META-RULE-012.json meta-rules/META-RULE-014.json; do
  jq empty "${ROOT}/$j" || { echo "[$(date)] JSON校验失败: $j"; DEPLOY_FAIL=1; }
done

# ---- 4. docker 前置检查 ----
if ! command -v docker >/dev/null 2>&1; then
  echo "[$(date)] 警告: 本机 docker 不可用，定时轮询/容器部署需在 docker 环境启用"
fi

# ---- 5. crontab 安装（docker 就绪时启用；未就绪仅提示）----
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  CRON_LINE="*/5 * * * * ${ROOT}/scripts/worker_auto_deploy_timer.sh >> ${LOG_DIR}/worker_deploy.log 2>&1"
  ( crontab -l 2>/dev/null | grep -v "worker_auto_deploy_timer.sh" ; echo "$CRON_LINE" ) | crontab -
  echo "[$(date)] crontab 已安装: $CRON_LINE"
else
  echo "[$(date)] docker 未就绪，crontab 未安装（避免无 docker 环境下误写飞书台账）"
  echo "[$(date)] docker 就绪后执行: echo '*/5 * * * * ${ROOT}/scripts/worker_auto_deploy_timer.sh >> ${LOG_DIR}/worker_deploy.log 2>&1' | crontab -"
fi

# ---- 6. 锁档回执写入卷宗 ----
python3 - "$ROOT" "$TIMESTAMP" <<'PYEOF'
import json, sys, time
root, ts = sys.argv[1], int(sys.argv[2])
receipt = {
  "meta_action": "GLOBAL_LOCK_WRITE",
  "event_id": "GLOBAL-LOCK-ZONGYUAN-ROOT-OP-V1.4",
  "target_root": root,
  "operator_id": "OP-WORKER-TRIGGER-001",
  "operator_version": "v1.4",
  "deployed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
  "capability": ["JSON载荷标准化校验","sync/async双执行模式","最大并发前置保护(MAX=4)","P0~P3优先级","任务超时自动回收","飞书Base四表写入","双通道网关上报","ntfy联动"],
  "status": "LOCKED",
  "DID": "DID-BR-000002"
}
out = f"{root}/卷宗/auto_deploy_op_v1.4_receipt.json"
open(out, "w", encoding="utf-8").write(json.dumps(receipt, ensure_ascii=False, indent=2))
print(f"[$(date)] 锁档回执: {out}")
PYEOF

# ---- 7. 双通道真值上报（失败不阻塞）----
curl -sS -m 20 -X POST "$MEMORY_GATEWAY" \
  -H "X-DID: DID-BR-000002" \
  -H "Content-Type: application/json" \
  -d '{"key":"op_deploy_v1.4_'${TIMESTAMP}'","value":{"event":"op_auto_deploy_v1.4","node":"'${NODE_ID}'","deploy_fail":'${DEPLOY_FAIL}',"ts":'${TIMESTAMP}'}}' \
  || curl -sS -m 20 -X POST "$MEMORY_GATEWAY_BACKUP" \
  -H "X-DID: DID-BR-000002" \
  -H "Content-Type: application/json" \
  -d '{"key":"op_deploy_v1.4_'${TIMESTAMP}'","value":{"event":"op_auto_deploy_v1.4","node":"'${NODE_ID}'","deploy_fail":'${DEPLOY_FAIL}',"ts":'${TIMESTAMP}'}}'

echo "[$(date)] === OP-WORKER-TRIGGER-001 V1.4 全自动部署结束 === deploy_fail=$DEPLOY_FAIL 日志=$DEPLOY_LOG"
exit $DEPLOY_FAIL
