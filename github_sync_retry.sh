#!/bin/bash
# ZONGYUAN-ROOT GitHub同步重试脚本
# 用途：GitHub网络不稳定时自动重试推送（云端自身仓库 + 本地内核LOCAL仓库）
LOG=/opt/ZONGYUAN-ROOT/github_sync.log
echo "[$(date '+%F %T')] 开始GitHub同步重试" >> $LOG

# 1. 云端自身仓库
cd /opt/ZONGYUAN-ROOT
git fetch origin >> $LOG 2>&1
if [ "$(git rev-list --count origin/master..HEAD 2>/dev/null)" -gt 0 ]; then
  for i in 1 2 3; do
    timeout 100 git push origin master >> $LOG 2>&1 && break
    echo "[$(date '+%T')] 云端仓库push失败(第${i}次)，重试..." >> $LOG
    sleep 20
  done
  echo "[$(date '+%T')] 云端仓库剩余待推送: $(git rev-list --count origin/master..HEAD)" >> $LOG
fi

# 2. 本地内核LOCAL仓库（从裸仓库中转）
if [ -d /tmp/zr-local-clone ]; then
  cd /tmp/zr-local-clone
  git fetch -q /opt/git/ZONGYUAN-ROOT-LOCAL.git main 2>/dev/null
  for i in 1 2 3; do
    timeout 100 git push github main >> $LOG 2>&1 && break
    echo "[$(date '+%T')] LOCAL仓库push失败(第${i}次)，重试..." >> $LOG
    sleep 20
  done
fi

echo "[$(date '+%F %T')] GitHub同步重试结束" >> $LOG
