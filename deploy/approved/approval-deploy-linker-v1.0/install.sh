#!/bin/bash
# 审批驱动部署联动器 V1.0 - 监听审批通过→触发部署
set -e
echo "=== 审批→部署联动器 V1.0 安装 ==="
mkdir -p /opt/ZONGYUAN-ROOT/engines/approval_linker
# 复制联动器核心
cp approval_deploy_linker.py /opt/ZONGYUAN-ROOT/engines/approval_linker/ 2>/dev/null || echo "WARN: 源文件缺失"
# 注册systemd服务(每5分钟轮询)
cat > /etc/systemd/system/approval-linker.service << 'SVC'
[Unit]
Description=ZONGYUAN-ROOT 审批驱动部署联动器
After=network.target
[Service]
WorkingDirectory=/opt/ZONGYUAN-ROOT/engines/approval_linker
ExecStart=/usr/bin/python3 approval_deploy_linker.py
Restart=always
RestartSec=300
[Install]
WantedBy=multi-user.target
SVC
systemctl daemon-reload
systemctl enable approval-linker.service
systemctl restart approval-linker.service
echo "[安装完成] approval-linker.service 已注册并启动"
