#!/usr/bin/env bash
# 生成设计系统完整目录树（幂等，可重复执行）
set -euo pipefail
cd "$(dirname "$0")/.."

DIRS=(
  "tokens/build"
  "foundation"
  "components/_template"
  "components/primitives/button"
  "components/primitives/input"
  "components/primitives/table"
  "components/primitives/tag"
  "components/primitives/modal"
  "components/primitives/tooltip"
  "components/domain/task-card"
  "components/domain/operator-status-panel"
  "components/domain/lock-receipt-card"
  "components/domain/log-panel"
  "components/domain/approval-dialog"
  "patterns/layout"
  "patterns/flows"
  "patterns/templates"
  "content"
  "governance"
  "automation"
  "aigc"
  "docs"
  "examples"
  "archive"
)

for d in "${DIRS[@]}"; do
  mkdir -p "$d"
  # 空目录留 .gitkeep，保证 git 可追踪
  if [ -z "$(ls -A "$d" 2>/dev/null)" ]; then
    touch "$d/.gitkeep"
  fi
done

echo "[OK] 目录树已生成：$(pwd)"
echo "[NEXT] npm run tokens:build -> npm run lint:hardcode -> npm run audit:tokens"
