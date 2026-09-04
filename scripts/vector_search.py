#!/usr/bin/env python3
"""
动作4: 轻量语义向量检索模块（零依赖降级方案）
Chroma不可用时的纯Python实现：hash embedding + 余弦相似度
配置豆包Embedding API后可无缝升级为真实向量检索
"""
import json
import hashlib
import math
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
VECTOR_CACHE = ROOT / "cache" / "vector_cache"
VECTOR_CACHE.mkdir(parents=True, exist_ok=True)

# 向量维度（降级方案用256维确定性hash embedding）
VECTOR_DIM = 256

class LightVectorStore:
    """轻量向量存储（内存+JSON持久化）"""
    def __init__(self, collection_name: str = "truth_base"):
        self.collection_name = collection_name
        self.store_file = VECTOR_CACHE / f"{collection_name}.json"
        self.vectors = {}  # id -> {text, vector, metadata}
        self._load()

    def _hash_embedding(self, text: str) -> List[float]:
        """
        确定性hash embedding（降级方案）
        将文本映射为256维向量，保证相同文本向量一致
        """
        vec = [0.0] * VECTOR_DIM
        # 用多个hash函数填充向量
        tokens = text.lower().split()
        for token in tokens:
            for i in range(4):  # 4个hash函数
                h = hashlib.md5(f"{token}_{i}".encode()).hexdigest()
                idx = int(h[:8], 16) % VECTOR_DIM
                sign = 1 if int(h[8:9], 16) % 2 == 0 else -1
                vec[idx] += sign * (1.0 / math.sqrt(len(tokens) + 1))
        # L2归一化
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """余弦相似度"""
        dot = sum(a * b for a, b in zip(v1, v2))
        return dot  # 已归一化，点积即余弦相似度

    def _load(self):
        if self.store_file.exists():
            with open(self.store_file) as f:
                data = json.load(f)
                self.vectors = data.get("vectors", {})

    def _save(self):
        with open(self.store_file, "w") as f:
            json.dump({"collection": self.collection_name, "vectors": self.vectors}, f, ensure_ascii=False)

    def add(self, doc_id: str, text: str, metadata: Dict[str, Any] = None):
        """添加文档到向量库"""
        vec = self._hash_embedding(text)
        self.vectors[doc_id] = {
            "text": text,
            "vector": vec,
            "metadata": metadata or {}
        }
        self._save()

    def add_batch(self, docs: List[Dict[str, Any]]):
        """批量添加"""
        for doc in docs:
            self.add(doc["id"], doc["text"], doc.get("metadata"))

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """语义检索"""
        query_vec = self._hash_embedding(query)
        results = []
        for doc_id, doc in self.vectors.items():
            sim = self._cosine_similarity(query_vec, doc["vector"])
            results.append({
                "id": doc_id,
                "text": doc["text"],
                "similarity": round(sim, 4),
                "metadata": doc["metadata"]
            })
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def count(self) -> int:
        return len(self.vectors)

def build_truth_base_vector_store():
    """从真值基座构建向量索引"""
    store = LightVectorStore("truth_base")
    truth_dir = ROOT / "truth_base"
    count = 0
    if truth_dir.exists():
        for fp in truth_dir.glob("*.json"):
            with open(fp) as f:
                data = json.load(f)
            # 索引真值公式
            formulas = data.get("formulas", []) + data.get("truth_formulas", [])
            for i, formula in enumerate(formulas):
                if isinstance(formula, dict):
                    text = formula.get("name", "") + " " + formula.get("expression", "") + " " + formula.get("description", "")
                    fid = f"{fp.stem}_formula_{i}"
                else:
                    text = str(formula)
                    fid = f"{fp.stem}_formula_{i}"
                store.add(fid, text, {"source": fp.name, "type": "truth_formula"})
                count += 1
            # 索引公理
            axioms = data.get("axioms", []) + data.get("planning_axioms", [])
            for i, axiom in enumerate(axioms):
                if isinstance(axiom, dict):
                    text = axiom.get("name", "") + " " + axiom.get("content", "")
                else:
                    text = str(axiom)
                store.add(f"{fp.stem}_axiom_{i}", text, {"source": fp.name, "type": "axiom"})
                count += 1
    return store, count

def demo():
    """演示：构建真值向量库并检索"""
    print("构建真值基座向量索引...")
    store, count = build_truth_base_vector_store()
    print(f"已索引 {count} 条真值/公理")

    print("\n语义检索测试: '自治内核 真值校验'")
    results = store.search("自治内核 真值校验", top_k=3)
    for r in results:
        print(f"  [{r['similarity']:.4f}] {r['id']}: {r['text'][:60]}...")

if __name__ == "__main__":
    demo()
