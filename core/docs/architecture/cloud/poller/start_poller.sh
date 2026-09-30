#!/bin/bash
# ============================================
# 云内核请求轮询服务 启动脚本
# 在云服务器上执行：bash start_poller.sh
# ============================================

set -e

PROJECT_DIR="/data/zongyuan-root"
SERVICE_NAME="zongyuan-poller"

echo "=========================================="
echo "  云内核请求轮询服务 安装脚本"
echo "=========================================="

# 1. 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
  echo "❌ 项目目录不存在: $PROJECT_DIR"
  echo "请先git clone仓库到 $PROJECT_DIR"
  exit 1
fi
cd "$PROJECT_DIR"
echo "✅ 项目目录: $PROJECT_DIR"

# 2. 拉取最新代码
echo ""
echo "--- 拉取最新代码 ---"
git pull origin main || git pull gitee main
echo "✅ 代码已更新"

# 3. 创建systemd服务
echo ""
echo "--- 创建systemd服务 ---"
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=ZONGYUAN-ROOT Request Poller
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/python3 $PROJECT_DIR/cloud/poller/request_poller.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ systemd服务文件已创建"

# 4. 启动服务
echo ""
echo "--- 启动服务 ---"
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

# 5. 检查状态
echo ""
echo "--- 服务状态 ---"
systemctl status $SERVICE_NAME --no-pager | head -10

echo ""
echo "=========================================="
echo "  安装完成！"
echo "=========================================="
echo ""
echo "  服务名称: $SERVICE_NAME"
echo "  状态查看: systemctl status $SERVICE_NAME"
echo "  日志查看: journalctl -u $SERVICE_NAME -f"
echo "  停止服务: systemctl stop $SERVICE_NAME"
echo "  重启服务: systemctl restart $SERVICE_NAME"
echo ""
echo "  轮询间隔: 60秒"
echo "  每次轮询自动: git pull → 执行请求 → 写入响应 → git push"
echo "=========================================="
