#!/bin/bash
# 云→沙箱 拉取同步（真值快照/元法则/节点注册/云内核状态）| DID-BR-000002
# 周期: cron */30; 只读拉取, 不写云侧; 失败不阻塞
HOST=zongyuan-cloud
DST=/home/user/ZONGYUAN-ROOT/var/cloud-pull
mkdir -p "$DST"
TS=$(date +%s)
# 1) 云内核心跳
ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" "cat /opt/ZONGYUAN-ROOT/meta/cloud-heartbeat.json" > "$DST/cloud-heartbeat.json" 2>/dev/null
# 2) 真值规模+最近条目（云上查询, 主truth库探测后取值）
ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" 'python3 -c "
import sqlite3, json, glob, os
cands = sorted(glob.glob(\"/opt/ZONGYUAN-ROOT/backups/truth_db_*.db\"), reverse=True)
if not cands: cands = sorted(glob.glob(\"/opt/ZONGYUAN-ROOT/data/*.db\"), reverse=True)
db = cands[0] if cands else None
try:
    c = sqlite3.connect(db)
    n = c.execute(\"SELECT COUNT(*) FROM truths\").fetchone()[0]
    recent = c.execute(\"SELECT id, created_at, substr(truth_key,1,60) FROM truths ORDER BY id DESC LIMIT 3\").fetchall()
    print(json.dumps({\"db\": os.path.basename(db), \"count\": n, \"recent\": recent}))
except Exception as e:
    print(json.dumps({\"error\": str(e)[:120]}))
"' > "$DST/truth-snapshot.json" 2>/dev/null
# 3) 元法则文档（只读拉取）
scp -q -o BatchMode=yes -o ConnectTimeout=10 "$HOST:/opt/ZONGYUAN-ROOT/docs/META_RULES.md" "$DST/" 2>/dev/null && echo "META_RULES 拉取OK" || echo "META_RULES 拉取失败"
# 4) 节点注册表
scp -q -o BatchMode=yes -o ConnectTimeout=10 "$HOST:/opt/ZONGYUAN-ROOT/data/nodes_registry.db" "$DST/" 2>/dev/null && echo "nodes_registry 拉取OK" || echo "nodes_registry 拉取失败"
echo "PULL_DONE ts=$TS"
# 5) 真值增量全量同步（本地 mirror 镜像库，append-only）
LAST=$(cat "$DST/last-sync-id" 2>/dev/null || echo 0)
for i in 1 2 3 4 5 6 7 8 9 10; do
  ssh -o BatchMode=yes -o ConnectTimeout=15 "$HOST" "python3 /opt/ZONGYUAN-ROOT/scripts/truth_export.py --last $LAST --limit 50000 --slim" > "$DST/inc.jsonl" 2>/dev/null
  python3 /home/user/ZONGYUAN-ROOT/scripts/truth_import.py "$DST/inc.jsonl" "$DST/truth-mirror.db" > "$DST/import.out" 2>&1
  NEW=$(awk -F'last=' '{print $2}' "$DST/import.out" | tail -1)
  if [ -z "$NEW" ] || [ "$NEW" = "$LAST" ]; then break; fi
  LAST=$NEW
  echo "$LAST" > "$DST/last-sync-id"
done
echo "TRUTH_MIRROR: $(cat "$DST/import.out" | tail -1)"
