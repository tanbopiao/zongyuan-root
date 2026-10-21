#!/bin/bash
# 魔搭数据湖 backup 幂等续传守护（SKIP cached 已传文件）
ZR=/home/user/ZONGYUAN-ROOT
LOG=$ZR/var/archive/upload-backup.log
TOKEN=$(grep "^MODELSCOPE_KEY=" $ZR/var/secrets/api_keys.env | cut -d= -f2-)
export MODELSCOPE_API_TOKEN="$TOKEN"
while :; do
  if grep -q "\[OK\] backup 全量" "$LOG" 2>/dev/null; then echo "DONE"; break; fi
  if ! pgrep -f "upload_folder" >/dev/null 2>&1; then
    echo "[resume] $(date +%H:%M:%S) 重启续传..."
    python3 - <<'PYEOF' >> "$LOG" 2>&1
import os, time
TOKEN = os.environ["MODELSCOPE_API_TOKEN"]
from modelscope.hub.api import HubApi
api = HubApi(token=TOKEN)
REPO="zongyuanroot/ZONGYUAN-SHARED-DATALAKE"
t0=time.time()
try:
    r=api.upload_folder(repo_id=REPO, folder_path="/home/user/ZONGYUAN-ROOT/backup", path_in_repo="zongyuan-root/backup", allow_patterns=["*"], ignore_patterns=[".git/*","*.pem","active_token.env","kek.env","api_keys.env"])
    print(f"[OK] backup 全量 | {time.time()-t0:.0f}s | {str(r)[:80]}")
except Exception as e:
    print(f"[ERR] backup | {str(e)[:200]}")
PYEOF
  fi
  sleep 90
done
