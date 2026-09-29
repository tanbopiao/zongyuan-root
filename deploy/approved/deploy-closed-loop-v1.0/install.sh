#!/bin/bash
set -e
echo "=== 部署闭环增强V1.0安装 ==="
# 1. 安装增强脚本
mkdir -p /opt/ZONGYUAN-ROOT/worker
cp /opt/ZONGYUAN-ROOT/deploy/approved/deploy-closed-loop-v1.0/enhance.sh /opt/ZONGYUAN-ROOT/worker/
# 2. 把notify注入worker consumer（如果consumer存在，在失败分支后调用notify）
CONSUMER=/opt/ZONGYUAN-ROOT/worker/consumer.sh
if [ -f "$CONSUMER" ]; then
  grep -q "notify.sh" "$CONSUMER" || sed -i 's|bash "$d/rollback.sh" >> $LOG 2>\&1|bash "$d/rollback.sh" >> $LOG 2>\&1; bash /opt/ZONGYUAN-ROOT/worker/notify.sh "$NAME 健康检查失败"|' "$CONSUMER"
  echo "[1/3] 失败告警已注入Worker消费流程"
else
  echo "[1/3] consumer.sh不存在,告警脚本已就位待挂载"
fi
# 3. 立即验证
bash /opt/ZONGYUAN-ROOT/worker/enhance.sh
echo "[2/3] 闭环增强验证完成"
echo "[3/3] 部署完成"
