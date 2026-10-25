#!/usr/bin/env bash
# ZONGYUAN-ROOT 一键小模型训练启动器 V1.0
# 确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-GPU-AMD
# 用法:
#   bash one_click_train.sh                # 默认 (Qwen2.5-3B, 显存自适应)
#   bash one_click_train.sh qwen25-7b      # 7B 全参 (192G 显存推荐)
#   bash one_click_train.sh qwen25-3b      # 3B 全参
#   bash one_click_train.sh qwen25-1.5b    # 1.5B (小显存/快速验证)
#   bash one_click_train.sh --epochs 2     # 透传训练参数
set -euo pipefail

echo "══════════════════════════════════════════"
echo "  ZONGYUAN-ROOT 一键训练 · AMD GPU 实例"
echo "══════════════════════════════════════════"

# 0) 环境自检
python3 - << 'PYEOF'
import torch
print(f"PyTorch: {torch.__version__}")
print(f"ROCm/CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"显存: {gb:.0f} GB  | 设备: {torch.cuda.get_device_name(0)}")
print(f"HIP版本: {getattr(torch.version, 'hip', 'N/A')}")
PYEOF

# 1) 模型映射
MODEL=""
case "${1:-default}" in
  qwen25-7b)   MODEL="Qwen/Qwen2.5-7B-Instruct"; shift ;;
  qwen25-3b)   MODEL="Qwen/Qwen2.5-3B-Instruct"; shift ;;
  qwen25-1.5b) MODEL="Qwen/Qwen2.5-1.5B-Instruct"; shift ;;
  --*)         MODEL="Qwen/Qwen2.5-3B-Instruct" ;;
  default)     MODEL="Qwen/Qwen2.5-3B-Instruct" ;;
  *)           echo "未知参数: $1 (支持 qwen25-7b/3b/1.5b 或透传训练参数)"; exit 1 ;;
esac

echo "基座模型: $MODEL"
echo "开始训练 (Ctrl+C 可中断, 断点由 Trainer 自动保存)..."

# 2) 执行训练
if [ -n "$*" ]; then
  python3 one_click_train.py --model "$MODEL" "$@"
else
  python3 one_click_train.py --model "$MODEL"
fi

# 3) 结果提示
echo ""
echo "══════════════════════════════════════════"
echo "  ✅ 训练结束! 产物: output_oneclick/"
echo "  打包下载:  tar czf output_oneclick.tar.gz output_oneclick"
echo "  (或直接用:  ls output_oneclick/model_merged)"
echo "══════════════════════════════════════════"
