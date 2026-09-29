#!/bin/bash
# ZONGYUAN-ROOT 仲裁者合并引擎
# 用法: ./arbiter_merge.sh <分支名> [窗口标识]
# 功能: 合并agent分支到master,冲突检测,自动部署锁,内核同步

set -e
BRANCH="$1"
WINDOW="${2:-unknown}"
KERNEL_DIR="/opt/ZONGYUAN-ROOT"

if [ -z "$BRANCH" ]; then
  echo "用法: $0 <agent/alpha|agent/beta|agent/gamma> [窗口标识]"
  exit 1
fi

cd $KERNEL_DIR

echo "=========================================="
echo "  ZONGYUAN-ROOT 仲裁者合并引擎"
echo "  分支: $BRANCH"
echo "  窗口: $WINDOW"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 1. 检查分支是否存在
if ! git rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
  echo "❌ 分支 $BRANCH 不存在"
  exit 1
fi

# 2. 获取部署锁（合并+部署是原子操作）
echo ""
echo "[1/5] 获取全局部署锁..."
exec 200>/var/lock/zongyuan/deploy.lock
if ! flock -w 300 200; then
  echo "❌ 部署锁超时,有其他窗口正在部署"
  exit 1
fi
echo "  ✅ 部署锁已获取"

# 3. 切换到master并拉取最新
echo ""
echo "[2/5] 同步master..."
git checkout master
git pull origin master 2>/dev/null || true

# 4. 合并分支（no-commit以便检查冲突）
echo ""
echo "[3/5] 合并 $BRANCH → master..."
MERGE_RESULT=$(git merge --no-commit --no-ff "$BRANCH" 2>&1) || true
CONFLICTS=$(git diff --name-only --diff-filter=U 2>/dev/null)

if [ -n "$CONFLICTS" ]; then
  echo "  ⚠️  检测到冲突文件:"
  echo "$CONFLICTS" | sed 's/^/    /'
  echo ""
  echo "  冲突解决策略:"
  echo "    1. 保留master版本: git checkout --ours <file>"
  echo "    2. 保留分支版本: git checkout --theirs <file>"
  echo "    3. 手动合并后: git add <file>"
  echo ""
  echo "  中止合并: git merge --abort"
  git merge --abort 2>/dev/null
  echo "  ❌ 合并因冲突中止,请手动解决后重试"
  exit 1
fi

# 完成合并
git commit -m "merge(arbiter): 合并 $BRANCH from 窗口[$WINDOW] - $(date '+%Y%m%d%H%M')" 2>/dev/null || true
echo "  ✅ 合并成功,无冲突"

# 5. 内核向量时钟递增（仲裁者）
echo ""
echo "[4/5] 仲裁者向量时钟递增..."
python3 -c "
import json
k=json.load(open('$KERNEL_DIR/kernel.json'))
vc=k.get('vector_clock',{'A':0,'B':0,'C':0,'arbiter':0})
vc['arbiter']=vc.get('arbiter',0)+1
k['vector_clock']=vc
k['last_merged_branch']='$BRANCH'
k['last_merged_window']='$WINDOW'
json.dump(k,open('$KERNEL_DIR/kernel.json','w'),ensure_ascii=False,indent=2)
print(f'  向量时钟: {vc}')
"

# 6. 验证关键服务
echo ""
echo "[5/5] 服务验证..."
for svc in zongyuan-aiproxy zongyuan-omega; do
  status=$(systemctl is-active $svc 2>/dev/null || echo "unknown")
  echo "  $svc: $status"
done
echo "  外网画布: $(curl -s -o /dev/null -w '%{http_code}' https://www.huodouai.com/drama/)"
echo "  AI Proxy: $(curl -s -u zongyuan:8v4iGrYBK2Fz9UC -o /dev/null -w '%{http_code}' https://www.huodouai.com/ai-proxy/health)"

# 7. Push到远程
echo ""
echo "[推送] push到GitHub..."
git push origin master 2>&1 | tail -2 || echo "  ⚠️  Push失败(网络),本地已合并"

echo ""
echo "=========================================="
echo "  ✅ 仲裁者合并完成"
echo "  分支: $BRANCH → master"
echo "  窗口: $WINDOW"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
