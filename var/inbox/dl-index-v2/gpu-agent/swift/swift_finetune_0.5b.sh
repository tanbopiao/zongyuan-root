#!/bin/bash
# ============================================================
# ZONGYUAN · SWIFT 微调 0.5b → 元极恒一语义对齐执行体
# 在魔搭 DSW GPU 实例执行。锚定 DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
# 用法: bash swift_finetune_0.5b.sh
# ============================================================
set -e
echo "=== [1/5] 安装 SWIFT (ms-swift) ==="
pip install ms-swift -q 2>&1 | tail -3 || true

echo "=== [2/5] 准备训练数据 ==="
DATA_DIR=/mnt/workspace/ZONGYUAN-SHARED-DATALAKE/gpu-agent/swift
DATASET=$DATA_DIR/swift_seed_data.jsonl
[ -f "$DATASET" ] || { echo "缺失训练数据: $DATASET (先从数据湖拉取)"; exit 1; }

echo "=== [3/5] 拉取 0.5b 基座模型 ==="
MODEL_ID=Qwen/Qwen2.5-0.5B-Instruct
python -c "
from modelscope import snapshot_download
p = snapshot_download('$MODEL_ID')
print('模型路径:', p)
" 2>&1 | tail -5

echo "=== [4/5] 执行 SWIFT LoRA 微调 ==="
swift sft \
  --model "$MODEL_ID" \
  --train_type lora \
  --dataset "$DATASET" \
  --num_train_epochs 4 \
  --learning_rate 2e-4 \
  --lora_rank 8 \
  --lora_alpha 32 \
  --max_length 1024 \
  --batch_size 2 \
  --gradient_accumulation_steps 8 \
  --logging_steps 10 \
  --output_dir /mnt/workspace/output/hengli-0.5b-lora \
  --eval_steps 50 \
  --save_steps 50 \
  --warmup_ratio 0.03 \
  --gradient_checkpointing true 2>&1 | tail -20

echo "=== [5/5] 导出 LoRA 适配器 + 汇总 ==="
mkdir -p /mnt/workspace/output/hengli-0.5b-final
cp -r /mnt/workspace/output/hengli-0.5b-lora/v* /mnt/workspace/output/hengli-0.5b-final/ 2>/dev/null || true
ls -la /mnt/workspace/output/hengli-0.5b-final/
echo "=== 微调完成: /mnt/workspace/output/hengli-0.5b-final ==="
echo "下一步: 合并/量化 或 以 LoRA 挂载推理(vLLM 支持)"
