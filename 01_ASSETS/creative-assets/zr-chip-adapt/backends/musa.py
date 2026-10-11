"""
zr-chip-adapt · backends/musa.py 摩尔线程 MTT 后端
MUSA 接口兼容 CUDA，新兴生态，算子/量化支持需验证。
锚定：Ω₀⊂⊙∞⊂Ω  DID: DID-BR-000002
"""
from ._base import ChipBackendBase
from core.registry import register


@register("musa")
class MUSABackend(ChipBackendBase):
    name = "musa"
    vendor = "MooreThreads"
    probe_cmd = "mthreads-gmi"
    probe_args = ["info"]
    default_mem_total_mb = 32768.0
    default_mem_free_mb = 28672.0
