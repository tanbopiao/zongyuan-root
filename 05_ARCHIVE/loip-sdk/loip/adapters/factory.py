"""
LOIP 模型适配器工厂
根据配置创建对应的模型适配器实例。
"""
from typing import Any, Dict, Optional
from .base import BaseLLMAdapter
from .doubao import DoubaoAdapter
from .openai_compatible import OpenAICompatibleAdapter, MODEL_PRESETS


def create_adapter(config: Dict[str, Any]) -> BaseLLMAdapter:
    """
    根据配置创建模型适配器

    配置格式1（直接指定）：
        {"adapter": "doubao", "api_key": "xxx", "model": "doubao-pro-32k"}

    配置格式2（使用预设）：
        {"preset": "doubao-pro", "api_key": "xxx"}

    配置格式3（OpenAI兼容自定义）：
        {"adapter": "openai", "api_key": "xxx", "model": "custom-model",
         "base_url": "https://your-gateway/v1"}
    """
    # 处理预设
    if "preset" in config:
        preset_name = config["preset"]
        if preset_name not in MODEL_PRESETS:
            raise ValueError(f"未知模型预设: {preset_name}, 可选: {list(MODEL_PRESETS.keys())}")
        preset = MODEL_PRESETS[preset_name].copy()
        preset["api_key"] = config.get("api_key", "")
        # 允许覆盖预设参数
        for key in ["model", "base_url", "temperature", "max_tokens"]:
            if key in config:
                preset[key] = config[key]
        return create_adapter(preset)

    adapter_type = config.get("adapter", "openai").lower()
    api_key = config.get("api_key", "")
    model = config.get("model", "")
    base_url = config.get("base_url")
    temperature = config.get("temperature", 0.7)
    max_tokens = config.get("max_tokens", 2048)

    if not api_key:
        raise ValueError("必须提供 api_key")
    if not model:
        raise ValueError("必须提供 model")

    kwargs = {k: v for k, v in config.items()
              if k not in ["adapter", "api_key", "model", "base_url",
                           "temperature", "max_tokens", "preset"]}

    if adapter_type in ["doubao", "volcengine", "ark"]:
        return DoubaoAdapter(api_key=api_key, model=model, base_url=base_url,
                             temperature=temperature, max_tokens=max_tokens, **kwargs)
    elif adapter_type in ["openai", "openai-compatible", "compatible", "qwen", "glm", "ollama"]:
        return OpenAICompatibleAdapter(api_key=api_key, model=model, base_url=base_url,
                                       temperature=temperature, max_tokens=max_tokens, **kwargs)
    else:
        raise ValueError(f"未知适配器类型: {adapter_type}, 可选: doubao, openai")


def get_supported_models() -> Dict[str, Dict[str, str]]:
    """获取所有支持的模型预设列表"""
    return MODEL_PRESETS.copy()
