# FM-Core 联邦记忆智能体内核（元极恒一 Lv11 基线锁档）

三段式：**内核（记忆治理）→ 适配器（模型无关）→ 边缘 Agent（对话应用）**。
4G 纯 CPU 本地可跑，无 GPU 依赖。

```
fm_project/
├── fm_core/              内核：记忆原子、提案、共识投票、冲突检测、生命周期、审计哈希链   → :8100
├── fm_adapters/          适配层：embedding/retriever/extractor/generator 四类抽象 + 实现
├── fm_agent/             应用层：OpenAI 兼容对话服务，检索内核→生成→抽取→回写提案      → :8000
├── test_core.py          内核单元测试（独立临时库，不依赖 HTTP）
├── test_adapter.py       适配器联调测试（向量/检索/抽取/生成）
├── test_agent.py         端到端闭环测试（双端口，需先起服务）
├── fetch_models.sh       模型资产拉取（已就位即跳过）
└── requirements.txt
```

## 快速启动（严格按顺序）

```bash
pip install -r requirements.txt
./fetch_models.sh                      # 模型缺失时才需要联网

python -m fm_core.api.http_server       # 终端1：内核 :8100
python -m fm_agent.edge_agent           # 终端2：边缘 Agent :8000

python test_core.py                    # 单元测试（不依赖服务）
python test_adapter.py                 # 适配器联调（不依赖服务）
python test_agent.py                   # 闭环测试（需两个服务已起）
```

## 内核 API（:8100）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/fm/seed/add` | 种子真值写入（`status=seed`，投票/改写一律拒绝） |
| POST | `/fm/propose` | 提案写入（`status=proposed`，同义重复自动去重、语义冲突标 `conflict`） |
| GET | `/fm/retrieve?topk=3` | 检索：种子 → 归档 → 提案，同级按分数降序 |
| POST | `/fm/vote` | 共识投票；≥`MIN_VOTES` 票后，赞同比例 ≥0.60 归档、≤0.40 软遗忘（非删除） |
| GET | `/fm/atoms?status=` | 原子列表 |
| GET | `/fm/audit?verify=true` | 审计账本 + 哈希链完整性校验 |
| GET | `/health` | 健康 |

**生命周期**：`proposed → (vote) → archived | soft_forget | conflict`；`seed` 永久只读。
**审计**：每条变更写 `prev_hash` 链式记录，`verify_chain` 检出断链即 `valid=false`。

## 边缘 Agent（:8000）

`POST /v1/chat/completions`（OpenAI 兼容，messages/temperature/max_tokens/model），响应在标准字段之上附带：

| 字段 | 含义 |
|---|---|
| `local_fact_extract` | 从回答中抽取的事实（`[NO_STORE]` 表示无可存事实） |
| `audit_mid` / `fact_stored` | 回写成功的提案哈希 / 本次是否回写 |
| `memory_used` | 本次回答引用的内核原子 `mid` 列表 |
| `ram_used_gb` | 内存占用；超过 `high_watermark_gb`（默认 2.2）**不回写**，防 OOM |

`GET /health` 会连带探活内核（`kernel_reachable`）。内核未起时 Agent 返回 **503** 而非假成功。

## 模型资产（模型无关，换模型只改配置）

| 用途 | 文件 | 来源 | 说明 |
|---|---|---|---|
| Embedding | `bge-small-zh-int8.onnx` (23.9MB) | `Xenova/bge-small-zh-v1.5` | 384 维，均值池化 + L2 归一化，带磁盘缓存 |
| 分词器 | `tokenizer.json` / `vocab.txt` | 同上 | 适配器同时兼容 `.json` 与 `.txt` |
| LLM | `minimind2-Q4_K_M.gguf` (66MB) | `jingyaogong/MiniMind2-gguf` | MiniMind2 家族，2 线程 CPU 推理 |

> 原设计稿指定 `MiniMind-26M-Q4_K_M.gguf` 与 `bge-small-zh-q4.onnx`：前者在本环境无可达分发源，
> 后者需 ORT 未内置的算子。**均已替换为等价可用版本**，其余逻辑零改动。换回官方模型只需改
> `fm_agent/agent_config.yaml` 对应路径。

## 设计边界

- **适配器是唯一模型耦合点**：内核不 import 任何 LLM/向量库，换模型不动内核。
- **本层不含分布式**：跨节点联邦共识（`federated.py`）为下一阶段，边缘提案通过 A2A 上报。
- **回写是提议不是事实**：Agent 产出一律走 `propose`，需共识投票才归档；种子真值不可被 Agent 改写。
- 运行期产物（模型/索引/缓存/数据库）由 `.gitignore` 排除。
