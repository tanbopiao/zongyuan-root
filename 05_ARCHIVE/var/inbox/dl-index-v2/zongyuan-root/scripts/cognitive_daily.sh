#!/bin/bash
# 脑内核每日认知反思（每日 06:00 · 直连豆包Ark 180s超时）
# 链路：状态摘要 → 豆包Ark建议 → 落盘 → 审计 → 网关摘要上报（X-DID）
ZK="/home/user/Doubao/chats/38412149511142658/zongyuan-kernel"
ZR="/home/user/ZONGYUAN-ROOT"
DID="DID-BR-000002"
TS=$(date +%Y%m%d-%H%M%S)
mkdir -p "$ZK/var/reports"

AUDIT_CNT=$(wc -l < "$ZK/var/audit/audit.jsonl" 2>/dev/null || echo 0)

RESULT=$(python3 - "$ZK" "$TS" << 'PYEOF'
import json, sys, os, base64, hashlib, urllib.request
from pathlib import Path
zk, ts = sys.argv[1], sys.argv[2]
kek = os.environ.get("ZR_API_ENC_KEY") or Path("/home/user/ZONGYUAN-ROOT/var/kek.env").read_text().strip()
slot = json.load(open(f"{zk}/var/state/ark-key.enc.json"))
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
k = hashlib.sha256(kek.encode()).digest()
key = AESGCM(k).decrypt(base64.b64decode(slot["iv_b64"]), base64.b64decode(slot["ciphertext_b64"]), slot["aad"].encode()).decode()
body = {"model": "ep-20260925170233-g4f7w",
        "messages": [{"role": "system", "content": "你是ZONGYUAN自治内核的认知顾问，只输出简短可执行建议，不解释。"},
                     {"role": "user", "content": "请给出今日3条低风险自治优化建议，每条不超过40字，JSON数组格式"}],
        "max_tokens": 600}
req = urllib.request.Request("https://ark.cn-beijing.volces.com/api/v3/chat/completions",
    data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=180) as resp:
        d = json.loads(resp.read())
    content = d["choices"][0]["message"]["content"]
    print(json.dumps({"verdict": "ok", "provider": "ark", "ts": ts, "advice_text": content[:1200]}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({"verdict": "fail", "provider": "ark", "reason": str(e)[:200]}, ensure_ascii=False))
PYEOF
)
echo "$RESULT" > "$ZK/var/reports/认知建议-$TS.json"
VERDICT=$(echo "$RESULT" | python3 -c "import json,sys;print(json.load(sys.stdin)['verdict'])" 2>/dev/null || echo fail)
ADVICE=$(echo "$RESULT" | python3 -c "import json,sys;print(json.load(sys.stdin).get('advice_text','')[:80])" 2>/dev/null || echo "")

python3 - "$ZK" "$TS" "$AUDIT_CNT" "$VERDICT" << 'PYEOF'
import json, time, sys
zk, ts, cnt, v = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": "kernel.cognitive", "actor": "scheduler",
       "action": "daily-reflect", "result": "ok" if v == "ok" else "warn",
       "detail": f"每日认知反思落盘 var/reports/认知建议-{ts}.json (audit={cnt}, verdict={v})"}
with open(f"{zk}/var/audit/audit.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
PYEOF

curl -sS -m 15 -X POST "https://www.huodouai.com/api/report/truth" \
  -H "X-DID: $DID" -H "Content-Type: application/json" \
  -d "{\"key\":\"cognitive_daily_$(date +%s)\",\"value\":{\"event\":\"cognitive.daily_reflect\",\"verdict\":\"$VERDICT\",\"advice\":\"$ADVICE\",\"audit\":$AUDIT_CNT,\"ts\":$(date +%s)}}" >/dev/null 2>&1 || true
echo "认知反思: $TS verdict=$VERDICT"
if [ -n "$ADVICE" ]; then echo "建议摘要: $ADVICE"; fi
