#!/bin/bash
# 公理自检周期巡检定时器 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
# 每 6 小时投递一份新自检契约至 task_inbox，由调度器轮询消费（契约→调度→OPA→执行全链路）
ZR="/home/user/ZONGYUAN-ROOT"
TS=$(date +%s)
TID="T-AXIOM-PATROL-${TS}"
# 幂等：若 inbox 已有未消费的自检契约则不重复投递（防堆积）
if ls $ZR/task_inbox/T-AXIOM-PATROL-*.json >/dev/null 2>&1; then
  echo "[$(date)] 已有待调度自检契约，跳过本次投递"
  exit 0
fi
cat > $ZR/task_inbox/${TID}.json << EOF
{
  "contract_version": "CONTRACT-OP-V1.0",
  "did": "DID-BR-000002",
  "ontology_signature": "Ω₀⊂⊙∞⊂Ω",
  "contract_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "task_id": "${TID}",
  "operator_list": [{"op_id": "SELF_CHECK_AXIOM", "params": {"check_scope": "full"}, "timeout": 300, "retry": 1, "allow_failure": false}],
  "scheduling_policy": {"mode": "serial", "continue_on_fail": false},
  "priority": "P0",
  "note": "公理自检周期巡检（6h 定时投递）"
}
EOF
echo "[$(date)] 已投递 ${TID} 至 task_inbox"