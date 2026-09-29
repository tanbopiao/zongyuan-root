#!/usr/bin/env python3
"""
火斗云智AIOS · 异构架构自适应训练配置器 V1.0
自动检测GPU拓扑/卡数/显存，选择最优并行策略与功耗优化方案
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import json
import subprocess
import os
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class GPUInfo:
    index: int
    name: str
    memory_total_mb: int
    memory_free_mb: int
    pcie_gen: int = 0
    nvlink: bool = False

@dataclass
class HeterogeneousConfig:
    """异构训练最优配置"""
    gpu_count: int
    total_memory_gb: float
    gpu_model: str
    parallel_strategy: str           # single / ddp / tensor / pipeline / zero3
    tensor_parallel_size: int
    pipeline_parallel_size: int
    data_parallel_size: int
    precision: str                   # fp32 / fp16 / bf16 / fp8
    gradient_checkpointing: bool
    cpu_offload: bool
    nvme_offload: bool
    max_model_size_b: float          # 可训练的最大模型参数量(十亿)
    recommended_model: str
    recommended_method: str          # full / lora / qlora
    estimated_power_w: int
    efficiency_score: float          # 0-100, 越高越好
    warnings: List[str] = field(default_factory=list)

def detect_gpus() -> List[GPUInfo]:
    """检测GPU拓扑和显存"""
    gpus = []
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.free,pcie.link.gen.current",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split("\n"):
            if not line.strip(): continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                gpus.append(GPUInfo(
                    index=int(parts[0]),
                    name=parts[1],
                    memory_total_mb=int(parts[2]),
                    memory_free_mb=int(parts[3]),
                    pcie_gen=int(parts[4]) if len(parts) > 4 else 0
                ))
        # 检测NVLink
        try:
            nvlink_result = subprocess.run(
                ["nvidia-smi", "nvlink", "--status"],
                capture_output=True, text=True, timeout=5
            )
            has_nvlink = "active" in nvlink_result.stdout.lower() or "2578" in nvlink_result.stdout
            for g in gpus:
                g.nvlink = has_nvlink
        except: pass
    except FileNotFoundError:
        print("⚠️ nvidia-smi未找到，使用默认单卡配置")
    return gpus

def detect_cpu_memory() -> int:
    """检测CPU内存(GB)"""
    try:
        result = subprocess.run(["free", "-g"], capture_output=True, text=True)
        for line in result.stdout.split("\n"):
            if line.startswith("Mem:"):
                return int(line.split()[1])
    except: pass
    return 32

def select_parallel_strategy(gpus: List[GPUInfo], cpu_mem_gb: int) -> HeterogeneousConfig:
    """根据硬件拓扑选择最优并行策略"""
    if not gpus:
        return HeterogeneousConfig(
            gpu_count=0, total_memory_gb=0, gpu_model="CPU-only",
            parallel_strategy="single", tensor_parallel_size=1,
            pipeline_parallel_size=1, data_parallel_size=1,
            precision="fp32", gradient_checkpointing=False,
            cpu_offload=False, nvme_offload=False,
            max_model_size_b=1, recommended_model="Qwen2.5-1.8B",
            recommended_method="qlora", estimated_power_w=100,
            efficiency_score=20, warnings=["无GPU，仅CPU训练，建议使用QLoRA小模型"]
        )

    n = len(gpus)
    total_mem_gb = sum(g.memory_total_mb for g in gpus) / 1024
    gpu_model = gpus[0].name
    has_nvlink = any(g.nvlink for g in gpus)
    pcie_gen = max(g.pcie_gen for g in gpus)

    warnings = []

    # ---- 并行策略选择 ----
    if n == 1:
        strategy = "single"
        tp = pp = dp = 1
    elif n == 2:
        if has_nvlink or total_mem_gb >= 80:
            strategy, tp, pp, dp = "tensor", 2, 1, 1
        else:
            strategy, tp, pp, dp = "ddp", 1, 1, 2
            warnings.append("双卡无NVLink，使用DDP数据并行，大模型建议开梯度检查点")
    elif n == 4:
        if has_nvlink:
            strategy, tp, pp, dp = "tensor", 4, 1, 1
        elif total_mem_gb >= 160:
            strategy, tp, pp, dp = "pipeline", 1, 4, 1
            warnings.append("4卡流水线并行，注意流水线气泡开销")
        else:
            strategy, tp, pp, dp = "zero3", 1, 1, 4
    elif n >= 8:
        if has_nvlink and total_mem_gb >= 320:
            strategy, tp, pp, dp = "tensor+ddp", 8, 1, 1
        else:
            strategy, tp, pp, dp = "zero3", 1, 1, n
            warnings.append(f"{n}卡使用ZeRO-3，确保InfiniBand/RoCE网络")
    else:
        strategy, tp, pp, dp = "ddp", 1, 1, n

    # ---- 精度选择 ----
    if "A100" in gpu_model or "H100" in gpu_model or "A800" in gpu_model:
        precision = "bf16"
    elif "V100" in gpu_model or "T4" in gpu_model:
        precision = "fp16"
        warnings.append("V100/T4不支持BF16，使用FP16需注意loss溢出")
    else:
        precision = "bf16"

    # ---- 显存优化 ----
    grad_ckpt = total_mem_gb < 200  # 显存小于200G开梯度检查点
    cpu_offload = cpu_mem_gb >= 128 and total_mem_gb < 160
    nvme_offload = total_mem_gb < 80

    # ---- 最大可训练模型估算 ----
    # 全参微调: 模型权重(2GB/B参数 BF16) + 优化器状态(8GB/B参数 Adam) + 梯度(2GB/B) + 激活
    # 粗略: 每1B参数全参约需16GB(不开检查点)或10GB(开检查点)
    mem_per_b_full = 10 if grad_ckpt else 16
    mem_per_b_lora = 1.5  # LoRA只需加载基础模型+少量适配器
    mem_per_b_qlora = 0.8  # QLoRA 4-bit量化

    if strategy in ("zero3", "ddp"):
        effective_mem = total_mem_gb  # ZeRO分片后可用总显存
    elif strategy == "tensor":
        effective_mem = total_mem_gb / tp * 0.85  # 张量并行有通信开销
    elif strategy == "pipeline":
        effective_mem = total_mem_gb / pp * 0.8
    else:
        effective_mem = total_mem_gb * 0.9

    max_full = effective_mem / mem_per_b_full
    max_lora = effective_mem / mem_per_b_lora
    max_qlora = effective_mem / mem_per_b_qlora

    # ---- 推荐模型和方法 ----
    if max_full >= 70:
        recommended_model = "Qwen2.5-72B-Instruct"
        recommended_method = "full"
        max_model = 72
    elif max_full >= 32:
        recommended_model = "Qwen2.5-32B-Instruct"
        recommended_method = "full"
        max_model = 32
    elif max_full >= 14:
        recommended_model = "Qwen2.5-14B-Instruct"
        recommended_method = "full"
        max_model = 14
    elif max_lora >= 72:
        recommended_model = "Qwen2.5-72B-Instruct"
        recommended_method = "lora"
        max_model = 72
    elif max_lora >= 32:
        recommended_model = "Qwen2.5-32B-Instruct"
        recommended_method = "lora"
        max_model = 32
    else:
        recommended_model = "Qwen2.5-14B-Instruct"
        recommended_method = "qlora"
        max_model = 14

    # ---- 功耗估算 ----
    power_per_gpu = 300 if "A100" in gpu_model else (400 if "H100" in gpu_model else 250)
    estimated_power = n * power_per_gpu

    # ---- 效率评分 ----
    score = 50
    if has_nvlink: score += 15
    if precision == "bf16": score += 10
    if n >= 4: score += 10
    if total_mem_gb >= 160: score += 10
    if cpu_offload: score -= 5
    if warnings: score -= len(warnings) * 3
    score = max(10, min(100, score))

    return HeterogeneousConfig(
        gpu_count=n, total_memory_gb=round(total_mem_gb, 1),
        gpu_model=gpu_model, parallel_strategy=strategy,
        tensor_parallel_size=tp, pipeline_parallel_size=pp,
        data_parallel_size=dp, precision=precision,
        gradient_checkpointing=grad_ckpt, cpu_offload=cpu_offload,
        nvme_offload=nvme_offload, max_model_size_b=round(max_model, 1),
        recommended_model=recommended_model, recommended_method=recommended_method,
        estimated_power_w=estimated_power, efficiency_score=score,
        warnings=warnings
    )

def generate_training_command(config: HeterogeneousConfig, train_data: str, output_dir: str) -> str:
    """根据配置生成实际训练命令"""
    base = f"""torchrun --nproc_per_node={config.gpu_count} train.py \\
  --model_name_or_path {config.recommended_model} \\
  --train_data {train_data} \\
  --output_dir {output_dir} \\
  --precision {config.precision} \\
  --max_seq_length 4096 \\
  --batch_size 4 --gradient_accumulation_steps 8 \\
  --learning_rate 2e-5 --num_train_epochs 3 \\
  --warmup_ratio 0.03 --weight_decay 0.01 \\
  --lr_scheduler_type cosine \\
  --logging_steps 10 --save_steps 500"""

    if config.gradient_checkpointing:
        base += " \\\n  --gradient_checkpointing"
    if config.cpu_offload:
        base += " \\\n  --cpu_offload"
    if config.recommended_method == "lora":
        base += " \\\n  --use_lora --lora_r 64 --lora_alpha 128"
    elif config.recommended_method == "qlora":
        base += " \\\n  --use_qlora --load_in_4bit"
    if config.parallel_strategy == "zero3":
        base += " \\\n  --zero_stage 3"
    elif config.parallel_strategy == "tensor":
        base += f" \\\n  --tensor_parallel_size {config.tensor_parallel_size}"

    return base

def main():
    print("=" * 60)
    print("  火斗云智AIOS · 异构架构自适应训练配置器")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 60)

    gpus = detect_gpus()
    cpu_mem = detect_cpu_memory()

    print(f"\n📊 硬件检测:")
    print(f"  GPU数量: {len(gpus)}")
    for g in gpus:
        print(f"    GPU{g.index}: {g.name} | 显存: {g.memory_total_mb//1024}G | 空闲: {g.memory_free_mb//1024}G | NVLink: {'是' if g.nvlink else '否'}")
    print(f"  CPU内存: {cpu_mem}G")

    config = select_parallel_strategy(gpus, cpu_mem)

    print(f"\n🎯 最优训练配置:")
    print(f"  并行策略: {config.parallel_strategy} (TP={config.tensor_parallel_size}, PP={config.pipeline_parallel_size}, DP={config.data_parallel_size})")
    print(f"  训练精度: {config.precision}")
    print(f"  梯度检查点: {'开启' if config.gradient_checkpointing else '关闭'}")
    print(f"  CPU Offload: {'开启' if config.cpu_offload else '关闭'}")
    print(f"  推荐模型: {config.recommended_model}")
    print(f"  训练方式: {config.recommended_method}")
    print(f"  最大可训练: {config.max_model_size_b}B参数")
    print(f"  预估功耗: {config.estimated_power_w}W")
    print(f"  效率评分: {config.efficiency_score}/100")

    if config.warnings:
        print(f"\n⚠️ 注意事项:")
        for w in config.warnings:
            print(f"  - {w}")

    # 生成配置文件
    config_dict = {
        "version": "1.0",
        "did": "DID-BR-000002",
        "anchor": "Ω₀⊂⊙∞⊂Ω",
        "detected_hardware": {
            "gpu_count": config.gpu_count,
            "gpu_model": config.gpu_model,
            "total_memory_gb": config.total_memory_gb,
            "cpu_memory_gb": cpu_mem
        },
        "optimal_config": {
            "parallel_strategy": config.parallel_strategy,
            "tensor_parallel_size": config.tensor_parallel_size,
            "pipeline_parallel_size": config.pipeline_parallel_size,
            "data_parallel_size": config.data_parallel_size,
            "precision": config.precision,
            "gradient_checkpointing": config.gradient_checkpointing,
            "cpu_offload": config.cpu_offload,
            "nvme_offload": config.nvme_offload
        },
        "recommendation": {
            "model": config.recommended_model,
            "method": config.recommended_method,
            "max_model_size_b": config.max_model_size_b,
            "estimated_power_w": config.estimated_power_w,
            "efficiency_score": config.efficiency_score
        },
        "warnings": config.warnings,
        "generated_at": __import__("datetime").datetime.now().isoformat()
    }

    os.makedirs("config", exist_ok=True)
    with open("config/heterogeneous_config.json", "w") as f:
        json.dump(config_dict, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 配置已保存: config/heterogeneous_config.json")

    cmd = generate_training_command(config, "data/train.json", "output/final_model")
    print(f"\n📋 训练命令:")
    print(cmd)
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
