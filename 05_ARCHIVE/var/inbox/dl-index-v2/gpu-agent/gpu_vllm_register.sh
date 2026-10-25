#!/bin/bash
# ============================================================
# gpu_vllm_register.sh · 魔搭 GPU 实例 vLLM 推理接入注册 V1.0
# ZONGYUAN-ROOT 通用协议全面兼容 · OpenAI 兼容端点 GPU 推理接入
# 用法: bash gpu_vllm_register.sh [model] [port]
#   默认 model=Qwen/Qwen2.5-7B-Instruct, port=8000
# 流程: 检测GPU → 拉起vLLM → 注册云端 /v1/gpu/register → 上报联邦
# ============================================================
set -e
MODEL="${1:-Qwen/Qwen2.5-7B-Instruct}"
PORT="${2:-8000}"
NODE_ID="ZR-NODE-GPU-$(hostname | cut -c1-8)"
CLOUD="https://www.huodouai.com"
TS=$(date +%s)

echo "════════ ZONGYUAN GPU vLLM 推理接入 ════════"
echo "节点: $NODE_ID | 模型: $MODEL | 端口: $PORT"

# 1. 检测 GPU
echo "[1/5] 检测 GPU..."
if ! python3 -c "import torch; print('GPU:', torch.cuda.get_device_name(0))" 2>/dev/null; then
  echo "⚠️ 无GPU可用(CPU模式回退)"; GPU_MODE="cpu"
else
  GPU_MODE="cuda"
fi

# 2. 安装/检查 vLLM (最小额度: 已装则跳过)
echo "[2/5] 检查 vLLM..."
if ! python3 -c "import vllm" 2>/dev/null; then
  echo "  vLLM 未装, 安装中... (pip install vllm)"
  pip install -q vllm 2>&1 | tail -1
fi

# 3. 拉起 vLLM (后台)
echo "[3/5] 拉起 vLLM (model=$MODEL port=$PORT)..."
pkill -f "vllm.entrypoints.openai.api_server" 2>/dev/null || true
nohup python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
  --port "$PORT" \
  --served-model-name "zr-gpu-$(echo $MODEL | tr '/' '-')" \
  > /mnt/workspace/vllm.log 2>&1 &
VLLM_PID=$!
echo "  vLLM PID: $VLLM_PID, 等待就绪..."

# 4. 等待就绪 (最多90s)
echo "[4/5] 等待 vLLM 就绪..."
for i in $(seq 1 18); do
  if curl -s -m 3 "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    echo "  ✅ vLLM 就绪 (${i}x5s)"
    break
  fi
  [ $i -eq 18 ] && { echo "  ❌ vLLM 启动超时, 查看 /mnt/workspace/vllm.log"; exit 1; }
  sleep 5
done

# 5. 注册云端 + 上报联邦
echo "[5/5] 注册云端 OpenAI 兼容端点..."
curl -s -m 10 -X POST "${CLOUD}/api/report/truth" \
  -H "Content-Type: application/json" \
  -H "X-DID: DID-BR-000002" \
  -d "{\"key\":\"GPU.VLLM.REGISTER.${TS}\",\"value\":{\"content\":\"GPU实例vLLM推理接入注册\",\"node\":\"${NODE_ID}\",\"model\":\"${MODEL}\",\"endpoint\":\"http://127.0.0.1:${PORT}/v1/chat/completions\",\"mode\":\"${GPU_MODE}\",\"ts\":${TS},\"did\":\"DID-BR-000002\"}}" \
  | head -c 120
echo ""

echo "════════ 接入完成 ════════"
echo "本地 OpenAI 兼容端点: http://127.0.0.1:${PORT}/v1"
echo "测试: curl http://127.0.0.1:${PORT}/v1/models"
echo "云端联邦: ${CLOUD}/v1/federated/status"
echo "NODE_ID: ${NODE_ID}"
