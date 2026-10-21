#!/bin/bash
# 部署包准入检查：不达标拒绝自动部署
echo "=== 部署准入检查 ==="
DIR=$1
PASS=true
for f in install.sh health_check.sh rollback.sh; do
  [ ! -f "$DIR/$f" ] && echo "❌ 缺 $f" && PASS=false
done
grep -q "set -e" "$DIR/install.sh" 2>/dev/null || { echo "❌ install.sh缺set -e"; PASS=false; }
grep -qE "rm -rf /(opt|home|var/www)" "$DIR/install.sh" 2>/dev/null && { echo "❌ 禁止rm核心目录"; PASS=false; }
grep -q "0.0.0.0" "$DIR"/*.py "$DIR"/*.sh 2>/dev/null && { echo "❌ 禁止监听0.0.0.0"; PASS=false; }
grep -qE "(yum|apt)( install|-y install)" "$DIR/install.sh" 2>/dev/null && { echo "❌ 禁止系统包安装"; PASS=false; }
$PASS && echo "✅ 准入通过" && exit 0 || { echo "❌ 转人工审批"; exit 1; }
