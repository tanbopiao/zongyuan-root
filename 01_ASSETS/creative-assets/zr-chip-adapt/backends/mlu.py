"""
zr-chip-adapt · backends/mlu.py 寒武纪 Cambricon 后端
llama.cpp/vLLM 有 MLU 支持，中等生态。
锚定：Ω₀⊂⊙∞⊂Ω  DID: DID-BR-000002
"""
from ._base import ChipBackendBase
from core.registry import register


@register("mlu")
class MLUBackend(ChipBackendBase):
    name = "mlu"
    vendor = "Cambricon"
    probe_cmd = "cnmon"
    probe_args = ["info"]
    default_mem_total_mb = 32768.0
    default_mem_free_mb = 28672.0
