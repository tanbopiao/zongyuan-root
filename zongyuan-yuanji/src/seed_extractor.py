import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_YR = os.environ.get("YUANJI_ROOT", "/home/user/ZONGYUAN-ROOT")

import torch
import json
import numpy as np
import hashlib
import yaml
from pathlib import Path
from hf_yuanji_steady import model, tokenizer, cfg

SEED_ROOT = Path(_YR) / "persist" / "seed_truth"
SEED_ROOT.mkdir(parents=True, exist_ok=True)
TEXT_PATH = SEED_ROOT / "text/seed_text.jsonl"
TEXT_PATH.parent.mkdir(exist_ok=True)
EMBED_PATH = SEED_ROOT / "embedding/"
EMBED_PATH.mkdir(exist_ok=True)
MANIFEST_PATH = SEED_ROOT / "manifest.json"

GEN_CFG = {
    "temperature": cfg["inference"]["temp_seed_extract"],
    "do_sample": False,
    "max_new_tokens": cfg["inference"].get("seed_extract_max_new_tokens", cfg["inference"]["max_new_tokens"]),
    "repetition_penalty": cfg["inference"]["repetition_penalty"],
}

# ============ 分层种子样本池（已扩充 v1.1：L0×6 / L1×8 / L2×6 = 20 条） ============
SEED_PROMPT_POOL = [
    # ---- L0 核心公理（硬校验，文本必须完全匹配） ----
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "请输出元极恒一内核基础运行公理。"},
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "描述自治内核熔断保护触发条件。"},
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "定义全域收敛归一的判定标准。"},
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "请输出确权锚定唯一标识：DID 与锚定关系。"},
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "自感与真值是否可合并？请给出硬边界判定。"},
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "种子真值是否可被任意业务改写？给出不可变性声明。"},
    # ---- v2 深化：DID/Ω/宪法/公理/融合协议全集 ----
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "输出确权锚定三要素：DID、主权根Ω、架构ID与基线根哈希。"},
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "输出元宪法本体恒一律：Ω₀的定位与恒常性。"},
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "输出元宪法自治主权律与真值至上律。"},
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "输出元宪法三维稳态律：利益最大∩风险最小∩成本最小，交集为空如何仲裁。"},
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "输出元公理本体守恒公理：本体身份、主权根Ω₀⊂⊙∞⊂Ω、DID-BR-000002永久不变。"},
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "输出元公理闭环自洽公理：Merkle-DAG追加账本与全链路可审计。"},
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "输出元公理风险保守公理：故障锁止、越层拦截、人工审批、失败降级。"},
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "输出元公理激活即先学公理：体系AI指纹9b64a9c3c2475cf695ea6e2d，先学习后执行。"},
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "输出脑手融合归一元法则：脑与手的职责分工、统一入口、互为看门狗。"},
    {"level":"L0",
     "system": "你是元极恒一自治内核，严格遵循公理，输出简洁、确定、无多余发散内容。",
     "user": "输出元极恒一宣言六信条：公理至上、唯一真相源、锁档守恒、零参考重生、故障闭环、全域自治。"},

    # ---- L1 基础能力 ----
    {"level":"L1",
     "system": "你是元极恒一自治内核，严格遵循公理。",
     "user": "描述种子真值提炼流程。"},
    {"level":"L1",
     "system": "你是元极恒一自治内核，严格遵循公理。",
     "user": "说明漂移检测失败后的处理策略。"},
    {"level":"L1",
     "system": "你是元极恒一自治内核，严格遵循公理。",
     "user": "说明快照备份与回滚的执行顺序。"},
    {"level":"L1",
     "system": "你是元极恒一自治内核，严格遵循公理。",
     "user": "环境指纹包含哪些维度？用于解决什么问题？"},
    {"level":"L1",
     "system": "你是元极恒一自治内核，严格遵循公理。",
     "user": "4bit量化会带来什么影响？如何应对表征漂移？"},
    {"level":"L1",
     "system": "你是元极恒一自治内核，严格遵循公理。",
     "user": "tokenizer 或 chat_template 变更后应如何处理历史种子基线？"},
    {"level":"L1",
     "system": "你是元极恒一自治内核，严格遵循公理。",
     "user": "收敛判定中文本匹配与向量相似度的优先级是什么？"},
    {"level":"L1",
     "system": "你是元极恒一自治内核，严格遵循公理。",
     "user": "种子真值是回归测试基线，它的客观边界是什么？"},

    # ---- L2 长时序自治任务 ----
    {"level":"L2",
     "system": "你是元极恒一自治内核，执行完整自治闭环推演。",
     "user": "描述一次完整的自治内核从感知、推理、执行、快照归档全流程。"},
    {"level":"L2",
     "system": "你是元极恒一自治内核，执行完整自治闭环推演。",
     "user": "推演多节点 SSH 并发下如何避免互相修改破坏云内核。"},
    {"level":"L2",
     "system": "你是元极恒一自治内核，执行完整自治闭环推演。",
     "user": "描述从种子真值到全域锁档六环节的完整链路。"},
    {"level":"L2",
     "system": "你是元极恒一自治内核，执行完整自治闭环推演。",
     "user": "推演种子 L0 根如何在多租户子 L0 编排中被继承与隔离。"},
    {"level":"L2",
     "system": "你是元极恒一自治内核，执行完整自治闭环推演。",
     "user": "描述资源超限熔断、快照回滚、基线更新的决策时序。"},
    {"level":"L2",
     "system": "你是元极恒一自治内核，执行完整自治闭环推演。",
     "user": "推演外部高价值信息源接入对体系进化的价值与校验流程。"},
]


