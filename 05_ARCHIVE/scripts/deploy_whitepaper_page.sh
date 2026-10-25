#!/usr/bin/env bash
# ============================================================================
# ZONGYUAN-ROOT 官网技术白皮书部署器
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 元极恒一自治体系
#
# 作用：把单篇白皮书 HTML 推送到 huodouai.com/whitepaper/，
#       并在库索引 index.html 中「幂等」登记卡片 + 同步「共 N 份白皮书」计数。
#
# 用法：
#   deploy_whitepaper_page.sh --src <本地html> --slug <文件名> --title <标题> [选项]
#
# 必填：
#   --src      本地白皮书 HTML 路径
#   --slug     线上文件名（不含 .html），仅允许 [A-Za-z0-9._-]
#   --title    索引卡片标题
#
# 选项：
#   --marker <文本>     页面校验标记（默认取标题）；curl 正文须含该串
#   --position top|bottom  卡片插入位置（默认 top）
#   --host <别名>       SSH 别名（默认 zongyuan-cloud）
#   --webroot <路径>    站点根（默认 /www/wwwroot/huodouai.com）
#   --dir <子目录>      白皮书目录（默认 whitepaper）
#   --owner <属主>      文件属主（默认 www:www）
#   --base-url <URL>    校验用基址（默认 https://huodouai.com）
#   --receipt-dir <目录> 回执目录（默认 reports）
#   --dry-run           只做本地校验 + 远端只读预检，不上传不修改
#   --no-index          只推页面，不改索引
#   --no-verify         跳过部署后 HTTP 校验
#
# 退出码：0 成功 / 2 参数或本地校验失败 / 3 远端预检失败 / 4 上传或注入失败 / 5 校验失败
#
# 示例：
#   scripts/deploy_whitepaper_page.sh \
#     --src reports/AUTONOMY-LV11-UPGRADE-DASHBOARD-20261018.html \
#     --slug autonomy-lv11-upgrade-dashboard \
#     --title "ZONGYUAN-ROOT 自治层级 Lv11 升级白皮书 · 火斗云智AIOS" \
#     --marker "95.19" --dry-run
# ============================================================================
set -euo pipefail

HOST="zongyuan-cloud"
WEBROOT="/www/wwwroot/huodouai.com"
DIR="whitepaper"
OWNER="www:www"
BASE_URL="https://huodouai.com"
POSITION="top"
RECEIPT_DIR="reports"
SRC=""; SLUG=""; TITLE=""; MARKER=""
DRY_RUN=0; DO_INDEX=1; DO_VERIFY=1

SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INJECTOR="$SCRIPT_DIR/wp_index_inject.py"

die(){ echo "ERROR: $*" >&2; exit "${2:-2}"; }

usage(){ grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --src) SRC="${2:-}"; shift 2;;
    --slug) SLUG="${2:-}"; shift 2;;
    --title) TITLE="${2:-}"; shift 2;;
    --marker) MARKER="${2:-}"; shift 2;;
    --host) HOST="${2:-}"; shift 2;;
    --webroot) WEBROOT="${2:-}"; shift 2;;
    --dir) DIR="${2:-}"; shift 2;;
    --owner) OWNER="${2:-}"; shift 2;;
    --base-url) BASE_URL="${2:-}"; shift 2;;
    --position) POSITION="${2:-}"; shift 2;;
    --receipt-dir) RECEIPT_DIR="${2:-}"; shift 2;;
    --dry-run) DRY_RUN=1; shift;;
    --no-index) DO_INDEX=0; shift;;
    --no-verify) DO_VERIFY=0; shift;;
    -h|--help) usage; exit 0;;
    *) die "未知参数: $1" 2;;
  esac
done

# ---------- 1. 本地参数校验 ----------
[ -n "$SRC" ] || die "缺少 --src" 2
[ -n "$SLUG" ] || die "缺少 --slug" 2
[ -n "$TITLE" ] || die "缺少 --title" 2
[ -f "$SRC" ] || die "本地文件不存在: $SRC" 2
[ -s "$SRC" ] || die "本地文件为空: $SRC" 2
[ -f "$INJECTOR" ] || die "注入器缺失: $INJECTOR" 2

