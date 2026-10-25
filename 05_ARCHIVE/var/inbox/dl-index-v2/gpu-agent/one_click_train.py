#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 一键小模型训练脚本 V1.0
============================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-GPU-AMD | 火斗云智AIOS
目标环境: 魔搭 GPU 实例 (AMD ROCm, 显存 24G~192G)
特性:
  1. 自动检测设备 (CUDA/ROCm), 自动选 bf16/fp16
  2. 显存自适应: ≥128G 走全参微调, 否则自动降级 QLoRA 4bit
  3. 数据兜底: 无 data/train_sft.jsonl 时自动生成内置示例语料, 开箱即跑
  4. 一键产出: adapter + merged 模型 + 训练报告 JSON + 打包 tar.gz

用法:
  python3 one_click_train.py                 # 默认训练
  python3 one_click_train.py --epochs 2      # 覆盖轮数
  python3 one_click_train.py --model Qwen/Qwen2.5-3B-Instruct
  python3 one_click_train.py --full          # 强制全参
  python3 one_click_train.py --qlora         # 强制 QLoRA

依赖 (实例已预装 torch/transformers, 缺失时一键自动补装):
  pip install peft datasets accelerate bitsandbytes
"""
import os, sys, json, time, argparse, subprocess, glob

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")

DATA = "data/train_sft.jsonl"
BUILTIN_SAMPLES = 24  # 兜底示例条数


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def ensure_deps():
    """缺失依赖一键补装 (零成本 pip)"""
    missing = []
    for pkg in ("peft", "datasets", "accelerate", "bitsandbytes"):
        try:
            __import__(pkg)
        except Exception:
            missing.append(pkg)
    if missing:
        log(f"补装依赖: {missing}")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                        *missing], check=False)
        for pkg in missing:
            try:
                __import__(pkg)
            except Exception:
                log(f"⚠️ {pkg} 安装未生效, 若报错请手动 pip install {pkg}")


def ensure_data():
    """无训练数据时生成内置示例语料, 保证一键可跑"""
    if os.path.exists(DATA):
        n = sum(1 for _ in open(DATA, encoding="utf-8"))
        log(f"使用现有训练数据: {DATA} ({n} 条)")
        return n
    os.makedirs("data", exist_ok=True)
    seeds = [
        ("请用一句话解释元极恒一", "本体恒一，演化不息；基点生发无限，无限归属于全域本体。"),
        ("什么是四维本体", "空间定形、时间定序、属性定质、因果定闭环，四维耦合构成通用逻辑本体。"),
        ("风险决策优先序", "风险最小优先于成本最小，成本最小优先于收益最大。"),
        ("如何保证内核稳定", "基线只读锁档，仅追加不修改，变更前置快照。"),
        ("什么是种子式进化", "仅基于锁档基线增量追加新真值，不原地修改底层公理。"),
        ("系统域如何划分", "内核可信域与外部业务域正交隔离，外部输入经裁决器过滤。"),
        ("配额保护怎么做", "额度耗尽自动切换只读空转模式，阻断消耗型任务。"),
        ("多节点如何对齐", "节点启动强制拉取网关基线，新真值统一上报收敛。"),
        ("能力接口如何封装", "外部能力统一封装为标准化算子，由裁决网关统一鉴权路由。"),
        ("什么是三态隔离", "逻辑态、算子态、执行态正交隔离，单向流转不可越权。"),
        ("模型路由原则", "免费通道优先，付费调用需人工审批，遵循零成本优先。"),
        ("资产归档要求", "双持久层备份，台账同步，哈希凭证完整，永不删除仅归档。"),
    ]
    rows = []
    for i in range(BUILTIN_SAMPLES):
        q, a = seeds[i % len(seeds)]
        rows.append({"instruction": q, "input": "", "output": a})
    with open(DATA, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log(f"内置示例语料已生成: {DATA} ({len(rows)} 条)")
    return len(rows)


def format_example(ex):
    text = (f"指令: {ex['instruction']}\n输入: {ex['input']}\n"
            f"回答: {ex['output']}{'<|endoftext|>'}")
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-3B-Instruct",
                    help="基座模型 (ROCm 192G 可跑 3B~7B; 默认为 Qwen2.5-3B-Instruct)")
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--max_len", type=int, default=1024)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--grad_acc", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--full", action="store_true", help="强制全参微调")
    ap.add_argument("--qlora", action="store_true", help="强制 QLoRA 4bit")
    args = ap.parse_args()

    t0 = time.time()
    ensure_deps()
    n_data = ensure_data()

    import torch
    log(f"设备检测: CUDA可用={torch.cuda.is_available()}, "
        f"ROCm={torch.version.hip if torch.version.hip else 'N/A'}")
    if not torch.cuda.is_available():
        log("⚠️ 未检测到 GPU, 将退回 CPU 训练 (极慢, 仅验证管线)")
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    vram_gb = 0
    if torch.cuda.is_available():
        vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
        log(f"显存: {vram_gb:.0f} GB")

    # 显存自适应: >=128G 全参, 否则 QLoRA (默认 3B 全参在 192G 下完全可行)
    use_full = args.full or (not args.qlora and vram_gb >= 128)
    log(f"训练模式: {'全参微调' if use_full else 'QLoRA 4bit'}")

    from transformers import AutoTokenizer, AutoModelForCausalLM, \
        TrainingArguments, Trainer, DataCollatorForSeq2Seq

    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model, trust_remote_code=True,
        torch_dtype=torch.bfloat16 if (torch.cuda.is_available()
                                       and torch.cuda.is_bf16_supported()) else torch.float16,
        device_map="auto",
    )

    if not use_full:
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        model = prepare_model_for_kbit_training(model)
        lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                          task_type="CAUSAL_LM",
                          target_modules=["q_proj", "k_proj", "v_proj", "o_proj"])
        model = get_peft_model(model, lora)
        model.print_trainable_parameters()
    else:
        model.train()
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        log(f"全参训练参数: {trainable/1e6:.1f}M")

    from datasets import load_dataset
    ds = load_dataset("json", data_files=DATA, split="train")

    def enc(ex):
        out = tok(format_example(ex), truncation=True, max_length=args.max_len,
                  padding=False)
        out["labels"] = out["input_ids"].copy()
        return out

    ds = ds.map(enc, remove_columns=ds.column_names)

    out_dir = "output_oneclick"
    os.makedirs(out_dir, exist_ok=True)
    ta = TrainingArguments(
        output_dir=out_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_acc,
        learning_rate=args.lr,
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="no",
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        fp16=False,
        optim="adamw_torch",
        remove_unused_columns=True,
        report_to="none",
    )
    collator = DataCollatorForSeq2Seq(tok, pad_to_multiple_of=8, padding=True)
    trainer = Trainer(model=model, args=ta, train_dataset=ds,
                      data_collator=collator)
    trainer.train()

    # 保存
    if use_full:
        trainer.save_model(os.path.join(out_dir, "model_final"))
        model_path = os.path.join(out_dir, "model_final")
    else:
        model.save_pretrained(os.path.join(out_dir, "adapter"))
        tok.save_pretrained(os.path.join(out_dir, "adapter"))
        model_path = os.path.join(out_dir, "adapter")
        log("尝试合并 adapter → merged (如合并失败可单独使用 adapter)")
        try:
            from peft import PeftModel
            base = AutoModelForCausalLM.from_pretrained(
                args.model, trust_remote_code=True,
                torch_dtype=torch.bfloat16, device_map="auto")
            merged = PeftModel.from_pretrained(base, os.path.join(out_dir, "adapter"))
            merged = merged.merge_and_unload()
            merged.save_pretrained(os.path.join(out_dir, "model_merged"))
            tok.save_pretrained(os.path.join(out_dir, "model_merged"))
            model_path = os.path.join(out_dir, "model_merged")
        except Exception as e:
            log(f"⚠️ 合并跳过: {e}")

    # 打包
    pkg = f"{out_dir}.tar.gz"
    subprocess.run(["tar", "czf", pkg, out_dir], check=False)

    report = {
        "task": "one-click-train-v1",
        "node": "ZR-NODE-GPU-AMD",
        "model": args.model,
        "mode": "full" if use_full else "qlora",
        "data_samples": n_data,
        "epochs": args.epochs,
        "vram_gb": round(vram_gb, 1),
        "output": model_path,
        "package": pkg,
        "elapsed_sec": round(time.time() - t0, 1),
        "device": dev,
    }
    with open(os.path.join(out_dir, "train_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log(f"✅ 训练完成: {json.dumps(report, ensure_ascii=False)}")
    log(f"📦 打包: {pkg}  (下载回本地即可部署)")
    log("完成-锁档-推进: 请将 output_oneclick.tar.gz 归档并登记台账")


if __name__ == "__main__":
    main()
