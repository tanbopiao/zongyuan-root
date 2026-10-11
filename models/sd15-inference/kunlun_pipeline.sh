#!/bin/bash
# ============================================================
# 昆仑洞天 全链路流水线
# 训练LoRA → 推理生成 → 自动归档 → 中枢上报
# 用法: bash kunlun_pipeline.sh <角色目录> <生成次数>
# 例:   bash kunlun_pipeline.sh 004_jiutian_xuannv 3
# ============================================================

set -e

ROLE=${1:-004_jiutian_xuannv}
N_GEN=${2:-3}
MODEL="/home/user/Doubao/models/sd15"
LORA_OUT="./lora_output/${ROLE}"

echo "============================================================"
echo "  昆仑洞天全链路流水线"
echo "  角色: $ROLE | 生成: $N_GEN张"
echo "============================================================"

# 1. 确认LoRA权重存在
echo ""
echo "【1/4】检查LoRA权重..."
if [ ! -f "$LORA_OUT/pytorch_lora_weights.safetensors" ]; then
    echo "  ❌ LoRA权重不存在: $LORA_OUT"
    echo "  先运行训练: bash train_kunlun_lora.sh $ROLE"
    exit 1
fi
echo "  ✅ LoRA就绪"

# 2. 生成提示词模板
echo ""
echo "【2/4】准备生成prompt..."
case $ROLE in
    001_red_goddess)
        PROMPT="kunlun dongtian red goddess, nine-tailed fox, crimson flowing dress, beautiful woman, Chinese fantasy, cinematic lighting, 9:16 vertical, elegant and alluring, Ω₀⊂⊙∞⊂Ω"
        ;;
    004_jiutian_xuannv)
        PROMPT="jiutian xuannv nine heavens mystic goddess, black and gold armor, mysterious bird, Chinese mythology, cinematic, 9:16 vertical, warrior goddess, Ω₀⊂⊙∞⊂Ω"
        ;;
    *)
        PROMPT="kunlun dongtian style goddess, Chinese fantasy, cinematic, 9:16 vertical, Ω₀⊂⊙∞⊂Ω"
        ;;
esac
echo "  prompt: ${PROMPT:0:60}..."

# 3. 批量生成
echo ""
echo "【3/4】开始生成..."
mkdir -p "./pipeline_output"
for i in $(seq 1 $N_GEN); do
    echo "  生成第 $i/$N_GEN 张..."
    python3 "$MODEL/generate_kunlun.py" \
        --lora "$LORA_OUT/pytorch_lora_weights.safetensors" \
        --prompt "$PROMPT" \
        --role "$ROLE" \
        --name "pipeline_${ROLE}_$(date +%s)_$i" \
        --steps 30 \
        --scale 7.5 2>&1 | grep -E "✅|保存|SHA|中枢"
done

# 4. 汇总
echo ""
echo "【4/4】流水线完成"
echo "  生成: $N_GEN 张"
echo "  角色: $ROLE"
echo "  自动归档: ZONGYUAN-ROOT/kunlun-assets/$(date +%Y-%m-%d)/generated/"
echo "  中枢已自动上报"
echo "============================================================"
