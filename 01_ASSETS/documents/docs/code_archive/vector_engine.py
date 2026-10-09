#!/usr/bin/env python3
"""
9120语义向量检索引擎（稀疏优化版）
纯Python实现，零外部API依赖，内存占用<100MB
支持中文分词+TF-IDF稀疏向量+余弦相似度检索
"""
import os
import re
import math
import pickle
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime

try:
    import jieba
    jieba.setLogLevel(40)
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
INDEX_PATH = "/opt/ZONGYUAN-ROOT/engine/semantic_search/index.pkl"
LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/semantic_search.log"

MAX_VOCAB_SIZE = 8000

def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write("[{}] {}\n".format(datetime.now().isoformat(), msg))

STOP_WORDS = set("""的 了 在 是 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 自己 这 那 这个 那个 他 她 它 们 么 什么 怎么 这样 那样 因为 所以 如果 但是 然后 可以 已经 还是 或者 与 及 等 之 其 此 该 各 每 某 另 更 最 太 真 正 新 旧 大 小 多 少 高 低 长 短 先 后 前 后 里 外 中 内 间 旁 边 面 头 尾 始 终 初 末 本 末 源 流 根 枝 干 叶 花 果 种 子 实 虚 真 假 对 错 是 非 善 恶 美 丑 好 坏 优 劣 强 弱 快 慢 轻 重 深 浅 浓 淡 厚 薄 宽 窄 远 近 亲 疏 冷 热 温 凉 明 暗 亮 昏 清 浊 净 污 整 乱 齐 散 聚 分 合 开 关 起 落 升 降 进 退 来 去 出 入 上 下 左 右 东 西 南 北""".split())

def tokenize(text):
    if not text:
        return []
    english_words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', text)
    chinese = re.findall(r'[\u4e00-\u9fff]+', text)
    tokens = []
    for w in english_words:
        w_lower = w.lower()
        if len(w_lower) > 1 and w_lower not in STOP_WORDS:
            tokens.append(w_lower)
    for seg in chinese:
        if HAS_JIEBA:
            words = jieba.lcut(seg)
        else:
            words = [seg[i:i+2] for i in range(len(seg)-1)]
        for w in words:
            w = w.strip()
            if len(w) > 1 and w not in STOP_WORDS:
                tokens.append(w)
    return tokens

class SparseVectorSearchEngine:
    def __init__(self):
        self.documents = {}
        self.vocabulary = {}
        self.idf = {}
        self.doc_sparse_vectors = {}
        self.built = False

    def add_document(self, key, text, category="", node_id=""):
        tokens = tokenize(text)
        tf = Counter(tokens)
        self.documents[key] = {
            "text": text[:500],
            "category": category,
            "node_id": node_id,
            "tf": dict(tf),
            "token_count": len(tokens)
        }

    def build_index(self):
        log("开始构建稀疏索引...")
        total_docs = len(self.documents)
        if total_docs == 0:
            log("无文档可索引")
            return
        term_doc_count = defaultdict(int)
        for key, doc in self.documents.items():
            for term in doc["tf"]:
                term_doc_count[term] += 1
        sorted_terms = sorted(term_doc_count.items(), key=lambda x: x[1], reverse=True)
        selected_terms = [t for t, c in sorted_terms if c >= 2][:MAX_VOCAB_SIZE]
        self.vocabulary = {term: idx for idx, term in enumerate(selected_terms)}
        log("词汇表大小: {} (从{}个候选中筛选)".format(len(self.vocabulary), len(term_doc_count)))
        for term in selected_terms:
            df = term_doc_count[term]
            self.idf[term] = math.log((total_docs + 1) / (df + 1)) + 1
        for key, doc in self.documents.items():
            sparse_vec = {}
            total_tokens = doc["token_count"]
            if total_tokens == 0:
                continue
            norm_sq = 0
            for term, count in doc["tf"].items():
                if term in self.vocabulary:
                    term_idx = self.vocabulary[term]
                    tf_score = count / total_tokens
                    tfidf = tf_score * self.idf[term]
                    sparse_vec[term_idx] = tfidf
                    norm_sq += tfidf * tfidf
            if norm_sq > 0:
                norm = math.sqrt(norm_sq)
                for idx in sparse_vec:
                    sparse_vec[idx] /= norm
            self.doc_sparse_vectors[key] = sparse_vec
        self.built = True
        log("稀疏索引构建完成: {}个文档, {}个词".format(total_docs, len(self.vocabulary)))

    def search(self, query, top_k=10, category_filter=None):
        if not self.built:
            return []
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        query_tf = Counter(query_tokens)
        query_sparse = {}
        total = len(query_tokens)
        norm_sq = 0
        for term, count in query_tf.items():
            if term in self.vocabulary:
                term_idx = self.vocabulary[term]
                tfidf = (count / total) * self.idf[term]
                query_sparse[term_idx] = tfidf
                norm_sq += tfidf * tfidf
        if norm_sq > 0:
            norm = math.sqrt(norm_sq)
            for idx in query_sparse:
                query_sparse[idx] /= norm
        scores = defaultdict(float)
        for term_idx, query_val in query_sparse.items():
            for key, doc_vec in self.doc_sparse_vectors.items():
                if term_idx in doc_vec:
                    scores[key] += query_val * doc_vec[term_idx]
        results = []
        for key, similarity in scores.items():
            if similarity > 0.01:
                if category_filter and self.documents[key].get("category") != category_filter:
                    continue
                results.append({
                    "key": key,
                    "similarity": round(similarity, 4),
                    "text": self.documents[key]["text"][:200],
                    "category": self.documents[key].get("category", ""),
                    "node_id": self.documents[key].get("node_id", "")
                })
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def save(self, path=INDEX_PATH):
        save_data = {
            "documents": {k: {"text": v["text"], "category": v["category"],
                              "node_id": v["node_id"], "tf": v["tf"],
                              "token_count": v["token_count"]}
                          for k, v in self.documents.items()},
            "vocabulary": self.vocabulary,
            "idf": self.idf,
            "doc_sparse_vectors": self.doc_sparse_vectors,
            "built": self.built
        }
        with open(path, "wb") as f:
            pickle.dump(save_data, f)
        log("索引已保存: {}".format(path))

    def load(self, path=INDEX_PATH):
        if os.path.exists(path):
            with open(path, "rb") as f:
                data = pickle.load(f)
            self.documents = data["documents"]
            self.vocabulary = data["vocabulary"]
            self.idf = data["idf"]
            self.doc_sparse_vectors = data["doc_sparse_vectors"]
            self.built = data["built"]
            log("索引已加载: {}个文档".format(len(self.documents)))
            return True
        return False

def build_index_from_db(engine):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT truth_key, truth_value, category, node_id FROM truths ORDER BY updated_at DESC")
    rows = c.fetchall()
    conn.close()
    for key, value, category, node_id in rows:
        text = "{} {}".format(key, value)
        engine.add_document(key, text, category, node_id)
    engine.build_index()
    engine.save()
    return len(rows)

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = SparseVectorSearchEngine()
        if not _engine.load():
            build_index_from_db(_engine)
    return _engine
