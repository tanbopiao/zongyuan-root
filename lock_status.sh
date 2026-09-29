#!/bin/bash
echo "=== ZONGYUAN-ROOT 锁状态 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
for lock in deploy kernel_write; do
  f="/var/lock/zongyuan/${lock}.lock"
  owner="/var/lock/zongyuan/${lock}.lock.owner"
  if [ -f "$owner" ]; then
    echo "  $lock: 🔒 被持有 - $(cat $owner)"
  else
    echo "  $lock: 🔓 空闲"
  fi
done
echo ""
echo "=== Git分支 ==="
cd /opt/ZONGYUAN-ROOT && git branch -v 2>/dev/null | sed 's/^/  /'
