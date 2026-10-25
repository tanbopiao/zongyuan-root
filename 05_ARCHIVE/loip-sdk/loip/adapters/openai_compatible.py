"""
OpenAI兼容API适配器
适用于所有兼容OpenAI接口的模型：
- OpenAI (gpt-4, gpt-3.5-turbo)
- 通义千问 (DashScope兼容模式)
- 智谱GLM (BigModel兼容模式)
- 本地模型 (Ollama, vLLM, LM Studio)
- 其他OpenAI兼容网关
"""
import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from .base import BaseLLMAdapter, LLMResponse


class OpenAICompatibleAdapter(BaseLLMAdapter):
    """OpenAI兼容接口适配器"""

    DEFAULT_BASE_URL = "https://api.openai.com/v1"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini",
                 base_url: Optional[str] = None, **kwargs):
        super().__init__(api_key, model, base_url or self.DEFAULT_BASE_URL, **kwargs)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens)
        }
        for key in ["top_p", "frequency_penalty", "presence_penalty", "stop", "stream"]:
            if key in kwargs:
                payload[key] = kwargs[key]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                         headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return LLMResponse(
                content=content,
                model=self.model,
                usage=usage,
                raw_response=data
            )
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            return LLMResponse(content="", model=self.model,
                               error=f"HTTP {e.code}: {error_body[:200]}")
        except Exception as e:
            return LLMResponse(content="", model=self.model, error=str(e))


# 常用模型预设配置
MODEL_PRESETS = {
    "openai-gpt4o": {
        "adapter": "openai",
        "model": "gpt-4o",
        "base_url": "https://api.openai.com/v1"
    },
    "openai-gpt4o-mini": {
        "adapter": "openai",
        "model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1"
    },
    "qwen-turbo": {
        "adapter": "openai",
        "model": "qwen-turbo",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
    },
    "qwen-plus": {
        "adapter": "openai",
        "model": "qwen-plus",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
    },
    "glm-4": {
        "adapter": "openai",
        "model": "glm-4",
        "base_url": "https://open.bigmodel.cn/api/paas/v4"
    },
    "ollama-llama3": {
        "adapter": "openai",
        "model": "llama3",
        "base_url": "http://localhost:11434/v1"
    },
    "doubao-pro": {
        "adapter": "doubao",
        "model": "doubao-pro-32k",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3"
    },
    "doubao-lite": {
        "adapter": "doubao",
        "model": "doubao-lite-32k",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3"
    }
}
