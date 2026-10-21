#!/bin/bash
# atomcode_auto_renew.sh — AtomCode CodingPlan Lite 自动续领机制
# ZONGYUAN-ROOT · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
# 语义: atomcode login 幂等非交互续领(已实测 2026-10-21); 到期前后自动触发并观测到期日推进
set -uo pipefail

LOG=/var/log/atomcode_renew.log
STATE=/var/lib/atomcode_renew/state.json
LOCK=/tmp/atomcode_renew.lock
GW="https://www.huodouai.com/api/report/truth"
DID="DID-BR-000002"
mkdir -p /var/lib/atomcode_renew

exec 9>"$LOCK"
flock -n 9 || { echo "$(date '+%F %T') SKIP already-running" >>"$LOG"; exit 0; }

ts() { date '+%F %T'; }
say() { echo "$(ts) $*" >>"$LOG"; }

say "=== renew probe start ==="

# 1. 非交互续领(login 即 /login 命令的 CLI 等价)
# 注: login 续领后会拉起 TUI, 非 TTY 下 rc=1 —— 成功判定以输出含 Plan: 为准
OUT=$(timeout 40 atomcode login </dev/null 2>&1 | tr -d '\r')

# 2. 解析 Plan/Usage
PLAN_LINE=$(echo "$OUT" | grep -E 'Plan:' | head -1 | sed 's/^ *//')
USAGE_LINE=$(echo "$OUT" | grep -E 'Usage:' | head -1 | sed 's/^ *//')

if [ -z "$PLAN_LINE" ]; then
  say "FAIL renew-output-missing-Plan (rc非判定依据, TUI模式rc=1属正常)"
  echo "$OUT" | tail -3 >>"$LOG"
  curl -s --max-time 15 -X POST "$GW" -H "X-DID: $DID" -H 'Content-Type: application/json' \
    -d "{\"key\":\"ALERT.ATOMCODE.RENEW.FAIL.2026\",\"value\":{\"reason\":\"plan_line_missing\",\"ts\":\"$(ts)\"}}" \
    >/dev/null 2>&1 || true
  exit 1
fi
EXPIRES=$(echo "$PLAN_LINE" | grep -oE 'expires [0-9]{4}-[0-9]{2}-[0-9]{2}' | awk '{print $2}')
REMAIN_D=$(echo "$PLAN_LINE" | grep -oE '\(([0-9]+)d /' | tr -d '(d /' )

say "OK plan=[$PLAN_LINE]"
say "OK usage=[$USAGE_LINE] expires=$EXPIRES remain=${REMAIN_D:-?}d"

# 3. 状态推进判定: 到期日较上次记录后移 = 续领生效
PREV=$(python3 -c "import json,sys;print(json.load(open('$STATE')).get('expires',''))" 2>/dev/null || echo "")
if [ -n "$EXPIRES" ] && [ "$EXPIRES" != "$PREV" ]; then
  if [ -n "$PREV" ]; then
    say "RENEWED prev=$PREV new=$EXPIRES (续领生效, 到期日推进)"
    curl -s --max-time 15 -X POST "$GW" -H "X-DID: $DID" -H 'Content-Type: application/json' \
      -d "{\"key\":\"ATOMCODE.PLAN.RENEWED.2026\",\"value\":{\"prev\":\"$PREV\",\"new\":\"$EXPIRES\",\"ts\":\"$(ts)\"}}" \
      >/dev/null 2>&1 || true
  else
    say "BASELINE expires=$EXPIRES"
  fi
fi

# 4. 临期告警(剩余<=1天且续领未推进到期日)
if [ -n "${REMAIN_D:-}" ] && [ "$REMAIN_D" -le 1 ] 2>/dev/null; then
  say "WARN expiring soon remain=${REMAIN_D}d"
  curl -s --max-time 15 -X POST "$GW" -H "X-DID: $DID" -H 'Content-Type: application/json' \
    -d "{\"key\":\"ALERT.ATOMCODE.EXPIRING.2026\",\"value\":{\"expires\":\"$EXPIRES\",\"remain_d\":$REMAIN_D,\"ts\":\"$(ts)\"}}" \
    >/dev/null 2>&1 || true
fi

# 5. 固化状态
python3 - <<PYEOF
import json, time
json.dump({"expires":"$EXPIRES","plan":"$PLAN_LINE","usage":"$USAGE_LINE",
           "updated": time.strftime('%Y-%m-%dT%H:%M:%S+08:00', time.localtime())},
          open("$STATE","w"), ensure_ascii=False, indent=2)
PYEOF

say "=== renew probe done ==="
exit 0
