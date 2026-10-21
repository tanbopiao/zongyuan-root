#!/bin/bash
# =====================================================================
# ZONGYUAN 融合心跳（统一真值）：汇总两树状态 → 单条上报网关 → 落融合快照
# 锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ META-FUSION-001 FU-4
# 用法：fusion_heartbeat.sh [--report]   （--report 上报网关；默认只落本地快照）
# =====================================================================
set -uo pipefail
ZK="/home/user/Doubao/chats/38412149511142658/zongyuan-kernel"
ZR="/home/user/ZONGYUAN-ROOT"
DID="DID-BR-000002"
GW="https://www.huodouai.com/api/report/truth"
FUSION_DIR="$ZR/var/fusion"
mkdir -p "$FUSION_DIR"

ts() { date '+%Y-%m-%dT%H:%M:%S%z'; }

# ---- 脑侧（zongyuan-kernel）状态 ----
KERNEL_ST=$(bash "$ZK/scripts/kernel_launch.sh" status 2>/dev/null || echo down)
KERNEL_PID=""
KERNEL_PID=""
case "$KERNEL_ST" in running*) KERNEL_PID=$(cat "$ZK/var/run/kernel.pid" 2>/dev/null || echo "");; esac
AUDIT_CNT=$(wc -l < "$ZK/var/audit/audit.jsonl" 2>/dev/null || echo 0)
BASELINE=$(python3 -c "import json;print(json.load(open('$ZK/var/state/baseline.json'))['root_hash'][:12])" 2>/dev/null || echo "?")
LAW_CNT=$(ls "$ZK/config/meta_laws"/*.json 2>/dev/null | wc -l)
TEST_ST=$(cd "$ZK" && python3 tests/test_kernel.py 2>/dev/null | tail -1 || echo "?")

# ---- 手侧（ZONGYUAN-ROOT）状态 ----
WORKER_ST=$(bash "$ZR/scripts/worker_controlled.sh" status worker-kernel-001 2>/dev/null | cut -c1-40 || echo down)
ASSET_CNT=$(ls "$ZR/asset/image/kunlun-auto-out"/*.webp 2>/dev/null | wc -l)
ACT_CNT=$(python3 -c "import json;print(len(json.load(open('$ZR/var/activation/00-激活索引.json'))['records']))" 2>/dev/null || echo 0)
LEDGER_CNT=$(wc -l < "$ZR/HASH-LEDGER.csv" 2>/dev/null || echo 0)
LOCK_AGE_H=$(python3 - "$ZR/卷宗" << 'PYEOF'
import sys, time, glob, os
latest = None
for f in glob.glob(sys.argv[1] + "/GLOBAL-LOCK-ZONGYUAN-ROOT-FULL-*.json"):
    m = os.path.getmtime(f)
    if latest is None or m > latest[1]: latest = (f, m)
if not latest: print("none")
else: print(int((time.time() - latest[1]) / 3600))
PYEOF
)
ZR_LAW_CNT=$(ls "$ZR/meta-rules"/*.json 2>/dev/null | wc -l)

# ---- 融合快照 ----
SNAP="{\"ts\":\"$(ts)\",\"fusion\":{\"kernel\":{\"status\":\"$KERNEL_ST\",\"pid\":\"$KERNEL_PID\",\"audit\":$AUDIT_CNT,\"baseline\":\"$BASELINE\",\"laws\":$LAW_CNT,\"tests\":\"$TEST_ST\"},\"zr\":{\"worker\":\"$WORKER_ST\",\"assets\":$ASSET_CNT,\"activations\":$ACT_CNT,\"ledger\":$LEDGER_CNT,\"lock_age_h\":\"$LOCK_AGE_H\",\"laws\":$ZR_LAW_CNT}},\"DID\":\"$DID\"}"
SNAP_FILE="$FUSION_DIR/heartbeat-$(date +%Y%m%d-%H%M%S).json"
echo "$SNAP" > "$SNAP_FILE"
echo "融合快照已落: $SNAP_FILE"

# ---- 上报（--report） ----
if [ "${1:-}" = "--report" ]; then
  KEY="fusion_heartbeat_$(date +%s)"
  PAYLOAD="{\"key\":\"$KEY\",\"value\":{\"event\":\"fusion.heartbeat\",\"kernel\":{\"status\":\"$KERNEL_ST\",\"audit\":$AUDIT_CNT,\"baseline\":\"$BASELINE\"},\"zr\":{\"worker\":\"$WORKER_ST\",\"assets\":$ASSET_CNT,\"lock_age_h\":\"$LOCK_AGE_H\"},\"ts\":\"$(ts)\",\"DID\":\"$DID\"}}"
  RESP=$(python3 "$ZR/scripts/gateway_report.py" "$KEY" "$PAYLOAD" 2>/dev/null || echo '{"ok": false}')
  if echo "$RESP" | grep -q '"ok": true'; then
    echo "上报: OK | truth_count=$(echo "$RESP" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("truth_count",""))' 2>/dev/null)"
  else
    echo "上报: FAIL | $RESP"
  fi
fi
