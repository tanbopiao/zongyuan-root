#!/bin/bash
# SYSTEM-STATE 统一状态总线采集器（本地执行面）
# W-02 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
ROOT=/home/user/ZONGYUAN-ROOT
OUT=$ROOT/var/SYSTEM-STATE.json
TS=$(date +%s)
KP=$(pgrep -f "[k]ernel/main.py" | head -1 | awk "{print \$1}")
[ -z "$KP" ] && KP=0
WP=$(pgrep -f "[w]orker_daemon.sh worker-kernel-001" | head -1 | awk "{print \$1}")
[ -z "$WP" ] && WP=0
LED=$(wc -l < $ROOT/HASH-LEDGER.csv 2>/dev/null || echo 0)
CRON=$(crontab -l 2>/dev/null | grep -v '^#' | grep -c . || true)
PORTS=$(ss -tlnp 2>/dev/null | grep -oE ':(8081|8082|8092|8766|9120)\b' | sort -u | tr '\n' ' ')
python3 - "$TS" "$KP" "$WP" "$LED" "$CRON" "$PORTS" "$OUT" << 'PY'
import json, sys
ts, kp, wp, led, cr, ports, out = sys.argv[1:]
st = {
  "node": "ZR-SANDBOX", "role": "local-exec",
  "ts": ts, "kernel_pid": int(kp), "worker_pid": int(wp),
  "hash_ledger_rows": int(led), "cron_tasks": int(cr),
  "ports": [p for p in ports.split()],
  "health": "ok" if int(kp) > 0 and int(wp) > 0 else "degraded",
  "trace": "Ω₀⊂⊙∞⊂Ω", "did": "DID-BR-000002"
}
json.dump(st, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("SYSTEM-STATE:", out, "| health:", st["health"])
PY
