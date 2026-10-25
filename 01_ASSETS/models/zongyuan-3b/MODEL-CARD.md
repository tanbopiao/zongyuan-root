# Model Card: Zongyuan-3B-Instruct-GGUF (Q4_K_M)

## 基本信息

| 项 | 值 |
|---|---|
| 模型名称 | zongyuan-3b-instruct-gguf |
| 基座模型 | Qwen/Qwen2.5-3B-Instruct |
| 权重来源 | 魔搭 ModelScope `Qwen/Qwen2.5-3B-Instruct-GGUF`（上游官方发布） |
| 本仓定位 | 国内二次分发备份，**未做任何权重改动、未做 LoRA 合并、未做增量训练** |
| 量化格式 | GGUF（llama.cpp 生态） |
| 量化方案 | Q4_K_M（4-bit 权重，部分张量保留较高精度以平衡质量与体积） |
| 文件大小 | 2.01 GB（2,104,932,768 字节） |
| 上下文长度 | 默认 2048（Modelfile 中 `num_ctx` 可调，Qwen2.5-3B 原生支持 32K） |

## 用途

- **本地 CPU 推理底座**：用于 ZONGYUAN-ROOT 自治体系的冷启动与离线推理，零 GPU 成本。
- **Ollama 一键导入**：随仓附带 `Modelfile.qwen25`，`ollama create` 即可用。
- **多源分发备份**：魔搭为上游主源，AtomGit 为国内加速/备份通道。

## 不适用场景

- 生产环境高精度对话（仅 3B 规模，Q4 量化后质量有损失）。
- 长文档理解（默认 num_ctx=2048，需手动调大并评估显存/内存）。
- 本仓**不包含**任何 Zongyuan 自研 LoRA 权重；`zongyuan-3b/` 目录名下当前仅分发原版 Qwen2.5-3B GGUF。

## 实测性能参考

2026-10-01 云端 CPU 实测（llama.cpp / Ollama）：

- 单条回复生成耗时：约 22 s（CPU，短文本）
- 推理峰值内存：约 2548 MB
- 空闲卸载后内存回落：约 497 MB（`OLLAMA_KEEP_ALIVE=30`）

## 量化参数说明

- 量化方法：GGUF Q4_K_M，属于 llama.cpp K-quant 系列。
- 权重位宽：4-bit；KV cache 不在量化范围内（默认 f16）。
- 精度损失：Q4_K_M 相对 f16 通常在困惑度上有轻微损失，对话任务主观感受接近原版；复杂推理/代码任务建议用 Q5_K_M 或 Q6_K。
- 复现方式：如需重新量化，可从魔搭下载 Qwen2.5-3B-Instruct 原版 fp16 权重，用 llama.cpp `quantize` 工具选择 `q4_k_m` 目标。

## 训练数据

本仓未对基座做任何二次训练。Qwen2.5-3B-Instruct 的训练数据说明请参阅官方卡：
https://www.modelscope.cn/models/Qwen/Qwen2.5-3B-Instruct

## 许可证

- 权重：Apache-2.0（Qwen2.5 模型 License，以官方为准）
- 本仓附带的 Modelfile / README / Model Card 文本：Apache-2.0
- 商业使用请同时遵循 Qwen 官方许可条款。

## 局限性与风险

- 3B 参数规模，知识截止与推理能力有限，可能产生幻觉。
- Q4 量化后对数字、代码、多语言长句的鲁棒性下降。
- 未经过安全对齐微调评估，输出内容需自行过滤。

## 维护

- 分发通道：AtomGit 模型仓库（本仓）+ 魔搭（上游）
- 维护者：ZONGYUAN-ROOT 自治体系
- 本模型卡由 staging 流程自动生成，对应本地源文件：`atomgit-model-release/qwen2.5-3b-instruct-q4_k_m.gguf`
