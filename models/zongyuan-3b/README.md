# Zongyuan-3B-Instruct-GGUF (Q4_K_M)

> ZONGYUAN-ROOT 元极恒一自治体系 · 国内快速分发备份仓
> 基座：Qwen/Qwen2.5-3B-Instruct（阿里云通义千问）
> 量化格式：GGUF Q4_K_M（llama.cpp / Ollama 可直接加载）

## 模型清单

| 文件 | 格式 | 大小 | 分发方式 |
|---|---|---|---|
| `qwen2.5-3b-instruct-q4_k_m.gguf` | GGUF Q4_K_M | 2.01 GB | AtomGit 模型仓库网页端上传（非 git LFS） |
| `Modelfile.qwen25` | Ollama Modelfile | 119 B | 随仓 git 推送 |
| `MODEL-CARD.md` | 模型卡 | — | 随仓 git 推送 |

> **注意**：2GB GGUF 权重文件不随本仓 git 推送。请在 AtomGit 模型仓库网页端新建模型后上传该文件，上传完成后在本 README 替换下方「权重链接占位」为实际下载地址。

## 权重链接占位

- AtomGit 模型仓库：`<待用户网页端上传后回填，预期格式 https://atomgit.com/zongyuangen/qwen2.5-3b-instruct-gguf>`
- 上游原始来源：魔搭 `Qwen/Qwen2.5-3B-Instruct-GGUF`

## 快速部署

### 方式一：Ollama（含 Modelfile，一键导入）

```bash
# 1. 下载 qwen2.5-3b-instruct-q4_k_m.gguf 到本目录
# 2. 基于 Modelfile 创建 ollama 模型
ollama create zongyuan-3b -f Modelfile.qwen25
# 3. 运行
ollama run zongyuan-3b
```

### 方式二：llama.cpp（CPU 推理）

```bash
./llama-cli -m qwen2.5-3b-instruct-q4_k_m.gguf \
  -p "你好" -n 256 -t 4
```

## 实测指标（2026-10-01 云端 CPU 部署）

| 指标 | 实测值 |
|---|---|
| 推理耗时 | 约 22 s 正常回复（CPU） |
| 峰值内存 | 约 2548 MB |
| 空闲释放 | 30 s 后回落至约 497 MB（OLLAMA_KEEP_ALIVE=30 自动卸载） |

## 授权

本仓仅为 Qwen2.5-3B-Instruct 的 GGUF 量化分发备份，权重版权归原作者所有，遵循 Apache-2.0（Qwen2.5 模型 License）。商业使用请遵循 Qwen 官方条款。
