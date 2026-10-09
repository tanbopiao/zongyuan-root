#!/usr/bin/env python3
"""
Ω-Brainμ 本地轻量语义召回引擎（修复版）
TF-IDF + 五维语义路由 + 标签匹配
"""
import json, math, os, re
from pathlib import Path
from collections import Counter
from datetime import datetime

ROOT = Path("/opt/ZONGYUAN-ROOT")
TRUTH_INDEX = ROOT / "Ω-Brainμ" / "truth_index.json"

class LocalSemanticRecall:
    def __init__(self):
        self.truths = self._load_truths()
        self.idf = self._build_idf()
        self.five_dim_router = self._build_five_dim_router()
        
    def _load_truths(self):
        truths = []
        if TRUTH_INDEX.exists():
            idx = json.loads(TRUTH_INDEX.read_text(encoding="utf-8"))
            for t in idx.get("truths", []):
                direct_text = t.get("content", t.get("text", ""))
                text = direct_text if len(direct_text) > 10 else self._extract_text(t["id"])
                truths.append({
                    "id": t["id"],
                    "type": t.get("type", "unknown"),
                    "priority": t.get("priority", 99),
                    "sha256": t.get("sha256", ""),
                    "text": text
                })
        return truths
    
    def _find_file(self, truth_id):
        """模糊匹配真值文件"""
        raw = truth_id.replace("TRUTH-", "")
        # 直接匹配
        for d in ["autonomous_kernel_protocol", "truth_architecture"]:
            p = ROOT / d / (raw + ".json")
            if p.exists():
                return p
        # 模糊匹配（包含关系）
        for d in ["autonomous_kernel_protocol", "truth_architecture"]:
            dirpath = ROOT / d
            if dirpath.exists():
                for f in dirpath.glob("*.json"):
                    if raw in f.stem or f.stem in raw:
                        return f
        return None
    
    def _extract_text(self, truth_id):
        """从真值文件提取可搜索文本"""
        path = self._find_file(truth_id)
        if not path:
            return truth_id.replace("TRUTH-", "").replace("-", " ")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            texts = []
            # 递归提取所有字符串值
            def extract_strings(obj, depth=0):
                if depth > 5:
                    return
                if isinstance(obj, str):
                    if len(obj) > 2 and len(obj) < 500:
                        texts.append(obj)
                elif isinstance(obj, dict):
                    for k, v in obj.items():
                        if k not in ("self_sha256", "sha256", "merkle_root"):
                            extract_strings(v, depth+1)
                elif isinstance(obj, list):
                    for item in obj[:10]:
                        extract_strings(item, depth+1)
            extract_strings(data)
            return " ".join(texts) if texts else path.stem
        except:
            return path.stem
    
    def _build_idf(self):
        N = max(len(self.truths), 1)
        df = Counter()
        for t in self.truths:
            words = set(self._tokenize(t.get("text", t.get("content", ""))))
            for w in words:
                df[w] += 1
        idf = {}
        for w, count in df.items():
            idf[w] = math.log((N + 1) / (count + 1)) + 1
        return idf
    
    def _tokenize(self, text):
        text = text.lower()
        en_words = re.findall(r'[a-z]{2,}', text)
        cn_chars = re.findall(r'[\u4e00-\u9fff]', text)
        cn_bigrams = [''.join(cn_chars[i:i+2]) for i in range(len(cn_chars)-1)]
        return en_words + cn_bigrams + cn_chars
    
    def _tfidf_vector(self, text):
        words = self._tokenize(text)
        if not words:
            return {}
        tf = Counter(words)
        vec = {}
        for w, count in tf.items():
            if w in self.idf:
                vec[w] = (count / len(words)) * self.idf[w]
        return vec
    
    def _cosine_sim(self, v1, v2):
        common = set(v1.keys()) & set(v2.keys())
        dot = sum(v1[w] * v2[w] for w in common)
        norm1 = math.sqrt(sum(v*v for v in v1.values()))
        norm2 = math.sqrt(sum(v*v for v in v2.values()))
        if norm1 == 0 or norm2 == 0:
            return 0
        return dot / (norm1 * norm2)
    
    def _build_five_dim_router(self):
        return {
            "元极恒一": ["锚点", "本源", "元极", "恒一", "唯一", "did", "主权", "根"],
            "三态收敛": ["三态", "逻辑态", "信息态", "能量态", "收敛", "秩序", "闭包"],
            "符号涌现": ["涌现", "符号", "自组织", "认知", "进化", "内生"],
            "宇宙规律": ["宇宙", "物理", "数学", "自然", "客观", "规律", "密度"],
            "哈希确权": ["哈希", "merkle", "efuse", "锁档", "确权", "不可变", "blown"],
        }
    
    def _route_to_dimension(self, query):
        query_lower = query.lower()
        scores = {}
        for dim, keywords in self.five_dim_router.items():
            scores[dim] = sum(1 for kw in keywords if kw in query_lower)
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else None
    
    def recall(self, query, top_k=8, min_score=0.01):
        query_vec = self._tfidf_vector(query)
        target_dim = self._route_to_dimension(query)
        scored = []
        for t in self.truths:
            truth_vec = self._tfidf_vector(t.get("text", t.get("content", "")))
            sim = self._cosine_sim(query_vec, truth_vec)
            dim_boost = 1.3 if target_dim and target_dim in t.get("text", t.get("content", "")) else 1.0
            priority_weight = 1.0 + max(0, (2 - t["priority"])) * 0.15
            final_score = sim * dim_boost * priority_weight
            if final_score >= min_score:
                scored.append({
                    "id": t["id"],
                    "type": t["type"],
                    "priority": t["priority"],
                    "score": round(final_score, 4),
                    "tfidf_sim": round(sim, 4),
                    "dimension": target_dim,
                    "preview": t.get("text", t.get("content", ""))[:60]
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return {
            "query": query,
            "routed_dimension": target_dim,
            "total_truths": len(self.truths),
            "matched": len(scored),
            "results": scored[:top_k],
            "engine": "local_tfidf_five_dim_router_v2",
            "recall_time": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import sys
    engine = LocalSemanticRecall()
    query = sys.argv[1] if len(sys.argv) > 1 else "三态收敛"
    result = engine.recall(query)
    print(json.dumps(result, indent=2, ensure_ascii=False))
