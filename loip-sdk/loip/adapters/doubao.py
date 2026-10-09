"""
豆包（Doubao）API适配器
支持火山引擎方舟平台的豆包大模型调用。
文档参考：https://www.volcengine.com/docs/82379
"""
import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from .base import BaseLLMAdapter, LLMResponse


class DoubaoAdapter(BaseLLMAdapter):
    """豆包大模型适配器（火山引擎方舟）"""

    DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    def __init__(self, api_key: str, model: str = "doubao-pro-32k",
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
        # 透传额外参数
        for key in ["top_p", "frequency_penalty", "presence_penalty", "stop"]:
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
