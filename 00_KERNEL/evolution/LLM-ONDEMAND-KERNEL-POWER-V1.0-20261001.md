# 本地自治内核按需算力动力源方案 V1.0

- **确权**: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
- **批次**: LLM-ONDEMAND-20261001-B
- **状态**: 已真实部署并验证通过

## 一、方案定位

用**最小内存负载 + 按需拉起权重参数**为本地自治内核提供推理动力源：
空闲时零模型进程（内存 ~500MB），请求到来才加载 3B 模型权重（+2GB），推理完成 30 秒空闲自动卸载。

## 二、架构

```
┌─────────────────────────────────────────────────┐
│  本地自治内核 (00_KERNEL)                         │
│  meta_cognition / truth_generator / evolve       │
│         │ 调用推理                                │
│         ▼                                        │
│  llm_kernel_bridge.py (桥接器)                    │
│  · 自动探测/拉起网关 · 重试 · 内核专用prompt模板    │
│         │ HTTP /v1/chat/completions               │
│         ▼                                        │
│  llm_on_demand_server.py (按需网关) 127.0.0.1:8777│
│  · 零进程常驻 · 请求触发模型拉起                    │
│         │                                        │
│         ▼                                        │
│  ollama serve (11434) + qwen2.5:3b (Q4_K_M 2.1GB)│
│  · OLLAMA_KEEP_ALIVE=30 空闲自动卸载               │
└─────────────────────────────────────────────────┘
```

## 三、内存负载实测（总内存 4033MB）

| 状态 | 内存已用 | 说明 |
|---|---|---|
| 待命态（模型未启动） | ~500MB | ollama serve + 网关 |
| 启动后（加载+推理） | ~2548MB | 模型权重 2.05GB + KV + 开销 |
| 空闲卸载后 | ~500MB | 30s 自动回归待命 |

## 四、组件清单

| 组件 | 路径 | 职责 |
|---|---|---|
| 按需网关 | ZONGYUAN-ROOT/scripts/llm_on_demand_server.py | HTTP 网关，按需拉起/释放 |
| 网关配置 | ZONGYUAN-ROOT/config/llm_on_demand_config.json | backend=ollama, model=qwen2.5:3b, idle=30s |
| 内核桥接器 | 00_KERNEL/scripts/llm_kernel_bridge.py | 内核脚本调推理的统一入口 |
| 推理后端 | ~/ollama (v0.35.0) | ollama serve @11434 |
| 模型权重 | ~/models/qwen25-3b/ (2.1GB GGUF) | 魔搭官方 Q4_K_M，已导入 qwen2.5:3b |

## 五、内核接入方式

内核脚本（meta_cognition / truth_generator / evolve_closed_loop 等）调用桥接器：

```python
from llm_kernel_bridge import refine, decide, generate, chat, status

# 1. 元法则提炼
r = refine("原始素材文本", truth_type="meta_law")
# 2. 自主决策评估(80分门槛)
r = decide("某进化方案描述", threshold=80)   # r["pass"]=True/False
# 3. 内容生成(回执/文档/报告)
r = generate("生成一条执行回执")
# 4. 算力状态
s = status()
```

命令行方式：
```bash
python3 llm_kernel_bridge.py status
python3 llm_kernel_bridge.py chat "用一句话介绍昆仑洞天"
python3 llm_kernel_bridge.py refine "素材..." --type meta_law
python3 llm_kernel_bridge.py decide "方案..." --threshold 80
```

## 六、验证记录

| 验证项 | 结果 |
|---|---|
| 魔搭拉取 Qwen2.5-3B Q4_K_M | ✅ 2.1GB / 1分38秒 |
| GGUF 导入 ollama | ✅ qwen2.5:3b 创建成功 |
| 网关端到端推理 | ✅ 22.2s 正常回复 |
| 空闲自动释放 | ✅ 2548MB → 497MB (30s) |
| 进程守护 | ✅ setsid 常驻 (ollama + 网关) |

## 七、资源约束

- 最低规格：2 核 CPU + 4GB 内存云 VM
- 上下文 4096 时 KV 缓存 ~0.3GB；8192 时 +0.3GB（仍安全）
- 零 GPU、零云费用、零付费额度
