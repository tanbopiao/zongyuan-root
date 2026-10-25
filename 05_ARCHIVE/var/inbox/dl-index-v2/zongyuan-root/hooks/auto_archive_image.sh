#!/usr/bin/env bash
# =====================================================================
# ZONGYUAN-ROOT AUTO-ARCHIVE V2.0 — 图片全自动归档脚本（代码执行态）
# 用法：auto_archive_image.sh <asset_id> <temp_url> <title> <prompt> <ratio> <tags> <did> <out_dir> <local_name> <local_url> <cloud_url>
# 约束：append_only；禁止覆写旧文件；失败重试由总入口负责；网关失败不阻塞
# =====================================================================
set -uo pipefail

ASSET_ID="$1"; TEMP_URL="$2"; TITLE="$3"; PROMPT="$4"; RATIO="$5"; TAGS="$6"; DID="$7"
OUT_DIR="$8"; LOCAL_NAME="$9"; LOCAL_URL="${10}"; CLOUD_URL="${11}"

ROOT="/home/user/ZONGYUAN-ROOT"
META_DIR="$ROOT/meta"
INDEX_FILE="$META_DIR/auto-asset-index.json"
URL_MAP="$META_DIR/auto-url-mapping.json"
LEDGER="$ROOT/HASH-LEDGER.csv"
DID_EXPECT="DID-BR-000002"

# ---- 0. 参数白名单校验（防注入） ----
case "$ASSET_ID" in
  AUTO-IMG-[0-9][0-9][0-9][0-9][0-9]) ;;
  *) echo '{"result":"failed","reason":"bad_asset_id"}' >&2; exit 2 ;;
esac
[ "$DID" = "$DID_EXPECT" ] || { echo '{"result":"failed","reason":"bad_did"}' >&2; exit 2; }
mkdir -p "$OUT_DIR"
DEST="$OUT_DIR/$LOCAL_NAME"

# ---- 1. append_only 锁：目标文件已存在则拒绝覆写 ----
if [ -e "$DEST" ]; then
  echo "{\"result\":\"failed\",\"reason\":\"append_only_reject_existing\",\"asset_id\":\"$ASSET_ID\"}" >&2
  exit 2
fi

# ---- 2. 二进制流直落磁盘（不产生中间碎片） ----
curl -fL -sS --connect-timeout 30 --max-time 900 -o "$DEST" "$TEMP_URL" || { rm -f "$DEST"; echo '{"result":"failed","reason":"download_error"}' >&2; exit 1; }

# ---- 3. 完整性校验：0 字节 / 文件类型 ----
if [ ! -s "$DEST" ]; then
  rm -f "$DEST"; echo '{"result":"failed","reason":"zero_byte_file"}' >&2; exit 1
fi
if ! file "$DEST" | grep -qi 'image'; then
  rm -f "$DEST"; echo '{"result":"failed","reason":"not_image_file"}' >&2; exit 1
fi

# ---- 4. SHA-256 指纹 ----
SHA=$(sha256sum "$DEST" | awk '{print $1}')
BYTES=$(stat -c %s "$DEST")

TS=$(python3 -c "import time;print(time.strftime('%Y-%m-%dT%H:%M:%S%z'))")
TAG_JSON=$(python3 - "$TAGS" <<'PYEOF'
import json, sys
raw = sys.argv[1]
tags = [t for t in raw.split('|') if t]
print(json.dumps(tags, ensure_ascii=False))
PYEOF
)

# ---- 5. 元数据追加写入（index / url-mapping / HASH-LEDGER，历史行不改） ----
python3 - "$INDEX_FILE" "$URL_MAP" "$ASSET_ID" "$TITLE" "$PROMPT" "$RATIO" "$TAG_JSON" "$TEMP_URL" "$LOCAL_URL" "$CLOUD_URL" "$SHA" "$TS" "$DID" <<'PYEOF'
import json, sys
idx_path, url_path, aid, title, prompt, ratio, tag_json, temp_url, local_url, cloud_url, sha, ts, did = sys.argv[1:14]
tags = json.loads(tag_json)
record = {
  "asset_id": aid, "asset_kind": "image", "asset_title": title,
  "prompt": prompt, "ratio": ratio, "tag": tags,
  "session_temp_url": temp_url, "local_instance_url": local_url,
  "cloud_gallery_url": cloud_url, "sha256": sha,
  "create_timestamp": ts, "status": "pending_sync", "DID": did
}
for path in (idx_path, url_path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list): data = []
    except Exception:
        data = []
    data.append(record)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
print(f"asset_index_rows={len(data)}")
PYEOF

echo "$ASSET_ID,image,$TITLE,$SHA,$BYTES,$TS,pending_sync" >> "$LEDGER"

# ---- 6. 同源协议上报真值网关（X-DID 单头 + key/value 信封；失败不阻塞，写失败日志） ----
GATEWAY="https://www.huodouai.com/api/report/truth"
REPORT=$(curl -sS -m 20 -w "|%{http_code}" -X POST "$GATEWAY" \
    -H "X-DID: $DID" -H "Content-Type: application/json" \
    --data-binary "$(python3 -c "
import json,sys,time
aid, kind, sha, did = sys.argv[1:5]
print(json.dumps({'key': 'asset_archive_'+aid+'_'+str(int(time.time())),
                  'value': {'event':'asset_archive','asset_id': aid,'asset_kind': kind,
                            'sha256': sha,'status':'pending_sync','DID': did}}, ensure_ascii=False))
" "$ASSET_ID" "image" "$SHA" "$DID")" 2>/dev/null || true)
case "$REPORT" in
  *"|200"|*"|201"|*"|202") GW_STATUS="ok" ;;
  *) GW_STATUS="failed_$REPORT" ;;
esac
if [ "$GW_STATUS" != "ok" ]; then
  python3 - "$META_DIR/auto-failed-task-log.json" "$ASSET_ID" "$TEMP_URL" "gateway_report_failed" <<'PYEOF'
import json, sys, time
log_path, aid, url, reason = sys.argv[1:5]
try:
    with open(log_path, encoding="utf-8") as f: data = json.load(f)
    if not isinstance(data, list): data = []
except Exception: data = []
data.append({"asset_id": aid, "session_temp_url": url, "reason": reason,
             "record_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "status": "gateway_failed"})
with open(log_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
PYEOF
fi

# ---- 7. 异步 rsync 推云端（不阻塞本流程） ----
nohup bash "$ROOT/hooks/auto_rsync_sync.sh" "$ASSET_ID" "image" >/dev/null 2>&1 &

echo "{\"result\":\"success\",\"asset_id\":\"$ASSET_ID\",\"sha256\":\"$SHA\",\"bytes\":$BYTES,\"local_url\":\"$LOCAL_URL\",\"cloud_url\":\"$CLOUD_URL\",\"gateway\":\"$GW_STATUS\",\"status\":\"pending_sync\",\"DID\":\"$DID\"}"
