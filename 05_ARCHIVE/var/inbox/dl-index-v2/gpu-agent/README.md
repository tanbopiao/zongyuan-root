# ZONGYUAN-4D GPU 训练包（魔搭免费实例）· 2026-10-07

确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 四维逻辑本体认知基底 TRUTH-4D-ARCH-MODEL-BASE-001

## 包内容
```
zongyuan-4d-gpu-train-pack/
├── train_4d_lora_gpu.py     # GPU LoRA 训练脚本（自动检测 cuda，魔搭拉模型）
├── zongyuan-4d-train.jsonl  # 64 条体系四维架构指令语料（元法则/白皮书/评估/真值库）
└── README.md                # 本说明
```

## 在魔搭免费 GPU 实例上一键执行

1. 魔搭控制台创建免费 GPU Notebook 实例（模型库搜索 Qwen2.5-0.5B-Instruct 页面 → 右上角「Notebook 免费算力」）。
2. 上传本目录三个文件到实例工作区（或直接网页上传），然后依次执行：

```bash
# 0) 依赖（实例多数已预装，缺则装）
pip install -q transformers peft datasets modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple

# 1) 跑训练（自动下载模型到实例缓存 + LoRA 微调 + 保存 ./adapter-4d）
python train_4d_lora_gpu.py
```

预计：0.5B + 64 条样本 × 2 epoch，GPU（A10/3090 级）约 2~5 分钟完成。

