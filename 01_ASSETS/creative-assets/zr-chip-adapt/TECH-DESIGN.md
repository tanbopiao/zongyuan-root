# 跨芯片自适应推理架构技术设计文档

**项目**：zr-chip-adapt（跨芯片自适应 + 国产拉平层）
**版本**：V1.0（M1 骨架 + M2 拉平层）
**日期**：2026-10-11
**锚定**：Ω₀⊂⊙∞⊂Ω · DID: DID-BR-000002
**体系**：ZONGYUAN-ROOT 元极恒一自治体系 · 品牌「火斗云智 AIOS」

---

## 一、背景与目标

### 1.1 问题
通用大模型之上的约束型自治架构（元公理/元法则/27算子/真值引擎/记忆网关）本质是**软件层、硬件无关**。但"模型推理"层依赖推理引擎与芯片加速，国产芯片（昇腾/海光/寒武纪/摩尔线程）在算子、量化、显存管理、长上下文、吞吐等方面与英伟达存在生态与利用效率差距。

### 1.2 目标
1. **硬件无关**：约束层通吃国内外芯片，零感知差异。
2. **可插拔**：推理后端抽象成统一接口，一份约束层多端通吃。
3. **国产拉平**：通过软件拉平层把国产芯片"实际发挥度"向理论峰值拉近，补齐生态短板。
4. **对外展示**：作为技术研究/技术展示资产发布到魔搭与 atomgit。

---

## 二、总体架构

```
┌──────────────────────────────┐
│ 约束层（硬件无关，已有）        │
│  27算子 / 真值引擎 / 记忆网关 / 调度 │
└──────────────┬───────────────┘
┌──────────────┴───────────────┐
│ ① 推理后端抽象层（M1，可插拔）  │
│  统一接口: infer/quantize/      │
│  set_context/batch/metrics     │
│  ┌───┬───┬───┬───┬───┐        │
│  │CUDA│ROCm│CANN│MLU│MUSA│     │
│  └───┴───┴───┴───┴───┘        │
└──────────────┬───────────────┘
┌──────────────┴───────────────┐
│ ② 国产拉平层（M2，仅国产启用）  │
│  算子路由/量化适配/显存调度/    │
│  上下文压缩/投机解码·批处理     │
└──────────────┬───────────────┘
┌──────────────┴───────────────┐
│ ③ 芯片层（不动）               │
│ 英伟达/AMD/昇腾/寒武纪/海光/    │
│ 摩尔线程                       │
└──────────────────────────────┘
```

---

## 三、M1 · 推理后端抽象层（可插拔）

### 3.1 统一接口（约束层只依赖 5 个方法）

| 方法 | 签名 | 作用 |
|---|---|---|
| `infer` | `infer(prompt, **kw) -> InferenceResult` | 推理 |
| `quantize` | `quantize(model, bit, **kw) -> Any` | 量化（Q4/GPTQ/动态位宽） |
| `set_context_len` | `set_context_len(len, **kw) -> None` | 长上下文 |
| `batch` | `batch(requests, **kw) -> List[InferenceResult]` | 批处理并发 |
| `get_device_metrics` | `get_device_metrics() -> DeviceMetrics` | 芯片算力/显存上报 |

### 3.2 数据契约

**InferenceResult**：`text / usage_tokens / latency_ms / backend / extra`
**DeviceMetrics**：`backend / vendor / device_name / memory_total_mb / memory_free_mb / compute_unit / is_available / raw`

### 3.3 注册机制（可插拔核心）

```python
@register("cuda")          # 类装饰器注册
class CUDABackend(ChipBackendBase):
    name = "cuda"; vendor = "NVIDIA"; probe_cmd = "nvidia-smi"; ...

# 约束层调用
b = auto_backend()         # 自动识别芯片并加载
r = b.infer(prompt)        # 与具体芯片无关
```

新增芯片 = 新增一个继承 `ChipBackendBase` 的文件 + 一个 `@register`，约束层零改动。

### 3.4 芯片自动识别
探测命令：`nvidia-smi`（NVIDIA）/ `rocm-smi`（AMD·海光）/ `npu-smi`（昇腾）/ `cnmon`（寒武纪）/ `mthreads-gmi`（摩尔线程）。
`auto_backend()` 按健康检查选可用后端；无真实芯片时回退 mock 模式（POC 可端到端跑通）。

### 3.5 后端清单

