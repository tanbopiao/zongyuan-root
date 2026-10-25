#!/bin/bash
# ZONGYUAN 沙箱↔云服务器 心跳互报 + 账本双写 | DID-BR-000002
# 周期: cron */5; 幂等; SSH失败不阻塞
ZR=/home/user/ZONGYUAN-ROOT
ZK=/home/user/Doubao/chats/38412149511142658/zongyuan-kernel
HOST=zongyuan-cloud
TS=$(date +%s)
K=$(pgrep -f "kernel/main.py" >/dev/null 2>&1 && echo up || echo down)
W=$(pgrep -f worker_daemon.sh >/dev/null 2>&1 && echo up || echo down)
C=$(crontab -l 2>/dev/null | grep -c '^[^#]')
# 1) 沙箱心跳 → 云服务器（覆盖式写最新状态）
echo "{\"node\":\"vefaas-sandbox\",\"ts\":$TS,\"kernel\":\"$K\",\"worker\":\"$W\",\"cron\":$C}" | \
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" "mkdir -p /opt/ZONGYUAN-ROOT/meta && cat > /opt/ZONGYUAN-ROOT/meta/sandbox-heartbeat.json" 2>/dev/null \
  && echo "心跳上报OK ts=$TS k=$K w=$W c=$C" || echo "心跳上报失败(不阻塞)"
# 2) 云内核状态读回（探测）
CLOUD=$(ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" "cat /opt/ZONGYUAN-ROOT/meta/cloud-heartbeat.json 2>/dev/null || echo NONE" 2>/dev/null)
echo "云内核: $CLOUD"
# 3) 审计/账本 rsync 双写（沙箱 → 云服务器 inbox）
ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" "mkdir -p /opt/ZONGYUAN-ROOT/var/inbox" 2>/dev/null
if which rsync >/dev/null 2>&1; then
  rsync -az --timeout=20 "$ZK/var/audit/audit.jsonl" "$ZR/HASH-LEDGER-MAIN.csv" "$HOST:/opt/ZONGYUAN-ROOT/var/inbox/" 2>/dev/null \
    && echo "账本双写OK" || echo "账本双写失败"
else
  for f in "$ZK/var/audit/audit.jsonl" "$ZR/HASH-LEDGER-MAIN.csv"; do
    scp -q -o BatchMode=yes -o ConnectTimeout=10 "$f" "$HOST:/opt/ZONGYUAN-ROOT/var/inbox/" 2>/dev/null
  done && echo "账本双写OK(scp)" || echo "账本双写失败(scp)"
fi
