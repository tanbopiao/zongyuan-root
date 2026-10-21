# -*- coding: utf-8 -*-
"""llama.cpp 生成适配器：只依据给定种子真值/共识记忆作答，禁止编造。"""
from .base import BaseLLMGenAdapter, chat_or_raw

GEN_SYSTEM = """你是基于可信真值工作的智能助手。
你必须严格依据给定的【种子真值/共识记忆】回答，禁止编造、禁止脑补、禁止新增设定。
回答简洁、稳定、忠于事实。"""

GEN_USER_TPL = """【可信真值上下文】：{context}
用户问题：{question}"""

# 原始续写回退模板（GGUF 无 chat_template 时才用）
GEN_PROMPT_TPL = GEN_SYSTEM + """
【可信真值上下文】：{context}
用户问题：{question}
回答："""


class LlamaCppGenAdapter(BaseLLMGenAdapter):
    def __init__(self, llm):
        self.llm = llm
        self.tpl = GEN_PROMPT_TPL

    def generate(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """原始续写（基类契约；无模板模型的回退路径）。"""
        out = self.llm(prompt, max_tokens=max_tokens, temperature=temperature)
        return out["choices"][0]["text"].strip()

    def answer(self, context: str, question: str, max_tokens: int,
               temperature: float) -> str:
        """带约束的对话式作答（推荐路径：自动套用 GGUF 对话模板）。"""
        messages = [{"role": "system", "content": GEN_SYSTEM},
                    {"role": "user",
                     "content": GEN_USER_TPL.format(context=context, question=question)}]
        return chat_or_raw(self.llm, messages, self.build_prompt(context, question),
                           max_tokens, temperature)

    def build_prompt(self, context: str, question: str):
        return self.tpl.format(context=context, question=question)
