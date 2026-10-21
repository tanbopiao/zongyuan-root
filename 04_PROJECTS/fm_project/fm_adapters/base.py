# -*- coding: utf-8 -*-
"""适配器抽象基类：四类能力（嵌入 / 检索 / 事实抽取 / 生成）的统一接口。"""
from abc import ABC, abstractmethod
from typing import List


def chat_or_raw(llm, messages, fallback_prompt: str, max_tokens: int,
                temperature: float, stop=None):
    """统一推理入口：GGUF 带对话模板 → 走 chat 路径；否则退回原始续写。

    实测差异是决定性的：MiniMind2 未套模板会输出「或或或/聚聚聚」式重复乱码，
    套模板后为连贯中文。模板取自 GGUF 的 tokenizer.chat_template 元数据。
    """
    tpl = (getattr(llm, "metadata", None) or {}).get("tokenizer.chat_template")
    if tpl:
        kw = {"max_tokens": max_tokens, "temperature": temperature}
        if stop:
            kw["stop"] = stop
        out = llm.create_chat_completion(messages, **kw)
        return out["choices"][0]["message"]["content"].strip()
    kw = {"max_tokens": max_tokens, "temperature": temperature}
    if stop:
        kw["stop"] = stop
    out = llm(fallback_prompt, **kw)
    return out["choices"][0]["text"].strip()


class BaseEmbeddingAdapter(ABC):
    @abstractmethod
    def encode(self, text: str) -> List[float]:
        ...


class BaseRetrieverAdapter(ABC):
    @abstractmethod
    def add(self, text: str, vec: List[float]):
        ...

    @abstractmethod
    def search(self, query_vec: List[float], topk: int):
        ...

    @abstractmethod
    def save(self, path: str):
        ...

    @abstractmethod
    def load(self, path: str):
        ...


class BaseExtractorAdapter(ABC):
    @abstractmethod
    def extract_fact(self, raw_text: str) -> str:
        """返回事实字符串，无事实返回 [NO_STORE]"""
        ...


class BaseLLMGenAdapter(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int, temperature: float) -> str:
        ...
