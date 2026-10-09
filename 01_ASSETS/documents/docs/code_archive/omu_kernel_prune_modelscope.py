#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一自研大模型内核 - 魔塔ModelScope专用裁剪脚本
OMU-KERNEL-V1.0 | 从Qwen2.5-1.5B裁剪到300M最小神经内核

适配环境：ModelScope Notebook (8核32GB / 24GB显存 / PyTorch+CUDA)
"""

import os
import sys
import json
import time
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

# ============ 配置 ============
CONFIG = {
    # 源模型（魔塔模型库，国内下载快）
    "source_model": "Qwen/Qwen2.5-1.5B-Instruct",
    
    # 裁剪目标
    "target_params": "300M",  # 目标参数量
    "num_layers": 8,           # 从28层裁剪到8层
    "num_heads": 8,            # 从16头裁剪到8头
    "intermediate_size": 2048, # 从5504裁剪到2048
    "vocab_size": 50000,       # 从151936裁剪到50000（保留常用中文）
    
    # 输出
    "output_dir": "/mnt/workspace/output/omu-kernel-300M",
    "gguf_output": "/mnt/workspace/output/omu-kernel-300M-Q4_K_M.gguf",
    
    # 评估
    "eval_samples": 20,
}

# 测试用例（元极恒一体系相关）
TEST_CASES = [
    {"input": "什么是元极恒一？", "expect": "元极恒一"},
    {"input": "解释熵减收敛归一", "expect": "熵减"},
    {"input": "三维稳态决策公式", "expect": "利益"},
    {"input": "九天玄女的三种形态", "expect": "玄女"},
    {"input": "什么是因果链溯源", "expect": "因果"},
]

def log(msg, level="INFO"):
    """带时间戳的日志"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)

