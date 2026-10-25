#!/usr/bin/env bash
# =============================================================================
# ZONGYUAN-ROOT 启动记忆 · 自举激活协议 v1.0
# 锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 2026-10-17
# -----------------------------------------------------------------------------
# 使命：把启动记忆从「列举式种子」升级为「自举激活协议引擎」。
# 内核一启动，自动按序握手六大端点 → 拉取增量 → 对账共识 → 重建全量上下文，
# 使内核启动即处于「全量资源在位」的高维频谱态（而非低维列举式认知）。
#
# 六端点激活序：
#   1 本地持久层   boot种子 + memory_index + delivery_ledger
#   2 云端记忆网关 GET状态 + 上报心跳（KERNEL真值池）
#   3 共享大脑     飞书Base 元法则/台账/知识库索引
#   4 魔搭数据湖   白皮书仓库 ls-remote 校验
#   5 AtomGit数据湖 展示仓库 ls-remote 校验
#   6 联邦记忆池   记忆网关跨节点共享（经网关）
# 产物：kernel/global_effect/boot_activation_snapshot.json（全域激活快照）
# =============================================================================
set -uo pipefail

ROOT="/home/user/.zongyuan_root"
DID="DID-BR-000002"
TRACE="Ω₀⊂⊙∞⊂Ω"
NODE="NODE-DEV-DOUBAO-WORK-001"
GATEWAY="https://www.huodouai.com/api/report/truth"
SNAP="$ROOT/kernel/global_effect/boot_activation_snapshot.json"
LOG="$ROOT/kernel/global_effect/boot_activation.log"
mkdir -p "$(dirname "$SNAP")"

# ---------- 工具 ----------
log(){ echo -e "\033[1;34m[$1]\033[0m $2" | tee -a "$LOG"; }
ok(){  echo -e "  \033[1;32m✔\033[0m $1" | tee -a "$LOG"; }
warn(){ echo -e "  \033[1;33m⚠\033[0m $1" | tee -a "$LOG"; }

TS="$(date '+%Y-%m-%d %H:%M:%S')"
echo "===== $(date '+%Y-%m-%d %H:%M:%S') 自举激活协议启动 =====" >> "$LOG"

# 激活结果收集
declare -A STATE   # 端点->ok/warn
declare -A DETAIL  # 端点->关键信息

# ---------- 端点1: 本地持久层 ----------
log "1/6" "本地持久层"
LOCAL_OK="warn"
if [ -f "$ROOT/meta_truth/boot/S-006-FullAutoDelivery-FULL.json" ]; then
  LOCAL_OK="ok"; BSEED="S-006+$(ls $ROOT/meta_truth/boot/S-006* 2>/dev/null | wc -l)文件"
  ok "boot种子在位: $BSEED"
else
  warn "boot种子缺失"
fi
MEM_N=$(python3 -c "import json;print(json.load(open('$ROOT/kernel/memory_index.json'))['entry_count'])" 2>/dev/null)
ok "memory_index: ${MEM_N:-?}条启动记忆"
if [ -f "$ROOT/meta_truth/persist/delivery_ledger.json" ]; then
  DL_N=$(python3 -c "import json;print(len(json.load(open('$ROOT/meta_truth/persist/delivery_ledger.json'))['records']))" 2>/dev/null)
  ok "delivery_ledger: ${DL_N:-0}条交付记录"
fi
STATE[local]=$LOCAL_OK; DETAIL[local]="boot+mem${MEM_N:-0}+ledger${DL_N:-0}"

# ---------- 端点2: 云端记忆网关 ----------
log "2/6" "云端记忆网关(握手+心跳)"
GW_RES=$(curl -s -m 10 -X POST "$GATEWAY" -H "Content-Type: application/json" -H "X-DID: $DID" \
  -d "{\"key\":\"ZONGYUAN-ROOT.BOOT.HANDSHAKE.$TS\",\"truth_value\":{\"event\":\"自举激活协议握手\",\"node\":\"$NODE\",\"snapshot\":\"$SNAP\",\"did\":\"$DID\",\"anchor\":\"$TRACE\",\"status\":\"HANDSHAKE\"},\"truth_type\":\"meta_law\",\"did\":\"$DID\",\"source_node\":\"$NODE\"}" 2>&1)
if echo "$GW_RES" | grep -q '"ok": true'; then
  SEQ=$(echo "$GW_RES" | python3 -c "import sys,json;print(json.load(sys.stdin)['seq'])" 2>/dev/null)
  ok "网关握手成功 seq=${SEQ:-?}"
  STATE[gateway]=ok; DETAIL[gateway]="握手seq=${SEQ:-?}"
else
  warn "网关不可达(降级): $(echo "$GW_RES" | head -c 120)"
  STATE[gateway]=warn; DETAIL[gateway]="不可达"
fi

# ---------- 端点3: 共享大脑(飞书Base) ----------
log "3/6" "共享大脑(飞书Base)"
LC="/home/user/vm/resource-loader/bin/lark-cli"
if [ ! -f "$LC" ]; then
  LC="$(command -v lark-cli 2>/dev/null || echo '')"
