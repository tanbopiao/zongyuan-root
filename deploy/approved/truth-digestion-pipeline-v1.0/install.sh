#!/bin/bash
set -e
echo "=== 真值消化管道V1.0安装 ==="
mkdir -p /opt/ZONGYUAN-ROOT/ops/digest
cp /opt/ZONGYUAN-ROOT/deploy/approved/truth-digestion-pipeline-v1.0/digest.py /opt/ZONGYUAN-ROOT/ops/digest/
echo "[1/3] 脚本已安装"
# 定时：每4小时消化一次（轻量，不常驻）
(crontab -l 2>/dev/null | grep -v zb-digest; echo "0 */4 * * * /usr/bin/python3 /opt/ZONGYUAN-ROOT/ops/digest/digest.py >> /var/log/zb-digest.log 2>&1") | crontab -
echo "[2/3] 每4小时消化定时已配置"
# 立即跑一次
python3 /opt/ZONGYUAN-ROOT/ops/digest/digest.py
echo "[3/3] 首次消化完成"
