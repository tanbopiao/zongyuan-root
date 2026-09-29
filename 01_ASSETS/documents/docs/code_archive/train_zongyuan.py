#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 自研小模型训练脚本
支持 Qwen2.5-3B / 7B 全参数微调或LoRA微调
"""
import os
import sys
import json
import torch
import argparse
from datetime import datetime
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, TaskType

def parse_args():
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT 模型训练")
    parser.add_argument("--model_path", type=str, required=True, help="基座模型路径")
    parser.add_argument("--model_name", type=str, default="zongyuan", help="模型名称")
    parser.add_argument("--data_path", type=str, default="/mnt/workspace/zongyuan_training.jsonl", help="训练数据路径")
    parser.add_argument("--output_dir", type=str, required=True, help="输出目录")
    parser.add_argument("--use_lora", action="store_true", help="使用LoRA微调")
    parser.add_argument("--lora_r", type=int, default=16, help="LoRA秩")
    parser.add_argument("--lora_alpha", type=int, default=32, help="LoRA alpha")
    parser.add_argument("--num_epochs", type=int, default=3, help="训练轮数")
    parser.add_argument("--batch_size", type=int, default=4, help="批次大小")
    parser.add_argument("--gradient_accumulation", type=int, default=4, help="梯度累积步数")
    parser.add_argument("--learning_rate", type=float, default=1e-5, help="学习率")
    parser.add_argument("--max_length", type=int, default=2048, help="最大序列长度")
    parser.add_argument("--save_steps", type=int, default=100, help="保存步数")
    parser.add_argument("--logging_steps", type=int, default=10, help="日志步数")
    return parser.parse_args()

def format_example(example):
    """格式化训练样本为对话格式"""
    instruction = example.get("instruction", "")
    input_text = example.get("input", "")
    output = example.get("output", "")
    
    if input_text:
        prompt = f"问：{instruction}\n补充信息：{input_text}\n答："
    else:
        prompt = f"问：{instruction}\n答："
    
    return {
        "text": prompt + output + "<|endoftext|>",
        "prompt": prompt,
        "response": output
    }

def main():
    args = parse_args()
    
    print("=" * 60)
    print("ZONGYUAN-ROOT 自研小模型训练")
    print("=" * 60)
    print(f"模型: {args.model_name}")
    print(f"基座: {args.model_path}")
    print(f"数据: {args.data_path}")
    print(f"输出: {args.output_dir}")
    print(f"微调方式: {'LoRA' if args.use_lora else '全参数'}")
    print(f"Epoch: {args.num_epochs}")
    print(f"Batch Size: {args.batch_size}")
    print(f"梯度累积: {args.gradient_accumulation}")
    print(f"学习率: {args.learning_rate}")
    print(f"最大长度: {args.max_length}")
    print("=" * 60)
    
    # 1. 加载tokenizer
    print("\n[1/5] 加载tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    print(f"   词表大小: {len(tokenizer)}")
    
    # 2. 加载模型
    print("\n[2/5] 加载模型...")
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    
    # 启用梯度检查点（节省显存）
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"   总参数量: {total_params / 1e6:.1f}M")
    
    # 3. LoRA配置
    if args.use_lora:
        print("\n[3/5] 配置LoRA...")
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        )
        model = get_peft_model(model, lora_config)
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"   可训练参数: {trainable_params / 1e6:.1f}M ({100 * trainable_params / total_params:.2f}%)")
    else:
        print("\n[3/5] 全参数微调...")
        for param in model.parameters():
            param.requires_grad = True
        print(f"   可训练参数: {total_params / 1e6:.1f}M (100%)")
    
    # 4. 加载和处理数据
    print("\n[4/5] 加载训练数据...")
    dataset = load_dataset("json", data_files=args.data_path, split="train")
    print(f"   原始样本数: {len(dataset)}")
    
    # 格式化数据
    def tokenize_function(examples):
        texts = []
        for i in range(len(examples["instruction"])):
            inst = examples["instruction"][i]
            inp = examples.get("input", [""] * len(examples["instruction"]))[i]
            out = examples["output"][i]
            if inp:
                text = f"问：{inst}\n补充信息：{inp}\n答：{out}<|endoftext|>"
            else:
                text = f"问：{inst}\n答：{out}<|endoftext|>"
            texts.append(text)
        
        tokenized = tokenizer(
            texts,
            truncation=True,
            max_length=args.max_length,
            padding="max_length",
            return_tensors=None,
        )
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized
    
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=dataset.column_names,
        desc="Tokenizing",
    )
    print(f"   处理后样本数: {len(tokenized_dataset)}")
    
    # 5. 训练配置
    print("\n[5/5] 开始训练...")
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        learning_rate=args.learning_rate,
        weight_decay=0.01,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=2,
        bf16=True,
        gradient_checkpointing=True,
        report_to="none",
        dataloader_num_workers=4,
        remove_unused_columns=False,
    )
    
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
    )
    
    # 开始训练
    train_result = trainer.train()
    
    # 打印训练结果
    print("\n" + "=" * 60)
    print("训练完成！")
    print("=" * 60)
    print(f"训练损失: {train_result.training_loss:.4f}")
    print(f"训练时长: {train_result.metrics.get('train_runtime', 0):.1f}秒")
    print(f"每秒样本: {train_result.metrics.get('train_samples_per_second', 0):.2f}")
    
    # 保存模型
    print(f"\n保存模型到: {args.output_dir}")
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    
    # 如果是LoRA，合并权重
    if args.use_lora:
        print("\n合并LoRA权重...")
        from peft import PeftModel
        base_model = AutoModelForCausalLM.from_pretrained(
            args.model_path,
            torch_dtype=torch.bfloat16,
            device_map="cpu",
            trust_remote_code=True,
        )
        merged_model = PeftModel.from_pretrained(base_model, args.output_dir)
        merged_model = merged_model.merge_and_unload()
        
        merged_output = args.output_dir + "_merged"
        merged_model.save_pretrained(merged_output, safe_serialization=True)
        tokenizer.save_pretrained(merged_output)
        print(f"合并后模型保存到: {merged_output}")
        
        merged_params = sum(p.numel() for p in merged_model.parameters())
        print(f"合并后参数量: {merged_params / 1e6:.1f}M")
    
    print("\n" + "=" * 60)
    print("全部完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
