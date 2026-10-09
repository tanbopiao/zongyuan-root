#!/usr/bin/env python3
"""Ω-Brainμ Embedding服务 - 豆包API 2560维 + hash降级128维"""
import hashlib, json, os, urllib.request

def _load_env():
    env = {}
    try:
        with open("/opt/ZONGYUAN-ROOT/.env") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except: pass
    return env

class EmbeddingService:
    def __init__(self):
        env = _load_env()
        self.api_key = env.get("DOUBAO_API_KEY", "")
        self.dimension = 2560 if self.api_key else 128
        self.mode = "doubao_api" if self.api_key else "hash_fallback"
    
    def embed(self, text):
        if self.mode == "doubao_api":
            return self._doubao_embed(text)
        return self._hash_embed(text)
    
    def _hash_embed(self, text, dim=128):
        vec = [0.0] * dim
        for i, ch in enumerate(text):
            h = hashlib.md5(f"{i}_{ch}".encode()).hexdigest()
            vec[int(h[:8], 16) % dim] += 1.0
        norm = sum(v*v for v in vec) ** 0.5 or 1
        return [v/norm for v in vec]
    
    def _doubao_embed(self, text):
        try:
            url = "https://ark.cn-beijing.volces.com/api/v3/embeddings"
            data = json.dumps({"model": "doubao-embedding-text-240715", "input": text}).encode()
            req = urllib.request.Request(url, data=data, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            })
            resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
            return resp["data"][0]["embedding"]
        except Exception as e:
            return self._hash_embed(text)
    
    def get_status(self):
        return {"mode": self.mode, "dimension": self.dimension, "api_configured": bool(self.api_key)}

embedding_service = EmbeddingService()

if __name__ == "__main__":
    s = embedding_service.get_status()
    print(f"Embedding: {s['mode']}, dim={s['dimension']}, api={s['api_configured']}")
    v = embedding_service.embed("test")
    print(f"Vector: {len(v)} dims")
