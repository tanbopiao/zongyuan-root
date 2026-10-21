#!/bin/bash
# ZONGYUAN-ROOT 云端真值同步 + 全域锁档（每日定期任务）
# 依据：META-LAYER-SEPARATE-001（只读+审计）、META-LAW-CRYPT-LOCK-001（零明文令牌）
# 步骤：1) 云端7表真值同步 → var/truth/  2) 全域锁档 → HASH-LEDGER+卷宗回执  3) 网关上报（仅 X-DID，合规）
set -e
ROOT="/home/user/ZONGYUAN-ROOT"
LOG="$ROOT/logs/truth_sync_lock_$(date +%Y%m%d-%H%M%S).log"
exec > "$LOG" 2>&1
echo "[$(date)] === 真值同步 + 全域锁档 启动 ==="

# ---------- 1. 云端真值同步 ----------
python3 - <<'EOF'
import json, subprocess, time
from pathlib import Path
BASE = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
OUT = Path("/home/user/ZONGYUAN-ROOT/var/truth")
TS = time.strftime('%Y-%m-%dT%H:%M:%S%z')
def lark(args):
    p = subprocess.run(["lark-cli","base"]+args+["--as","user"], capture_output=True, text=True)
    return json.loads(p.stdout)
tables = lark(["+table-list","--base-token",BASE])["data"]["tables"]
idx = {"title":"本地实例持久化真值存储（云端同步）","synced_at":TS,"source_base":BASE,"tables":[]}
for t in tables:
    tid, name = t["id"], t["name"]
    rows, offset = [], 0
    while True:
        d = lark(["+record-list","--base-token",BASE,"--table-id",tid,"--limit","200","--offset",str(offset),"--format","json"]).get("data",{})
        rows.extend(d.get("data",[]))
        if not d.get("has_more",False): break
        offset += len(d.get("data",[]))
    obj = {"table":name,"table_id":tid,"fields":d.get("fields",[]),"records":rows,"record_count":len(rows),"synced_at":TS}
    fname = f"{tables.index(t)+1:02d}-{name}.json"
    (OUT/fname).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
    idx["tables"].append({"table":name,"file":fname,"records":len(rows)})
(OUT/"00-同步索引.json").write_text(json.dumps(idx,ensure_ascii=False,indent=2),encoding="utf-8")
print(f"[sync] {len(idx['tables'])} 表 / {sum(x['records'] for x in idx['tables'])} 条 已同步")
EOF

# ---------- 2. 全域锁档 ----------
python3 - <<'EOF'
import hashlib, json, time
from pathlib import Path
ROOT = Path("/home/user/ZONGYUAN-ROOT")
def sha(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(65536),b''): h.update(c)
    return h.hexdigest()
files = []
for p in sorted(ROOT.rglob('*')):
    if not p.is_file(): continue
    rel = p.relative_to(ROOT).as_posix()
    if rel.startswith('logs/') or '/logs/' in rel or '/.git' in rel or '__pycache__' in rel: continue
    if rel == 'var/kek.env' or rel.startswith('var/kek.env'): continue  # KEK 受限文件（600）：不入锁档/账本，零明文资产
    if rel == 'var/nginx/zr_token.conf' or rel.startswith('var/nginx/zr_token.conf'): continue  # 访问令牌（600）：明文不入锁档/账本
    files.append({'path':'/'+rel,'sha256':sha(p),'bytes':p.stat().st_size})
batch = hashlib.sha256()
for f in files:
    batch.update(f['path'].encode()); batch.update(f['sha256'].encode())
TS = time.strftime('%Y-%m-%dT%H:%M:%S%z')
event = f"GLOBAL-LOCK-ZONGYUAN-ROOT-FULL-{time.strftime('%Y%m%d-%H%M%S')}"
receipt = {"meta_action":"GLOBAL_LOCK_WRITE","event_id":event,"target_root":str(ROOT),
           "lock_timestamp":int(time.time()),"locked_at":TS,"asset_count":len(files),
           "batch_root_sha256":batch.hexdigest(),
           "gateway_report":{"endpoint":"https://www.huodouai.com/api/report/truth","did":"DID-BR-000002","status":"to_report"},
           "DID":"DID-BR-000002","anchor":"Ω₀⊂⊙∞⊂Ω","status":"LOCKED","files":files}
out = ROOT/'卷宗'/f'{event}.json'
out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
with open(ROOT/'HASH-LEDGER.csv','a',encoding='utf-8') as f:
    for fl in files:
        f.write(f"FRAMEWORK,{fl['path']},{event},{fl['sha256']},{fl['bytes']},{TS},locked\n")
print(f"[lock] {len(files)} 资产 批次根 {batch.hexdigest()[:16]}… 回执 {out.name}")
print(event)
EOF
EVENT=$(grep -oE 'GLOBAL-LOCK-ZONGYUAN-ROOT-FULL-[0-9]+-[0-9]+' "$LOG" | tail -1)

# ---------- 3. 网关上报（仅 X-DID，零令牌明文） ----------
python3 - <<'EOF'
import json, subprocess, time
from pathlib import Path
latest = sorted(Path("/home/user/ZONGYUAN-ROOT/卷宗").glob("GLOBAL-LOCK-ZONGYUAN-ROOT-FULL-*.json"), key=lambda p: p.stat().st_mtime)[-1]
r = json.load(open(latest, encoding='utf-8'))
GW = "https://www.huodouai.com/api/report/truth"
payload = {"key": f"global_lock_full_{int(time.time())}",
           "value": {"event":"global_lock_write","target":"ZONGYUAN-ROOT",
                     "lock_id":r["event_id"],"asset_count":r["asset_count"],
                     "batch_root_sha256":r["batch_root_sha256"],"locked_at":r["locked_at"],"DID":"DID-BR-000002"}}
p = subprocess.run(["curl","-sS","-m","20","-X","POST",GW,
                    "-H","X-DID: DID-BR-000002","-H","Content-Type: application/json",
                    "--data-binary",json.dumps(payload,ensure_ascii=False)], capture_output=True, text=True)
ok = '真值写入成功' in (p.stdout or "")
print(f"[report] {'OK' if ok else 'FAIL'} {(p.stdout or p.stderr)[-120:]}")
EOF

echo "[$(date)] === 完成 ==="
