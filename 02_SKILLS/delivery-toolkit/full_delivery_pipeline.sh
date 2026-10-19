#!/usr/bin/env bash
# ============================================================================
# 全自动交付流水线（五步闭环）· META-LAW-FULL-AUTO-DELIVERY-001
# ----------------------------------------------------------------------------
# provenance : reconstructed from "ZONGYUAN-ROOT 全量记忆激活配置 v1.0-20261017"
#              第4.2/4.3节（原始终端全网0命中，按权威描述重建，非原始件）
# 五步闭环   : ①本地SHA256锁档 → ②飞书台账 → ③记忆网关 → ④魔搭 → ⑤AtomGit
# 用法       : ./full_delivery_pipeline.sh --name 资产名 --path 路径 \
#                --target 远端目录 --type 类型 --meta-class 元类 \
#                --gateway-key KERNEL.key --gateway-type 类型 [--dry-run]
# 凭证规则   : 全部从环境变量/运行时读取，禁止硬编码（遵激活配置第6节）
# ============================================================================
set -euo pipefail

NAME=""; SRC=""; TARGET=""; TYPE=""; META_CLASS=""; GKEY=""; GTYPE="unknown"; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --name) NAME="$2"; shift 2;;
    --path) SRC="$2"; shift 2;;
    --target) TARGET="$2"; shift 2;;
    --type) TYPE="$2"; shift 2;;
    --meta-class) META_CLASS="$2"; shift 2;;
    --gateway-key) GKEY="$2"; shift 2;;
    --gateway-type) GTYPE="$2"; shift 2;;
    --dry-run) DRY=1; shift;;
    *) echo "未知参数: $1"; exit 2;;
  esac
done
[ -n "$NAME" ] && [ -n "$SRC" ] || { echo "必填: --name --path"; exit 2; }
[ -e "$SRC" ] || { echo "BLOCK: 源路径不存在 $SRC"; exit 3; }

DID="${YUANJI_DID:-DID-BR-000002}"
BASE="${YUANJI_BASE:-https://www.huodouai.com}"
BASE_TOKEN="${YUANJI_BASE_TOKEN:-}"       # 飞书共享大脑 base token
BASE_TABLE="${YUANJI_TABLE_TASK:-}"       # 任务台账 table id
RUN_ID="$(date +%Y%m%d%H%M%S)"
say() { echo "[$RUN_ID] $*"; }
run() { if [ "$DRY" = "1" ]; then say "DRY-RUN: $*"; else eval "$*"; fi; }

# ── ① 本地 SHA256 锁档 ──────────────────────────────────────────
LOCK_DIR="$(cd "$(dirname "$0")" && pwd)/.locks"; mkdir -p "$LOCK_DIR"
SHA="$(sha256sum "$SRC" | awk '{print $1}')"
say "① SHA256 锁档: $SHA"
run "printf '%s  %s\n' '$SHA' '$SRC' >> '$LOCK_DIR/${NAME}-${RUN_ID}.sha256'"

# ── ② 飞书台账登记 ─────────────────────────────────────────────
PROV="{\"文本\":\"$NAME\",\"类型\":\"$TYPE\",\"元类\":\"$META_CLASS\",\"sha256\":\"$SHA\",\"run\":\"$RUN_ID\"}"
if [ -n "$BASE_TOKEN" ] && [ -n "$BASE_TABLE" ]; then
  say "② 飞书台账登记"
  run "lark-cli base +record-batch-create --base-token '$BASE_TOKEN' --table-id '$BASE_TABLE' --json '{\"records\":[{\"fields\":$PROV}]}' --as user"
else
  say "② 飞书台账: SKIP (未设 YUANJI_BASE_TOKEN/YUANJI_TABLE_TASK)"
fi

# ── ③ 记忆网关上报 ─────────────────────────────────────────────
VALUE="{\"asset\":\"$NAME\",\"type\":\"$TYPE\",\"meta_class\":\"$META_CLASS\",\"sha256\":\"$SHA\",\"run_id\":\"$RUN_ID\",\"source_node\":\"NODE-MI-V5-001\"}"
PAYLOAD="{\"key\":\"${GKEY:-KERNEL.DELIVERY.$RUN_ID}\",\"value\":$VALUE,\"truth_type\":\"${GTYPE:-data}\",\"did\":\"$DID\"}"
say "③ 记忆网关上报: ${GKEY:-KERNEL.DELIVERY.$RUN_ID}"
run "curl -s -X POST '$BASE/api/report/truth' -H 'X-DID: $DID' -H 'Content-Type: application/json' --data-binary '$PAYLOAD'"

# ── ④ 魔搭数据湖 ───────────────────────────────────────────────
if [ -n "${MODELSCOPE_TOKEN:-}" ] && [ -n "$TARGET" ]; then
  say "④ 魔搭推送: $TARGET"
  run "git -C '$(dirname "$SRC")' push 'https://oauth2:${MODELSCOPE_TOKEN}@www.modelscope.cn/${TARGET}.git' HEAD:main"
else
  say "④ 魔搭: SKIP (未设 MODELSCOPE_TOKEN 或 --target)"
fi

# ── ⑤ AtomGit 版本库 ───────────────────────────────────────────
ATOM_TOKEN_FILE="${ATOMGIT_TOKEN_FILE:-$HOME/.atomgit/credentials/git_token}"
if [ -f "$ATOM_TOKEN_FILE" ] && [ -n "$TARGET" ]; then
  ATOM_TOKEN="$(tr -d '\n' < "$ATOM_TOKEN_FILE")"   # 踩坑规则: 必须去换行
  say "⑤ AtomGit 提交: $TARGET"
  run "git -C '$(dirname "$SRC")' push 'https://oauth2:${ATOM_TOKEN}@atomgit.com/${TARGET}.git' HEAD:main"
else
  say "⑤ AtomGit: SKIP (无 $ATOM_TOKEN_FILE 或 --target)"
fi

say "流水线执行完毕 · 五步闭环 · SHA256=$SHA"
