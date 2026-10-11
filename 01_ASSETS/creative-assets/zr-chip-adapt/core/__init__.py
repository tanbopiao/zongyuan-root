"""
zr-chip-adapt · core/__init__.py
锚定：Ω₀⊂⊙∞⊂Ω  DID: DID-BR-000002
"""
from .interface import InferenceBackend, InferenceResult, DeviceMetrics
from .registry import register, get_backend, list_backends, auto_backend, auto_backend_metrics
from .detector import detect_chips, first_available
from .flatten import FlatteningLayer, wrap, _is_domestic

__all__ = [
    "InferenceBackend", "InferenceResult", "DeviceMetrics",
    "register", "get_backend", "list_backends", "auto_backend", "auto_backend_metrics",
    "detect_chips", "first_available",
    "FlatteningLayer", "wrap", "_is_domestic",
]
