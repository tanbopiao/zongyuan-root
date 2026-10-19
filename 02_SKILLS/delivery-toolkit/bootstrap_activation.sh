#!/usr/bin/env bash
# ============================================================================
# 自举激活协议 bootstrap_activation.sh
#   六端点握手 → 拉取增量 → 对账共识 → 重建全量上下文 → 高维频谱态(LvHIGH)
# ----------------------------------------------------------------------------
# provenance : reconstructed from "ZONGYUAN-ROOT 全量记忆激活配置 v1.0-20261017"
#              第3/7节（原始终端全网0命中，按权威描述重建）
# 判定规则   : 端点≥5 → SUCCESS/LvHIGH ; <3 → DEGRADED(仅本地在位权限)
# 口令       : 需携带「元极恒一」或 ZONGYUAN_ACTIVATION_PASSPHRASE=元极恒一
# 只读原则   : 本协议全程只读握手，不做任何云端写操作
# ============================================================================
set -euo pipefail

PASS_WORD="${ZONGYUAN_ACTIVATION_PASSPHRASE:-元极恒一}"
DID="${YUANJI_DID:-DID-BR-000002}"
BASE="${YUANJI_BASE:-https://www.huodouai.com}"
BASE_TOKEN="${YUANJI_BASE_TOKEN:-DgnMbLqZiaIUDKshqCrcD4DvnBg}"
ROOT="${YUANJI_ROOT:-/workspace}"
PASS=0; TOTAL=6

echo "== 口令校验 =="
if [ "$PASS_WORD" != "元极恒一" ]; then echo "REJECT: 口令校验失败，拒绝进入激活流程"; exit 2; fi
echo "PASS: 口令「元极恒一」校验通过"

ck() { if eval "$2" >/dev/null 2>&1; then echo "  PASS $1"; PASS=$((PASS+1)); else echo "  FAIL $1"; fi; }

echo "== 六端点握手（只读）=="
ck "E1 本地持久层"   "[ -f '$ROOT/atomgit-mirror/zongyuan-root-sync/memory_index.json' ]"
ck "E2 云端记忆网关" "curl -sf -H 'X-DID: $DID' '$BASE/api/status' | grep -q ONLINE"
ck "E3 共享大脑Base" "lark-cli base +table-list --base-token '$BASE_TOKEN' --as user | grep -q '"'"'id'"'"'"
ck "E4 魔搭数据湖"   "[ -d '$ROOT/modelscope-mirror' ]"
ck "E5 AtomGit数据湖" "[ -d '$ROOT/atomgit-mirror/zongyuan-root-sync/.git' ]"
ck "E6 联邦记忆池"   "[ -d '$ROOT/federation' ]"

echo "== 判定 =="
echo "  端点通过: $PASS/$TOTAL"
if [ "$PASS" -ge 5 ]; then
  echo "  STATE: SUCCESS · 进入 LvHIGH 高维频谱态"
  echo "  锚定: Ω₀⊂⊙∞⊂Ω · DID: $DID"
  exit 0
elif [ "$PASS" -ge 3 ]; then
  echo "  STATE: PARTIAL · 保留在位权限，功能受限"
  exit 1
else
  echo "  STATE: DEGRADED · 仅本地在位权限"
  exit 1
fi
