#!/bin/bash
# 一键训练脚本（在AutoDL GPU实例上执行）
# 用法: bash train_lora.sh <角色目录名>
# 例: bash train_lora.sh 004_jiutian_xuannv

ROLE=${1:-004_jiutian_xuannv}
echo "=== 训练昆仑洞天 LoRA: $ROLE ==="

# 安装依赖（首次）
pip install diffusers[torch] transformers accelerate datasets bitsandbytes --quiet

# 训练命令（diffusers官方LoRA训练脚本）
export MODEL_NAME="runwayml/stable-diffusion-v1-5"
export OUTPUT_DIR="./output/${ROLE}_lora"
export INSTANCE_DIR="./${ROLE}"
export INSTANCE_PROMPT="kunlun dongtian style goddess, Chinese fantasy, cinematic, 9:16, Ω₀⊂⊙∞⊂Ω"

python3 -m accelerate.commands.launch \
  --mixed_precision="fp16" \
  train_text_to_image_lora.py \
  --pretrained_model_name_or_path=$MODEL_NAME \
  --instance_data_dir=$INSTANCE_DIR \
  --output_dir=$OUTPUT_DIR \
  --resolution=512 \
  --train_batch_size=2 \
  --gradient_accumulation_steps=4 \
  --learning_rate=1e-4 \
  --lr_scheduler="constant" \
  --lr_warmup_steps=0 \
  --max_train_steps=1500 \
  --checkpointing_steps=500 \
  --seed=42 \
  --instance_prompt="$INSTANCE_PROMPT"

echo "=== 训练完成，LoRA权重在: $OUTPUT_DIR ==="
