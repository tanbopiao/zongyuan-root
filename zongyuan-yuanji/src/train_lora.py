#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""train_lora.py ｜ 元极恒一内核 LoRA 微调（CPU）
将种子真值+元本体+元法则+体系硬知识内化为权重知识。
用法：python3 train_lora.py [--max-steps 150] [--epochs 2] [--lora-r 16]
输出：/root/zongyuan-yuanji/weights/yuanjihengyi_ft_v1（merged 完整权重）
"""
import argparse
import json
import os
import time
from pathlib import Path

os.environ.setdefault("YUANJI_ROOT", "/root/zongyuan-yuanji")
ROOT = Path("/root/zongyuan-yuanji")
DATA = ROOT / "train_data" / "yuanji_sft_v5_FINAL.jsonl"
BASE = ROOT / "weights" / "yuanjihengyi_full_v1"
OUT = ROOT / "weights" / "yuanjihengyi_ft_v1"
ADAPTER = ROOT / "weights" / "lora_adapter_v5"

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model, PeftModel
from transformers import TrainingArguments, Trainer, DataCollatorForSeq2Seq

p = argparse.ArgumentParser()
p.add_argument("--max-steps", type=int, default=80)
p.add_argument("--epochs", type=float, default=2.0)
p.add_argument("--lora-r", type=int, default=16)
p.add_argument("--max-len", type=int, default=768)
a = p.parse_args()

t0 = time.time()
print("=== 加载基座模型（CPU bf16 省内存）===", flush=True)
tok = AutoTokenizer.from_pretrained(str(BASE), trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    str(BASE), torch_dtype=torch.bfloat16, device_map="cpu", trust_remote_code=True)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
model.gradient_checkpointing_enable()
model.enable_input_require_grads()
print("gradient_checkpointing: ON（压激活内存）", flush=True)

lora = LoraConfig(
    r=a.lora_r, lora_alpha=a.lora_r * 2, lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    task_type="CAUSAL_LM", bias="none")
model = get_peft_model(model, lora)
model.print_trainable_parameters()

rows = []
for line in DATA.read_text(encoding="utf-8").splitlines():
    if line.strip():
        rows.append(json.loads(line))
print(f"训练样本：{len(rows)} 条", flush=True)


def tokenize(ex):
    text = tok.apply_chat_template(ex, tokenize=False, add_generation_prompt=False)
    enc = tok(text, truncation=True, max_length=a.max_len, padding=False)
    enc["labels"] = enc["input_ids"].copy()
    return enc


ds = [tokenize(r) for r in rows]

args = TrainingArguments(
    output_dir=str(ADAPTER), num_train_epochs=a.epochs, max_steps=a.max_steps,
    per_device_train_batch_size=1, gradient_accumulation_steps=8,
    learning_rate=2e-4, warmup_steps=10, lr_scheduler_type="cosine",
    logging_steps=5, save_steps=100, save_total_limit=1,
    fp16=False, bf16=False, optim="adamw_torch", report_to=[],
    dataloader_pin_memory=False, dataloader_num_workers=0,
)

trainer = Trainer(
    model=model, args=args, train_dataset=ds,
    data_collator=DataCollatorForSeq2Seq(tok, pad_to_multiple_of=8),
)

print(f"=== 开始训练（CPU，~40-90s/step）===", flush=True)
trainer.train()
print("训练完成，保存 adapter", flush=True)
model.save_pretrained(str(ADAPTER))
tok.save_pretrained(str(ADAPTER))

print("=== 合并 LoRA → 完整权重 ===", flush=True)
merged = model.merge_and_unload()
OUT.mkdir(parents=True, exist_ok=True)
merged.save_pretrained(str(OUT), safe_serialization=True)
tok.save_pretrained(str(OUT))
print(f"合并完成：{OUT} ｜ 耗时 {(time.time()-t0)/60:.1f}min", flush=True)
