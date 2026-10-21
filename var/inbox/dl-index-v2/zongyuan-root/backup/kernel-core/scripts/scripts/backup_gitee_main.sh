#!/usr/bin/env bash
# 收敛备份：将本地 zongyuan-kernel 最新快照同步到主仓库 ZONGYUAN-ROOT 的
# 00_KERNEL/zongyuan-kernel-20260925/ 子目录并推送 main 分支。
# 仅更新该子目录，不覆盖主仓库其他任何文件；凭据来自本机 git credential store。
set -euo pipefail

LOCAL_KERNEL="/home/user/Doubao/chats/38412149511142658/zongyuan-kernel"
REMOTE="https://gitee.com/huodou-cloud-intelligence-aios/ZONGYUAN-ROOT.git"
SUB_DIR="00_KERNEL/zongyuan-kernel-20260925"
WORK="/tmp/zr-converge-backup"

echo ">>> [1/4] 拉取主仓库 main"
rm -rf "$WORK"
git clone --depth 1 --branch main "$REMOTE" "$WORK" >/dev/null 2>&1
cd "$WORK"

echo ">>> [2/4] 同步内核快照到 $SUB_DIR"
mkdir -p "$SUB_DIR"
rsync -a --delete \
  --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude 'var/reports' --exclude 'var/lock' --exclude 'var/state' \
  --exclude 'var/run' --exclude 'var/truth' --exclude 'console/_shots' \
  "$LOCAL_KERNEL/" "$SUB_DIR/"

echo ">>> [3/4] 提交"
git config user.name "火斗云智AIOS"
git config user.email "huodou@huodouai.com"
git add "$SUB_DIR"
if git diff --cached --quiet; then
  echo "无变更，跳过提交"
else
  git commit -m "sync: zongyuan-kernel 内核快照更新 $(date +'%F %T')" >/dev/null
fi

echo ">>> [4/4] 推送 main"
git push origin main 2>&1 | tail -2

cd / && rm -rf "$WORK"
echo ">>> 完成"