| 后端 | 厂商 | 生态 |
|---|---|---|
| `cuda` | 英伟达 | 最成熟 |
| `rocm` | AMD / 海光 DCU | ROCm 复用，国产适配成本低 |
| `cann` | 华为昇腾 | 最全（llama.cpp/vLLM-Ascend/MindIE） |
| `mlu` | 寒武纪 | 中等 |
| `musa` | 摩尔线程 | 新兴 |

---

## 四、M2 · 国产拉平层

### 4.1 定位
在约束层与推理后端之间插入一层拦截器，**仅国产芯片启用**（vendor ∈ 华为/寒武纪/海光/摩尔线程），英伟达/AMD 直通零开销。

### 4.2 五个子模块

| 模块 | 拦截点 | 功能 | 拉平什么 |
|---|---|---|---|
| **算子路由** | `infer` 前 | 国产不擅长算子→通用算子兜底/替换 | 算子性能差 |
| **量化适配** | `quantize` | 动态降位宽适配国产显存（Q8→Q4） | 显存带宽/容量不足 |
| **显存调度** | `infer`/`batch` | 张量切分/offload 决策 | 显存管理磨合不足 |
| **上下文压缩** | `set_context` | 长对话压缩 | 长上下文波动 |
| **投机解码/批处理** | `infer`/`batch` | 提升生成吞吐 | 单卡吞吐偏低 |

### 4.3 拦截器实现

```python
class FlatteningLayer:
    def __init__(self, backend):
        self.backend = backend
        self.enabled = _is_domestic(backend.vendor)   # 仅国产启用

    def infer(self, prompt, **kw):
        if not self.enabled: return self.backend.infer(prompt, **kw)
        prompt = self.operator_router.apply(prompt)     # 算子路由
        plan = self.mem_scheduler.plan(mem_free_mb, len(prompt))  # 显存调度
        return self.backend.infer(prompt, **kw)

    def quantize(self, model, bit, **kw):
        if not self.enabled: return self.backend.quantize(model, bit, **kw)
        bit = self.quantize_adapter.adapt(bit, mem_free_mb)
        return self.backend.quantize(model, bit, **kw)
```

### 4.4 启用判定

```python
DOMESTIC_VENDORS = ("Huawei", "Cambricon", "MooreThreads", "Hygon", "Sunway", "Biren")
```

---

## 五、验证结果（本机实跑）

### 5.1 M1 骨架（test_backend.py）✅
- 5 后端全部注册：`cann cuda mlu musa rocm`
- 统一接口 5 方法全通
- 芯片自动识别正确（本机无 GPU → 回退 mock）
- 全后端指标上报正常

### 5.2 M2 拉平层（test_flatten.py）✅
- 国产厂商识别正确
- cann/mlu/rocm/musa → enabled=True；cuda → 直通 enabled=False
- 量化适配：8GB 显存 → 自动降 4bit
- 显存调度：低显存+长token → offload
- 上下文压缩：16384 → 4096
- 拉平层总装 infer 走拦截器正常

---

## 六、落地优先级与里程碑

| 阶段 | 内容 | 状态 |
|---|---|---|
| M1 | 抽象层接口 + 后端注册 + 芯片识别 | ✅ 完成 |
| M2 | 拉平层五子模块 | ✅ 完成（本轮） |
| M3 | 多后端集成 + 真实模型引擎接入 + 基准对比 | 待续 |

**芯片优先级**：海光（ROCm 复用）≈ 昇腾（生态最全）→ 寒武纪 → 摩尔线程。

---

## 七、关键设计声明（边界诚实标注）

- 拉平层拉平的是**利用率/生态/算子**层差距，**不改变芯片物理上限**（单卡峰值/显存带宽/制程）。
- 作用 = 把国产芯片"实际发挥度"从偏低拉到接近满血 + 补齐生态；不创造硬件不存在的算力。
- 真实模型推理由模型引擎（llama.cpp/vLLM/Ollama）注入后端，本架构定义契约与注册机制。

---

## 八、对外价值

**约束架构：芯片无关底座 + 国产利用率拉平引擎** —— 既是技术事实，也是信创场景的差异化卖点。一份约束层，通吃国内外芯片，国产芯片利用率拉平。

---

**文档归属**：ZONGYUAN-ROOT 元极恒一自治体系 / 火斗云智 AIOS / DID-BR-000002 / Ω₀⊂⊙∞⊂Ω
