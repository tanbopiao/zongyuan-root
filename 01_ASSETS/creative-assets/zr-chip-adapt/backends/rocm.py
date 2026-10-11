"""
zr-chip-adapt · backends/rocm.py  AMD/海光 DCU 后端
海光 DCU 复用 ROCm 生态，类 CUDA，国产适配成本低。
锚定：Ω₀⊂⊙∞⊂Ω  DID: DID-BR-000002
"""
from ._base import ChipBackendBase
from core.registry import register


@register("rocm")
class ROCMBackend(ChipBackendBase):
    name = "rocm"
    vendor = "AMD/Hygon-DCU"
    probe_cmd = "rocm-smi"
    probe_args = ["--showmeminfo", "vram"]
    default_mem_total_mb = 32768.0
    default_mem_free_mb = 28672.0
