# -*- coding: utf-8 -*-
"""ZONGYUAN-4D 一键微调（魔搭 GPU 实例 · 零文件上传版）
用法：把本文件全部内容复制进魔搭 Notebook 单元格（或终端 python 文件）执行。
流程：装依赖 → 魔搭拉取 Qwen2.5-0.5B-Instruct → LoRA 微调(内嵌20条体系核心语料) → 保存 ./adapter-4d → 打印回传指引
确权: DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ TRUTH-4D-ARCH-MODEL-BASE-001
"""
import os, json, torch

# 1) 内嵌体系核心语料（四维架构 + 元极恒一精要, 20条指令对）
CORPUS = [
    ("四维逻辑本体架构是什么", "四维逻辑本体架构是自研小模型的顶层认知基底（TRUTH-4D-ARCH-MODEL-BASE-001）：空间存在维（对象/结构/边界）+ 时间时序维（阶段/演进）+ 属性规则维（规则/约束）+ 因果真值维（因果链/真值校验）。底层神经网络负责语义表征，四维架构负责逻辑约束、真值校验、状态管理，二者正交隔离，可外挂集成或训练融合。"),
    ("什么是空间存在维", "空间存在维：明确对象、实体、结构与边界。回答任何问题先定位主体对象、组成结构与作用边界，避免概念模糊与越界。"),
    ("什么是时间时序维", "时间时序维：明确阶段、时序与演进。把问题放在时间轴上：现状、历史阶段、未来演化，不做静态切片式判断。"),
    ("什么是属性规则维", "属性规则维：明确可枚举属性与硬性规则约束。用可枚举的属性列表与规则边界约束推理，不越规则、不编造属性。"),
    ("什么是因果真值维", "因果真值维：明确因果链与真值校验。区分事实与推断，每个结论标注因果依据与真值来源，无法校验的标为待确认。"),
    ("元极恒一是什么", "元极恒一：火斗云智AIOS的超认知永恒自治内核体系，昆仑洞天短剧流水线、政务AI中台、作品画廊、记忆网关、全域资产持久层的底层中枢，多智能体闭环自治架构。元极=不可修改的底层基准（修改须人工审批）；恒一=所有会话、资产、真值、知识库收敛到同一基准态，全域锁档、哈希固化、稳态进化。"),
    ("体系决策元法则公式是什么", "决策元法则（本地Windows口径）：P = 0.3U − 0.4R − 0.3C，收益最大/风险最小（权重最高）/成本最小。P≥0.7 立即自愈校准；P<0.3 强制回滚纯净母版；破坏性动作先可逆小步。"),
    ("全域锁档六环节是什么", "全域锁档六环节（append-only 只追加）：①本地快照锁档(SHA-256→卷宗回执+HASH-LEDGER) ②飞书Base真值同步 ③飞书云盘归档 ④飞书知识库归档 ⑤云端记忆网关上报 ⑥心跳握手。失败不阻塞主流程，逐源容错。"),
    ("双内核联邦结构是什么", "双内核联邦（META-FUSION-001）：脑=zongyuan-kernel（认知/审批/记忆/审计），手=ZONGYUAN-ROOT（调度/归档/锁档/上报）。统一入口 zongyuan_fusion.sh，两树零改动逻辑联邦，互为看门狗。"),
    ("记忆网关协议是什么", "记忆网关协议：端点 https://www.huodouai.com/api/report/truth（无尾部斜杠）；仅 X-DID: DID-BR-000002 单头认证；POST + application/json；载荷 {key,value} 信封；成功判定含 message=真值写入成功 + truth_count；失败不阻塞主流程；备份通道 drama.huodouai.com。"),
    ("四层实体架构是什么", "四层实体架构：L0 元宪法层（不动点根层,不可覆盖）→ L1 元公理层（七公理A1-A7冻结版）→ L2 元法则层（可枚举实体）→ L3 元规则层（执行层规则）。冲突裁决序：L0 > L1 > L2 > L3 > 任务指令 > 声明值。"),
    ("五面拓扑是哪五面", "五面拓扑：①本机ZONGYUAN-ROOT内核（权威写入面）②云端资料库（人读镜像面）③飞书Base共享大脑（结构化台账面）④云端记忆网关（仲裁面）⑤沙箱LITE（降级读面）。各司其职互不重叠。"),
    ("三级记忆架构是什么", "三级记忆架构：L1每次注入=最高约束实体全文+全量索引；L2资料库=全量索引与逐件指纹按需精读；L3只读实体源=AGENTS.md/metalaws/metarules逐字节不可改。验收判据是实体标识命中率而非字数。"),
    ("语义基座是什么", "语义基座 SEMANTIC-CORE-STABLE V2.1：统一元宪法/元公理/元法则/元规则/元智能/元认知等体系通用语义，SHA锁定零漂移，统摄通用大模型对齐。"),
    ("联邦记忆池是什么", "联邦记忆池：10源合并的持久化记忆（元法则/白皮书/协议/飞书53表等），Merkle哈希锁档，每日定时刷新并推送魔搭数据湖镜像。"),
    ("稳态评分评估维度有哪些", "本地内核全维度评估8维：真值链、记忆体系、语义基座、自治能力、决策体系、同步灾备、治理合规、存储健康。实测口径可复现，不混用未验证声明。"),
    ("镜像数据湖是什么", "魔搭数据湖镜像：ZONGYUAN-ROOT 收敛资产双向镜像（zongyuan-root/web/等子目录），git 哈希链完整，增量推送，双盘分散缓解C盘压力。"),
    ("本地0.5B模型部署结构", "本地0.5B部署：魔搭拉取 Qwen2.5-0.5B-Instruct（safetensors+GGUF多档量化），venv于D盘，transformers+peft，推理注入四维架构认知基底，CPU实测3.41tok/s，adapter可热加载微调。"),
    ("推理时如何注入四维认知基底", "推理时通过 system prompt 注入四维逻辑本体架构（空间/时间/属性/因果四维约束），要求回答简洁、结构化、可溯源；语义由权重提供，逻辑约束由架构层提供。"),
    ("审计留痕规范是什么", "审计留痕规范：事件统一写 logs/local_converge_*.jsonl，格式 {event,ts,actor,action,result,detail}，append-only 只追加不修改历史行；重要变更后自动全域锁档六环节。"),
]

