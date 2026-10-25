#!/bin/bash
# =====================================================================
# ZONGYUAN 周期运行态巡检留证 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# 用法: 由 cron 每 30 分钟触发（*/30 * * * *）
# 逻辑: 服务状态探测 + 平台环境快照 → var/patrol/patrol-<ts>.json
#       异常(内核/服务down)时自动全屏截图留证（存 var/evidence/）
# 输出: 摘要 JSON（444 只读）+ 异常审计追加
# =====================================================================
set -uo pipefail
ZR="/home/user/ZONGYUAN-ROOT"
DID="DID-BR-000002"
TS=$(date +%Y%m%d-%H%M%S)
DIR="$ZR/var/patrol"
mkdir -p "$DIR"

# 1) 服务状态探测
KERNEL=$(pgrep -f "kernel/main.py" | wc -l)
WORKER=$(pgrep -f "worker" | wc -l)
CRON=$(pgrep -x cron | wc -l)
SS_8081=$(ss -tln 2>/dev/null | grep -c ":8081 ")
SS_8091=$(ss -tln 2>/dev/null | grep -c ":8091 ")
SITE_CODE=$(curl -s -m 10 -o /dev/null -w "%{http_code}" "https://www.huodouai.com" 2>/dev/null)

# 2) 平台环境快照（摘要）
ENV_SNAP=$(python3 "$ZR/scripts/sandbox_mcp.py" sandbox_get_context '{}' 2>/dev/null | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('output','')[:600])" 2>/dev/null)

# 3) 异常判定（以端口+主站为硬基准：8081/8091 缺失 或 主站非200；进程数仅记录不判异常，避免进程名差异致永久误报）
ABNORMAL=0
if [ "$SS_8081" -lt 1 ] || [ "$SS_8091" -lt 1 ] || [ "$SITE_CODE" != "200" ]; then
  ABNORMAL=1
  python3 "$ZR/scripts/sandbox_mcp.py" browser_gui_screenshot '{}' >/dev/null 2>&1   # 异常留证截图
fi

# 4) 写摘要
python3 - "$DIR" "$TS" "$KERNEL" "$WORKER" "$CRON" "$SS_8081" "$SS_8091" "$SITE_CODE" "$ABNORMAL" "$ENV_SNAP" "$DID" << 'PY'
import json, os, sys, time
d, ts, k, w, cr, s1, s2, site, ab, env, did = sys.argv[1:12]
rec = {
  "did": did, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
  "status": {
    "kernel": int(k), "worker": int(w), "cron": int(cr),
    "port8081": int(s1), "port8091": int(s2), "site_http": site,
    "abnormal": int(ab)
  },
  "env_snapshot": env,
}
fp = os.path.join(d, f"patrol-{ts}.json")
with open(fp, "w", encoding="utf-8") as f:
    json.dump(rec, f, ensure_ascii=False, indent=2)
os.chmod(fp, 0o444)
print(f"[{time.strftime('%H:%M:%S')}] patrol {'ABNORMAL' if int(ab) else 'OK'} kernel={k} 8081={s1} 8091={s2} site={site} -> {fp}")
PY

# 5) 异常审计留痕
if [ "$ABNORMAL" = "1" ]; then
  python3 - "$ZR" "$TS" << 'PY'
import json, os, sys, time
zr, ts = sys.argv[1:3]
audit = os.path.join(zr, "var", "patrol", "patrol-abnormal.log")
rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": "kernel.truth", "actor": "patrol",
       "action": "patrol-abnormal", "result": "warn", "detail": f"巡检异常 {ts}（内核/端口/主站）已截图留证"}
with open(audit, "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
PY
fi
exit 0