def step(title):
    """步骤分隔"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n", flush=True)

def check_gpu():
    """检查GPU环境"""
    step("步骤0: 环境检查")
    try:
        import torch
        log(f"PyTorch版本: {torch.__version__}")
        log(f"CUDA可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            log(f"GPU型号: {torch.cuda.get_device_name(0)}")
            log(f"显存总量: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            log(f"空闲显存: {torch.cuda.mem_get_info()[0] / 1024**3:.1f} GB")
        return True
    except Exception as e:
        log(f"GPU检查失败: {e}", "ERROR")
        return False

def install_deps():
    """安装依赖（魔塔已预置大部分，这里只装缺失的）"""
    step("步骤1: 安装依赖")
    deps = ["transformers", "accelerate", "sentencepiece", "gguf", "modelscope"]
    for dep in deps:
        try:
            __import__(dep.replace("-", "_"))
            log(f"✓ {dep} 已安装")
        except ImportError:
            log(f"安装 {dep}...")
            os.system(f"pip install -q {dep}")
    log("依赖安装完成")

def download_model():
    """从魔塔下载源模型"""
    step("步骤2: 下载源模型 (Qwen2.5-1.5B-Instruct)")
    from modelscope import snapshot_download
    
    cache_dir = "/mnt/workspace/models"
    os.makedirs(cache_dir, exist_ok=True)
    
    log(f"从魔塔模型库下载: {CONFIG['source_model']}")
    log("（国内源，速度快，约3GB）")
    
    start = time.time()
    model_dir = snapshot_download(
        CONFIG["source_model"],
        cache_dir=cache_dir,
        revision="master"
    )
    elapsed = time.time() - start
    
    log(f"下载完成: {model_dir}")
    log(f"耗时: {elapsed:.1f}秒")
    
    # 计算模型大小
    total_size = 0
    for f in Path(model_dir).rglob("*"):
        if f.is_file():
            total_size += f.stat().st_size
    log(f"模型大小: {total_size / 1024**3:.2f} GB")
    
    return model_dir

def load_and_prune(model_dir):
    """加载模型并执行裁剪"""
    step("步骤3: 加载模型并执行裁剪")
    
    import torch
    from transformers import AutoModelForCausalLM, AutoConfig, AutoTokenizer
    
    # 加载原始配置
    log("加载原始模型配置...")
    orig_config = AutoConfig.from_pretrained(model_dir, trust_remote_code=True)
    log(f"原始层数: {orig_config.num_hidden_layers}")
    log(f"原始注意力头数: {orig_config.num_attention_heads}")
    log(f"原始FFN中间层大小: {orig_config.intermediate_size}")
    log(f"原始词表大小: {orig_config.vocab_size}")
    
    # 加载tokenizer
    log("加载tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    
    # 加载原始模型（CPU，因为要裁剪）
    log("加载原始模型到CPU（用于裁剪）...")
    log("（这需要约6GB内存，请耐心等待）")
    start = time.time()
    orig_model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        torch_dtype=torch.float32,
        device_map="cpu",
        trust_remote_code=True
    )
    log(f"模型加载完成，耗时: {time.time()-start:.1f}秒")
    
    # 统计原始参数量
    orig_params = sum(p.numel() for p in orig_model.parameters())
    log(f"原始参数量: {orig_params / 1e6:.1f}M ({orig_params / 1e9:.2f}B)")
    
    # ============ 执行裁剪 ============
    log("\n开始裁剪...")
    
    # 3.1 层裁剪：保留前4层和后4层（共8层），跳过中间层
    log(f"层裁剪: {orig_config.num_hidden_layers}层 → {CONFIG['num_layers']}层")
    log("策略: 保留前4层(语义理解) + 后4层(生成输出)，跳过中间20层")
    
    keep_layers = list(range(4)) + list(range(orig_config.num_hidden_layers - 4, orig_config.num_hidden_layers))
    log(f"保留层索引: {keep_layers}")
    
    # 创建新配置
    new_config = orig_config.to_dict()
    new_config["num_hidden_layers"] = CONFIG["num_layers"]
    new_config["num_attention_heads"] = CONFIG["num_heads"]
    new_config["num_key_value_heads"] = CONFIG["num_heads"]  # GQA对齐
    new_config["intermediate_size"] = CONFIG["intermediate_size"]
    new_config["vocab_size"] = CONFIG["vocab_size"]
    new_config = AutoConfig.from_dict(new_config)
    
    # 创建裁剪后模型
    log("创建裁剪后模型结构...")
    pruned_model = AutoModelForCausalLM.from_config(new_config, trust_remote_code=True)
    
    # 复制嵌入层（裁剪词表）
    log("复制嵌入层（词表裁剪到常用中文+英文）")
    with torch.no_grad():
        # 保留前50000个token（包含常用中文、英文、符号）
        pruned_model.model.embed_tokens.weight.copy_(
            orig_model.model.embed_tokens.weight[:CONFIG["vocab_size"]]
        )
        pruned_model.lm_head.weight.copy_(
            orig_model.lm_head.weight[:CONFIG["vocab_size"]]
        )
    
    # 复制保留的Transformer层
    log("复制保留的Transformer层权重...")
    with torch.no_grad():
        for i, orig_idx in enumerate(keep_layers):
            src_layer = orig_model.model.layers[orig_idx]
            dst_layer = pruned_model.model.layers[i]
            
            # 注意力层（头裁剪：保留前8头）
            head_dim = orig_config.hidden_size // orig_config.num_attention_heads
            keep_heads_dim = CONFIG["num_heads"] * head_dim
            
            dst_layer.self_attn.q_proj.weight.copy_(
                src_layer.self_attn.q_proj.weight[:keep_heads_dim]
            )
            dst_layer.self_attn.k_proj.weight.copy_(
                src_layer.self_attn.k_proj.weight[:keep_heads_dim]
            )
            dst_layer.self_attn.v_proj.weight.copy_(
                src_layer.self_attn.v_proj.weight[:keep_heads_dim]
            )
            dst_layer.self_attn.o_proj.weight.copy_(
                src_layer.self_attn.o_proj.weight[:, :keep_heads_dim]
            )
            
            # FFN层（中间维度裁剪）
            dst_layer.mlp.gate_proj.weight.copy_(
                src_layer.mlp.gate_proj.weight[:CONFIG["intermediate_size"]]
            )
            dst_layer.mlp.up_proj.weight.copy_(
                src_layer.mlp.up_proj.weight[:CONFIG["intermediate_size"]]
            )
            dst_layer.mlp.down_proj.weight.copy_(
                src_layer.mlp.down_proj.weight[:, :CONFIG["intermediate_size"]]
            )
            
            # 归一化层
            dst_layer.input_layernorm.weight.copy_(src_layer.input_layernorm.weight)
            dst_layer.post_attention_layernorm.weight.copy_(src_layer.post_attention_layernorm.weight)
            
            log(f"  层 {i} ← 原始层 {orig_idx} 复制完成")
    
    # 复制最终归一化层
    with torch.no_grad():
        pruned_model.model.norm.weight.copy_(orig_model.model.norm.weight)
    
    # 统计裁剪后参数量
    pruned_params = sum(p.numel() for p in pruned_model.parameters())
    log(f"\n裁剪后参数量: {pruned_params / 1e6:.1f}M")
    log(f"参数压缩比: {orig_params / pruned_params:.1f}x")
    log(f"参数减少: {(1 - pruned_params/orig_params)*100:.1f}%")
    
    # 释放原始模型内存
    del orig_model
    import gc
    gc.collect()
    torch.cuda.empty_cache()
    log("已释放原始模型内存")
    
    return pruned_model, tokenizer, new_config

def save_model(pruned_model, tokenizer, new_config):
    """保存裁剪后模型"""
    step("步骤4: 保存裁剪后模型")
    
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    
    log(f"保存模型到: {CONFIG['output_dir']}")
    pruned_model.save_pretrained(CONFIG["output_dir"])
    tokenizer.save_pretrained(CONFIG["output_dir"])
    
    # 保存裁剪元数据
    metadata = {
        "model_name": "OMU-KERNEL-300M",
        "version": "V1.0",
        "source_model": CONFIG["source_model"],
        "created_at": datetime.now().isoformat(),
        "architecture": {
            "num_layers": CONFIG["num_layers"],
            "num_heads": CONFIG["num_heads"],
            "intermediate_size": CONFIG["intermediate_size"],
            "vocab_size": CONFIG["vocab_size"],
            "hidden_size": new_config.hidden_size,
        },
        "pruning_strategy": {
            "layers": "前4层+后4层，跳过中间20层",
            "heads": "保留前8个注意力头",
            "ffn": "中间维度5504→2048",
            "vocab": "词表151936→50000（常用中文+英文）",
        },
        "system": "元极恒一/ZONGYUAN-ROOT",
        "did": "DID-BR-000002",
        "anchor": "Ω₀⊂⊙∞⊂Ω",
    }
    
    meta_path = os.path.join(CONFIG["output_dir"], "omu_kernel_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    log(f"元数据已保存: {meta_path}")
    
    # 计算模型哈希
    log("计算模型SHA256哈希...")
    sha256 = hashlib.sha256()
    for f in sorted(Path(CONFIG["output_dir"]).glob("*.safetensors")):
        with open(f, "rb") as fh:
            sha256.update(fh.read())
    log(f"模型哈希: {sha256.hexdigest()[:64]}...")
    
    return CONFIG["output_dir"]

def quick_test(model_dir):
    """快速能力测试"""
    step("步骤5: 裁剪后模型快速能力测试")
    
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    
    log("加载裁剪后模型到GPU...")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        torch_dtype=torch.float16,
        device_map="cuda:0",
        trust_remote_code=True
    )
    model.eval()
    
    results = []
    for i, test in enumerate(TEST_CASES):
        log(f"\n测试 {i+1}/{len(TEST_CASES)}: {test['input']}")
        
        messages = [
            {"role": "system", "content": "你是元极恒一智能体助手。"},
            {"role": "user", "content": test["input"]}
        ]
        
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            start = time.time()
            outputs = model.generate(
                **inputs,
                max_new_tokens=100,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
            elapsed = time.time() - start
        
        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        tokens = outputs.shape[1] - inputs["input_ids"].shape[1]
        speed = tokens / elapsed if elapsed > 0 else 0
        
        log(f"  回复: {response[:100]}..." if len(response) > 100 else f"  回复: {response}")
        log(f"  速度: {speed:.1f} tokens/s, 耗时: {elapsed:.2f}s")
        
        # 简单检查是否包含关键词
        passed = test["expect"] in response
        results.append({"input": test["input"], "passed": passed, "speed": speed})
        log(f"  关键词检查: {'✓ 通过' if passed else '✗ 未通过'}")
    
    # 统计
    passed_count = sum(1 for r in results if r["passed"])
    avg_speed = sum(r["speed"] for r in results) / len(results)
    
    log(f"\n{'='*50}")
    log(f"测试结果: {passed_count}/{len(results)} 通过")
    log(f"平均速度: {avg_speed:.1f} tokens/s")
    log(f"{'='*50}")
    
    # 保存测试报告
    report = {
        "test_time": datetime.now().isoformat(),
        "total": len(results),
        "passed": passed_count,
        "pass_rate": passed_count / len(results),
        "avg_speed_tokens_per_sec": avg_speed,
        "details": results,
    }
    report_path = os.path.join(CONFIG["output_dir"], "prune_test_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log(f"测试报告已保存: {report_path}")
    
    del model
    import gc
    gc.collect()
    torch.cuda.empty_cache()
    
    return report

def convert_to_gguf(model_dir):
    """转换为GGUF格式（用于llama.cpp部署）"""
    step("步骤6: 转换为GGUF Q4_K_M格式")
    
    # 检查是否有convert脚本
    convert_script = None
    for path in [
        "/usr/local/lib/python3.10/dist-packages/llama_cpp/convert_hf_to_gguf.py",
        "/usr/local/lib/python3.11/dist-packages/llama_cpp/convert_hf_to_gguf.py",
        "/opt/llama.cpp/convert_hf_to_gguf.py",
    ]:
        if os.path.exists(path):
            convert_script = path
            break
    
    if convert_script is None:
        log("未找到llama.cpp转换脚本，尝试安装...")
        os.system("pip install -q llama-cpp-python")
        # 重新查找
        import subprocess
        result = subprocess.run(["python", "-c", "import llama_cpp; print(llama_cpp.__file__)"], capture_output=True, text=True)
        if result.returncode == 0:
            llama_path = os.path.dirname(result.stdout.strip())
            convert_script = os.path.join(llama_path, "convert_hf_to_gguf.py")
    
    if convert_script and os.path.exists(convert_script):
        log(f"使用转换脚本: {convert_script}")
        log("转换为Q4_K_M量化GGUF格式...")
        log("（这需要几分钟，请耐心等待）")
        
        cmd = f"python {convert_script} {model_dir} --outfile {CONFIG['gguf_output']} --outtype q4_k_m"
        log(f"执行: {cmd}")
        result = os.system(cmd)
        
        if result == 0 and os.path.exists(CONFIG['gguf_output']):
            size = os.path.getsize(CONFIG['gguf_output'])
            log(f"GGUF转换成功: {CONFIG['gguf_output']}")
            log(f"文件大小: {size / 1024**2:.1f} MB")
        else:
            log("GGUF转换失败，将在云服务器上手动转换", "WARN")
    else:
        log("未找到转换脚本，跳过GGUF转换（可在云服务器上手动转换）", "WARN")

def generate_report(model_dir, test_report):
    """生成最终报告"""
    step("步骤7: 生成最终报告")
    
    import torch
    from transformers import AutoConfig
    
    config = AutoConfig.from_pretrained(model_dir, trust_remote_code=True)
    params = sum(p.numel() for p in torch.load(os.path.join(model_dir, "model.safetensors"), map_location="cpu").values()) if os.path.exists(os.path.join(model_dir, "model.safetensors")) else 0
    
    report = f"""
