# -*- coding: utf-8 -*-
"""FM-Core 标准适配器层：内核不感知 LLM/向量模型，模型可随时替换。"""
from .base import BaseEmbeddingAdapter, BaseRetrieverAdapter, BaseExtractorAdapter, BaseLLMGenAdapter
from .embedding_onnx import OnnxBgeAdapter
from .retriever_faiss import FaissFlatRetriever
from .extractor_llamacpp import LlamaCppExtractor
from .llm_gen_llamacpp import LlamaCppGenAdapter

__all__ = [
    "BaseEmbeddingAdapter",
    "BaseRetrieverAdapter",
    "BaseExtractorAdapter",
    "BaseLLMGenAdapter",
    "OnnxBgeAdapter",
    "FaissFlatRetriever",
    "LlamaCppExtractor",
    "LlamaCppGenAdapter",
]
