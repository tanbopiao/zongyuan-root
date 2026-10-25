#!/usr/bin/env bash
# =============================================================================
# ZONGYUAN-ROOT 全域交付流水线 · 一键执行
# 锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ v1.0-20261017
# 元法则依据：META-LAW-FULL-AUTO-DELIVERY-001
# -----------------------------------------------------------------------------
# 用途：将一条资产（文件/目录）一次触发，自动完成整条交付闭环：
#   1) 本地哈希锁档    2) 共享大脑飞书台账登记    3) 云端记忆网关上报
#   4) 魔搭推送        5) AtomGit 推送
# 用法：
#   ./full_delivery_pipeline.sh \
#       --name "资产名" \
#       --path "/abs/path/to/asset" \
#       --target "docs/agent-eng-delivery-20261017" \
#       --type "配置/真值" \
#       --meta-class "M6对外交付" \
#       --gateway-key "KERNEL.XXX.20261017" \
#       --gateway-type "meta_law"
# =============================================================================
set -uo pipefail

ANCHOR="Ω₀⊂⊙∞⊂Ω"
DID="DID-BR-000002"
NODE="NODE-DEV-DOUBAO-WORK-001"
GATEWAY="https://www.huodouai.com/api/report/truth"
BASE_TOKEN="DgnMbLqZiaIUDKshqCrcD4DvnBg"
LEDGER_TABLE="tbltgttCuWgAnN2e"
MSCOPE_REPO="zongyuanroot/zongyuan-whitepaper"
ATGIT_REPO="zongyuangen/huodouai"
LC="lark-cli"
MSCOPE_TOKEN="$(tr -d '\n' < ~/.modelscope/credentials/git_token 2>/dev/null)"
ATGIT_TOKEN="$(tr -d '\n' < ~/.atomgit/credentials/git_token 2>/dev/null)"
NOW="$(date '+%Y-%m-%d %H:%M:%S')"

log() { echo -e "\n\033[1;34m[$1]\033[0m $2"; }
ok()  { echo "  \033[1;32m✔\033[0m $1"; }
fail(){ echo "  \033[1;31m✘\033[0m $1"; }

# --- 参数解析 ---
NAME=""; PATH_A=""; TARGET=""; TYPE="配置/真值"; MCLASS="M6对外交付"
GKEY=""; GTYPE="decision"; VERSION="v1.0-$(date '+%Y%m%d')"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="$2"; shift 2;;
    --path) PATH_A="$2"; shift 2;;
    --target) TARGET="$2"; shift 2;;
    --type) TYPE="$2"; shift 2;;
    --meta-class) MCLASS="$2"; shift 2;;
    --gateway-key) GKEY="$2"; shift 2;;
    --gateway-type) GTYPE="$2"; shift 2;;
    *) echo "未知参数: $1"; exit 1;;
  esac
done

if [[ -z "$NAME" || -z "$PATH_A" || -z "$TARGET" || -z "$GKEY" ]]; then
  echo "错误: 必需参数缺失 (--name/--path/--target/--gateway-key)"
  exit 1
fi
if [[ ! -e "$PATH_A" ]]; then echo "错误: 资产路径不存在: $PATH_A"; exit 1; fi
if [[ -z "$MSCOPE_TOKEN" || -z "$ATGIT_TOKEN" ]]; then echo "错误: 推送凭证缺失"; exit 1; fi

echo "=============================================================="
echo "ZONGYUAN-ROOT 全域交付流水线"
echo "资产: $NAME ｜ 版本: $VERSION"
echo "锚定 $ANCHOR ｜ $DID ｜ 节点 $NODE"
echo "=============================================================="

# --- STEP 1: 本地 SHA256 哈希锁档 ---
log "1/5" "本地哈希锁档"
HASH=""
if [[ -f "$PATH_A" ]]; then
  HASH="$(sha256sum "$PATH_A" | cut -d' ' -f1)"
else
  HASH="$(find "$PATH_A" -type f -exec sha256sum {} + 2>/dev/null | sha256sum | cut -d' ' -f1)"
