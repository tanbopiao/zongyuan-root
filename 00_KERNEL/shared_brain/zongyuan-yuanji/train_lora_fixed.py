#!/usr/bin/env python3
"""元极微模型LoRA微调 - 修正版"""
import json, os, sys
from pathlib import Path

# 1. 加载模型和tokenizer
from modelscope_hub import snapshot_download
model_path = snapshot_download("Qwen/Qwen2-0.5B-Instruct")
print(f"MODEL_PATH: {model_path}")

from transformers import AutoModelForCausalLM, AutoTokenizer
tok = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype="auto", device_map="cpu")
print("模型加载完成")

# 2. 加载数据 - 修正字段名
from datasets import Dataset
data_dir = Path("/mnt/workspace/lora_skills")
all_samples = []
for skill_dir in data_dir.iterdir():
    train_file = skill_dir / "train.jsonl"
    if not train_file.exists(): continue
    with open(train_file) as f:
        for line in f:
            d = json.loads(line)
            # 正确格式：system + user + response
            system = d.get("system_prompt", "")
            user = d.get("user_prompt", "")
            resp = d.get("response", "")
            text = f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n{resp}<|im_end|>"
            all_samples.append({"text": text})
    print(f"  {skill_dir.name}: {len(all_samples)} samples total")

ds = Dataset.from_list(all_samples)
print(f"数据量: {len(ds)}")

# 3. LoRA配置
from peft import LoraConfig, TaskType
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=8, lora_alpha=16, lora_dropout=0.05,
    target_modules=["q_proj", "v_proj"]
)

# 4. SFTTrainer - 新版API用processing_class
from trl import SFTTrainer, SFTConfig
OUT = "/mnt/workspace/lora_output"
os.makedirs(OUT, exist_ok=True)

args = SFTConfig(
    output_dir=OUT,
    num_train_epochs=3,
    per_device_train_batch_size=4,
    max_seq_length=512,
    logging_steps=5,
    save_strategy="epoch",
)

trainer = SFTTrainer(
    model=model,
    args=args,
    train_dataset=ds,
    peft_config=lora_config,
    processing_class=tok,  # 新版参数
)

print("开始训练...")
trainer.train()
print("训练完成！")

# 5. 保存adapter
trainer.save_model(OUT)
print(f"保存到: {OUT}")
print("DONE")
