"""豆包Embedding函数 - 兼容ChromaDB EmbeddingFunction接口"""
import os, json, urllib.request
from typing import List

DOUBAO_API_KEY = os.environ.get("DOUBAO_API_KEY", "")
DOUBAO_EMBEDDING_MODEL = os.environ.get("DOUBAO_EMBEDDING_MODEL", "doubao-embedding-text-240515")
DOUBAO_EMBEDDING_URL = "https://ark.cn-beijing.volces.com/api/v3/embeddings"

class DoubaoEmbeddingFunction:
    """ChromaDB兼容的豆包Embedding函数"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or DOUBAO_API_KEY
        self.model = model or DOUBAO_EMBEDDING_MODEL
        self.dimension = 2560  # 豆包embedding维度
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        if not self.api_key:
            # 降级为hash嵌入
            return self._hash_fallback(input)
        try:
            payload = json.dumps({"model": self.model, "input": input}).encode()
            req = urllib.request.Request(
                DOUBAO_EMBEDDING_URL,
                data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                return [item["embedding"] for item in result["data"]]
        except Exception as e:
            print(f"豆包Embedding失败，降级hash: {e}")
            return self._hash_fallback(input)
    
    def _hash_fallback(self, input: List[str]) -> List[List[float]]:
        """hash降级嵌入（256维）"""
        import hashlib
        result = []
        for text in input:
            vec = [0.0] * 256
            h = hashlib.md5(text.encode()).hexdigest()
            for i, c in enumerate(h):
                vec[i % 256] += int(c, 16) / 16.0
            norm = sum(v*v for v in vec) ** 0.5 or 1
            result.append([v/norm for v in vec])
        return result

# 单例
_default_ef = None
def get_embedding_function():
    global _default_ef
    if _default_ef is None:
        _default_ef = DoubaoEmbeddingFunction()
    return _default_ef