case "$SLUG" in
  */*|*..*|.*|-*) die "--slug 非法（禁路径分隔/点点/前导点或连字符）: $SLUG" 2;;
esac
printf '%s' "$SLUG" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9._-]*$' \
  || die "--slug 非法（仅允许 [A-Za-z0-9._-]）: $SLUG" 2

case "$POSITION" in top|bottom) ;; *) die "--position 仅支持 top|bottom" 2;; esac
[ -n "$MARKER" ] || MARKER="$TITLE"

# HTML 基本形态校验（不猜内容，只确认是网页）
if ! grep -qiE '<html|<!doctype html' "$SRC"; then
  die "--src 不是 HTML（未含 <html>/<!DOCTYPE html>）: $SRC" 2
fi

SRC_SHA="$(sha256sum "$SRC" | awk '{print $1}')"
R_DIR="$WEBROOT/$DIR"
R_PAGE="$R_DIR/$SLUG.html"
R_INDEX="$R_DIR/index.html"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
URL_PAGE="$BASE_URL/$DIR/$SLUG.html"
URL_INDEX="$BASE_URL/$DIR/"

echo "=== [1/6] 参数校验通过 ==="
echo "    src   = $SRC"
echo "    slug  = $SLUG"
echo "    title = $TITLE"
echo "    sha256= ${SRC_SHA:0:16}…"
echo "    host  = $HOST   remote = $R_PAGE"

# ---------- 2. 远端预检（只读） ----------
echo "=== [2/6] 远端预检（只读） ==="
if ssh "${SSH_OPTS[@]}" "$HOST" "test -d '$R_DIR' && command -v python3 >/dev/null 2>&1 && echo PREFLIGHT_OK" 2>/dev/null | grep -q PREFLIGHT_OK; then
  echo "    远端目录 + python3 就绪"
else
  die "远端预检失败：无法 ssh $HOST，或 $R_DIR 不存在，或远端无 python3。请先确认 SSH 通道（沙箱内直连不可用属预期）。" 3
fi

# 读取远端当前计数（只读；失败不视为致命）
REMOTE_COUNT="$(ssh "${SSH_OPTS[@]}" "$HOST" \
  "grep -oE '共 ?[0-9]+ ?份白皮书' '$R_INDEX' 2>/dev/null | head -1" 2>/dev/null || echo '')"
REMOTE_COUNT="${REMOTE_COUNT:-未知}"
echo "    远端当前计数 = $REMOTE_COUNT"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "=== [dry-run] 计划 ==="
  echo "    上传 $SRC -> $R_PAGE"
  if [ "$DO_INDEX" -eq 1 ]; then
    echo "    注入卡片 slug=$SLUG position=$POSITION -> $R_INDEX（幂等 + 备份 + 自校验）"
  fi
  echo "    属主 $OWNER"
  [ "$DO_VERIFY" -eq 1 ] && echo "    校验 $URL_PAGE 与 $URL_INDEX"
  echo "=== dry-run 结束：未做任何修改 ==="
  exit 0
fi

# ---------- 3. 上传页面（先写临时文件再原子替换） ----------
echo "=== [3/6] 上传白皮书页面 ==="
R_TMP="$R_DIR/.$SLUG.html.tmp.$TS"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --chmod=F644 -e "ssh ${SSH_OPTS[*]}" "$SRC" "$HOST:$R_TMP" \
    || die "rsync 上传失败" 4
else
  scp "${SSH_OPTS[@]}" -q "$SRC" "$HOST:$R_TMP" || die "scp 上传失败" 4
fi
ssh "${SSH_OPTS[@]}" "$HOST" "mv -f '$R_TMP' '$R_PAGE' && chmod 644 '$R_PAGE'" \
  || die "远端落位失败" 4
echo "    已落位 $R_PAGE"

# ---------- 4. 索引幂等注入 ----------
INDEX_RESULT='{"status":"skipped","reason":"--no-index"}'
if [ "$DO_INDEX" -eq 1 ]; then
  echo "=== [4/6] 索引注入（幂等） ==="
  TITLE_B64="$(printf '%s' "$TITLE" | base64 -w0)"
  INDEX_RESULT="$(ssh "${SSH_OPTS[@]}" "$HOST" \
    "python3 - --index '$R_INDEX' --slug '$SLUG' --title-b64 '$TITLE_B64' --position '$POSITION' --json" \
    < "$INJECTOR")" || die "索引注入失败" 4
  echo "    $INDEX_RESULT"
else
  echo "=== [4/6] 跳过索引注入（--no-index） ==="
fi

ssh "${SSH_OPTS[@]}" "$HOST" "chown $OWNER '$R_PAGE' '$R_INDEX' 2>/dev/null || true" || true

# ---------- 5. 部署后 HTTP 校验 ----------
VERIFY_JSON='{"skipped":true}'
if [ "$DO_VERIFY" -eq 1 ]; then
  echo "=== [5/6] 部署后 HTTP 校验 ==="
  code_page="$(curl -sS --max-time 25 -o /tmp/wp_page_check.$$ -w '%{http_code}' "$URL_PAGE" || echo 000)"
  body_page="$(grep -c -- "$MARKER" /tmp/wp_page_check.$$ 2>/dev/null || true)"
  has_marker=0; [ "${body_page:-0}" -gt 0 ] && has_marker=1
  code_index="$(curl -sS --max-time 25 -o /tmp/wp_index_check.$$ -w '%{http_code}' "$URL_INDEX" || echo 000)"
  link_ok=0; grep -q "href=\"$SLUG.html\"" /tmp/wp_index_check.$$ 2>/dev/null && link_ok=1
  count_live="$(grep -oE '共 ?[0-9]+ ?份白皮书' /tmp/wp_index_check.$$ 2>/dev/null | head -1 || echo '')"
  rm -f /tmp/wp_page_check.$$ /tmp/wp_index_check.$$
  echo "    页面 $URL_PAGE -> HTTP $code_page, marker命中=$has_marker"
  echo "    索引 $URL_INDEX -> HTTP $code_index, 新链接=$link_ok, $count_live"
  VERIFY_JSON="{\"page\":\"$URL_PAGE\",\"page_http\":$code_page,\"marker\":\"$MARKER\",\"marker_found\":$has_marker,\"index\":\"$URL_INDEX\",\"index_http\":$code_index,\"link_found\":$link_ok,\"count_label\":\"$count_live\"}"
  if [ "${code_page:-0}" != "200" ] || [ "$has_marker" -ne 1 ] || { [ "$DO_INDEX" -eq 1 ] && [ "$link_ok" -ne 1 ]; }; then
    echo "!! 部署后校验未通过。未自动回滚（回滚属高危动作，需人工确认）" >&2
    if [ "$DO_INDEX" -eq 1 ]; then
      BK="$(printf '%s' "$INDEX_RESULT" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("backup") or "")' 2>/dev/null || true)"
      [ -n "$BK" ] && echo "   回滚索引: ssh $HOST \"cp -f '$BK' '$R_INDEX'\"" >&2
    fi
    echo "   移除页面: ssh $HOST \"rm -f '$R_PAGE'\"" >&2
    die "部署后校验未通过" 5
  fi
else
  echo "=== [5/6] 跳过 HTTP 校验（--no-verify） ==="
fi

# ---------- 6. 回执落盘 ----------
echo "=== [6/6] 回执落盘 ==="
mkdir -p "$RECEIPT_DIR"
RECEIPT="$RECEIPT_DIR/WHITEPAPER-DEPLOY-$TS.json"
export WP_RECEIPT="$RECEIPT" WP_TS="$TS" WP_SLUG="$SLUG" WP_TITLE="$TITLE" \
  WP_SRC="$SRC" WP_SRC_SHA="$SRC_SHA" WP_HOST="$HOST" WP_PAGE="$R_PAGE" \
  WP_INDEX="$R_INDEX" WP_INDEX_RESULT="$INDEX_RESULT" WP_VERIFY="$VERIFY_JSON" \
  WP_BASE="$BASE_URL" WP_URL_PAGE="$URL_PAGE" WP_OWNER="$OWNER"
python3 - <<'PY'
import json, os
r = {
  "receipt": "WHITEPAPER-DEPLOY",
  "ts_utc": os.environ["WP_TS"],
  "slug": os.environ["WP_SLUG"],
  "title": os.environ["WP_TITLE"],
  "local_src": os.environ["WP_SRC"],
  "local_sha256": os.environ["WP_SRC_SHA"],
  "host": os.environ["WP_HOST"],
  "remote_page": os.environ["WP_PAGE"],
  "remote_index": os.environ["WP_INDEX"],
  "owner": os.environ["WP_OWNER"],
  "base_url": os.environ["WP_BASE"],
  "url_page": os.environ["WP_URL_PAGE"],
  "index_result": json.loads(os.environ["WP_INDEX_RESULT"]),
  "verify": json.loads(os.environ["WP_VERIFY"]),
  "status": "deployed",
  "provenance": "measured",
}
with open(os.environ["WP_RECEIPT"], "w", encoding="utf-8") as f:
    json.dump(r, f, ensure_ascii=False, indent=2)
print("回执:", os.environ["WP_RECEIPT"])
PY
echo "=== 部署完成 ==="
