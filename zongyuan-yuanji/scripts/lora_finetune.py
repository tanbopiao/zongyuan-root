#!/usr/bin/env python3
# 小量LoRA微调
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model
import torch

model_path = "/root/zongyuan-yuanji/weights/yuanjihengyi_int4"
print("加载模型...")
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.float32, device_map="cpu")

# LoRA配置
lora_config = LoraConfig(
    r=8, lora_alpha=16, target_modules=["q_proj", "v_proj"], lora_dropout=0.05
)
model = get_peft_model(model, lora_config)
print(f"可训练参数: {sum(p.numel() for p in model.parameters() if p.requires_grad)}")

# 保存LoRA adapter
model.save_pretrained("/root/zongyuan-yuanji/weights/lora_adapter_v6")
print("LoRA v6已保存")