SYSTEM = "你是元极恒一体系下的自研轻量认知Agent。遵循四维逻辑本体架构：空间存在维、时间时序维、属性规则维、因果真值维。回答简洁、结构化、可溯源。锚定 DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω。"

# 2) 依赖
print("[1/4] 安装依赖...", flush=True)
os.system("pip -q install transformers peft datasets modelscope 2>/dev/null || pip -q install transformers peft datasets modelscope")

# 3) 拉模型
print("[2/4] 拉取 Qwen2.5-0.5B-Instruct...", flush=True)
from modelscope import snapshot_download
model_dir = snapshot_download('qwen/Qwen2.5-0.5B-Instruct')

# 4) 训练
print("[3/4] LoRA 微调...", flush=True)
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, TaskType

tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16, device_map="auto", trust_remote_code=True)
model = get_peft_model(model, LoraConfig(task_type=TaskType.CAUSAL_LM, r=8, lora_alpha=16, lora_dropout=0.05,
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"]))
model.print_trainable_parameters()

def build(recs):
    ex = []
    for q, a in recs:
        msgs = [{"role":"system","content":SYSTEM},{"role":"user","content":q},{"role":"assistant","content":a}]
        pe = tok.apply_chat_template(msgs[:2], tokenize=True, add_generation_prompt=True)
        fe = tok.apply_chat_template(msgs, tokenize=True)
        p = pe.input_ids if hasattr(pe,"input_ids") else pe
        f = fe.input_ids if hasattr(fe,"input_ids") else fe
        f = f[:512]
        lab = [-100]*len(p) + f[len(p):]
        if len(lab) < 512:
            lab += [-100]*(512-len(lab)); f += [tok.pad_token_id]*(512-len(f))
        ex.append({"input_ids": f, "labels": lab})
    return ex

def coll(batch):
    il = torch.tensor([e["input_ids"] for e in batch], dtype=torch.long)
    lb = torch.tensor([e["labels"] for e in batch], dtype=torch.long)
    return {"input_ids": il, "attention_mask": torch.ones_like(il), "labels": lb}

ds = build(CORPUS)
args = TrainingArguments(output_dir="./train_out", per_device_train_batch_size=8, gradient_accumulation_steps=2,
    num_train_epochs=3, learning_rate=2e-4, warmup_steps=2, logging_steps=2, save_strategy="no", report_to=[], bf16=True)
Trainer(model=model, args=args, train_dataset=ds, data_collator=coll, processing_class=tok).train()
model.save_pretrained("./adapter-4d"); tok.save_pretrained("./adapter-4d")
print("[4/5] adapter 已保存到 ./adapter-4d", flush=True)

# [5/5] 自动回传: adapter 推送魔搭数据湖 gpu-agent/adapter-4d/（读环境变量令牌，无需人工）
import os as _os, shutil as _sh, subprocess as _sp
TOKEN = _os.environ.get("MODELSCOPE_SDK_TOKEN", "").strip()
DL_URL = "https://www.modelscope.cn/datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE.git"
here = _os.path.dirname(_os.path.abspath(__file__))
root = _os.path.abspath(_os.path.join(here, ".."))
if TOKEN and _os.path.isdir(_os.path.join(root, ".git")):
    try:
        _sh.copytree("./adapter-4d", _os.path.join(root, "gpu-agent", "adapter-4d"), dirs_exist_ok=True)
        _sp.run(["git", "add", "gpu-agent/adapter-4d"], cwd=root, check=True, capture_output=True)
        _sp.run(["git", "commit", "-m", "adapter-4d 四维LoRA训练结果 20261007"], cwd=root, check=True, capture_output=True)
        _sp.run(["git", "push", DL_URL.replace("https://", f"https://{TOKEN}@"), "master"],
                cwd=root, check=True, capture_output=True, timeout=300)
        print("[5/5] 回传完成: adapter 已推送到魔搭数据湖 gpu-agent/adapter-4d/", flush=True)
    except Exception as e:
        print("[5/5] 回传失败:", repr(e)[:300], " 请手动打包 adapter-4d 回传", flush=True)
else:
    print("[5/5] 未设置 MODELSCOPE_SDK_TOKEN 或非仓库目录，跳过自动回传；请手动打包 adapter-4d 回传", flush=True)
print("TRAIN-ALL-DONE", flush=True)
