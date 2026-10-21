# -*- coding: utf-8 -*-
"""Qwen2.5-0.5B-Instruct LoRA 领域微调 —— GPU 版（魔搭免费实例）
- 基座: 魔搭模型 qwen/Qwen2.5-0.5B-Instruct（实例上拉取, 冻结不动）
- 数据: zongyuan-4d-train.jsonl（64条体系四维架构语料, 同目录）
- 产物: ./adapter-4d（LoRA adapter, 基座零改动）
用法: python train_4d_lora_gpu.py
"""
import json, os, time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, TaskType

MODEL_ID = 'qwen/Qwen2.5-0.5B-Instruct'   # 魔搭模型ID
MODEL_DIR = os.environ.get('MODEL_DIR', './model/qwen25-05b')
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'zongyuan-4d-train.jsonl')
ADAPTER_OUT = './adapter-4d'

def load_data():
    with open(DATA_PATH, encoding='utf-8') as f:
        return [json.loads(l) for l in f]

def build_examples(tokenizer, recs):
    examples = []
    for r in recs:
        msgs = [
            {"role": "system", "content": r.get("system", "")},
            {"role": "user", "content": r["instruction"]},
            {"role": "assistant", "content": r["output"]},
        ]
        prompt_enc = tokenizer.apply_chat_template(msgs[:2], tokenize=True, add_generation_prompt=True)
        full_enc = tokenizer.apply_chat_template(msgs, tokenize=True)
        prompt_ids = prompt_enc.input_ids if hasattr(prompt_enc, "input_ids") else prompt_enc
        full_ids = full_enc.input_ids if hasattr(full_enc, "input_ids") else full_enc
        full_ids = full_ids[:512]
        labels = [-100] * len(prompt_ids) + full_ids[len(prompt_ids):]
        if len(labels) < 512:
            labels = labels + [-100] * (512 - len(labels))
            full_ids = full_ids + [tokenizer.pad_token_id] * (512 - len(full_ids))
        examples.append({"input_ids": full_ids, "labels": labels})
    return examples

def collate_fn(batch):
    il = torch.tensor([e["input_ids"] for e in batch], dtype=torch.long)
    lb = torch.tensor([e["labels"] for e in batch], dtype=torch.long)
    return {"input_ids": il, "attention_mask": torch.ones_like(il), "labels": lb}

def main():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[env] device={dev} cuda_count={torch.cuda.device_count()}", flush=True)
    if not os.path.isdir(MODEL_DIR):
        os.makedirs(MODEL_DIR, exist_ok=True)
        print(f"[pull] modelscope download {MODEL_ID} ...", flush=True)
        from modelscope import snapshot_download
        d = snapshot_download(MODEL_ID)
        MODEL_DIR_ACT = d
    else:
        MODEL_DIR_ACT = MODEL_DIR
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL_DIR_ACT, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    dtype = torch.bfloat16 if dev == "cuda" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR_ACT, dtype=dtype, device_map="auto", trust_remote_code=True)
    print(f"[boot] base loaded {time.time()-t0:.0f}s dtype={dtype}", flush=True)

    lora = LoraConfig(
        task_type=TaskType.CAUSAL_LM, r=8, lora_alpha=16, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    examples = build_examples(tok, load_data())
    print(f"[data] {len(examples)} examples", flush=True)

    args = TrainingArguments(
        output_dir='./train_out', per_device_train_batch_size=8,
        gradient_accumulation_steps=2, num_train_epochs=2, learning_rate=2e-4,
        warmup_steps=2, logging_steps=2, save_strategy="no", report_to=[],
        bf16=(dev == "cuda"), fp16=False, dataloader_num_workers=0)

    def collate(batch):
        return collate_fn(batch)

    trainer = Trainer(model=model, args=args, train_dataset=examples,
                      data_collator=collate, processing_class=tok)
    t1 = time.time()
    trainer.train()
    print(f"[train] done in {(time.time()-t1)/60:.1f}min", flush=True)
    model.save_pretrained(ADAPTER_OUT)
    tok.save_pretrained(ADAPTER_OUT)
    print(f"[save] adapter -> {ADAPTER_OUT}", flush=True)

if __name__ == "__main__":
    main()
