#!/bin/bash
# ZONGYUAN-ROOT worker 云端 API 全自动调用脚本
# 同源协议：密钥 AES-GCM 加密存储（meta/worker-api-key.enc.json），KEK 经环境变量 ZR_API_ENC_KEY 注入（不落盘）
# 全自动：解密 → 调用 → 3 次重试 → 审计留痕；失败不阻塞
# 用法：worker_api_call.sh [payload_key] [api_url]
#   默认目标：真值网关（POST 上报）；请求头 X-Api-Key: <ak-*>
set -uo pipefail
ROOT="/home/user/ZONGYUAN-ROOT"
DID="DID-BR-000002"
ENC_FILE="$ROOT/meta/worker-api-key.enc.json"
GW="${2:-https://www.huodouai.com/api/report/truth}"
KEY="${1:-worker_api_auto_$(date +%s)}"
AUDIT="$ROOT/var/audit/worker-api-calls.jsonl"
mkdir -p "$(dirname "$AUDIT")"

# ---- 1) 解密 API 密钥（KEK 来源：环境变量 ZR_API_ENC_KEY 优先；否则受限文件 var/kek.env（600），零明文进 cron/账本）----
if [ -z "${ZR_API_ENC_KEY:-}" ] && [ -f "$ROOT/var/kek.env" ]; then
  export ZR_API_ENC_KEY="$(cat "$ROOT/var/kek.env" 2>/dev/null || true)"
fi
if [ -z "${ZR_API_ENC_KEY:-}" ]; then
  echo "API_CALL_BLOCK: KEK 未注入（环境变量 ZR_API_ENC_KEY 缺失且受限文件 var/kek.env 不可用）"
  exit 2
fi
AK=$(python3 - "$ENC_FILE" "$ZR_API_ENC_KEY" <<'PYEOF'
import json, sys, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
rec = json.load(open(sys.argv[1], encoding='utf-8'))
key = bytes.fromhex(sys.argv[2])
iv = base64.b64decode(rec["iv_b64"]); ct = base64.b64decode(rec["ciphertext_b64"])
print(AESGCM(key).decrypt(iv, ct, rec["aad"].encode()).decode())
PYEOF
)
[ -z "$AK" ] && { echo "API_CALL_BLOCK: 解密失败（KEK 错误或载体损坏）"; exit 3; }

# ---- 2) 全自动调用（3 次重试，失败不阻塞主流程）----
TS=$(date +%s)
payload=$(python3 -c "import json;print(json.dumps({'key':'$KEY','value':{'event':'worker_api_call','did':'$DID','ts':$TS}}))")
RESP=""; RET=1
for i in 1 2 3; do
  RESP=$(curl -sS -m 15 -X POST "$GW" \
    -H "X-DID: $DID" -H "X-Api-Key: $AK" -H "Content-Type: application/json" \
    --data-binary "$payload" 2>/dev/null || true)
  echo "$RESP" | grep -q "真值写入成功" && { RET=0; break; }
  sleep 2
done

# ---- 3) 审计留痕（只记指纹与结果，不记密钥明文）----
python3 - "$RET" "$KEY" "$TS" <<'PYEOF'
import json, sys, time
ret, key, ts = sys.argv[1], sys.argv[2], sys.argv[3]
rec = {"ts": time.strftime('%Y-%m-%dT%H:%M:%S%z'), "key": key, "status": "ok" if ret == "0" else "fail",
       "retries": 3 if ret != "0" else 0, "event": "worker_api_call"}
with open("/home/user/ZONGYUAN-ROOT/var/audit/worker-api-calls.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(f"[api_call] {'ok' if ret=='0' else 'fail'} key={key}")
PYEOF
exit $RET
