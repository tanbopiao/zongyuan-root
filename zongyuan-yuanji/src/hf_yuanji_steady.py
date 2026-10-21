import os
import torch
torch.set_num_threads(4)

import psutil
import logging
import yaml
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# 根目录适配：YUANJI_ROOT 环境变量优先，默认本机路径（本地=沙箱，云端=/root/zongyuan-yuanji）
_YR = os.environ.get("YUANJI_ROOT", "/home/user/ZONGYUAN-ROOT")
log_dir = Path(_YR) / "logs"; log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(log_dir / "seed.log"), level=logging.INFO)

# 加载配置
with open(Path(_YR) / "config" / "yuanji_steady.yaml","r",encoding="utf-8") as f:
    cfg = yaml.safe_load(f)
if _YR != "/home/user/ZONGYUAN-ROOT":
    cfg["weight"]["model_path"] = cfg["weight"]["model_path"].replace("/home/user/ZONGYUAN-ROOT", _YR)

# 4bit量化配置
bnb_cfg = BitsAndBytesConfig(
    load_in_4bit=cfg["quant"]["load_in_4bit"],
    bnb_4bit_quant_type=cfg["quant"]["bnb_4bit_quant_type"],
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=cfg["quant"]["bnb_4bit_use_double_quant"]
)
model_path = cfg["weight"]["model_path"]

# 加载分词器与模型
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
_device_map = "auto" if torch.cuda.is_available() else "cpu"  # 无GPU自动降级CPU
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    quantization_config=bnb_cfg,
    device_map=_device_map,
    trust_remote_code=True,
    torch_dtype=torch.bfloat16
)
model.eval()
torch.manual_seed(42)


def check_resource_safe() -> bool:
    mem = psutil.virtual_memory()
    mem_usage = mem.percent / 100
    cpu_usage = psutil.cpu_percent(interval=0.2)/100
    if mem_usage > cfg["resource"]["mem_critical"] or cpu_usage>cfg["resource"]["cpu_load_max"]:
        logging.warning(f"资源超限 mem:{mem_usage:.2f}, cpu:{cpu_usage:.2f}，拒绝推理")
        return False
    return True


def steady_chat(user_msg:str, system_prompt:str="你是元极恒一自治内核", temperature=0.3):
    if not check_resource_safe():
        raise RuntimeError("资源超限，触发熔断")
    messages = [
        {"role":"system", "content":system_prompt},
        {"role":"user", "content":user_msg}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    input_len = inputs["input_ids"].shape[-1]
    if input_len > cfg["inference"]["max_ctx_len"] - cfg["inference"]["max_new_tokens"]:
        raise ValueError("上下文超限，上层内核分片处理")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=cfg["inference"]["max_new_tokens"],
            temperature=temperature,
            top_p=cfg["inference"]["top_p"],
            repetition_penalty=cfg["inference"]["repetition_penalty"],
            do_sample= True if temperature>0 else False,
            pad_token_id=tokenizer.eos_token_id
        )
    resp = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True)
    if len(resp.strip()) < 2:
        raise ValueError("脏输出，丢弃")
    return resp
