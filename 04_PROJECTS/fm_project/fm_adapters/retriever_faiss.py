# -*- coding: utf-8 -*-
"""FAISS Flat（L2）检索适配器。

修正原设计稿缺陷：原 save() 只写 FAISS 索引、不写文本库，重启后 load() 出
文本与向量错位（text_store 为空 → 检索结果全部被丢弃）。此处将文本库与索引
同盘落盘（path + ".texts.json"），保证 save/load 往返一致。
"""
import json
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np

from .base import BaseRetrieverAdapter


class FaissFlatRetriever(BaseRetrieverAdapter):
    def __init__(self, dim: int = 384):
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)
        self.text_store: List[str] = []

    def add(self, text: str, vec: List[float]):
        arr = np.expand_dims(np.array(vec, dtype=np.float32), axis=0)
        if arr.shape[1] != self.dim:
            raise ValueError(f"向量维度 {arr.shape[1]} 与索引维度 {self.dim} 不符")
        self.index.add(arr)
        self.text_store.append(text)

    def search(self, query_vec: List[float], topk: int) -> List[Tuple[str, float]]:
        if self.index.ntotal == 0:
            return []
        arr = np.expand_dims(np.array(query_vec, dtype=np.float32), axis=0)
        k = min(int(topk), self.index.ntotal)
        D, I = self.index.search(arr, k)
        res = []
        for idx, dist in zip(I[0], D[0]):
            if 0 <= idx < len(self.text_store):
                res.append((self.text_store[idx], float(dist)))
        return res

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, path)
        Path(str(path) + ".texts.json").write_text(
            json.dumps(self.text_store, ensure_ascii=False), encoding="utf-8")

    def load(self, path: str):
        if not Path(path).exists():
            return False
        index = faiss.read_index(path)
        if index.d != self.dim:
            raise ValueError(
                f"索引维度 {index.d} 与当前模型维度 {self.dim} 不符（模型已更换，需重建）")
        self.index = index
        side = Path(str(path) + ".texts.json")
        self.text_store = json.loads(side.read_text(encoding="utf-8")) if side.exists() else []
        # 文本库与索引必须同长，否则视为损坏并拒绝使用（避免静默错位）
        if len(self.text_store) != self.index.ntotal:
            raise ValueError(
                f"检索索引与文本库不一致: index={self.index.ntotal} texts={len(self.text_store)}")
        return True

    @property
    def size(self) -> int:
        return int(self.index.ntotal)
