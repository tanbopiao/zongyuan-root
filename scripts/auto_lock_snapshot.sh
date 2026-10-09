#!/usr/bin/env bash
# ZONGYUAN-ROOT 云端锁档加固 (重建版 20261009)
# 职责: SHA256哈希确权 + HASH-LEDGER追加 + Merkle根更新 + 状态快照
set -e
ROOT=/opt/ZONGYUAN-ROOT
LEDGER=$ROOT/var/inbox/HASH-LEDGER-MAIN.csv
SNAP=$ROOT/var/state-snapshot.json
TS=$(date "+%Y-%m-%dT%H:%M:%S%z")
EVENT="AUTO-LOCK-SNAPSHOT-$(date +%Y%m%d-%H%M%S)"

echo "[$TS] 开始锁档加固..."

# 1. 收集核心资产哈希
if [ -f "$ROOT/var/inbox/HASH-LEDGER-MAIN.csv" ]; then
  LEDGER_SHA=$(sha256sum "$LEDGER" | cut -d" " -f1)
else
  LEDGER_SHA="NA"
fi
DB_SHA="NA"
if [ -f "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db" ]; then
  DB_SHA=$(sha256sum /www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db | cut -d" " -f1)
fi
NODES_SHA="NA"
if [ -f "$ROOT/data/nodes_registry.db" ]; then
  NODES_SHA=$(sha256sum "$ROOT/data/nodes_registry.db" | cut -d" " -f1)
fi

# 2. 计算聚合根哈希
ROOT_HASH=$(echo "$LEDGER_SHA|$DB_SHA|$NODES_SHA|$TS" | sha256sum | cut -d" " -f1)

# 3. 追加账本
echo "$TS,$EVENT,$ROOT_HASH,DID-BR-000002,Ω₀⊂⊙∞⊂Ω,ledger=$LEDGER_SHA,db=$DB_SHA,nodes=$NODES_SHA" >> "$LEDGER"

# 4. 状态快照
cat > "$SNAP" << SNAPEOF
{"event": "$EVENT", "ts": "$TS", "root_sha256": "$ROOT_HASH", "ledger_sha": "$LEDGER_SHA", "truth_db_sha": "$DB_SHA", "nodes_db_sha": "$NODES_SHA", "did": "DID-BR-000002", "anchor": "Ω₀⊂⊙∞⊂Ω"}
SNAPEOF

echo "[$TS] 锁档完成: root=$ROOT_HASH"
echo "账本: $LEDGER (尾部已追加)"
echo "快照: $SNAP"
