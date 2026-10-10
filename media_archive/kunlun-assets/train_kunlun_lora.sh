#!/bin/bash
# ============================================================
# 昆仑洞天 LoRA 一键训练脚本 (AutoDL版)
# 用法: bash train_kunlun_lora.sh <角色目录名>
# 例:   bash train_kunlun_lora.sh 004_jiutian_xuannv
# ============================================================

set -e

ROLE=${1:-004_jiutian_xuannv}
MODEL_DIR="./sd15_local"
OUTPUT_DIR="./lora_output/${ROLE}"
INSTANCE_DIR="./lora_dataset/${ROLE}"

echo "============================================================"
echo "  昆仑洞天 LoRA 训练"
echo "  角色: $ROLE"
echo "  数据: $INSTANCE_DIR"
echo "  输出: $OUTPUT_DIR"
echo "============================================================"

# 1. 检查GPU
echo ""
echo "【1/6】检查GPU..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "❌ 未检测到GPU，请在AutoDL GPU实例上运行"
    exit 1
fi

# 2. 安装依赖
echo ""
echo "【2/6】安装依赖..."
pip install -q diffusers[torch] transformers accelerate datasets bitsandbytes safetensors 2>&1 | tail -3

# 3. 检查数据
echo ""
echo "【3/6】检查训练数据..."
N_IMAGES=$(ls $INSTANCE_DIR/*.jpg $INSTANCE_DIR/*.png 2>/dev/null | wc -l)
echo "  训练图片数: $N_IMAGES"
if [ "$N_IMAGES" -lt 10 ]; then
    echo "  ⚠️ 图片数不足10张，效果可能不佳"
fi

# 4. 下载SD1.5基础模型（如果本地没有）
echo ""
echo "【4/6】准备基础模型..."
if [ ! -f "$MODEL_DIR/unet/diffusion_pytorch_model.bin" ]; then
    echo "  下载SD1.5到本地..."
    mkdir -p $MODEL_DIR
    pip install -q huggingface_hub
    python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('runwayml/stable-diffusion-v1-5', local_dir='$MODEL_DIR')
print('  ✅ 模型下载完成')
"
else
    echo "  ✅ 本地模型已存在"
fi

# 5. 生成caption（如果还没有）
echo ""
echo "【5/6】准备caption..."
cd $INSTANCE_DIR
for img in *.jpg *.png; do
    [ -f "$img" ] || continue
    base="${img%.*}"
    if [ ! -f "${base}.txt" ]; then
        echo "kunlun dongtian style goddess, Chinese fantasy, cinematic, 9:16, Ω₀⊂⊙∞⊂Ω" > "${base}.txt"
    fi
done
cd -
echo "  ✅ caption就绪"

# 6. 开始训练
echo ""
echo "【6/6】开始训练..."
mkdir -p $OUTPUT_DIR

accelerate launch --mixed_precision="fp16" \
  --num_processes=1 \
  train_text_to_image_lora.py \
  --pretrained_model_name_or_path=$MODEL_DIR \
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
  --rank=32 \
  --instance_prompt="kunlun dongtian style goddess, Chinese fantasy, cinematic, 9:16"

echo ""
echo "============================================================"
echo "  ✅ 训练完成！"
echo "  LoRA权重: $OUTPUT_DIR/pytorch_lora_weights.safetensors"
echo "  大小: $(du -h $OUTPUT_DIR/pytorch_lora_weights.safetensors 2>/dev/null | awk '{print $1}')"
echo "============================================================"
echo ""
echo "下一步: 把 .safetensors 文件下载到本地持久层 models/lora/"
