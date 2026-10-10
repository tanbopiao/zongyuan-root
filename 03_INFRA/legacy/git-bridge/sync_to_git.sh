#!/bin/bash
# ZONGYUAN-ROOT 内核真值同步到Git桥接仓库
set -e

REPO_DIR=/opt/ZONGYUAN-ROOT/git-bridge
KERNEL_DIR=/opt/ZONGYUAN-ROOT/kernel

cd $REPO_DIR

# 同步最新文件
cp $KERNEL_DIR/truths/*.json truths/ 2>/dev/null || true
cp $KERNEL_DIR/knowledge_graphs/*.json knowledge-graphs/ 2>/dev/null || true
cp $KERNEL_DIR/cloud_disk_manifests/*.json manifests/ 2>/dev/null || true
cp $KERNEL_DIR/locks/*.json locks/ 2>/dev/null || true
cp $KERNEL_DIR/config/*.json config/ 2>/dev/null || true
cp $KERNEL_DIR/kernel_state.json kernel-state/ 2>/dev/null || true
cp $KERNEL_DIR/root_state.json kernel-state/ 2>/dev/null || true

# 提交
git add -A
git commit -m "sync: kernel truths $(date +%Y%m%d-%H%M%S)" || echo 'No changes'

# 推送到双远程
git push gitee main || git push gitee master || true
git push github main || git push github master || true

echo '同步完成'
