#!/usr/bin/env bash
# ============================================================
# ZONGYUAN 同源节点 · 一键快速接入 (zr_node_connect.sh)
# 确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 协议: NTFY-CONNECT-001
# 用法(实例侧, 一行):
#   bash zr_node_connect.sh
# 可选环境变量:
#   ZR_NODE=ZR-NODE-MODEL-GPU-01   自定义节点名
#   NTFY_MODE=strict|legacy        严格(默认)/兼容旧命令
# 功能: 拉取worker → 启动 → 发上线宣告 → 验证
# ============================================================
set -uo pipefail
echo "════════════════════════════════════════════"
echo "  ZONGYUAN 同源节点一键接入 · NTFY-CONNECT-001"
echo "════════════════════════════════════════════"

WORK_DIR="${ZR_WORK_DIR:-/mnt/workspace}"
cd "$WORK_DIR" || exit 1

# 1) 拉取协议+worker+client (本地已有则跳过)
if [ ! -f "zr_node_worker.py" ] || [ ! -f "zr_node_protocol.py" ]; then
  echo "[1/4] 从魔搭拉取联通套件..."
  rm -rf /tmp/zr_connect && git clone --depth 1 --filter=blob:none --sparse \
    "https://modelscope.cn/datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE.git" /tmp/zr_connect 2>/dev/null
  cd /tmp/zr_connect && git sparse-checkout set gpu-agent 2>/dev/null
  cp gpu-agent/zr_node_protocol.py gpu-agent/zr_node_worker.py gpu-agent/zr_node_client.py . 2>/dev/null
  cd "$WORK_DIR"
  echo "  ✅ 拉取完成"
fi

# 2) 停止旧 boot.py (如有)
echo "[2/4] 检查旧worker..."
pkill -f "python3 boot.py" 2>/dev/null && echo "  已停止旧boot.py" || echo "  无旧boot.py"

# 3) 启动标准 worker
echo "[3/4] 启动标准 worker..."
nohup python3 zr_node_worker.py > worker_stdout.log 2>&1 &
sleep 3
if ps aux | grep -q "[z]r_node_worker.py"; then
  echo "  ✅ worker 已启动"
else
  echo "  ⚠️ 启动失败, 查看 worker_stdout.log"
  tail -5 worker_stdout.log
  exit 1
fi

# 4) 确认上线宣告
echo "[4/4] 上线宣告..."
tail -3 worker_stdout.log

echo "════════════════════════════════════════════"
echo "✅ 接入完成! 本地侧执行握手验证:"
echo "  python3 zr_node_client.py --handshake"
echo "════════════════════════════════════════════"
