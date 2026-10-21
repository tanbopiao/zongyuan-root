#!/bin/bash
# git_sync.sh 每日自动git同步
cd /home/user/ZONGYUAN-ROOT
git add -A 2>/dev/null
git commit -m "auto-sync $(date +%F)" 2>/dev/null
git push origin main 2>/dev/null
echo "git同步完成 $(date)"
