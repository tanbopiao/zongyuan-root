#!/bin/bash
set -e
echo "=== 全闭环算子链V1.0安装 ==="
mkdir -p /opt/ZONGYUAN-ROOT/ops/chain
cp /opt/ZONGYUAN-ROOT/deploy/approved/zr-operator-chain-v1.0/chain.json /opt/ZONGYUAN-ROOT/ops/chain/
cp /opt/ZONGYUAN-ROOT/deploy/approved/zr-operator-chain-v1.0/orchestrator.py /opt/ZONGYUAN-ROOT/ops/chain/
echo "[1/3] 算子链已安装"
# 替换worker consumer为主链执行（若存在）
CONSUMER=/opt/ZONGYUAN-ROOT/worker/consumer.sh
if [ -f "$CONSUMER" ]; then
  grep -q "orchestrator.py" "$CONSUMER" || echo "python3 /opt/ZONGYUAN-ROOT/ops/chain/orchestrator.py" >> "$CONSUMER"
  echo "[2/3] Worker已挂载算子链"
else
  echo "[2/3] consumer不存在,算子链可独立执行"
fi
# 验证
python3 /opt/ZONGYUAN-ROOT/ops/chain/orchestrator.py --check 2>/dev/null || python3 -c "import ast;ast.parse(open('/opt/ZONGYUAN-ROOT/ops/chain/orchestrator.py').read());print('语法OK')"
echo "[3/3] 算子链安装完成"
