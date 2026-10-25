#!/bin/bash
# =====================================================================
# ZONGYUAN 节点编队指挥层 fleet | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# 用法: bash fleet.sh <subcmd>
#   status   → 聚合全部节点巡检回执（本地 + 云端），一眼健康
#   dispatch <指令> → 中枢统一下发：真值审计通道 + 云端主库即时写（双写）
#   lock     → 全员锁档：本地全域锁 + 云端基准灾备打包
# 节点侧: cron */5 拉取指令（worker_instruction_pull.sh，读云端真值库指令类）
# 可见性: 真值通道依赖备份周期（最长6h）；主库即时写保证最终一致
# =====================================================================
set -uo pipefail
ZR="/home/user/ZONGYUAN-ROOT"
CLOUD="zongyuan-cloud"
REMOTE_ROOT="/opt/ZONGYUAN-ROOT"
DID="DID-BR-000002"
ACT="${1:-status}"

case "$ACT" in
  status)
    echo "== 本地 ZR-SANDBOX =="
    python3 - "$ZR" << 'PY'
import json, glob, sys
fs = sorted(glob.glob(f"{sys.argv[1]}/var/patrol/patrol-2*.json"))
if fs:
    d = json.load(open(fs[-1]))
    st = d['status']
    if 'ports' in st:
        print(f"  巡检 {d['ts'][:16]} | ports={st['ports']} | site={st['site_http']} | abnormal={st['abnormal']}")
    else:  # 兼容旧版增强结构（port8081/port8091 键）
        print(f"  巡检 {d['ts'][:16]} | ports={{8081:{st.get('port8081',0)}, 8091:{st.get('port8091',0)}}} | site={st.get('site_http')} | abnormal={st.get('abnormal')}")
else:
    print("  无巡检记录")
PY
    echo "  镜像:"
    MIRROR_STATE="$ZR/var/cloud-kernel-mirror/MIRROR-STATE.json"
    if [ -f "$MIRROR_STATE" ]; then
      python3 -c "import json;d=json.load(open('$MIRROR_STATE'));print('   cloud-kernel-mirror:',d['kernel_mirror']['files'],'文件',d['kernel_mirror']['gb'],'G @',d['ts'][:16])"
    else
      echo "   （无镜像，先 cloud-mirror sync-core）"
    fi
    echo "== 云端 ZR-CLOUD-HUB =="
    timeout 20 ssh -o BatchMode=yes -o ConnectTimeout=15 "$CLOUD" "python3 -c \"
import json,glob
fs=sorted(glob.glob('$REMOTE_ROOT/var/patrol/patrol-2*.json'))
if fs:
    d=json.load(open(fs[-1]))
    print('  巡检 '+d['ts'][:16]+' | ports='+str(d['status']['ports'])+' | site='+d['status']['site_http']+' | abnormal='+str(d['status']['abnormal']))
else:
    print('  无巡检记录')
\"" 2>/dev/null || echo "  云端不可达"
    ;;
  dispatch)
    MSG="${2:?用法: fleet dispatch <指令内容>}"
    KEY="INSTRUCTION.$(date +%s)"
    echo "下发指令: $MSG"
    # ① 真值审计通道（公网网关）
    python3 - "$DID" "$KEY" "$MSG" << 'PY'
import json, sys, urllib.request, time
did, key, msg = sys.argv[1:4]
payload = {"key": key, "value": {"cmd": msg, "from": "hub-central", "ts": time.time()}}
req = urllib.request.Request("https://www.huodouai.com/api/report/truth",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "X-DID": did})
try:
    r = json.load(urllib.request.urlopen(req, timeout=15))
    print(f"  [真值通道] ok: {key} | {r.get('message','')} | truth_count={r.get('truth_count','?')}")
except Exception as e:
    print(f"  [真值通道] 失败: {e}")
