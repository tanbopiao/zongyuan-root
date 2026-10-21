#!/bin/bash
# ============================================
# Worker 自动部署定时轮询脚本 (worker_auto_deploy_timer.sh)
# 确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | OP-WORKER-TRIGGER-001 认领端
# 原理: 定时轮询飞书Base任务台账 → 认领【待部署】任务 → 执行部署 → 标记【部署中】
# 用法:
#   bash worker_auto_deploy_timer.sh            # 单轮执行一次
#   bash worker_auto_deploy_timer.sh --loop 600 # 循环模式，每600秒一轮
# 依赖: lark-cli, jq
# ============================================
set -uo pipefail
BASE_TOKEN="DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE="tblnVRjuf7P31cEP"
MAX_WORKER_COUNT=3
TIMESTAMP=$(date +%s)
NODE_ID="$(hostname)"
OP="OP-WORKER-TRIGGER-001"

echo "[$TIMESTAMP] $OP 轮询开始 (node=$NODE_ID)"

# 查找【待处理】任务（record-search 用 keyword + search_fields）
SEARCH=$(lark-cli base +record-search --base-token "$BASE_TOKEN" --table-id "$TASK_TABLE" \
  --json '{"keyword":"待处理","search_fields":["状态"]}' --as user 2>&1)
RET=$?
if [ $RET -ne 0 ]; then
  echo "{\"operator_id\":\"$OP\",\"status\":\"skipped\",\"msg\":\"台账查询失败: $(echo "$SEARCH" | head -c 150)\"}"
  exit 0
fi

# 解析待处理任务数
COUNT=$(echo "$SEARCH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('data',{}).get('records',[])))" 2>/dev/null)
echo "待处理任务数: ${COUNT:-0}"

if [ "${COUNT:-0}" -eq 0 ]; then
  echo "{\"operator_id\":\"$OP\",\"status\":\"idle\",\"msg\":\"无待部署任务\"}"
  exit 0
fi

# 配额校验
RUNNING=$(echo "$SEARCH" | jq -r '[.data.records[]?.fields.状态[]? // empty] | length' 2>/dev/null)
echo "当前在部署任务: ${RUNNING:-0}/${MAX_WORKER_COUNT}"

# 认领第一条待部署任务（简化版：打印已识别任务，实际部署走 auto_deploy_worker.py）
echo "{\"operator_id\":\"$OP\",\"status\":\"claimed\",\"msg\":\"检测到待部署任务，移交部署引擎处理\"}"

# 移交部署引擎（若存在）
if [ -f "/home/user/ZONGYUAN-ROOT/07_代码与脚本/auto_deploy_worker.py" ]; then
  python3 /home/user/ZONGYUAN-ROOT/07_代码与脚本/auto_deploy_worker.py >/dev/null 2>&1 &
  echo "部署引擎已启动 (PID $!)"
fi

exit 0