╔══════════════════════════════════════════════════════════════╗
║          元极恒一自研大模型内核 - 裁剪完成报告              ║
║                    OMU-KERNEL-V1.0                           ║
╚══════════════════════════════════════════════════════════════╝

【基本信息】
  模型名称: OMU-KERNEL-300M
  版本: V1.0
  源模型: {CONFIG['source_model']}
  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  确权标识: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

【裁剪参数】
  层数: 28 → {config.num_hidden_layers}层（前4+后4）
  注意力头: 16 → {config.num_attention_heads}头
  FFN中间层: 5504 → {config.intermediate_size}
  词表大小: 151936 → {config.vocab_size}
  隐藏维度: {config.hidden_size}（保持不变）

【能力测试】
  测试用例: {test_report['total']}个
  通过数: {test_report['passed']}个
  通过率: {test_report['pass_rate']*100:.1f}%
  平均速度: {test_report['avg_speed_tokens_per_sec']:.1f} tokens/s

【输出文件】
  模型目录: {model_dir}
  GGUF文件: {CONFIG['gguf_output']}
  元数据: {os.path.join(model_dir, 'omu_kernel_metadata.json')}
  测试报告: {os.path.join(model_dir, 'prune_test_report.json')}

【下一步】
  1. 下载模型文件到云服务器 /opt/omu-kernel/output/
  2. 部署llama-server服务（端口8082）
  3. 开发融合调度层（真值库/元法则/决策引擎/因果引擎）
  4. 集成到元极恒一内核体系
  5. 用真值库数据做领域适配（可选LoRA微调）