PY
    # ② 云端主库即时写（节点 */5 拉取最终可见；临时文件传递 + INSERT OR IGNORE 幂等）
    TMP_MSG=$(mktemp)
    python3 - "$KEY" "$MSG" > "$TMP_MSG" << 'PY'
import json, sys, time
key, msg = sys.argv[1:3]
print(json.dumps({"key": key, "cmd": msg, "from": "hub-central", "ts": int(time.time())}))
PY
    timeout 20 scp -q "$TMP_MSG" "$CLOUD:/tmp/fleet-msg.json" 2>/dev/null
    timeout 20 ssh -o BatchMode=yes -o ConnectTimeout=15 "$CLOUD" "python3 - << 'PY3'
import sqlite3, json
msg=json.load(open('/tmp/fleet-msg.json'))
db='/opt/ZONGYUAN-ROOT/data/gateway_9120_only/memory_gateway.db'
c=sqlite3.connect(db)
c.execute('INSERT OR IGNORE INTO truths(truth_key, truth_value, truth_hash, category, node_id, created_at, version) VALUES (?,?,?,?,?,?,?)',
 (msg['key'], json.dumps({'cmd': msg['cmd'], 'from': msg['from']}), 'fleet', 'instruction', 'hub-central', msg['ts'], 1))
c.commit()
print('  [主库即时写] ok:', msg['key'])
PY3
" 2>/dev/null || echo "  [主库即时写] 失败"
    rm -f "$TMP_MSG"
    ;;
  lock)
    echo "== 全员锁档 ｜ $DID =="
    echo "[本地] 全域锁档:"
    bash "$ZR/scripts/worker_kernel.sh" lock 2>/dev/null | tail -2 || echo "  本地锁档失败"
    echo "[云端] 基准灾备打包（云端自身锁档体系不动）:"
    timeout 60 ssh -o BatchMode=yes -o ConnectTimeout=15 "$CLOUD" "bash $REMOTE_ROOT/scripts/disaster_backup.sh 2>&1 | tail -2" 2>/dev/null || echo "  云端不可达"
    ;;
  propose)
    # 联邦融合进化 · 分身演化提案上云（联邦融合进化三子命令之1）
    SUB="${2:-truth}"
    if [ "$SUB" = "truth" ]; then
      KEY="${3:?用法: fleet propose truth --key <K> --value <V> [--note <说明>]}"   # 兼容: 位置参数
      # 支持 --key/--value/--note 风格
      k=""; v=""; note=""
      while [ $# -gt 2 ]; do
        case "$3" in
          --key) k="$4"; shift 2;;
          --value) v="$4"; shift 2;;
          --note) note="$4"; shift 2;;
          *) shift;;
        esac
      done
      [ -z "$k" ] && k="$KEY"
      [ -z "$v" ] && v="${4:?用法: fleet propose truth --key K --value V}"
      TS=$(date +%s)
      PID="FUSION.EVOL.${TS}"
      PROP_FILE="/tmp/${PID}.json"
      python3 - "$PID" "$k" "$v" "$note" > "$PROP_FILE" << 'PY'
import json, sys, time
pid, k, v, note = sys.argv[1:5]
print(json.dumps({
  "proposal_id": pid, "did": "DID-BR-000002", "ontology_signature": "Ω₀⊂⊙∞⊂Ω",
  "type": "truth", "node": "ZR-SANDBOX", "ts": int(time.time()),
  "note": note, "items": [{"key": k, "value": v}]
}, ensure_ascii=False, indent=2))
PY
      echo "== 演化提案 ｜ $DID =="
      echo "  提案ID: $PID ｜ type=truth ｜ key=$k"
      timeout 20 scp -q "$PROP_FILE" "$CLOUD:$REMOTE_ROOT/var/fleet/proposals/" 2>/dev/null && echo "  [提案落位] ok 云端 proposals/"
      timeout 20 ssh -o BatchMode=yes -o ConnectTimeout=15 "$CLOUD" "python3 - << 'PY3'
