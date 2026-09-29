#!/bin/bash
# ZONGYUAN-ROOT 内核真值同步脚本
# 本地内核 ↔ Git仓库 ↔ 云内核 三端桥接同步
# 确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω

set -e

REPO="$HOME/zongyuan-root-kernel"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%dT%H:%M:%S%z)

echo "=== ZONGYUAN-ROOT 内核真值同步 ==="
echo "时间: $TIMESTAMP"

cd "$REPO"

# 1. 从源位置拉取最新内核数据
echo "[1/4] 同步本地内核数据..."
cp ~/.zongyuan_root/axioms_new.json axioms/ 2>/dev/null || true
cp ~/.zongyuan_root/axioms_strengthened.json axioms/ 2>/dev/null || true
cp ~/.zongyuan_root/axioms_challenged.json axioms/ 2>/dev/null || true
cp ~/.zongyuan_root/evolution_log.jsonl evolution/ 2>/dev/null || true
cp ~/.zongyuan_os/daily_todos.json todos/ 2>/dev/null || true

# 同步当日搜索数据
if [ -d ~/daily_search/$DATE ]; then
  mkdir -p truth_cards/$DATE search_compiled/$DATE
  cp ~/daily_search/$DATE/top5_truth_cards.json truth_cards/$DATE/ 2>/dev/null || true
  cp ~/daily_search/$DATE/compiled_search.txt search_compiled/$DATE/ 2>/dev/null || true
  cp ~/daily_search/$DATE/compiled_search_truth.json search_compiled/$DATE/ 2>/dev/null || true
fi

# 2. Git提交
echo "[2/4] Git提交..."
git add -A
if git diff --cached --quiet; then
  echo "无变更，跳过提交"
else
  git commit -m "kernel-sync: $DATE 真值快照 | Ω₀⊂⊙∞⊂Ω | DID-BR-000002"
fi

# 3. 推送双远端
echo "[3/4] 推送Gitee..."
git push gitee main --force 2>/dev/null || git push gitee master --force 2>/dev/null || echo "Gitee推送失败"

echo "[4/4] 推送GitHub..."
git push github main --force 2>/dev/null || git push github master --force 2>/dev/null || echo "GitHub推送失败"

echo "=== 同步完成 ==="
echo "Gitee: https://gitee.com/huodou-cloud-intelligence-aios/zongyuan-root-kernel"
echo "GitHub: https://github.com/tanbopiao/zongyuan-root-kernel"
