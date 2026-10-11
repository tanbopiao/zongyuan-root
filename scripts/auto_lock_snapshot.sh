#!/usr/bin/env bash
# ZONGYUAN-ROOT 云端锁档加固 (重建版 20261009, trace 接入 v2.1 20261011)
# 职责: SHA256哈希确权 + HASH-LEDGER追加 + Merkle根更新 + 状态快照 + 三远端推送
# 全链路 trace 覆盖: trace_core 步骤链
set -e
ROOT=/opt/ZONGYUAN-ROOT
LEDGER=$ROOT/var/inbox/HASH-LEDGER-MAIN.csv
SNAP=$ROOT/var/state-snapshot.json
TS=$(date "+%Y-%m-%dT%H:%M:%S%z")
EVENT="AUTO-LOCK-SNAPSHOT-$(date +%Y%m%d-%H%M%S)"
TRACE_BIN=/opt/ZONGYUAN-ROOT/scripts/trace_core.py

# 启动 trace（缺模块则不阻断原流程）
TRACE_ID=$(python3 "$TRACE_BIN" start "auto-lock-snapshot" "{\"event\":\"$EVENT\",\"did\":\"DID-BR-000002\"}" 2>/dev/null || echo NA)
TRACE_ID=${TRACE_ID:-NA}
TR() { python3 "$TRACE_BIN" step "$TRACE_ID" "$1" "$2" "$3" "$4" 2>/dev/null || true; }

echo "[$TS] 开始锁档加固... (trace=$TRACE_ID)"
TR "STEP-01" "开始锁档加固" "ok"

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
TR "STEP-02" "收集核心资产哈希" "ok" "ledger=$LEDGER_SHA"

# 2. 计算聚合根哈希
ROOT_HASH=$(echo "$LEDGER_SHA|$DB_SHA|$NODES_SHA|$TS" | sha256sum | cut -d" " -f1)

# 3. 追加账本
echo "$TS,$EVENT,$ROOT_HASH,DID-BR-000002,Ω₀⊂⊙∞⊂Ω,ledger=$LEDGER_SHA,db=$DB_SHA,nodes=$NODES_SHA" >> "$LEDGER"
TR "STEP-03" "哈希确权+账本追加" "ok" "root=$ROOT_HASH"

# 4. 状态快照
cat > "$SNAP" << SNAPEOF
{"event": "$EVENT", "ts": "$TS", "root_sha256": "$ROOT_HASH", "ledger_sha": "$LEDGER_SHA", "truth_db_sha": "$DB_SHA", "nodes_db_sha": "$NODES_SHA", "did": "DID-BR-000002", "anchor": "Ω₀⊂⊙∞⊂Ω"}
SNAPEOF
TR "STEP-04" "状态快照" "ok"

echo "[$TS] 锁档完成: root=$ROOT_HASH"
echo "账本: $LEDGER (尾部已追加)"
echo "快照: $SNAP"

# 5. Git 三远端自动推送 (Gitee/GitHub/atomgit)
echo "[$TS] 开始 Git 三远端推送..."
cd $ROOT || true
git add -A 2>/dev/null || true
if git diff --cached --quiet 2>/dev/null; then
  echo "[$TS] 无变更, 跳过提交"
else
  git -c user.name="ZONGYUAN-ROOT" -c user.email="zr@huodouai.com" commit -m "lock: $EVENT root=$ROOT_HASH" 2>&1 | tail -1
fi
PUSH_OK=0; PUSH_FAIL=0
for remote in atomgit gitee github; do
  if timeout 60 git push "$remote" main 2>/dev/null; then
    echo "[$TS] $remote 推送成功"
    PUSH_OK=$((PUSH_OK+1))
  else
    echo "[$TS] $remote 推送失败, 尝试合并远端历史..."
    timeout 60 git fetch "$remote" main 2>/dev/null
    timeout 60 git merge --allow-unrelated-histories FETCH_HEAD -m "merge: $remote 远端历史" 2>/dev/null || true
    if timeout 60 git push "$remote" main 2>/dev/null; then
      echo "[$TS] $remote 推送成功(合并后)"
      PUSH_OK=$((PUSH_OK+1))
    else
      echo "[$TS] $remote 推送失败, 已记录告警"
      echo "$TS,$EVENT,$ROOT_HASH,git-push-fail,$remote" >> "$LEDGER" 2>/dev/null || true
      PUSH_FAIL=$((PUSH_FAIL+1))
    fi
  fi
done
TR "STEP-05" "Git三远端推送" "$([ $PUSH_FAIL -eq 0 ] && echo ok || echo warn)" "ok=$PUSH_OK fail=$PUSH_FAIL"
echo "[$TS] 三远端推送流程完成"
TR "STEP-06" "锁档加固完成" "ok"
python3 "$TRACE_BIN" end "$TRACE_ID" 2>/dev/null || true
