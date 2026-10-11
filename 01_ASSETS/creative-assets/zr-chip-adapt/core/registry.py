"""
zr-chip-adapt · core/registry.py
后端注册框架 —— 可插拔机制的核心。

约束层通过 get_backend(name) 或 auto_backend() 获取后端实例，
运行时会自动识别芯片并加载对应驱动，约束层代码零改动。

锚定：Ω₀⊂⊙∞⊂Ω  DID: DID-BR-000002
"""
from __future__ import annotations

from typing import Dict, Optional, Type

from .interface import InferenceBackend

# 全局后端注册表：name -> Backend 类
_REGISTRY: Dict[str, Type[InferenceBackend]] = {}


def register(name: str):
    """类装饰器：注册一个后端实现"""
    def deco(cls: Type[InferenceBackend]) -> Type[InferenceBackend]:
        cls.name = name
        _REGISTRY[name] = cls
        return cls
    return deco


def get_backend(name: str) -> Optional[InferenceBackend]:
    """按名称实例化后端（未找到返回 None，不抛异常）"""
    cls = _REGISTRY.get(name)
    return cls() if cls is not None else None


def list_backends() -> list:
    """列出已注册后端名"""
    return sorted(_REGISTRY.keys())


def auto_backend(preferred: Optional[str] = None) -> Optional[InferenceBackend]:
    """
    自动识别芯片并返回对应后端。
    逻辑：优先用配置指定的 preferred；否则按注册表顺序做健康检查，
    返回第一个 is_available 的后端。
    """
    if preferred and preferred in _REGISTRY:
        b = get_backend(preferred)
        if b and b.health_check():
            return b
    for name in list_backends():
        b = get_backend(name)
        if b and b.health_check():
            return b
    return None


def auto_backend_metrics() -> dict:
    """返回所有注册后端的设备指标（用于调度/上报）"""
    out = {}
    for name in list_backends():
        b = get_backend(name)
        if b:
            try:
                m = b.get_device_metrics()
                out[name] = {
                    "available": m.is_available,
                    "vendor": m.vendor,
                    "device": m.device_name,
                    "mem_free_mb": m.memory_free_mb,
                }
            except Exception as e:
                out[name] = {"available": False, "error": str(e)}
    return out
