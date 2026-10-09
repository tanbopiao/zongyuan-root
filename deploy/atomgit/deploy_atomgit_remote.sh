#!/bin/bash
# 云端Worker执行：添加AtomGit第三远端并同步
# PROTO-DEPLOY-001 部署工单

set -e
REPO_DIR="/opt/ZONGYUAN-ROOT"  # 云端仓库路径，Worker会自动定位
ATOMGIT_TOKEN="KVovfrVnasw6WzLtfbx9tBqp"
ATOMGIT_REPO="https://zongyuangen:${ATOMGIT_TOKEN}@atomgit.com/zongyuangen/my_first_repo.git"

echo "=== AtomGit第三远端部署 ==="
echo "时间: $(date)"

# 定位仓库
if [ -d "/opt/ZONGYUAN-ROOT/.git" ]; then
    REPO_DIR="/opt/ZONGYUAN-ROOT"
elif [ -d "/home/user/ZONGYUAN-ROOT/.git" ]; then
    REPO_DIR="/home/user/ZONGYUAN-ROOT"
elif [ -d "/root/ZONGYUAN-ROOT/.git" ]; then
    REPO_DIR="/root/ZONGYUAN-ROOT"
else
    echo "❌ 未找到ZONGYUAN-ROOT仓库"
    exit 1
fi

echo "仓库路径: $REPO_DIR"
cd "$REPO_DIR"

# 添加或更新atomgit remote
if git remote | grep -q atomgit; then
    git remote set-url atomgit "$ATOMGIT_REPO"
    echo "✅ 更新atomgit remote"
else
    git remote add atomgit "$ATOMGIT_REPO"
    echo "✅ 添加atomgit remote"
fi

# 推送到AtomGit
git push atomgit main --force 2>&1
echo "✅ 已同步main到AtomGit"

# 配置post-commit hook自动同步
cat > .git/hooks/post-commit << 'HOOK'
#!/bin/bash
git push atomgit main 2>/dev/null &
HOOK
chmod +x .git/hooks/post-commit
echo "✅ post-commit hook已配置"

echo "=== 部署完成 ==="
echo "三远端: $(git remote -v | grep push | wc -l)个"
