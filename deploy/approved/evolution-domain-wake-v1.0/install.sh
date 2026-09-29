#!/bin/bash
set -e
echo "=== 进化域算子唤醒V1.0安装 ==="
mkdir -p /opt/ZONGYUAN-ROOT/ops/evolve
cp /opt/ZONGYUAN-ROOT/deploy/approved/evolution-domain-wake-v1.0/evolve.py /opt/ZONGYUAN-ROOT/ops/evolve/
echo "[1/3] 进化引擎已安装"
(crontab -l 2>/dev/null | grep -v zb-evolve; echo "45 */6 * * * /usr/bin/python3 /opt/ZONGYUAN-ROOT/ops/evolve/evolve.py >> /var/log/zb-evolve.log 2>&1") | crontab -
echo "[2/3] 每6小时进化代际定时已配置"
python3 /opt/ZONGYUAN-ROOT/ops/evolve/evolve.py
echo "[3/3] 进化域唤醒完成"
