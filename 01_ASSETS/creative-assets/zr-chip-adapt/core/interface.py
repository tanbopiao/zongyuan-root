"""
zr-chip-adapt · core/interface.py
统一推理后端抽象接口 —— 约束层只依赖这 5 个方法，与具体芯片解耦。

约束层（27算子/真值引擎/记忆网关/调度）调用本接口，
具体实现由各后端（CUDA/ROCm/CANN/MLU/MUSA）注入，实现硬件无关。

锚定：Ω₀⊂⊙∞⊂Ω  DID: DID-BR-000002
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class InferenceResult:
    """统一推理返回结构"""
    text: str
    usage_tokens: Dict[str, int] = field(default_factory=dict)   # prompt/completion
    latency_ms: float = 0.0
    backend: str = ""                                            # 实际执行后端
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceMetrics:
    """芯片算力/显存上报，供调度与拉平层决策"""
    backend: str
    vendor: str
    device_name: str
    memory_total_mb: float = 0.0
    memory_free_mb: float = 0.0
    compute_unit: str = ""                                      # 如 CUDA Core / Ascend Core / ROCm CU
    is_available: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)


class InferenceBackend(ABC):
    """
    统一推理后端抽象基类。所有芯片后端必须实现这 5 个方法。
    约束层只调用这 5 个方法，不感知底层芯片细节。
    """
    name: str = "base"

    @abstractmethod
    def infer(self, prompt: str, **kwargs) -> InferenceResult:
        """推理：输入 prompt，返回生成文本"""

    @abstractmethod
    def quantize(self, model_ref: Any, bit: int, **kwargs) -> Any:
        """量化：对模型做指定位宽量化（Q4/GPTQ/动态位宽）"""

    @abstractmethod
    def set_context_len(self, length: int, **kwargs) -> None:
        """设置上下文长度（长上下文适配）"""

    @abstractmethod
    def batch(self, requests: List[str], **kwargs) -> List[InferenceResult]:
        """批处理并发推理"""

    @abstractmethod
    def get_device_metrics(self) -> DeviceMetrics:
        """上报芯片算力/显存指标"""

    # ---- 工具方法（可选覆盖） ----
    def health_check(self) -> bool:
        try:
            return self.get_device_metrics().is_available
        except Exception:
            return False
