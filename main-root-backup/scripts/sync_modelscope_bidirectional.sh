#!/bin/bash
# ZONGYUAN-ROOT 本地持久层 ↔ 魔搭数据湖 全量双向备份
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# 用法: bash sync_modelscope_bidirectional.sh

set -e

ARCHIVE="/home/user/ZONGYUAN-ROOT"
LOG="$ARCHIVE/archive/modelscope_sync.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] === 魔搭双向备份开始 ===" | tee -a "$LOG"

cd "$ARCHIVE"

# 阶段1: 魔搭 → 本地（拉取远程变更）
echo "[1/3] 魔搭→本地: 拉取远程变更..." | tee -a "$LOG"
git fetch modelscope master 2>&1 | tail -2 | tee -a "$LOG"

# 检查是否有远程变更
LOCAL_HASH=$(git rev-parse master 2>/dev/null)
REMOTE_HASH=$(git rev-parse modelscope/master 2>/dev/null)

if [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
    echo "  发现远程变更，执行rebase合并..." | tee -a "$LOG"
    git pull modelscope master --rebase --allow-unrelated-histories 2>&1 | tail -3 | tee -a "$LOG"
else
    echo "  本地与远程一致，无需拉取" | tee -a "$LOG"
fi

# 阶段2: 本地 → 魔搭（推送本地变更）
echo "[2/3] 本地→魔搭: 检查并推送本地变更..." | tee -a "$LOG"

# 统计变更
CHANGED=$(git status --porcelain | wc -l)
if [ "$CHANGED" -gt 0 ]; then
    echo "  发现$CHANGED个变更，提交中..." | tee -a "$LOG"
    git add -A 2>/dev/null
    git commit -m "双向同步: 本地变更自动推送
$TIMESTAMP
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω" 2>&1 | tail -2 | tee -a "$LOG"
else
    echo "  无本地变更" | tee -a "$LOG"
fi

# 推送
echo "  推送到魔搭数据湖..." | tee -a "$LOG"
git push modelscope master 2>&1 | tail -2 | tee -a "$LOG"

# 阶段3: 验证
echo "[3/3] 验证双向同步状态..." | tee -a "$LOG"
FINAL_LOCAL=$(git rev-parse master 2>/dev/null)
FINAL_REMOTE=$(git ls-remote modelscope master 2>/dev/null | awk '{print $1}')

if [ "$FINAL_LOCAL" = "$FINAL_REMOTE" ]; then
    echo "  ✅ 双向同步完成，本地与魔搭一致" | tee -a "$LOG"
    echo "  提交哈希: $FINAL_LOCAL" | tee -a "$LOG"
else
    echo "  ⚠️  本地与魔搭存在差异" | tee -a "$LOG"
    echo "  本地: $FINAL_LOCAL" | tee -a "$LOG"
    echo "  魔搭: $FINAL_REMOTE" | tee -a "$LOG"
fi

# 统计
FILE_COUNT=$(find "$ARCHIVE" -type f -not -path "*/.git/*" | wc -l)
TOTAL_SIZE=$(du -sh --exclude=.git "$ARCHIVE" | cut -f1)
echo "  归档母体: $FILE_COUNT文件 / $TOTAL_SIZE" | tee -a "$LOG"
echo "[$TIMESTAMP] === 魔搭双向备份完成 ===" | tee -a "$LOG"
echo "" | tee -a "$LOG"
