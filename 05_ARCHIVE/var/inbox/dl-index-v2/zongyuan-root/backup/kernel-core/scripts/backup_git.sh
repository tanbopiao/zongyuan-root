#!/usr/bin/env bash
# 双 Git 仓库签名备份：将内核（含元法则/配置/基线状态）提交并推送到 Gitee + GitHub。
#
# 用法:
#   export ZONGYUAN_ROOT=/opt/zongyuan-kernel   # 默认即 /opt/zongyuan-kernel
#   sudo bash scripts/backup_git.sh "月度备份"
#
# 首次需配置远端与签名:
#   cd "$ZONGYUAN_ROOT" && git init
#   git remote add gitee  https://gitee.com/<你>/<repo>.git
#   git remote add github https://github.com/<你>/<repo>.git
#   git config user.signingkey <GPG指纹>        # 启用 GPG 签名提交
#   git config user.name / user.email
set -euo pipefail

DEST="${ZONGYUAN_ROOT:-/opt/zongyuan-kernel}"
MSG="${1:-zongyuan-kernel backup $(date +'%F %T')}"

cd "$DEST"
[ -d .git ] || { echo "错误: $DEST 不是 Git 仓库，请先 git init 并配置 gitee/github 远端"; exit 1; }

git add -A

SIGNED=0
if git config user.signingkey >/dev/null 2>&1; then
    git commit -S -m "$MSG" >/dev/null 2>&1 && SIGNED=1 || true
fi
if [ "$SIGNED" -eq 0 ]; then
    git commit -m "$MSG（未配置 GPG 签名密钥，本次未签名）" >/dev/null 2>&1 || echo "提示: 无新变更，跳过提交"
fi

echo ">>> 推送到 gitee"
git push gitee HEAD 2>&1 || echo "警告: gitee 推送失败，请检查 remote 配置与凭证"
echo ">>> 推送到 github"
git push github HEAD 2>&1 || echo "警告: github 推送失败，请检查 remote 配置与凭证"

echo ">>> 完成: $MSG"
git log --oneline -1
