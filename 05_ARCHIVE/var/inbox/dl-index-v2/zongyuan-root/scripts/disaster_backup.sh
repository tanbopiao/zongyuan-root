#!/bin/bash
# =====================================================================
# ZONGYUAN 全量记忆基准 · 云端灾备 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# 作用: 把本地全量记忆基准（truth-mirror.db + 飞书镜像快照 + 账本）上传云端
#       灾备目录 → 本地文件丢失时恢复 = 云端全量回拉（分钟级），而非增量重拉（小时级）
# 调度: cron 每日 03:00 + 每次全域锁档后可手动触发
# 安全: 不含 KEK/令牌等敏感文件（密钥走云盘备份）；只覆盖最新基准快照
# =====================================================================
set -uo pipefail
ZR="/home/user/ZONGYUAN-ROOT"
HOST="zongyuan-cloud"
REMOTE="/opt/ZONGYUAN-ROOT/var/sandbox-restore-kit/var/cloud-pull"
TS=$(date +%Y%m%d-%H%M%S)
DID="DID-BR-000002"

log(){ echo "[$(date '+%H:%M:%S')] $1"; }

log "=== 全量记忆基准灾备上云启动 ｜ $DID ｜ $TS ==="

# 1) 云端灾备目录就绪
timeout 20 ssh -o BatchMode=yes -o ConnectTimeout=15 "$HOST" "mkdir -p $REMOTE/feishu-mirror-latest" 2>/dev/null \
  || { log "云端目录创建失败"; exit 1; }

# 2) 真值全量镜像（28MB）
SRC_DB="$ZR/var/cloud-pull/truth-mirror.db"
if [ -f "$SRC_DB" ]; then
  timeout 120 scp -q "$SRC_DB" "$HOST:$REMOTE/truth-mirror.db" 2>/dev/null \
    && log "truth-mirror.db 上云 ok ($(du -h "$SRC_DB" | cut -f1))" \
    || log "truth-mirror.db 上云失败"
else
  log "本地 truth-mirror.db 不存在，跳过"
fi

# 3) 飞书镜像最新快照（整个目录 932K）
LATEST_MIRROR=$(ls -dt "$ZR"/var/feishu-mirror/2* 2>/dev/null | head -1)
if [ -n "$LATEST_MIRROR" ] && [ -d "$LATEST_MIRROR" ]; then
  timeout 60 scp -q -r "$LATEST_MIRROR" "$HOST:$REMOTE/feishu-mirror-latest/" 2>/dev/null \
    && log "飞书镜像快照上云 ok ($(basename "$LATEST_MIRROR"), $(du -sh "$LATEST_MIRROR" | cut -f1))" \
    || log "飞书镜像上云失败"
else
  log "无飞书镜像快照，跳过"
fi

# 4) 账本（append-only，小）
if [ -f "$ZR/HASH-LEDGER.csv" ]; then
  timeout 30 scp -q "$ZR/HASH-LEDGER.csv" "$HOST:$REMOTE/HASH-LEDGER.csv" 2>/dev/null \
    && log "HASH-LEDGER 上云 ok ($(wc -l < "$ZR/HASH-LEDGER.csv") 行)" \
    || log "HASH-LEDGER 上云失败"
fi

# 5) 云端验证
timeout 20 ssh -o BatchMode=yes -o ConnectTimeout=15 "$HOST" "du -sh $REMOTE; ls $REMOTE" 2>/dev/null \
  | tail -4 || log "云端验证失败"

log "=== 灾备上云完成 ==="
exit 0
