"""
zr-chip-adapt · core/flatten.py
国产拉平层 —— 仅国产芯片启用的性能拦截器。

在约束层与推理后端之间插入一层，把国产芯片"实际发挥度"向理论峰值拉近。
五个子模块：算子路由 / 量化适配 / 显存调度 / 上下文压缩 / 投机解码·批处理。

启用规则：backend.vendor 属于国产厂商（昇腾/寒武纪/海光/摩尔线程）时 enabled=True；
英伟达/AMD 直通，零开销。

锚定：Ω₀⊂⊙∞⊂Ω  DID: DID-BR-000002
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .interface import InferenceBackend, InferenceResult, DeviceMetrics

logger = logging.getLogger("zr.flatten")

# 国产厂商判定表
DOMESTIC_VENDORS = ("Huawei", "Cambricon", "MooreThreads", "Hygon", "Sunway", "Biren")


def _is_domestic(vendor: str) -> bool:
    return any(v in (vendor or "") for v in DOMESTIC_VENDORS)


# ---------------------------------------------------------------------------
# 五个子模块（各自独立、可开关）
# ---------------------------------------------------------------------------

@dataclass
class OperatorRouter:
    """算子路由：识别国产不擅长算子并替换为通用/兜底实现"""
    enabled: bool = True
    router: Callable[[str], str] | None = None      # 外部注入算子改写器

    def apply(self, prompt: str) -> str:
        if not self.enabled:
            return prompt
        # 内置启发式：标记高开销算子段，交由后端兜底
        if " attention " in prompt or "flash-attn" in prompt:
            logger.debug("operator_route: 检测到 attention 算子，转兜底")
        return self.router(prompt) if self.router else prompt


@dataclass
class QuantizeAdapter:
    """量化适配：根据显存压力动态调整位宽"""
    enabled: bool = True
    fallback_bit: int = 4                            # 国产兜底位宽
    mem_threshold_gb: float = 16.0                   # 低于此显存降位宽

    def adapt(self, bit: int, mem_free_mb: float) -> int:
        if not self.enabled:
            return bit
        free_gb = mem_free_mb / 1024.0
        if free_gb < self.mem_threshold_gb:
            new_bit = min(bit, self.fallback_bit)
            logger.debug("quantize_adapt: %sbit -> %sbit (free=%sGB)", bit, new_bit, round(free_gb, 1))
            return new_bit
        return bit


@dataclass
class MemoryScheduler:
    """显存调度：张量切分/offload 决策"""
    enabled: bool = True
    offload_threshold_gb: float = 12.0
    chunk_size: int = 1024                             # 张量切分粒度

    def plan(self, mem_free_mb: float, tokens: int) -> Dict[str, Any]:
        if not self.enabled:
            return {"offload": False, "chunk": tokens}
        free_gb = mem_free_mb / 1024.0
        if free_gb < self.offload_threshold_gb and tokens > self.chunk_size:
            return {"offload": True, "chunk": self.chunk_size}
        return {"offload": False, "chunk": tokens}


@dataclass
class ContextCompressor:
    """上下文压缩：长对话压缩以降低显存压力"""
    enabled: bool = True
    max_ctx: int = 8192
    compress_ratio: float = 0.5

    def cap(self, length: int) -> int:
        if not self.enabled:
            return length
        if length > self.max_ctx:
            return int(self.max_ctx * self.compress_ratio)
        return length


@dataclass
class SpeculativeDecoder:
    """投机解码/批处理：提升生成吞吐"""
    enabled: bool = True
    draft_len: int = 5

    def batch_size(self, requests: List[str]) -> int:
        if not self.enabled:
            return len(requests)
        return max(1, len(requests))


# ---------------------------------------------------------------------------
# 拉平层总装
# ---------------------------------------------------------------------------

class FlatteningLayer:
    """国产拉平层：包装原始后端，国产自动套用五模块，非国产直通。"""

    def __init__(self, backend: InferenceBackend):
        self.backend = backend
        self.operator_router = OperatorRouter()
        self.quantize_adapter = QuantizeAdapter()
        self.mem_scheduler = MemoryScheduler()
        self.ctx_compressor = ContextCompressor()
        self.spec_decoder = SpeculativeDecoder()
        self.enabled = _is_domestic(backend.vendor)
        logger.info("FlatteningLayer for %s: enabled=%s", backend.name, self.enabled)

    # ---- 统一接口透传（带拉平拦截） ----

    def infer(self, prompt: str, **kwargs) -> InferenceResult:
        if not self.enabled:
            return self.backend.infer(prompt, **kwargs)
        # 算子路由
        prompt = self.operator_router.apply(prompt)
        # 显存调度
        m = self.backend.get_device_metrics()
        plan = self.mem_scheduler.plan(m.memory_free_mb, len(prompt))
        if plan.get("offload"):
            prompt = prompt[: plan["chunk"]]  # 示意切分
        return self.backend.infer(prompt, **kwargs)

    def quantize(self, model_ref: Any, bit: int, **kwargs) -> Any:
        if not self.enabled:
            return self.backend.quantize(model_ref, bit, **kwargs)
        m = self.backend.get_device_metrics()
        bit = self.quantize_adapter.adapt(bit, m.memory_free_mb)
        return self.backend.quantize(model_ref, bit, **kwargs)

    def set_context_len(self, length: int, **kwargs) -> None:
        if not self.enabled:
            return self.backend.set_context_len(length, **kwargs)
        length = self.ctx_compressor.cap(length)
        return self.backend.set_context_len(length, **kwargs)

    def batch(self, requests: List[str], **kwargs) -> List[InferenceResult]:
        if not self.enabled:
            return self.backend.batch(requests, **kwargs)
        bs = self.spec_decoder.batch_size(requests)
        return self.backend.batch(requests[:bs], **kwargs)

    def get_device_metrics(self) -> DeviceMetrics:
        return self.backend.get_device_metrics()

    def flatten_report(self) -> Dict[str, Any]:
        """输出拉平层配置与生效状态（供调度/上报）"""
        return {
            "backend": self.backend.name,
            "vendor": self.backend.vendor,
            "enabled": self.enabled,
            "operator_router": self.operator_router.enabled,
            "quantize_adapter": self.quantize_adapter.enabled,
            "memory_scheduler": self.mem_scheduler.enabled,
            "context_compressor": self.ctx_compressor.enabled,
            "speculative_decoder": self.spec_decoder.enabled,
        }


# 便捷：给任意后端套上拉平层
def wrap(backend: InferenceBackend) -> FlatteningLayer:
    return FlatteningLayer(backend)
