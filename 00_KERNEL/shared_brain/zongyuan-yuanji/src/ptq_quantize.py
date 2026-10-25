#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptq_quantize.py ｜ 把 bf16 微调权重固化为 nf4 INT4 量化模型（800MB）"""
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

SRC = "/root/zongyuan-yuanji/weights/yuanjihengyi_ft_v1"
DST = "/root/zongyuan-yuanji/weights/yuanjihengyi_int4"

print("=== 加载 tokenizer ===", flush=True)
tok = AutoTokenizer.from_pretrained(SRC, trust_remote_code=True)

print("=== 4bit nf4 量化加载 ===", flush=True)
bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)
model = AutoModelForCausalLM.from_pretrained(
    SRC, quantization_config=bnb, device_map="cpu", trust_remote_code=True)

print("=== 保存量化模型 ===", flush=True)
Path(DST).mkdir(parents=True, exist_ok=True)
model.save_pretrained(DST, safe_serialization=True)
tok.save_pretrained(DST)
print(f"=== 完成：{DST} ===", flush=True)

import os
size = sum(os.path.getsize(f"{DST}/{f}") for f in os.listdir(DST))
print(f"磁盘占用：{size/1024/1024:.0f} MB", flush=True)
