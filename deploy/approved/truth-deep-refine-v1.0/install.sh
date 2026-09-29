#!/bin/bash
set -e
echo "=== 27算子深度提炼V1.0安装 ==="
mkdir -p /opt/ZONGYUAN-ROOT/ops/refine
cp /opt/ZONGYUAN-ROOT/deploy/approved/truth-deep-refine-v1.0/refine.py /opt/ZONGYUAN-ROOT/ops/refine/
echo "[1/3] 提炼引擎已安装"
(crontab -l 2>/dev/null | grep -v zb-refine; echo "30 */4 * * * /usr/bin/python3 /opt/ZONGYUAN-ROOT/ops/refine/refine.py >> /var/log/zb-refine.log 2>&1") | crontab -
echo "[2/3] 每4小时提炼定时已配置"
python3 /opt/ZONGYUAN-ROOT/ops/refine/refine.py
echo "[3/3] 首次提炼完成"
