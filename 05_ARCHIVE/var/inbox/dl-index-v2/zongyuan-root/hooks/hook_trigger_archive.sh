#!/usr/bin/env bash
# =====================================================================
# ZONGYUAN-ROOT AUTO-ARCHIVE V2.0 — 总入口调度脚本（任务入队 → 分发）
# 确权标识：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
# 用法：hook_trigger_worker.sh '<PAYLOAD_JSON>'
# 约束：只解析并分发，不做磁盘 IO；append_only；超时1200s自动回收；失败重试3次
# =====================================================================
set -uo pipefail

ROOT="/home/user/ZONGYUAN-ROOT"
META_DIR="$ROOT/meta"
HOOKS_DIR="$ROOT/hooks"
INDEX_FILE="$META_DIR/auto-asset-index.json"
FAILED_LOG="$META_DIR/auto-failed-task-log.json"
LEDGER="$ROOT/HASH-LEDGER.csv"
DID_EXPECT="DID-BR-000002"
DEFAULT_TIMEOUT=1200
MAX_RETRY=3

PAYLOAD="${1:-}"
if [ -z "$PAYLOAD" ]; then
  echo '{"result":"failed","reason":"empty_payload"}' >&2
  exit 2
fi

# ---- 1. 校验载荷为合法 JSON 并提取字段 ----
eval "$(python3 - "$PAYLOAD" <<'PYEOF'
import json, sys
raw = sys.argv[1]
try:
    d = json.loads(raw)
except Exception as e:
    print(f'JSON_INVALID=1 REASON={str(e)!r}'); sys.exit(0)
def get(k, default=''):
    v = d.get(k, default)
    if isinstance(v, list):
        return '|'.join(str(x) for x in v)
    return str(v)
print(f'JSON_INVALID=0')
print(f"TASK_TYPE={get('task_type')!r}")
print(f"ASSET_KIND={get('asset_kind')!r}")
print(f"TEMP_URL={get('session_temp_url')!r}")
print(f"ASSET_TITLE={get('asset_title')!r}")
print(f"PROMPT={get('prompt')!r}")
print(f"RATIO={get('resolution_ratio')!r}")
print(f"TAGS={get('tag_list')!r}")
print(f"PRIORITY={get('priority','P0')!r}")
print(f"TIMEOUT={get('timeout_sec', '1200')!r}")
print(f"DID={get('DID')!r}")
PYEOF
)"

if [ "${JSON_INVALID:-0}" = "1" ]; then
  echo '{"result":"failed","reason":"invalid_json"}' >&2
  exit 2
fi

# ---- 2. 协议校验 ----
[ "$TASK_TYPE" = "auto_archive_asset" ] || { echo '{"result":"failed","reason":"bad_task_type"}' >&2; exit 3; }
[ "$DID" = "$DID_EXPECT" ] || { echo '{"result":"failed","reason":"bad_did"}' >&2; exit 3; }
case "$ASSET_KIND" in
  image|video) ;;
  *) echo '{"result":"failed","reason":"bad_asset_kind"}' >&2; exit 3 ;;
esac
if [ -z "$TEMP_URL" ]; then
  echo '{"result":"failed","reason":"empty_temp_url"}' >&2; exit 3
fi

# ---- 3. 生成全局唯一资产 ID（自增，append-only） ----
ASSET_ID=$(python3 - "$ASSET_KIND" "$INDEX_FILE" <<'PYEOF'
import json, os, sys
kind = sys.argv[1]        # image | video
idx_path = sys.argv[2]
prefix = "AUTO-IMG" if kind == "image" else "AUTO-VID"
seq = 0
try:
    with open(idx_path, encoding="utf-8") as f:
        data = json.load(f)
    seq = len(data) if isinstance(data, list) else 0
except Exception:
    seq = 0
print(f"{prefix}-{seq + 1:05d}")
PYEOF
)

LOCAL_NAME="$ASSET_ID.webp"; [ "$ASSET_KIND" = "video" ] && LOCAL_NAME="$ASSET_ID.mp4"
OUT_DIR="$ROOT/asset/$ASSET_KIND/kunlun-auto-out"
LOCAL_URL="http://127.0.0.1:9120/assets/kunlun-auto-out/$LOCAL_NAME"
CLOUD_URL="https://gallery.huodouai.com/kunlun-auto-out/$LOCAL_NAME"

# ---- 4. 校验并渲染任务参数，分发到对应归档脚本（timeout 回收 + 重试3次） ----
TIMEVAL="${TIMEOUT:-$DEFAULT_TIMEOUT}"
case "$TIMEVAL" in
  ''|*[!0-9]*) TIMEVAL=$DEFAULT_TIMEOUT ;;
esac
[ "$TIMEVAL" -gt 1200 ] && TIMEVAL=1200

ARCHIVER="$HOOKS_DIR/auto_archive_image.sh"
[ "$ASSET_KIND" = "video" ] && ARCHIVER="$HOOKS_DIR/auto_archive_video.sh"

rc=1
attempt=1
while [ "$attempt" -le "$MAX_RETRY" ]; do
  timeout "$TIMEVAL" bash "$ARCHIVER" \
      "$ASSET_ID" "$TEMP_URL" "$ASSET_TITLE" "$PROMPT" "$RATIO" "$TAGS" "$DID" \
      "$OUT_DIR" "$LOCAL_NAME" "$LOCAL_URL" "$CLOUD_URL"
  rc=$?
  if [ "$rc" -eq 0 ]; then
    break
  fi
  reason="download_or_verify_failed"
  [ "$rc" -eq 124 ] && reason="timeout_${TIMEVAL}s"
  echo "[hook] attempt=$attempt rc=$rc reason=$reason asset_id=$ASSET_ID" >&2
  attempt=$((attempt + 1))
done

# ---- 5. 失败/超时记录（append-only） ----
if [ "$rc" -ne 0 ]; then
  python3 - "$FAILED_LOG" "$ASSET_ID" "$ASSET_KIND" "$TEMP_URL" "$ASSET_TITLE" "$reason" "$DID" <<'PYEOF'
import json, os, sys, time
log_path, aid, kind, url, title, reason, did = sys.argv[1:8]
entry = {
  "asset_id": aid, "asset_kind": kind, "session_temp_url": url,
  "asset_title": title, "reason": reason,
  "attempts": 3, "record_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
  "status": "failed", "DID": did
}
try:
    with open(log_path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list): data = []
except Exception:
    data = []
data.append(entry)
with open(log_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
PYEOF
  echo "{\"result\":\"failed\",\"asset_id\":\"$ASSET_ID\",\"reason\":\"$reason\",\"status\":\"failed\"}"
  exit 1
fi

echo "{\"result\":\"success\",\"asset_id\":\"$ASSET_ID\",\"asset_kind\":\"$ASSET_KIND\",\"local_url\":\"$LOCAL_URL\",\"cloud_url\":\"$CLOUD_URL\",\"status\":\"pending_sync\",\"DID\":\"$DID\"}"
