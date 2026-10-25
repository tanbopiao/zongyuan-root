#!/bin/bash
# 一键LoRA微调脚本
# 用法: bash run_lora_train.sh [数据文件] [输出目录]
# 需要: GPU环境 + transformers + peft + torch

DATA_FILE=${1:-"/root/zongyuan-yuanji/data/train_small.jsonl"}
OUT_DIR=${2:-"/root/zongyuan-yuanji/weights/lora_adapter_new"}
MODEL_PATH="/root/zongyuan-yuanji/weights/yuanjihengyi_int4"

echo "=== LoRA微调启动 ==="
echo "数据: $DATA_FILE"
echo "模型: $MODEL_PATH"
echo "输出: $OUT_DIR"
echo ""

python3 /root/zongyuan-yuanji/scripts/lora_train_v7.py \
  --data $DATA_FILE \
  --model $MODEL_PATH \
  --output $OUT_DIR

echo "=== 训练完成 ==="
