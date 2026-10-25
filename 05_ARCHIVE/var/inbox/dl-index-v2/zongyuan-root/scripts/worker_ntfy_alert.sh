#!/bin/bash
# ZONGYUAN-ROOT worker ntfy 告警指令（锚定中枢智能记忆网关）
# 用法：worker_ntfy_alert.sh <事件名> <消息>
# 1) ntfy 推送（主题含 DID 锚定，防撞车） 2) 同步写入中枢记忆网关（X-DID 单头）——锚定 www.huodouai.com
# fail-closed：ntfy/网关不可达不阻塞主流程；消息不明文密钥
set -uo pipefail
ROOT="/home/user/ZONGYUAN-ROOT"
DID="DID-BR-000002"
EVENT="${1:-unknown}"
MSG="${2:-无详情}"
NTFY_SERVER="${NTFY_SERVER:-https://ntfy.sh}"
NTFY_TOPIC="${NTFY_TOPIC:-zr-node-dc2e51c0-ntfy-2026}"
GW="https://www.huodouai.com/api/report/truth"
TS=$(date +%s)

# 防泄漏：消息中若含密钥形如 ak-/KEK 特征，一律打码
MSG=$(echo "$MSG" | sed -E 's/(ak-[A-Za-z0-9]{6})[A-Za-z0-9]*/\1****/g; s/[0-9a-f]{64}/[REDACTED]/g')

# ---- 1) ntfy 推送（锚定标签：DID + 事件 + 节点）----
curl -sS -m 10 -o /dev/null -w "%{http_code}" \
  -H "Title: ZONGYUAN-ROOT ${EVENT}" \
  -H "Tags: zr" \
  -H "Priority: default" \
  -d "${MSG} ｜ DID:${DID} ｜ ${TS}" \
  "$NTFY_SERVER/$NTFY_TOPIC" >> "$ROOT/logs/ntfy_alert.log" 2>&1 || true

# ---- 2) 锚定中枢智能记忆网关（同源协议 X-DID 单头，告警留痕中枢记忆）----
python3 - "$EVENT" "$MSG" "$TS" <<'EOF'
import json, subprocess, sys
event, msg, ts = sys.argv[1:4]
GW = "https://www.huodouai.com/api/report/truth"
payload = {"key": f"worker_ntfy_{event}_{ts}",
           "value": {"event":"worker_ntfy_alert","alert_type":event,"msg":msg[:200],
                     "node":"NODE-DEV-DOUBAO-WORK-001","did":"DID-BR-000002",
                     "ts":int(ts),"anchor":"Ω₀⊂⊙∞⊂Ω"}}
p = subprocess.run(["curl","-sS","-m","15","-X","POST",GW,"-H","X-DID: DID-BR-000002",
                    "-H","Content-Type: application/json","--data-binary",json.dumps(payload,ensure_ascii=False)],capture_output=True,text=True)
resp = p.stdout or p.stderr
print(f"[ntfy] {event} 推送+记忆网关: {'ok' if '真值写入成功' in resp else 'fail'}")
EOF
exit 0
