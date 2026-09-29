"""
LOIP 大模型适配基础接口
所有模型适配器必须继承 BaseLLMAdapter，实现 chat 方法。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMResponse:
    """大模型响应统一格式"""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    raw_response: Any = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


class BaseLLMAdapter(ABC):
    """大模型适配器基类"""

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None,
                 temperature: float = 0.7, max_tokens: int = 2048, **kwargs):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.extra_config = kwargs

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """
        发送聊天请求
        :param messages: [{"role": "user"/"system"/"assistant", "content": "..."}]
        :return: LLMResponse
        """
        pass

    def simple_chat(self, user_input: str, system_prompt: Optional[str] = None,
                    **kwargs) -> LLMResponse:
        """简化调用：单轮对话"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_input})
        return self.chat(messages, **kwargs)

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型配置信息"""
        return {
            "adapter": self.__class__.__name__,
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
