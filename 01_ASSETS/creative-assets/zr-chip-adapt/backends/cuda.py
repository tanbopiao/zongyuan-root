"""
zr-chip-adapt · backends/cuda.py  NVIDIA 后端
锚定：Ω₀⊂⊙∞⊂Ω  DID: DID-BR-000002
"""
from ._base import ChipBackendBase
from core.registry import register


@register("cuda")
class CUDABackend(ChipBackendBase):
    name = "cuda"
    vendor = "NVIDIA"
    probe_cmd = "nvidia-smi"
    probe_args = ["--query-gpu=name,memory.total,memory.free", "--format=csv,noheader"]
    default_mem_total_mb = 24576.0
    default_mem_free_mb = 20480.0
