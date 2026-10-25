#!/bin/bash
set -e
echo "=== 智能推演引擎V1.0安装 ==="
mkdir -p /opt/ZONGYUAN-ROOT/ops/oracle
cp /opt/ZONGYUAN-ROOT/deploy/approved/intelligence-oracle-v1.0/oracle.py /opt/ZONGYUAN-ROOT/ops/oracle/
echo "[1/3] 推演引擎已安装"
(crontab -l 2>/dev/null | grep -v zb-oracle; echo "15 */6 * * * /usr/bin/python3 /opt/ZONGYUAN-ROOT/ops/oracle/oracle.py >> /var/log/zb-oracle.log 2>&1") | crontab -
echo "[2/3] 每6小时推演定时已配置"
python3 /opt/ZONGYUAN-ROOT/ops/oracle/oracle.py
echo "[3/3] 首次推演完成"
