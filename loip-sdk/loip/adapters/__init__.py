"""
LOIP 多模型适配层 v0.4
统一大模型调用接口，支持豆包/OpenAI/通义/智谱/Ollama等。
核心设计：用户只需配置模型类型和API密钥，loip.chat()自动完成调用+治理。
"""
from .base import BaseLLMAdapter, LLMResponse
from .doubao import DoubaoAdapter
from .openai_compatible import OpenAICompatibleAdapter
from .factory import create_adapter, get_supported_models

__all__ = ["BaseLLMAdapter", "LLMResponse", "DoubaoAdapter",
           "OpenAICompatibleAdapter", "create_adapter", "get_supported_models"]
