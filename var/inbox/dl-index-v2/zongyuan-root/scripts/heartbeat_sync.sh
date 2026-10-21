#!/bin/bash
# ZONGYUAN-ROOT 云端内核互通：心跳同步 + 双向握手
# 上行：本地心跳 → 真值网关（X-DID 单头，云端中枢存储）
# 下行：云端飞书 Base → 本地（识别云端指令：待部署任务 / 阻塞告警）
# 握手：双向状态落盘 var/heartbeat/ 持久化
set -e
ROOT="/home/user/ZONGYUAN-ROOT"
LOG="$ROOT/logs/heartbeat_sync_$(date +%Y%m%d-%H%M%S).log"
exec > "$LOG" 2>&1
echo "[$(date)] === 云端内核互通：心跳同步 + 双向握手 启动 ==="
python3 - <<'EOF'
import json, subprocess, time
from pathlib import Path

ROOT = Path("/home/user/ZONGYUAN-ROOT")
HB_DIR = ROOT / "var" / "heartbeat"
HB_DIR.mkdir(parents=True, exist_ok=True)
NODE = "NODE-DEV-DOUBAO-WORK-001"
DID = "DID-BR-000002"
BASE = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE = "tblnVRjuf7P31cEP"
BLOCK_TABLE = "tbljp3z11UtiuWCF"
GW = "https://www.huodouai.com/api/report/truth"
TS = int(time.time())
TS_H = time.strftime('%Y-%m-%dT%H:%M:%S%z')

# 本地健康探测（docker 不可用则 0/na，不阻塞）
worker_running = 0
try:
    p = subprocess.run(["docker","ps","--filter","name=worker-","--filter","status=running"],
                       capture_output=True, text=True, timeout=8)
    worker_running = len([l for l in p.stdout.splitlines()[1:] if l.strip()]) if p.returncode == 0 else 0
except Exception:
    worker_running = 0

# ---------- 上行：心跳上报（X-DID 单头） ----------
hb_key = f"node_heartbeat_{DID}_{TS}"
payload = {"key": hb_key, "value": {
    "event": "node_heartbeat", "node": NODE, "did": DID,
    "heartbeat_ts": TS_H, "status": "alive", "worker_running": worker_running,
    "truth_synced": 588, "local_ts": TS}}
try:
    p = subprocess.run(["curl","-sS","-m","20","-X","POST",GW,
                        "-H",f"X-DID: {DID}","-H","Content-Type: application/json",
                        "--data-binary", json.dumps(payload, ensure_ascii=False)],
                       capture_output=True, text=True, timeout=30)
    up_resp = p.stdout or p.stderr
    up_ok = "真值写入成功" in up_resp
except Exception as e:
    up_resp, up_ok = str(e), False
print(f"[上行] 心跳上报: {'OK' if up_ok else 'FAIL'} {up_resp[-100:]}")

# ---------- 下行：读云端指令（任务台账 + 阻塞记录） ----------
def lark(args):
    try:
        p = subprocess.run(["lark-cli","base"]+args+["--as","user"], capture_output=True, text=True, timeout=60)
        return json.loads(p.stdout)
    except Exception:
        return {}

down = {"pending_tasks": 0, "claiming_tasks": 0, "cloud_blocks": 0, "sample_instruction": None}
t = lark(["+record-list","--base-token",BASE,"--table-id",TASK_TABLE,"--limit","200","--offset","0","--format","json"])
if "data" in t and "data" in t["data"]:
    fields = t["data"].get("fields", [])
    idx = {n: i for i, n in enumerate(fields)} if isinstance(fields, list) else {}
    st_i = idx.get("status", -1)
    for row in t["data"]["data"]:
        if st_i >= 0 and isinstance(row, list) and st_i < len(row):
            v = str(row[st_i])
            if "待部署" in v: down["pending_tasks"] += 1
            if "认领中" in v: down["claiming_tasks"] += 1
b = lark(["+record-list","--base-token",BASE,"--table-id",BLOCK_TABLE,"--limit","200","--offset","0","--format","json"])
if "data" in b and "data" in b["data"]:
    down["cloud_blocks"] = len(b["data"]["data"])
    if down["cloud_blocks"] > 0 and b["data"]["data"]:
        bf = b["data"].get("fields", [])
        bidx = {n: i for i, n in enumerate(bf)} if isinstance(bf, list) else {}
        err_i = bidx.get("error_msg", bidx.get("问题描述", 0))
        row = b["data"]["data"][0]
        if isinstance(row, list) and err_i >= 0 and err_i < len(row):
            down["sample_instruction"] = str(row[err_i])[:80]
print(f"[下行] 云端指令: 待部署 {down['pending_tasks']} / 认领中 {down['claiming_tasks']} / 阻塞记录 {down['cloud_blocks']}")

# ---------- 握手回执（双向状态持久化） ----------
handshake = {
  "handshake_ts": TS_H, "node": NODE, "did": DID,
  "upstream": {"channel": "truth_gateway", "key": hb_key, "ok": up_ok, "response": up_resp[-80:]},
  "downstream": {"channel": "feishu_base", "task_table": TASK_TABLE, "block_table": BLOCK_TABLE, **down},
  "handshake_status": "bidirectional_ok" if (up_ok and "data" in t) else ("up_only" if up_ok else "down_only" if "data" in t else "failed"),
  "DID": DID, "anchor": "Ω₀⊂⊙∞⊂Ω"
}
fname = f"握手-{time.strftime('%Y%m%d-%H%M%S')}.json"
(HB_DIR / fname).write_text(json.dumps(handshake, ensure_ascii=False, indent=2), encoding='utf-8')

idxp = HB_DIR / "00-心跳索引.json"
idx = json.loads(idxp.read_text(encoding='utf-8')) if idxp.exists() else {"title":"本地-云端内核互通心跳索引","node":NODE,"records":[]}
idx["records"].append({"ts": TS_H, "file": fname, "status": handshake["handshake_status"],
                        "up": handshake["upstream"]["ok"], "pending_tasks": down["pending_tasks"]})
idxp.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"[握手] 状态={handshake['handshake_status']} 回执={HB_DIR/fname}")
EOF
echo "[$(date)] === 完成 ==="
