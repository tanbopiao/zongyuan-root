# -*- coding: utf-8 -*-
"""llama.cpp 事实抽取适配器：把回答提纯为可存档的客观事实。"""
from .base import BaseExtractorAdapter, chat_or_raw

EXTRACT_SYSTEM = """你是事实提纯器。
你只提取客观、固定、可存档的事实，剔除修辞、描写、主观推断。
输出纯事实条目，不要解释。
如果内容无有效事实，直接输出：[NO_STORE]"""

EXTRACT_USER_TPL = "原文：{raw_text}\n事实："

# 原始续写回退模板（GGUF 无 chat_template 时才用）
EXTRACT_PROMPT = EXTRACT_SYSTEM + """
原文：{raw_text}
事实："""


class LlamaCppExtractor(BaseExtractorAdapter):
    def __init__(self, llm):
        self.llm = llm

    def extract_fact(self, raw_text: str) -> str:
        if not (raw_text or "").strip():
            return "[NO_STORE]"
        stop = ["[NO_STORE]\n", "###", "</s>"]
        messages = [{"role": "system", "content": EXTRACT_SYSTEM},
                    {"role": "user",
                     "content": EXTRACT_USER_TPL.format(raw_text=raw_text)}]
        text = chat_or_raw(self.llm, messages,
                           EXTRACT_PROMPT.format(raw_text=raw_text),
                           max_tokens=64, temperature=0.1, stop=stop)
        if "[NO_STORE]" in text.split("\n")[0]:
            return "[NO_STORE]"
        return "[NO_STORE]" if not text else text
