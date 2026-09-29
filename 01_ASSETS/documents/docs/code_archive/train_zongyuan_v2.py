#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 自研小模型训练脚本 V2.0
基于Qwen2.5-0.5B进行LoRA微调
"""
import os
import json
import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, TaskType

# 配置
BASE_MODEL = "/mnt/workspace/models/models/qwen--Qwen2.5-0.5B/snapshots/master"
TRAINING_DATA = "/mnt/workspace/training/data/training_data_clean.json"
OUTPUT_DIR = "/mnt/workspace/models/lora/zongyuan-lora-v2"
FINAL_DIR = "/mnt/workspace/models/custom/zongyuan-0.5B-v2"

# LoRA配置
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05

# 训练配置
NUM_EPOCHS = 3
BATCH_SIZE = 4
GRADIENT_ACCUMULATION = 4
LEARNING_RATE = 2e-4
MAX_SEQ_LENGTH = 1024
WARMUP_RATIO = 0.1

def load_training_data(path):
    """加载训练数据并格式化为指令微调格式"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    formatted = []
    for item in data:
        question = item.get("question", "")
        answer = item.get("answer", "")
        if question and answer:
            # 格式化为Qwen2.5的chat template格式
            text = f"<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n{answer}<|im_end|>"
            formatted.append({"text": text})
    
    print(f"加载训练数据: {len(formatted)} 条")
    return Dataset.from_list(formatted)

def tokenize_function(examples, tokenizer):
    """分词函数"""
    return tokenizer(
        examples["text"],
        truncation=True,
        max_length=MAX_SEQ_LENGTH,
        padding="max_length",
    )

def main():
    print("=" * 60)
    print("ZONGYUAN-ROOT 自研小模型训练 V2.0")
    print("=" * 60)
    
    # 1. 加载模型和tokenizer
    print("\n[1/5] 加载基础模型...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.bfloat16,
        device_map="cuda:0",
        trust_remote_code=True,
    )
    print(f"模型加载完成: {sum(p.numel() for p in model.parameters())/1e6:.1f}M 参数")
    
    # 2. 配置LoRA
    print("\n[2/5] 配置LoRA...")
    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # 3. 加载和处理训练数据
    print("\n[3/5] 加载训练数据...")
    dataset = load_training_data(TRAINING_DATA)
    tokenized_dataset = dataset.map(
        lambda x: tokenize_function(x, tokenizer),
        batched=True,
        remove_columns=["text"],
    )
    print(f"数据处理完成: {len(tokenized_dataset)} 条")
    
    # 4. 训练
    print("\n[4/5] 开始训练...")
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION,
        learning_rate=LEARNING_RATE,
        warmup_ratio=WARMUP_RATIO,
        logging_steps=10,
        save_strategy="epoch",
        bf16=True,
        report_to="none",
        dataloader_num_workers=2,
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
    
    trainer.train()
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"LoRA权重已保存: {OUTPUT_DIR}")
    
    # 5. 合并权重
    print("\n[5/5] 合并权重...")
    from peft import PeftModel
    
    # 重新加载基础模型（CPU）
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.bfloat16,
        device_map="cpu",
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(base_model, OUTPUT_DIR)
    model = model.merge_and_unload()
    
    os.makedirs(FINAL_DIR, exist_ok=True)
    model.save_pretrained(FINAL_DIR, safe_serialization=True)
    tokenizer.save_pretrained(FINAL_DIR)
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"合并完成! 参数量: {total_params/1e6:.1f}M")
    print(f"最终模型: {FINAL_DIR}")
    
    print("\n" + "=" * 60)
    print("训练完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
