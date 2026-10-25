#!/bin/bash
# ZONGYUAN-ROOT 动态 IP 自动管理脚本（检测 → 记录 → 变化上报 → 保持连接）
# 多源回显检测公网 IP；与上次记录比对；变化时上报真值网关（X-DID 单头）
# 落盘：var/network/ip-state.json（当前 IP / 上次变更 / 历史）
set -uo pipefail
ROOT="/home/user/ZONGYUAN-ROOT"
NET="$ROOT/var/network"
mkdir -p "$NET"
DID="DID-BR-000002"
GW="https://www.huodouai.com/api/report/truth"
STATE="$NET/ip-state.json"
LOG="$ROOT/logs/dyn_ip.log"

# ---- 1) 多源检测公网 IP（任一成功即用）----
IP=""
for src in "https://api.ipify.org" "https://ifconfig.me/ip" "https://icanhazip.com"; do
  IP=$(curl -sS -m 8 "$src" 2>/dev/null | tr -d ' \n\r' || true)
  [ -n "$IP" ] && break
done
TS=$(date +%s); TS_H=$(date '+%Y-%m-%dT%H:%M:%S%z')

# ---- 2) 状态记录与变化判定 ----
python3 - "$STATE" "$IP" "$TS_H" "$TS" "$DID" <<'EOF'
import json, sys, time
from pathlib import Path
state_p, ip, ts_h, ts, did = sys.argv[1:6]
prev = {"current_ip": None, "last_change": None, "history": []}
p = Path(state_p)
if p.exists():
    try: prev = json.loads(p.read_text(encoding='utf-8'))
    except Exception: pass
changed = (ip != prev.get("current_ip"))
rec = {"ts": ts_h, "ip": ip}
if changed:
    prev["history"] = (prev.get("history") or [])[-19:] + [rec]
    prev["current_ip"] = ip
    prev["last_change"] = ts_h
    prev["change_count"] = prev.get("change_count", 0) + 1
else:
    prev["last_seen"] = ts_h
prev["last_check"] = ts_h
p.write_text(json.dumps(prev, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"IP={ip} changed={changed} change_count={prev.get('change_count',0)}")
print("STATE_UPDATED" if changed else "STATE_STABLE")
EOF
RET=$?
[ $RET -ne 0 ] && exit 1
CHANGED=$([ "$(python3 -c "import json;print(json.load(open('$STATE',encoding='utf-8')).get('last_change')=='$TS_H' and 1 or 0)")" = "1" ] && echo 1 || echo 0)

# ---- 3) IP 变化 → 同源协议上报（保持连接信息同步中枢）----
if [ "$CHANGED" = "1" ]; then
  python3 - "$IP" "$TS" "$DID" <<'EOF'
import json, subprocess, sys
ip, ts, did = sys.argv[1:4]
GW = "https://www.huodouai.com/api/report/truth"
payload = {"key": f"dyn_ip_change_{ts}",
           "value": {"event":"node_dynamic_ip_change","node":"NODE-DEV-DOUBAO-WORK-001",
                     "public_ip":ip,"ts":int(ts),"did":did,"anchor":"Ω₀⊂⊙∞⊂Ω"}}
p = subprocess.run(["curl","-sS","-m","15","-X","POST",GW,"-H",f"X-DID: {did}",
                    "-H","Content-Type: application/json","--data-binary",json.dumps(payload,ensure_ascii=False)],capture_output=True,text=True)
resp = p.stdout or p.stderr
print("IP变化已上报:", "真值写入成功" in resp, resp[-60:])
EOF
  # DDNS 联动：IP 变化 → 自动更新域名 A 记录（无密钥时 BLOCK 不阻塞）
  bash /home/user/ZONGYUAN-ROOT/scripts/ddns_update.sh "$IP" >> "$ROOT/logs/ddns.log" 2>&1 || true
else
  echo "[$(date)] IP 未变化，保持连接（last_seen 已刷新）" >> "$LOG"
fi
