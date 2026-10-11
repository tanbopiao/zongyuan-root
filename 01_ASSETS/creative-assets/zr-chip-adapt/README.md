# zr-chip-adapt · 跨芯片自适应 + 国产拉平层（M1 骨架）

**阶段**：M1（可插拔推理后端骨架）
**锚定**：Ω₀⊂⊙∞⊂Ω · DID: DID-BR-000002
**体系**：ZONGYUAN-ROOT 元极恒一自治体系

## 目标
把"推理后端"抽象成可插拔层，使约束层（27算子/真值引擎/记忆网关/调度）硬件无关、通吃国内外芯片；为国产芯片（昇腾/海光/寒武纪/摩尔线程）提供统一适配底座。

## 目录结构
```
zr-chip-adapt/
├── core/
│   ├── interface.py    # 统一推理接口（infer/quantize/set_context/batch/get_device_metrics）
│   ├── registry.py     # 后端注册框架（register/get_backend/auto_backend）
│   ├── detector.py     # 芯片自动识别（nvidia/rocm/ascend/cambricon/mthreads）
│   └── __init__.py
├── backends/
│   ├── _base.py        # 通用芯片后端基类（mock 模式 + 统一接口默认实现）
│   ├── cuda.py         # NVIDIA
│   ├── rocm.py         # AMD / 海光 DCU
│   ├── cann.py         # 华为昇腾 Ascend
│   ├── mlu.py          # 寒武纪 Cambricon
│   └── musa.py         # 摩尔线程 MTT
├── tests/test_backend.py  # 端到端验证
└── README.md
```

## 运行
```bash
cd zr-chip-adapt
python3 tests/test_backend.py
```

## 统一接口（约束层只依赖这 5 个方法）
| 方法 | 作用 |
|---|---|
| `infer(prompt)` | 推理 |
| `quantize(model, bit)` | 量化（Q4/GPTQ/动态位宽） |
| `set_context_len(len)` | 长上下文 |
| `batch(requests)` | 批处理并发 |
| `get_device_metrics()` | 芯片算力/显存上报 |

## POC 说明
- 无真实芯片时后端自动进入 `mock` 模式，可端到端跑通约束层调用链。
- 检测到真实芯片（`nvidia-smi`/`rocm-smi`/`npu-smi`/`cnmon`/`mthreads-gmi`）时上报真实指标。
- 真实模型推理由模型引擎（llama.cpp/vLLM/Ollama）注入后端，本骨架定义契约与注册机制。

## 技术设计文档
完整对外技术展示文档见 **`TECH-DESIGN.md`**（M1 骨架 + M2 拉平层，含架构图/接口契约/验证结果/边界声明）。

## M2 国产拉平层（已完成）
- `core/flatten.py`：五个子模块（算子路由/量化适配/显存调度/上下文压缩/投机解码·批处理），仅国产启用。
- 验证：`python3 tests/test_flatten.py` 全部通过（国产启用、非国产直通、量化降位宽、显存offload、上下文压缩）。

## 目录（完整）
```
zr-chip-adapt/
├── core/
│   ├── interface.py    # 统一推理接口（infer/quantize/set_context/batch/get_device_metrics）
│   ├── registry.py     # 后端注册框架（register/get_backend/auto_backend）
│   ├── detector.py     # 芯片自动识别（nvidia/rocm/ascend/cambricon/mthreads）
│   ├── flatten.py      # 国产拉平层（M2：算子路由/量化/显存/上下文/投机解码）
│   └── __init__.py
├── backends/
│   ├── _base.py        # 通用芯片后端基类（mock 模式 + 统一接口默认实现）
│   ├── cuda.py         # NVIDIA
│   ├── rocm.py         # AMD / 海光 DCU
│   ├── cann.py         # 华为昇腾 Ascend
│   ├── mlu.py          # 寒武纪 Cambricon
│   └── musa.py         # 摩尔线程 MTT
├── tests/
│   ├── test_backend.py    # M1 骨架端到端验证
│   └── test_flatten.py    # M2 拉平层端到端验证
├── TECH-DESIGN.md      # 对外技术设计文档
└── README.md
```
