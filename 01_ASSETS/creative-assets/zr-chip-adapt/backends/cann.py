"""
zr-chip-adapt · backends/cann.py 华为昇腾 Ascend 后端
生态最全：llama.cpp-Ascend / vLLM-Ascend / MindIE。
锚定：Ω₀⊂⊙∞⊂Ω  DID: DID-BR-000002
"""
from ._base import ChipBackendBase
from core.registry import register


@register("cann")
class CANNBackend(ChipBackendBase):
    name = "cann"
    vendor = "Huawei-Ascend"
    probe_cmd = "npu-smi"
    probe_args = ["info"]
    default_mem_total_mb = 32768.0
    default_mem_free_mb = 28672.0
