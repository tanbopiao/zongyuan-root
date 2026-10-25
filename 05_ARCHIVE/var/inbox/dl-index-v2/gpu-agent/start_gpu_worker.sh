#!/usr/bin/env bash
# ============================================================
# ZONGYUAN GPU Worker 自启动+自愈包装脚本 (start_gpu_worker.sh)
# 确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-GPU-AMD
# 原理: 检测/拉取 worker → 后台启动 → GPU心跳上报 → 崩溃自动重启(watchdog)
# 用法(在魔搭 AMD GPU 实例终端):
#   bash start_gpu_worker.sh            # 启动(自动拉取worker)
#   bash start_gpu_worker.sh --nopause # 启动后不进入循环模式(适合脚本调用)
# ============================================================
set -uo pipefail
WORKER="zongyuan_gpu_agent.py"
TOPIC="zongyuan-kunlun-2026"
DATA_LAKE="https://modelscope.cn/datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE.git"
HERE="$(cd "$(dirname "$0")" && pwd)"
LOG="$HERE/gpu_worker.log"
PIDFILE="$HERE/gpu_worker.pid"
NODE="ZR-NODE-GPU-AMD-$(hostname | cut -c1-8)"

echo "════════════════════════════════════════════"
echo "  ZONGYUAN GPU Worker 自启动+自愈 V1.0"
echo "  node=$NODE | topic=$TOPIC"
echo "════════════════════════════════════════════"

# 0) Python 自检
python3 -c "import urllib.request" 2>/dev/null || { echo "❌ python3 不可用"; exit 1; }

# 1) 若 worker 不存在则从魔搭数据湖拉取 (gpu-agent/)
if [ ! -f "$HERE/$WORKER" ]; then
  echo "[1/4] 本目录无 worker，从魔搭数据湖拉取..."
  cd /tmp
  git clone --depth 1 --filter=blob:none --sparse "$DATA_LAKE" dlt_pull 2>/dev/null || rm -rf dlt_pull && git clone --depth 1 --filter=blob:none --sparse "$DATA_LAKE" dlt_pull
  cd dlt_pull && git sparse-checkout set gpu-agent 2>/dev/null
  cp gpu-agent/$WORKER "$HERE/" 2>/dev/null && cp gpu-agent/README.md "$HERE/" 2>/dev/null
  echo "  ✅ worker 已拉取: $HERE/$WORKER"
else
  echo "[1/4] worker 已存在: $HERE/$WORKER"
fi

# 2) 启动 worker (后台)
start_worker() {
  cd "$HERE"
  nohup python3 "$WORKER" >> "$LOG" 2>&1 &
  echo $! > "$PIDFILE"
  echo "  ✅ worker 已启动 PID=$(cat $PIDFILE)"
}

# 3) GPU 心跳上报 (ntfy)
heartbeat() {
  python3 - "$1" << 'PYEOF'
import sys, json, urllib.request, time
node = sys.argv[1]
msg = json.dumps({"zr":"DID-BR-000002","type":"HEARTBEAT","node":node,
                  "ts":time.strftime("%Y-%m-%dT%H:%M:%S"),"payload":{"gpu":"online","role":"worker"}})
try:
    req = urllib.request.Request("https://ntfy.sh/zongyuan-kunlun-2026",
        data=msg.encode(), headers={"Title":"GPU-Worker-Online"})
    urllib.request.urlopen(req, timeout=10)
    print(f"  💓 心跳已上报 ({node})")
except Exception as e:
    print(f"  ⚠️ 心跳上报失败: {e}")
PYEOF
}

# 4) 主流程
echo "[2/4] 上报 GPU 上线心跳..."
heartbeat "$NODE"
echo "[3/4] 启动 worker 守护..."
start_worker

echo "[4/4] 自愈监控启动 (每30s检查, 崩溃自动重启)"
COUNT=0
while true; do
  sleep 30
  if ! kill -0 "$(cat $PIDFILE 2>/dev/null)" 2>/dev/null; then
    COUNT=$((COUNT+1))
    echo "[$(date +%H:%M:%S)] ⚠️ worker 掉线(第${COUNT}次), 重启中..."
    heartbeat "$NODE"
    start_worker
  fi
done