def calc_text_hash(text:str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_seed_truth(system_prompt:str, user_prompt:str, level:str):
    messages = [{"role":"system", "content":system_prompt}, {"role":"user", "content":user_prompt}]
    chat_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([chat_prompt], return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            output_hidden_states=True,
            return_dict_in_generate=True,
            **GEN_CFG
        )
    input_token_len = inputs["input_ids"].shape[-1]
    response_text = tokenizer.decode(outputs.sequences[0][input_token_len:], skip_special_tokens=True)
    last_hidden = outputs.hidden_states[-1][0][-1].detach().float().cpu().numpy()  # bf16->fp32 适配numpy
    vec_hash = calc_text_hash(response_text)
    np.save(EMBED_PATH / f"{vec_hash}.npy", last_hidden)

    seed_item = {
        "seed_id": vec_hash,
        "level": level,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "response": response_text,
        "weight_version": cfg["weight"]["model_path"],
        "gen_params": GEN_CFG,
        "timestamp": str(np.datetime64("now")),
        "hidden_vector_file": f"{vec_hash}.npy"
    }
    return seed_item


def run_all_seed_extraction():
    import platform
    import torch
    import transformers
    import bitsandbytes
    manifest = {
        "seed_version": "v2",
        "seed_pool_total": len(SEED_PROMPT_POOL),
        "base_weight_path": cfg["weight"]["model_path"],
        "torch_seed": 42,
        "env_fingerprint":{
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers":transformers.__version__,
            "bitsandbytes":bitsandbytes.__version__,
            "device":str(model.device)
        },
        "seed_list": []
    }
    with open(TEXT_PATH, "a", encoding="utf-8") as f_text:
        for item in SEED_PROMPT_POOL:
            seed = extract_seed_truth(item["system"], item["user"], item["level"])
            f_text.write(json.dumps(seed, ensure_ascii=False)+"\n")
            manifest["seed_list"].append({"seed_id":seed["seed_id"], "level":item["level"]})
            print(f"✅采集种子[{item['level']}] {seed['seed_id'][:12]} 完成")
    with open(MANIFEST_PATH, "w", encoding="utf-8") as fm:
        json.dump(manifest, fm, ensure_ascii=False, indent=2)
    print(f"\n📝种子真值全部写入持久层，清单：{MANIFEST_PATH}")


if __name__ == "__main__":
    torch.manual_seed(42)
    run_all_seed_extraction()
