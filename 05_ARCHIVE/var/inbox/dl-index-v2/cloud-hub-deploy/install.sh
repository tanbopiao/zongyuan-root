#!/usr/bin/env bash
# cloud-hub-deploy/install.sh · 云端中枢元内核 + 官网 一键部署
# 用法(重装后, 已 SSH 登录): bash install.sh
set -e
cd "$(dirname "$0")"
HUB_DIR="${HUB_DIR:-/www/wwwroot/huodouai.com/zhongshu}"
DOCROOT="${DOCROOT:-/www/wwwroot/huodouai.com}"
echo "=== 云端中枢元内核 + 官网 部署 ==="
echo "[1/6] 安装依赖"
if command -v apt-get >/dev/null; then
  sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-pip curl supervisor git >/dev/null 2>&1 || true
fi
echo "[2/6] 建目录"
mkdir -p "$HUB_DIR/data/truth"
echo "[3/6] 部署中枢服务"
cp -r zhongshu-server "$HUB_DIR/"
chmod +x "$HUB_DIR/zhongshu-server/run.sh"
echo "[4/6] 官网 docroot 恢复"
[ -d "$DOCROOT" ] || mkdir -p "$DOCROOT"
if [ -f "official-site-recover/homepage-mirror.tar.gz" ]; then
  tar -xzf official-site-recover/homepage-mirror.tar.gz -C "$DOCROOT" --strip-components=1 && echo "  官网镜像已恢复"
else
  echo "  ⚠ 官网镜像未随包携带 —— 请从本地 scp 传输 homepage-mirror.tar.gz 后重跑本步"
fi
echo "[5/6] supervisor 常驻"
[ -f /etc/supervisor/conf.d/zhongshu.conf ] || cp "$HUB_DIR/zhongshu-server/supervisor-zhongshu.conf" /etc/supervisor/conf.d/zhongshu.conf
[ -f /etc/supervisord.conf ] && { supervisorctl reread || true; supervisorctl update || true; } || { echo "  无 supervisor，将用 nohup 启动"; bash "$HUB_DIR/zhongshu-server/run.sh" start; }
echo "[6/6] 部署完成"
bash verify.sh || true
