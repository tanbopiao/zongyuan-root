#!/bin/bash
# 火斗云智AIOS 官网×自动展示站 一键集成脚本
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 2026-09-30 | 零成本
set -e
WEB_ROOT="/www/wwwroot/www.huodouai.com"   # 官网根目录(宝塔默认)
SHOW_DIR="$WEB_ROOT/showcase"
DL_URL="https://www.modelscope.cn/datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE/resolve/master/zongyuan-root/web"
echo "=== [1/5] 建立官网展示目录 ==="
mkdir -p "$SHOW_DIR"
echo "=== [2/5] 从魔搭拉取自动展示站 ==="
# 用curl拉取(免git凭据,公开仓库); 或用 git clone --depth 1 数据湖后拷贝
cd /tmp && rm -rf dl_sync && git clone --depth 1 "https://www.modelscope.cn/datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE.git" dl_sync 2>/dev/null || true
if [ -d /tmp/dl_sync/zongyuan-root/web ]; then
  cp -rf /tmp/dl_sync/zongyuan-root/web/* "$SHOW_DIR/"
  echo "  已同步 $(ls "$SHOW_DIR" | wc -l) 项"
else
  echo "  git通道失败, 退curl直拉"
  curl -sL -o "$SHOW_DIR/INDEX.html" "$DL_URL/INDEX.html"
  mkdir -p "$SHOW_DIR/showcase"
  for p in index architecture assets truth whitepaper reports; do
    curl -sL -o "$SHOW_DIR/showcase/$p.html" "$DL_URL/showcase/$p.html" || true
  done
fi
echo "=== [3/5] 首页加入口链接(幂等) ==="
IDX="$WEB_ROOT/index.html"
if [ -f "$IDX" ] && ! grep -q '/showcase/' "$IDX"; then
  sed -i 's#</body>#<a href="/showcase/" style="position:fixed;right:18px;bottom:18px;z-index:9999;background:#c9a962;color:#0d0d0f;padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:bold">体系展示</a></body>#' "$IDX" || true
  echo "  首页入口已加"
else
  echo "  入口已存在,跳过"
fi
echo "=== [4/5] nginx校验重载 ==="
nginx -t 2>&1 | tail -1 && systemctl reload nginx 2>/dev/null || echo "  nginx重载跳过(手动)"
echo "=== [5/5] 注册10分钟自动同步 ==="
CRON_LINE="*/10 * * * * curl -sL -o $SHOW_DIR/INDEX.html $DL_URL/INDEX.html && mkdir -p $SHOW_DIR/showcase && for p in index architecture assets truth whitepaper reports; do curl -sL -o $SHOW_DIR/showcase/\$p.html $DL_URL/showcase/\$p.html; done"
( crontab -l 2>/dev/null | grep -v 'showcase' ; echo "$CRON_LINE" ) | crontab -
echo "=== 完成: 官网展示子域已挂载,每10分钟自动同步 ==="