import sqlite3, json
p=json.load(open('$REMOTE_ROOT/var/fleet/proposals/$PID.json'))
db='$REMOTE_ROOT/data/gateway_9120_only/memory_gateway.db'
c=sqlite3.connect(db)
c.execute('INSERT OR IGNORE INTO truths(truth_key, truth_value, truth_hash, category, node_id, created_at, version) VALUES (?,?,?,?,?,?,?)',
 ('PROPOSAL.$PID', json.dumps({'proposal_id': p['proposal_id'], 'type': p['type'], 'node': p['node']}), 'fleet-propose', 'instruction', p['node'], p['ts'], 1))
c.commit()
print('  [主库提案登记] ok: PROPOSAL.$PID')
PY3
" 2>/dev/null || echo "  [主库提案登记] 失败"
      rm -f "$PROP_FILE"
      echo "  下一步: fleet merge ｜ 中枢仲裁合并 → fleet broadcast 广播全节点"
    elif [ "$SUB" = "files" ]; then
      # 文件级演化：扫描近期改动（24h）元法则/脚本/配置 → 哈希清单提案（中枢只登记不覆盖）
      TS=$(date +%s)
      PID="FUSION.FILES.${TS}"
      python3 - "$PID" "$ZR" << 'PY'
import json, os, sys, time, hashlib
pid, zr = sys.argv[1:3]
roots = [f"{zr}/../zongyuan-kernel/config/meta_laws", f"{zr}/config", f"{zr}/scripts"]
items = []
seen = set()
for r in roots:
    if not os.path.isdir(r): continue
    for root, dirs, files in os.walk(r):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "var", "meta")]
        for fn in files:
            if fn.endswith((".pyc", ".log")): continue
            fp = os.path.join(root, fn)
            try:
                if time.time() - os.path.getmtime(fp) > 86400: continue
                h = hashlib.sha256()
                h.update(open(fp, "rb").read())
                rel = fp.replace(zr, "ZR")
                items.append({"path": rel, "sha256": h.hexdigest()})
            except OSError: pass
print(json.dumps({
  "proposal_id": pid, "did": "DID-BR-000002", "ontology_signature": "Ω₀⊂⊙∞⊂Ω",
  "type": "files", "node": "ZR-SANDBOX", "ts": int(time.time()),
  "note": "24h内文件演化哈希清单（中枢仅登记，pending_review）",
  "items": items[:20]
}, ensure_ascii=False, indent=2))
PY
      echo "== 文件演化提案 ｜ $DID =="
      echo "  提案ID: $PID ｜ type=files"
      timeout 20 scp -q "/tmp/${PID}.json" "$CLOUD:$REMOTE_ROOT/var/fleet/proposals/" 2>/dev/null && echo "  [提案落位] ok"
      rm -f "/tmp/${PID}.json"
      echo "  注: 文件级只登记哈希清单，中枢不自动覆盖文件（风险闸门，pending_review）"
    else
      echo "用法: fleet propose truth|files"; exit 2
    fi
    ;;
  merge)
    echo "== 中枢仲裁合并 ｜ $DID =="
    timeout 40 ssh -o BatchMode=yes -o ConnectTimeout=15 "$CLOUD" "python3 $REMOTE_ROOT/scripts/fleet_merge.py merge" 2>/dev/null || echo "  云端不可达"
    ;;
  broadcast)
    echo "== 融合广播 ｜ $DID =="
    timeout 40 ssh -o BatchMode=yes -o ConnectTimeout=15 "$CLOUD" "python3 $REMOTE_ROOT/scripts/fleet_merge.py broadcast" 2>/dev/null || echo "  云端不可达"
    ;;
  review)
    echo "== 联邦文件评审门 ｜ $DID =="
    shift
    python3 "$ZR/scripts/fleet_review.py" "$@"
    ;;
  *)
    echo "用法: fleet [status | dispatch <指令> | lock | propose truth|files | merge | broadcast | review list|approve|reject]"; exit 2;;
esac
exit 0
