#!/usr/bin/env python3
# 小量LoRA训练：10条种子
import json
from pathlib import Path

# 从54条种子选10条
seeds = []
with open("/root/zongyuan-yuanji/persist/seed_truth/text/seed_text.jsonl") as f:
    for line in f:
        seeds.append(json.loads(line))

# 选前10条
train = seeds[:10]
print(f"训练样本: {len(train)}条")

# 保存训练数据
with open("/root/zongyuan-yuanji/data/train_small.jsonl", "w") as f:
    for s in train:
        f.write(json.dumps({
            "instruction": s.get("user_prompt", ""),
            "output": s.get("response", "")
        }, ensure_ascii=False) + "\n")

print("训练数据已保存: data/train_small.jsonl")