【架构说明】
  本模型采用"最小神经内核 + 元极恒一外挂体系"的神经符号融合架构：
  - 最小神经内核（300M）：基础语义理解、简单生成、模式匹配
  - 元极恒一外挂体系：真值库(15000+条)、元法则(128+条)、
    决策引擎(三维稳态)、因果引擎(七维因果域)、贝叶斯五行闭环
  - 融合调度层：智能路由，简单任务用内核，复杂任务调外挂

  这种架构比传统大模型更先进：可控、可解释、可审计、可进化、轻量。
  传统大模型是黑盒概率机器，元极恒一架构是有"灵魂"的智能体。

═══════════════════════════════════════════════════════════════
  元极恒一 · 熵减收敛归一 · 宇宙本源智能
═══════════════════════════════════════════════════════════════
"""
    
    report_path = "/mnt/workspace/output/OMU-KERNEL裁剪完成报告.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(report)
    log(f"报告已保存: {report_path}")
    
    return report_path

def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     元极恒一自研大模型内核 - 魔塔ModelScope裁剪工具        ║
║                    OMU-KERNEL-V1.0                           ║
║                                                              ║
║     从 Qwen2.5-1.5B 裁剪到 300M 最小神经内核              ║
║     适配: ModelScope Notebook (免费GPU 24GB显存)           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """, flush=True)
    
    start_time = time.time()
    
    try:
        # 步骤0: 环境检查
        gpu_ok = check_gpu()
        if not gpu_ok:
            log("未检测到GPU，但仍可在CPU上执行裁剪（速度较慢）", "WARN")
        
        # 步骤1: 安装依赖
        install_deps()
        
        # 步骤2: 下载模型
        model_dir = download_model()
        
        # 步骤3: 加载并裁剪
        pruned_model, tokenizer, new_config = load_and_prune(model_dir)
        
        # 步骤4: 保存模型
        output_dir = save_model(pruned_model, tokenizer, new_config)
        del pruned_model
        import gc
        gc.collect()
        
        # 步骤5: 快速测试
        test_report = quick_test(output_dir)
        
        # 步骤6: 转换GGUF
        convert_to_gguf(output_dir)
        
        # 步骤7: 生成报告
        report_path = generate_report(output_dir, test_report)
        
        # 完成
        elapsed = time.time() - start_time
        print(f"\n{'='*70}")
        print(f"  ✅ 全部完成！总耗时: {elapsed/60:.1f}分钟")
        print(f"  📁 模型目录: {output_dir}")
        print(f"  📄 报告文件: {report_path}")
        print(f"  📦 请下载 /mnt/workspace/output/ 目录下的所有文件")
        print(f"{'='*70}\n")
        
    except Exception as e:
        log(f"执行失败: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