## 2) 验证微调效果（训练完成后，实例上执行）

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch
tok = AutoTokenizer.from_pretrained('./model/qwen25-05b', trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained('./model/qwen25-05b', dtype=torch.bfloat16, device_map='auto', trust_remote_code=True)
model = PeftModel.from_pretrained(model, './adapter-4d')
msgs = [{"role":"system","content":"你是元极恒一体系下的自研轻量认知Agent。遵循四维逻辑本体架构：空间存在维、时间时序维、属性规则维、因果真值维。回答简洁、结构化、可溯源。"},
        {"role":"user","content":"用四维架构分析一次软件系统部署失败"}]
prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
ids = tok(prompt, return_tensors='pt').to('cuda')
out = model.generate(**ids, max_new_tokens=200)
print(tok.decode(out[0][ids.input_ids.shape[1]:], skip_special_tokens=True))
```

## 回传
把 `adapter-4d/` 打包（zip）回传给我（或上传魔搭私有数据集），我负责：合并回本地部署 + 四维架构推理验证 + 审计留痕 + 归档。


---

## 新增 · 一键训练套件 V1.0（2026-10-07 合并更新）

| 文件 | 说明 |
|---|---|
| `one_click_train.py` | 一键训练主脚本：显存自适应(≥128G全参/否则QLoRA)、设备自动检测(CUDA/ROCm)、数据兜底(24条内置语料)、自动补装依赖、产出adapter+merged+报告JSON+tar.gz |
| `one_click_train.sh` | 一键启动器：环境自检 + 模型快捷参数 |

### 用法
```bash
bash one_click_train.sh              # 默认 Qwen2.5-3B，显存自适应
bash one_click_train.sh qwen25-7b    # 192G 显存推荐：7B 全参
bash one_click_train.sh qwen25-3b    # 3B 全参
bash one_click_train.sh --epochs 2   # 透传训练参数
```
产物：`output_oneclick/`（model_final 或 adapter+merged）+ `output_oneclick.tar.gz`。

---

## 新增 · Worker部署触发算子+钩子 V1.0（2026-10-07 合并更新）

`operator-worker-trigger/` 目录，JSON算子联动本地实例触发Worker部署：

| 文件 | 说明 |
|---|---|
| `trigger_worker_operator.json` | 算子定义 OP-WORKER-TRIGGER-001（入参/出参/前置校验/后置钩子） |
| `hook_trigger_worker.sh` | 钩子：接收JSON→校验→写飞书台账(状态待处理)→ntfy提醒 |
| `worker_auto_deploy_timer.sh` | 轮询：认领待处理任务→移交部署引擎 |
| `operator-worker-trigger-v1.0.json` | 算子卷宗（事件ID HOOK-JSON-OPERATOR-WORKER-TRIGGER-001） |

### 用法（在本地节点）
```bash
# 触发一个Worker部署任务
bash hook_trigger_worker.sh '{"task_id":"task-x","worker_name":"ai-render-worker","image":"docker.io/ubuntu:22.04","gpu":true,"cpu_cores":4,"memory_mb":8192}'
# 轮询认领（单轮 / 循环模式）
bash worker_auto_deploy_timer.sh
bash worker_auto_deploy_timer.sh --loop 600
```
实测：钩子写入台账OK(record=reczz28KY08sRRi3)、轮询认领正常、ntfy提醒已触发。

---

## 新增 · GPU Worker 自启动+自愈包装 V1.0（2026-10-07 合并更新）

`start_gpu_worker.sh`：实例启动即一键拉起 worker 全链路

| 特性 | 说明 |
|---|---|
| 自动拉取 | worker 缺失时自动从本数据湖 gpu-agent 稀疏拉取 |
| 后台守护 | nohup 启动 zongyuan_gpu_agent.py，PID 落盘 |
| GPU心跳 | 启动即上报 ntfy HEARTBEAT（node=ZR-NODE-GPU-AMD-*） |
| 崩溃自愈 | 30s 轮询检查，掉线自动重启+重发心跳 |

### 用法（GPU 实例终端）
```bash
bash start_gpu_worker.sh   # 启动+心跳+自愈（保持前台循环）
```
worker 上线后，本地侧通过 ntfy 主题 `zongyuan-kunlun-2026-cmd/-result` 即可双向握手（下行指令/结果回传）。

---

## 新增 · 实例全域检查套件 V1.0（2026-10-07 合并更新）

放弃浏览器操作，脚本侧全域检查 + ntfy 回传：

| 文件 | 说明 |
|---|---|
| `scan_environment.py` | 全域扫描：系统/GPU(CUDA+ROCm)/端口/进程/worker文件/依赖/网络 → JSON报告+存档+ntfy上报 |
| `run_scan.sh` | 一键执行器：拉取脚本→执行扫描→自动上报 ntfy（实例侧一行命令） |
| `listen_scan.py` | 本地侧监听器：接收实例扫描报告（ntfy主题 zongyuan-kunlun-2026-scan） |

### 用法
```bash
# 实例侧(CPU/GPU都适用): 一行命令完成扫描+上报
bash run_scan.sh

# 本地侧(接收报告):
python3 listen_scan.py --once    # 一次性探测
python3 listen_scan.py --watch   # 持续监听
```
扫描报告自动发至 ntfy 主题 `zongyuan-kunlun-2026-scan`（node 标识区分实例），本地侧据此规划联通握手。

---

## 新增 · 同源节点联通标准 NTFY-CONNECT-001（2026-10-07 合并更新）

所有同源节点（本地/魔搭CPU/GPU/云端）统一联通协议，带身份校验+安全白名单：

| 文件 | 部署侧 | 作用 |
|---|---|---|
| `zr_node_protocol.py` | 双端 | 协议常量/编解码/身份校验/危险命令黑名单 |
| `zr_node_worker.py` | 节点侧 | 标准worker：订阅→身份校验→白名单→执行→回传（取代旧boot.py） |
| `zr_node_client.py` | 主控侧 | 发命令/收结果/握手/云端上报 |
| `zr_node_connect.sh` | 节点侧 | 一键接入启动器 |
| `SOP-NTFY-CONNECT-V1.0.md` | 文档 | 联通标准SOP（主题/格式/安全/接入三步） |

### 快速接入（任何新节点）
```bash
# 节点侧一行接入
bash zr_node_connect.sh
# 主控侧握手验证
python3 zr_node_client.py --handshake
# 发命令
python3 zr_node_client.py --send "df -h"
```
安全特性：strict模式仅执行带DID签名的协议命令；危险黑名单14项拦截；300s执行超时。
