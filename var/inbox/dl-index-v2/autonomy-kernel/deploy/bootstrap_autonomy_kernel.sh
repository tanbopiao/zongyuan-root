#!/bin/bash
# ============================================================
# ZONGYUAN-ROOT 自治内核一键部署脚本
#   Bootstrap Autonomy Kernel
# 确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0 | 火斗云智AIOS
# 版本: V1.0 (2026-10-08)
# 说明: 让任何同源节点一键拉起 "协议 + worker + 云端主控" 自治内核
#       支持 worker 单节点接入, 或云端主控全栈部署
# ============================================================

set -e
echo "══════════════════════════════════════════════"
echo "  ZONGYUAN-ROOT 自治内核引导 | V1.0"
echo "  确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002"
echo "══════════════════════════════════════════════"

# ---------- 0. 探测环境 ----------
KERNEL_DIR="$(cd "$(dirname "$0")/../kernel" && pwd)"
ROLE="${1:-worker}"            # worker | controller | full
NODE_NAME="${2:-}"
NODE_TOKEN_FILE="${NODE_TOKEN_FILE:-/mnt/workspace/.zr/node_token.env}"
WORKSPACE="${WORKSPACE:-/mnt/workspace}"
PYTHON="${PYTHON:-python3}"

echo "[0/4] 角色=$ROLE | 工作区=$WORKSPACE"
command -v "$PYTHON" >/dev/null || { echo "❌ 需要 python3"; exit 1; }
command -v curl >/dev/null || { echo "❌ 需要 curl"; exit 1; }

# ---------- 1. 节点身份 ----------
# 节点 token (同源节点级握手凭证), 无则生成
mkdir -p "$WORKSPACE/.zr"
if [ -f "$NODE_TOKEN_FILE" ]; then
  . "$NODE_TOKEN_FILE" 2>/dev/null || true
  echo "[1/4] 凭证已存在: $ZR_NODE_TOKEN"
else
  if [ -z "$ZR_NODE_TOKEN" ]; then
    ZR_NODE_TOKEN="ZR-NODE-$(hostname | tr 'A-Z' 'a-z' | head -c 20)-$(date +%s)"
  fi
  echo "ZR_NODE_TOKEN=$ZR_NODE_TOKEN" > "$NODE_TOKEN_FILE"
  chmod 600 "$NODE_TOKEN_FILE"
  echo "[1/4] 已生成凭证: $NODE_TOKEN_FILE"
fi

# ---------- 2. 部署核心协议 ----------
echo "[2/4] 部署自治内核协议..."
cp "$KERNEL_DIR/zr_node_protocol.py" "$WORKSPACE/" 2>/dev/null || true
echo "  ✓ zr_node_protocol.py (NTFY-CONNECT-001)"

# ---------- 3. 启动 worker / 主控 ----------
case "$ROLE" in
  worker)
    echo "[3/4] 启动 Worker ($NODE_NAME)..."
    pkill -f "zr_node_worker.py" 2>/dev/null || true
    sleep 1
    ZR_NODE="$NODE_NAME" nohup "$PYTHON" "$KERNEL_DIR/zr_node_worker.py" \
      >> "$WORKSPACE/worker_stdout.log" 2>&1 &
    sleep 3
    if pgrep -f "zr_node_worker.py" >/dev/null; then
      echo "  ✓ Worker 已启动 (PID $(pgrep -f 'zr_node_worker.py' | head -1))"
      tail -2 "$WORKSPACE/worker_stdout.log" | sed 's/^/  /'
    else
      echo "  ❌ Worker 启动失败, 查看 $WORKSPACE/worker_stdout.log"; exit 1
    fi
    ;;
  controller)
    echo "[3/4] 启动云端主控 (controller)..."
    pkill -f "zr_cloud_ctl.py" 2>/dev/null || true
    sleep 1
    nohup "$PYTHON" "$KERNEL_DIR/zr_cloud_ctl.py" >> /tmp/zr_cloud_ctl.log 2>&1 &
    sleep 3
    if pgrep -f "zr_cloud_ctl.py" >/dev/null; then
      echo "  ✓ 主控已启动 (PID $(pgrep -f 'zr_cloud_ctl.py' | head -1))"
    else
      echo "  ❌ 主控启动失败, 查看 /tmp/zr_cloud_ctl.log"; exit 1
    fi
    ;;
  full)
    echo "[3/4] 全栈部署: worker + 主控..."
    bash "$0" worker "$NODE_NAME"
    bash "$0" controller
    ;;
  *)
    echo "❌ 未知角色: $ROLE (worker|controller|full)"; exit 1
    ;;
esac

# ---------- 4. 上线宣告 ----------
echo "[4/4] 握手验证..."
if [ "$ROLE" != "controller" ]; then
  "$PYTHON" -c "
import sys; sys.path.insert(0,'$WORKSPACE')
from zr_node_protocol import report_truth
r = report_truth('REPORT.NODE.BOOT.'+str(__import__('time').time()),
  '{\"node\":\"$NODE_NAME\",\"proto\":\"NTFY-CONNECT-001\",\"role\":\"worker\",\"boot\":True}')
print('  ✓ 真值上报:', r.get('ok'))
" 2>/dev/null || echo "  ⚠ 真值上报跳过(可稍后手动)"
fi

echo "══════════════════════════════════════════════"
echo "✅ 自治内核部署完成!"
echo "  角色: $ROLE | 节点: ${NODE_NAME:-auto}"
echo "  协议: NTFY-CONNECT-001 | 确权: Ω₀⊂⊙∞⊂Ω"
echo "  查看: worker→tail -f $WORKSPACE/worker_stdout.log"
echo "  主控: 控制面 127.0.0.1:9010 (X-CTL-Token)"
echo "══════════════════════════════════════════════"