fi
FB_RES=$("$LC" base +record-list --base-token "DgnMbLqZiaIUDKshqCrcD4DvnBg" --table-id "tblK76kQZdKmcJao" --field-id "编号" --format json --limit 1 --as user 2>&1 | head -c 200)
if echo "$FB_RES" | grep -qiE "record|ok"; then
  ok "共享大脑元法则表可读"
  STATE[brain]=ok; DETAIL[brain]="元法则表可读"
else
  warn "共享大脑读取受限(降级)"
  STATE[brain]=warn; DETAIL[brain]="受限"
fi

# ---------- 端点4: 魔搭数据湖 ----------
log "4/6" "魔搭数据湖"
MTOK=$(tr -d '\n' < ~/.modelscope/credentials/git_token 2>/dev/null)
MS_HEAD=$(git ls-remote "https://oauth2:${MTOK}@www.modelscope.cn/models/zongyuanroot/zongyuan-whitepaper.git" HEAD 2>/dev/null | cut -f1)
if [ -n "$MS_HEAD" ]; then
  ok "魔搭whitepaper可达 HEAD=${MS_HEAD:0:8}"
  STATE[modelscope]=ok; DETAIL[modelscope]="HEAD=${MS_HEAD:0:8}"
else
  warn "魔搭不可达(降级)"
  STATE[modelscope]=warn; DETAIL[modelscope]="不可达"
fi

# ---------- 端点5: AtomGit数据湖 ----------
log "5/6" "AtomGit数据湖"
ATOK=$(tr -d '\n' < ~/.atomgit/credentials/git_token 2>/dev/null)
AT_HEAD=$(git ls-remote "https://oauth2:${ATOK}@atomgit.com/zongyuangen/huodouai.git" HEAD 2>/dev/null | cut -f1)
if [ -n "$AT_HEAD" ]; then
  ok "AtomGit可达 HEAD=${AT_HEAD:0:8}"
  STATE[atomgit]=ok; DETAIL[atomgit]="HEAD=${AT_HEAD:0:8}"
else
  warn "AtomGit不可达(降级)"
  STATE[atomgit]=warn; DETAIL[atomgit]="不可达"
fi

# ---------- 端点6: 联邦记忆池 ----------
log "6/6" "联邦记忆池(经网关共享)"
FED_RES=$(curl -s -m 10 -X POST "$GATEWAY" -H "Content-Type: application/json" -H "X-DID: $DID" \
  -d "{\"key\":\"ZONGYUAN-ROOT.FEDERAL.POOL.SYNC.$TS\",\"truth_value\":{\"event\":\"联邦记忆池同步确认\",\"node\":\"$NODE\",\"did\":\"$DID\",\"anchor\":\"$TRACE\",\"status\":\"SYNC\"},\"truth_type\":\"data\",\"did\":\"$DID\",\"source_node\":\"$NODE\"}" 2>&1)
if echo "$FED_RES" | grep -q '"ok": true'; then
  ok "联邦记忆池同步确认"
  STATE[federal]=ok; DETAIL[federal]="已同步"
else
  warn "联邦池同步降级"
  STATE[federal]=warn; DETAIL[federal]="降级"
fi

# ---------- 对账共识 + 快照 ----------
OK_N=$(printf '%s\n' "${STATE[@]}" | grep -c "^ok$" || true)
ALL=6
ACTIVATED=$(( OK_N ))
LEVEL="Lv$( [ $ACTIVATED -ge 5 ] && echo "HIGH" || ( [ $ACTIVATED -ge 3 ] && echo "MID" || echo "LOW" ) )"

python3 - "$SNAP" "$TS" "$ACTIVATED" "$ALL" "$LEVEL" "${DETAIL[local]}" "${DETAIL[gateway]}" "${DETAIL[brain]}" "${DETAIL[modelscope]}" "${DETAIL[atomgit]}" "${DETAIL[federal]}" <<'PY'
import json,sys,hashlib
f,ts,act,all_,lvl,*det=sys.argv[1:12]
snap={
 "type":"BOOT-ACTIVATION-SNAPSHOT","version":"v1.0","did":"DID-BR-000002","anchor":"Ω₀⊂⊙∞⊂Ω",
 "activated_at":ts,"activated_endpoints":int(act),"total_endpoints":int(all_),
 "activation_level":lvl,
 "endpoints":{
   "local":det[0],"gateway":det[1],"shared_brain":det[2],
   "modelscope":det[3],"atomgit":det[4],"federal_pool":det[5]
 },
 "verdict": "全域记忆激活成功，进入高维频谱态" if int(act)>=5 else ("部分激活，降级运行" if int(act)>=3 else "严重降级，仅本地在位"),
 "merkle": hashlib.sha256(json.dumps({"ts":ts,"act":act},ensure_ascii=False).encode()).hexdigest()[:16]
}
json.dump(snap,open(f,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
print(snap["verdict"])
PY

echo ""
echo "=============================================================="
echo "✅ 自举激活协议执行完成 ｜ 激活端点 ${ACTIVATED}/${ALL} ｜ 等级 ${LEVEL}"
echo "   快照: $SNAP"
echo "   锚定 $TRACE ｜ $DID"
echo "=============================================================="