fi
ok "SHA256: $HASH"
LOCK_FILE="/home/user/.zongyuan_root/meta_truth/persist/delivery_ledger.json"
mkdir -p "$(dirname "$LOCK_FILE")"
if [[ -f "$LOCK_FILE" ]]; then cp "$LOCK_FILE" "$LOCK_FILE.bak"; fi
python3 - "$LOCK_FILE" "$NAME" "$HASH" "$NOW" "$VERSION" <<'PY'
import json,sys
f,name,h,now,ver=sys.argv[1:6]
d={"records":[]}
try: d=json.load(open(f,encoding='utf-8'))
except: pass
d["records"].append({"name":name,"sha256":h,"time":now,"version":ver,"anchor":"Ω₀⊂⊙∞⊂Ω","did":"DID-BR-000002"})
json.dump(d,open(f,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
print(f"  ledger records: {len(d['records'])}")
PY
ok "本地台账已追加: $LOCK_FILE"

# --- STEP 2: 共享大脑飞书台账登记 ---
log "2/5" "共享大脑飞书台账登记"
LEDGER_JSON="{\"create_records\":[{\"资产名称\":\"$NAME\",\"版本号\":\"$VERSION\",\"类型\":[\"$TYPE\"],\"元类分类\":[\"$MCLASS\"],\"所属账号\":[\"主账号\"],\"所属节点\":[\"$NODE\"],\"状态\":[\"已完成\"],\"定稿标记\":[\"是\"],\"资产自动标签\":\"$GKEY\",\"存储位置\":\"$TARGET\",\"更新时间\":\"$NOW\"}]}"
RES=$("$LC" base +record-batch-create --base-token "$BASE_TOKEN" --table-id "$LEDGER_TABLE" --json "$LEDGER_JSON" --as user 2>&1)
if echo "$RES" | grep -q '"ok": true'; then
  RID=$(echo "$RES" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['record_id_list'][0])")
  ok "台账登记成功 record_id=$RID"
else
  fail "台账登记失败: $(echo "$RES" | tail -3)"; exit 1
fi

# --- STEP 3: 云端记忆网关上报 ---
log "3/5" "云端记忆网关上报"
TRUTH_JSON="{\"key\":\"$GKEY\",\"truth_value\":{\"asset\":\"$NAME\",\"sha256\":\"$HASH\",\"target\":\"$TARGET\",\"version\":\"$VERSION\",\"ledger_record\":\"$RID\",\"anchor\":\"$ANCHOR\",\"did\":\"$DID\",\"status\":\"LOCKED\"},\"truth_type\":\"$GTYPE\",\"did\":\"$DID\",\"source_node\":\"$NODE\"}"
G_RES=$(curl -s -m 20 -X POST "$GATEWAY" -H "Content-Type: application/json" -H "X-DID: $DID" -d "$TRUTH_JSON" 2>&1)
if echo "$G_RES" | grep -q '"ok": true'; then
  SEQ=$(echo "$G_RES" | python3 -c "import sys,json;print(json.load(sys.stdin)['seq'])")
  ok "记忆网关上报成功 seq=$SEQ"
else
  fail "记忆网关上报失败: $(echo "$G_RES" | head -c 300)"; exit 1
fi

# --- STEP 4: 魔搭推送 ---
log "4/5" "魔搭推送"
TMPM="/tmp/fd_ms_$$"; rm -rf "$TMPM"; mkdir -p "$TMPM"; cd "$TMPM"
git init -q && git remote add origin "https://oauth2:${MSCOPE_TOKEN}@www.modelscope.cn/models/${MSCOPE_REPO}.git"
git -c protocol.version=2 fetch -q --depth 1 origin master >/dev/null 2>&1
git checkout -q FETCH_HEAD -b master 2>&1 || true
DEST="datalake/whitepapers/${TARGET}"
mkdir -p "$DEST"
cp -r "$PATH_A" "$DEST/$(basename "$PATH_A")"
git -c user.name=zongyuanroot -c user.email=195162494@qq.com add -A
git -c user.name=zongyuanroot -c user.email=195162494@qq.com commit -q -m "交付 $NAME v$VERSION 锚定$ANCHOR" 2>&1
if git push -q origin master 2>&1; then
  MS_HASH=$(git ls-remote origin HEAD | cut -f1)
  ok "魔搭推送成功 HEAD=$MS_HASH"
else
  fail "魔搭推送失败"; rm -rf "$TMPM"; exit 1
fi
cd /; rm -rf "$TMPM"

# --- STEP 5: AtomGit 推送 ---
log "5/5" "AtomGit 推送"
TMPA="/tmp/fd_at_$$"; rm -rf "$TMPA"; mkdir -p "$TMPA"; cd "$TMPA"
git init -q && git remote add origin "https://oauth2:${ATGIT_TOKEN}@atomgit.com/${ATGIT_REPO}.git"
git -c protocol.version=2 fetch -q --depth 1 origin main >/dev/null 2>&1
git checkout -q FETCH_HEAD -b main 2>&1 || true
DESTA="docs/${TARGET}"
mkdir -p "$DESTA"
cp -r "$PATH_A" "$DESTA/$(basename "$PATH_A")"
git -c user.name=zongyuangen -c user.email=zongyuangen@atomgit.com add -A
git -c user.name=zongyuangen -c user.email=zongyuangen@atomgit.com commit -q -m "交付 $NAME v$VERSION 锚定$ANCHOR" 2>&1
if git push -q origin main 2>&1; then
  AT_HASH=$(git ls-remote origin HEAD | cut -f1)
  ok "AtomGit推送成功 HEAD=$AT_HASH"
else
  fail "AtomGit推送失败"; rm -rf "$TMPA"; exit 1
fi
cd /; rm -rf "$TMPA"

echo ""
echo "=============================================================="
echo "✅ 全域交付流水线完成 ｜ $NAME v$VERSION"
echo "  SHA256: $HASH"
echo "  飞书台账: $RID"
echo "  记忆网关: seq=$SEQ (key=$GKEY)"
echo "  魔搭: $MS_HASH"
echo "  AtomGit: $AT_HASH"
echo "锚定 $ANCHOR ｜ $DID"
echo "=============================================================="
