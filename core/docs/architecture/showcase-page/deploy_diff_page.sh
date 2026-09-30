#!/bin/bash
# ============================================
# 差异化展示页一键部署脚本
# 在云服务器上执行：bash deploy_diff_page.sh
# ============================================

set -e

echo "=========================================="
echo "  火斗云智AIOS 差异化展示页部署"
echo "=========================================="

# 1. 进入项目目录
cd /data/zongyuan-root || cd /opt/ZONGYUAN-ROOT || {
  echo "❌ 未找到项目目录，请手动修改路径"
  exit 1
}
echo "✅ 进入项目目录: $(pwd)"

# 2. 拉取最新代码
echo ""
echo "--- 拉取最新代码 ---"
git pull origin main
git pull gitee main
echo "✅ 代码拉取完成"

# 3. 查找Web根目录
echo ""
echo "--- 查找Web根目录 ---"
WEB_DIR=""
for dir in /www/wwwroot/www.huodouai.com /www/wwwroot/huodouai.com /var/www/html /usr/share/nginx/html; do
  if [ -d "$dir" ] && [ -f "$dir/index.html" ]; then
    WEB_DIR="$dir"
    break
  fi
done

if [ -z "$WEB_DIR" ]; then
  # 宝塔面板常见路径
  WEB_DIR=$(find /www/wwwroot -name "index.html" -maxdepth 2 2>/dev/null | head -1 | xargs dirname)
fi

if [ -z "$WEB_DIR" ]; then
  echo "⚠️ 未自动找到Web目录，请手动指定"
  echo "  常见路径: /www/wwwroot/www.huodouai.com"
  exit 1
fi

echo "✅ Web根目录: $WEB_DIR"

# 4. 复制差异化展示页
echo ""
echo "--- 部署差异化展示页 ---"
cp showcase-page/differential_capabilities.html "$WEB_DIR/diff/" 2>/dev/null || {
  mkdir -p "$WEB_DIR/diff"
  cp showcase-page/differential_capabilities.html "$WEB_DIR/diff/index.html"
}
echo "✅ 展示页已部署到: $WEB_DIR/diff/index.html"

# 5. 验证部署
echo ""
echo "--- 验证部署 ---"
if curl -s --max-time 3 -o /dev/null -w "%{http_code}" "http://localhost/diff/" | grep -q 200; then
  echo "✅ 本地访问验证通过: http://localhost/diff/"
else
  echo "⚠️ 本地验证未通过，请检查Nginx配置"
fi

# 6. 输出访问地址
echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "  访问地址: https://www.huodouai.com/diff/"
echo "  文件路径: $WEB_DIR/diff/index.html"
echo ""
echo "  如需在导航栏添加入口，请编辑 $WEB_DIR/index.html"
echo "=========================================="
