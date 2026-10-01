#!/bin/bash
# ZONGYUAN-ROOT 变更同步：主根→归档母体→Git冷存储
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# 用法: ./sync_to_archive.sh "提交说明"

KROOT="/home/user/.doubao/agent_mode/workspace/.user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT"
ARCHIVE="/home/user/ZONGYUAN-ROOT"
COMMIT_MSG="${1:-常规同步 $(date +%Y%m%d-%H%M%S)}"

echo "=== 变更同步开始 ==="

# 1. 主根→归档母体
echo "[1/3] 主根→归档母体 rsync..."
rsync -a --exclude='.git' --exclude='archive/' --exclude='assets/' --exclude='cache/' \
  "$KROOT/" "$ARCHIVE/main-root-backup/" 2>/dev/null
echo "  完成: $(find $ARCHIVE/main-root-backup -type f | wc -l)文件"

# 2. 归档母体→Git提交
echo "[2/3] Git提交..."
cd "$ARCHIVE"
git add -A 2>/dev/null
git commit -m "$COMMIT_MSG
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω" 2>&1 | tail -2

# 3. 推送冷存储
echo "[3/3] 推送冷存储..."
BRANCH=$(git branch --show-current 2>/dev/null)
git push gitee "$BRANCH" 2>&1 | tail -1 || echo "  Gitee: 跳过"
git push github "$BRANCH" 2>&1 | tail -1 || echo "  Github: 跳过"
git push modelscope "$BRANCH" 2>&1 | tail -1 || echo "  ModelScope: 跳过"

echo "=== 变更同步完成（四层冷存储：归档母体+Gitee+Github+ModelScope数据湖）==="
