#!/usr/bin/env python3
# LoRA v7微调：用334条种子
import json, torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model

SEED_FILE = "/root/zongyuan-yuanji/persist/seed_truth/text/seed_text.jsonl"
MODEL_PATH = "/root/zongyuan-yuanji/weights/yuanjihengyi_int4"
OUT_PATH = "/root/zongyuan-yuanji/weights/lora_adapter_v7"

print("加载tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print("加载模型（CPU fp32）...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH, torch_dtype=torch.float32, device_map="cpu", trust_remote_code=True
)

lora_config = LoraConfig(
    r=8, lora_alpha=16, target_modules=["q_proj","v_proj"], lora_dropout=0.05
)
model = get_peft_model(model, lora_config)
print("可训练参数:", sum(p.numel() for p in model.parameters() if p.requires_grad))

# 加载种子数据
print("加载种子数据...")
data = []
with open(SEED_FILE) as f:
    for line in f:
        try:
            s = json.loads(line)
            text = s.get("system_prompt","") + "\n" + s.get("user_prompt","") + "\n" + s.get("response","")
            data.append(text)
        except: pass
print("训练样本:", len(data))

# Tokenize
class Dataset(torch.utils.data.Dataset):
    def __len__(self): return len(data)
    def __getitem__(self, i):
        enc = tokenizer(data[i], truncation=True, max_length=128, padding="max_length")
        return {"input_ids": torch.tensor(enc["input_ids"]), "attention_mask": torch.tensor(enc["attention_mask"]), "labels": torch.tensor(enc["input_ids"])}

dataset = Dataset()

args = TrainingArguments(
    output_dir=OUT_PATH,
    num_train_epochs=2,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    logging_steps=5,
    save_steps=100,
    learning_rate=1e-4,
    use_cpu=True,
    report_to="none",
    max_steps=50,  # 只跑50步，防止OOM
)

trainer = Trainer(model=model, args=args, train_dataset=dataset)
print("开始训练...")
trainer.train()

model.save_pretrained(OUT_PATH)
tokenizer.save_pretrained(OUT_PATH)
print("LoRA v7已保存到", OUT_PATH)
