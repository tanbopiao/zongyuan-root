#!/bin/bash
# ZONGYUAN-ROOT Git桥接同步中间层
# 本地内核 ↔ GitHub ↔ Gitee 三向同步
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

set -e
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

MODE="${1:-full}"
BRANCH="${2:-main}"

echo "=========================================="
echo "ZONGYUAN-ROOT Git桥接同步"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "模式: $MODE | 分支: $BRANCH"
echo "=========================================="

case "$MODE" in
  status)
    echo "--- 远程状态 ---"
    git remote -v
    echo ""
    echo "--- 当前分支 ---"
    git branch -vv
    echo ""
    echo "--- 最近提交 ---"
    git log --oneline -5
    echo ""
    echo "--- 未推送提交 ---"
    echo "origin: $(git log origin/$BRANCH..$BRANCH --oneline 2>/dev/null | wc -l) 个"
    echo "gitee:  $(git log gitee/$BRANCH..$BRANCH --oneline 2>/dev/null | wc -l) 个"
    echo ""
    echo "--- 远程一致性 ---"
    if [ "$(git rev-parse origin/$BRANCH)" = "$(git rev-parse gitee/$BRANCH)" ]; then
      echo "✅ GitHub 与 Gitee 完全一致"
    else
      echo "⚠️ GitHub 与 Gitee 存在差异"
      echo "  GitHub: $(git rev-parse origin/$BRANCH)"
      echo "  Gitee:  $(git rev-parse gitee/$BRANCH)"
    fi
    ;;
  push)
    TARGET="${3:-all}"
    echo "--- 推送 origin (GitHub) ---"
    if [ "$TARGET" = "all" ] || [ "$TARGET" = "origin" ]; then
      git push origin "$BRANCH" 2>&1
    fi
    echo ""
    echo "--- 推送 gitee ---"
    if [ "$TARGET" = "all" ] || [ "$TARGET" = "gitee" ]; then
      git push gitee "$BRANCH" 2>&1
    fi
    echo ""
    echo "✅ 推送完成"
    ;;
  pull)
    TARGET="${3:-all}"
    echo "--- 拉取 origin (GitHub) ---"
    if [ "$TARGET" = "all" ] || [ "$TARGET" = "origin" ]; then
      git fetch origin 2>&1
    fi
    echo ""
    echo "--- 拉取 gitee ---"
    if [ "$TARGET" = "all" ] || [ "$TARGET" = "gitee" ]; then
      git fetch gitee 2>&1
    fi
    echo ""
    echo "✅ 拉取完成"
    ;;
  full)
    echo "--- 1. 暂存本地变更 ---"
    git add -A
    if ! git diff --staged --quiet; then
      SNAP="SNAP-$(date +%Y%m%d-%H%M%S)-BRIDGE-SYNC"
      git commit -m "$SNAP | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω"
      echo "✅ 已提交: $SNAP"
    else
      echo "无变更"
    fi
    echo ""
    echo "--- 2. 推送到 GitHub ---"
    git push origin "$BRANCH" 2>&1
    echo ""
    echo "--- 3. 推送到 Gitee ---"
    git push gitee "$BRANCH" 2>&1
    echo ""
    echo "--- 4. 验证一致性 ---"
    if [ "$(git rev-parse origin/$BRANCH)" = "$(git rev-parse gitee/$BRANCH)" ]; then
      echo "✅ GitHub 与 Gitee 一致"
    else
      echo "⚠️ 存在差异，需检查"
    fi
    echo ""
    echo "=========================================="
    echo "桥接同步完成 | $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=========================================="
    ;;
  *)
    echo "用法: $0 [status|push|pull|full] [分支] [目标]"
    echo "  status  - 查看同步状态"
    echo "  push    - 推送到远程 (origin/gitee/all)"
    echo "  pull    - 从远程拉取"
    echo "  full    - 完整同步（提交+推送双端）"
    exit 1
    ;;
esac
