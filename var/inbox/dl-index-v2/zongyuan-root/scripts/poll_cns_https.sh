#!/bin/bash
# ZONGYUAN-ROOT HTTPS 反向轮询脚本（本地端 → 云端中枢主动拉取）
# 语义：非云端推送，本地节点周期性地通过 HTTPS 反向轮询中枢，获取：
#   1) 中枢指令（任务台账：待部署/认领中）
#   2) kill-switch 状态（中枢不可达 → fail_closed，worker 不得执行）
#   3) 网关连通性探针（上行 truth_count）
# 输出：var/poll/轮询-<时间戳>.json + 00-轮询索引.json（持久化）
set -uo pipefail
ROOT="/home/user/ZONGYUAN-ROOT"
POLL_DIR="$ROOT/var/poll"
mkdir -p "$POLL_DIR"
DID="DID-BR-000002"
GW="https://www.huodouai.com/api/report/truth"
BASE="DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE="tblnVRjuf7P31cEP"

python3 - "$POLL_DIR" "$GW" "$DID" "$BASE" "$TASK_TABLE" <<'EOF'
import json, subprocess, sys, time
from pathlib import Path

POLL_DIR, GW, DID, BASE, TASK_TABLE = sys.argv[1:6]
TS = int(time.time())
TS_H = time.strftime('%Y-%m-%dT%H:%M:%S%z')

# ---- 1) 上行探针：网关连通性（POST 心跳探测，取 truth_count） ----
probe = {"key": f"poll_probe_{DID}_{TS}", "value": {"event": "reverse_poll_probe", "ts": TS, "DID": DID}}
up = {"ok": False, "truth_count": None}
try:
    p = subprocess.run(["curl","-sS","-m","15","-X","POST",GW,
                        "-H",f"X-DID: {DID}","-H","Content-Type: application/json",
                        "--data-binary", json.dumps(probe, ensure_ascii=False)],
                       capture_output=True, text=True, timeout=25)
    resp = p.stdout or p.stderr
    up["ok"] = "真值写入成功" in resp
    import re
    m = re.search(r'"truth_count"\s*:\s*(\d+)', resp)
    if m: up["truth_count"] = int(m.group(1))
except Exception as e:
    up["ok"] = False

# ---- 2) 下行轮询：中枢指令（精确解析状态字段，防备注误报） ----
down = {"cns_reachable": False, "pending": 0, "claiming": 0}
try:
    p = subprocess.run(["lark-cli","base","+record-list","--base-token",BASE,
                        "--table-id",TASK_TABLE,"--as","user","--limit","200","--offset","0","--format","json"],
                       capture_output=True, text=True, timeout=60)
    d = json.loads(p.stdout).get("data", {})
    fields = d.get("fields", []); rows = d.get("data", [])
    st_i = fields.index("状态") if "状态" in fields else -1
    for r in rows:
        if st_i >= 0 and st_i < len(r):
            v = r[st_i]
            if isinstance(v, list) and v:
                if "待部署" in str(v[0]): down["pending"] += 1
                if "认领中" in str(v[0]): down["claiming"] += 1
    down["cns_reachable"] = True
except Exception:
    down["cns_reachable"] = False

# ---- 3) 判定（kill-switch fail-closed：中枢不可达 → worker 不得执行） ----
if not down["cns_reachable"]:
    verdict = "fail_closed"; kill_switch = "on"
    note = "中枢不可达，kill-switch 生效：worker 保持受控空闲，禁止执行"
elif down["pending"] > 0:
    verdict = "executing"; kill_switch = "off"
    note = f"中枢有 {down['pending']} 条待部署指令，worker 可受控执行"
else:
    verdict = "idle"; kill_switch = "off"
    note = "中枢可达但无待部署指令，worker 空闲"

snapshot = {
  "poll_ts": TS_H, "DID": DID,
  "upstream": {"gateway": "ok" if up["ok"] else "fail", "truth_count": up["truth_count"]},
  "downstream": down,
  "kill_switch": kill_switch,
  "verdict": verdict,
  "note": note,
  "anchor": "Ω₀⊂⊙∞⊂Ω"
}
fname = f"轮询-{time.strftime('%Y%m%d-%H%M%S')}.json"
(Path(POLL_DIR) / fname).write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
idxp = Path(POLL_DIR) / "00-轮询索引.json"
idx = json.loads(idxp.read_text(encoding='utf-8')) if idxp.exists() else {"title":"HTTPS 反向轮询索引","node":"ZONGYUAN-ROOT","records":[]}
idx["records"].append({"ts": TS_H, "file": fname, "verdict": verdict, "pending": down["pending"], "kill_switch": kill_switch})
idxp.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding='utf-8')

print(f"[轮询] 上行: {'ok' if up['ok'] else 'fail'} truth_count={up['truth_count']} | 下行: 中枢{'可达' if down['cns_reachable'] else '不可达'} 待部署={down['pending']} | 判定: {verdict} kill_switch={kill_switch}")
print(f"[落盘] {Path(POLL_DIR)/fname}")
EOF
