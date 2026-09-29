#!/usr/bin/env python3
"""
Ω-Brainμ 向量存储 V2 - 本地高精度版
TF-IDF加权hash embedding + 混合检索（语义+关键词+分类）
零外部依赖，2核2GB可运行
"""
import json, os, hashlib, math, re
from collections import Counter
from typing import List, Dict

class VectorStoreV2:
    def __init__(self, truth_index_path="/opt/ZONGYUAN-ROOT/Ω-Brainμ/truth_index.json", dim=256):
        self.dim = dim
        self.docs = []  # [{id, text, vec, category, keywords}]
        self.idf = {}   # 逆文档频率
        self._load_truths(truth_index_path)
        self._build_idf()
    
    def _tokenize(self, text):
        """中英文混合分词"""
        # 英文按空格+标点分词
        text = text.lower()
        en_words = re.findall(r'[a-z0-9]+', text)
        # 中文按2-gram分词
        cn_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        cn_grams = []
        for seg in cn_chars:
            for i in range(len(seg)-1):
                cn_grams.append(seg[i:i+2])
        return en_words + cn_grams
    
    def _hash_embed(self, text, tf_weights=None):
        """TF-IDF加权hash embedding"""
        vec = [0.0] * self.dim
        tokens = self._tokenize(text)
        if not tokens: return vec
        tf = Counter(tokens)
        max_tf = max(tf.values())
        for token, count in tf.items():
            h = hashlib.md5(token.encode()).hexdigest()
            idx = int(h[:8], 16) % self.dim
            # TF-IDF加权
            tf_val = 0.5 + 0.5 * count / max_tf
            idf_val = self.idf.get(token, 1.0)
            weight = tf_val * idf_val
            # 符号散列（正负交替）
            sign = 1 if int(h[8:9], 16) % 2 == 0 else -1
            vec[idx] += sign * weight
        # L2归一化
        norm = math.sqrt(sum(v*v for v in vec)) or 1.0
        return [v/norm for v in vec]
    
    def _build_idf(self):
        """构建逆文档频率"""
        N = len(self.docs) or 1
        df = Counter()
        for doc in self.docs:
            tokens = set(self._tokenize(doc["text"]))
            for t in tokens:
                df[t] += 1
        self.idf = {t: math.log((N + 1) / (count + 1)) + 1 for t, count in df.items()}
    
    def _load_truths(self, path):
        """加载真值索引"""
        if not os.path.exists(path): return
        with open(path) as f:
            data = json.load(f)
        for t in data.get("truths", []):
            text = t.get("content", "") or t.get("id", "")
            # 对于只有id和sha的快照类型，用id作为文本
            if not text or len(text) < 5:
                text = t.get("id", "")
            self.docs.append({
                "id": t.get("id", ""),
                "text": text,
                "category": t.get("category", t.get("type", "unknown")),
                "type": t.get("type", "unknown"),
                "vec": None  # 延迟计算
            })
        # 预计算所有向量
        for doc in self.docs:
            doc["vec"] = self._hash_embed(doc["text"])
    
    def _cosine(self, a, b):
        return sum(x*y for x, y in zip(a, b))
    
    def _keyword_score(self, query, doc_text):
        """关键词匹配得分"""
        q_tokens = set(self._tokenize(query))
        d_tokens = set(self._tokenize(doc_text))
        if not q_tokens: return 0.0
        overlap = len(q_tokens & d_tokens)
        return overlap / len(q_tokens)
    
    def recall(self, query, top_k=8, category_filter=None):
        """混合检索：语义相似度(0.6) + 关键词匹配(0.4)"""
        q_vec = self._hash_embed(query)
        q_tokens = set(self._tokenize(query))
        
        scored = []
        for doc in self.docs:
            if category_filter and doc["category"] != category_filter:
                continue
            sem_score = self._cosine(q_vec, doc["vec"])
            kw_score = self._keyword_score(query, doc["text"])
            # 混合得分
            hybrid = 0.6 * sem_score + 0.4 * kw_score
            scored.append((hybrid, sem_score, kw_score, doc))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for hybrid, sem, kw, doc in scored[:top_k]:
            results.append({
                "id": doc["id"],
                "category": doc["category"],
                "type": doc["type"],
                "preview": doc["text"][:150],
                "hybrid_score": round(hybrid, 4),
                "semantic_score": round(sem, 4),
                "keyword_score": round(kw, 4)
            })
        return results
    
    def get_stats(self):
        return {
            "total_docs": len(self.docs),
            "dim": self.dim,
            "categories": list(set(d["category"] for d in self.docs)),
            "engine": "tfidf_hash_hybrid_v2"
        }

if __name__ == "__main__":
    vs = VectorStoreV2()
    print(f"向量库V2初始化: {vs.get_stats()}")
    print("\n召回测试:")
    for q in ["自治内核 架构", "axiom 元法则", "GPT model evolution", "漂移检测 自愈"]:
        r = vs.recall(q, top_k=3)
        print(f"  查询'{q}': top1={r[0]['hybrid_score'] if r else 'N/A'} ({r[0]['category'] if r else ''})")
