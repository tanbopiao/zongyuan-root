#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 语义向量引擎 v1.0
基于 TF-IDF + TruncatedSVD 的轻量语义嵌入
Phase 2: 真实向量计算，替换启发式漂移估算
Omega: Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""

import json
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
SAMPLES_PATH = os.path.join(WORKSPACE, "CALIBRATION-SAMPLES.json")
VECTORS_PATH = os.path.join(WORKSPACE, "ANCHOR-VECTORS.json")
MODEL_PATH = os.path.join(WORKSPACE, "semantic_model.json")


class SemanticVectorEngine:
    """轻量语义向量引擎：TF-IDF + SVD 降维"""

    def __init__(self, n_components=64):
        self.n_components = n_components
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),
            analyzer='char_wb',  # 字符级n-gram，适合中文无分词
            stop_words=None,
        )
        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        self.is_fitted = False
        self.baseline_vectors = None
        self.baseline_texts = None
        self.baseline_ids = None

    def fit(self, corpus_texts, corpus_ids=None):
        """用基准语料拟合TF-IDF + SVD模型"""
        tfidf_matrix = self.vectorizer.fit_transform(corpus_texts)
        self.svd.fit(tfidf_matrix)
        self.is_fitted = True
        print(f"模型拟合完成：TF-IDF特征数={len(self.vectorizer.vocabulary_)}, SVD维度={self.n_components}")

    def transform(self, texts):
        """将文本转换为SVD降维向量"""
        if not self.is_fitted:
            raise RuntimeError("模型未拟合，请先调用fit()")
        tfidf_matrix = self.vectorizer.transform(texts)
        svd_vectors = self.svd.transform(tfidf_matrix)
        return svd_vectors

    def set_baseline(self, texts, ids=None):
        """设置基准锚定向量集（流形中心区域）"""
        self.baseline_texts = texts
        self.baseline_ids = ids or [f"S{i:03d}" for i in range(len(texts))]
        self.baseline_vectors = self.transform(texts)
        print(f"基准锚定向量集已设置：{len(texts)}条")

    def compute_drift_score(self, query_texts):
        """
        计算当前文本相对基准锚点集的漂移分。
        基于余弦相似度的归一化漂移分。
        返回值范围：0~1，0=完美在中心，1=完全偏离
        """
        if self.baseline_vectors is None:
            raise RuntimeError("基准锚点未设置")
        if not query_texts:
            return 0.0

        query_vectors = self.transform(query_texts)
        # 计算查询向量与每个基准向量的余弦相似度
        similarities = cosine_similarity(query_vectors, self.baseline_vectors)
        # 取最大相似度（找最接近的基准锚点）
        max_similarity = np.max(similarities)
        # 漂移分 = 1 - max_similarity
        # 余弦相似度范围[0,1]（TF-IDF非负），所以漂移分天然在[0,1]
        drift_score = float(1.0 - max_similarity)
        drift_score = max(0.0, min(1.0, drift_score))
        return round(drift_score, 4)

    def save(self, path=MODEL_PATH):
        """保存模型参数（TF-IDF词汇表+SVD分量）"""
        # 转换numpy类型为Python原生类型
        vocab = {k: int(v) for k, v in self.vectorizer.vocabulary_.items()}
        model_data = {
            "n_components": self.n_components,
            "vocabulary": vocab,
            "svd_components": self.svd.components_.tolist(),
            "svd_mean": self.svd.mean_.tolist() if hasattr(self.svd, 'mean_') and self.svd.mean_ is not None else None,
            "baseline_ids": self.baseline_ids,
            "baseline_texts": self.baseline_texts,
            "baseline_vectors": self.baseline_vectors.tolist()
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(model_data, f, ensure_ascii=False)
        print(f"模型已保存至 {path}")

    def load(self, path=MODEL_PATH):
        """加载模型参数"""
        if not os.path.exists(path):
            return False
        with open(path, 'r', encoding='utf-8') as f:
            model_data = json.load(f)
        self.n_components = model_data["n_components"]
        # 用保存的词汇表重建TF-IDF向量器
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(vocabulary=model_data["vocabulary"], analyzer='char_wb')
        # 标记为已拟合（用假数据拟合一次以设置内部状态）
        dummy_tfidf = self.vectorizer.fit_transform(["dummy text for fitting"])
        # SVD分量
        self.svd.components_ = np.array(model_data["svd_components"])
        if model_data["svd_mean"]:
            self.svd.mean_ = np.array(model_data["svd_mean"])
        self.baseline_ids = model_data["baseline_ids"]
        self.baseline_texts = model_data["baseline_texts"]
        self.baseline_vectors = np.array(model_data["baseline_vectors"])
        self.is_fitted = True
        print(f"模型已加载，基准向量数={len(self.baseline_ids)}")
        return True


def build_baseline():
    """从校准样本库构建基准锚定向量集"""
    # 加载校准样本
    with open(SAMPLES_PATH, 'r', encoding='utf-8') as f:
        samples = json.load(f)

    sample_texts = [s["text"] for s in samples["axiomatic_samples"]]
    sample_ids = [s["id"] for s in samples["axiomatic_samples"]]

    # 同时加载更多元公理文本扩充语料（从元法则目录读取）
    meta_law_dir = "/home/user/ZONGYUAN-ROOT/01_ASSETS/documents/docs/meta_laws/"
    corpus_texts = list(sample_texts)
    corpus_ids = list(sample_ids)

    # 读取部分元法则文件作为语料扩充
    if os.path.exists(meta_law_dir):
        for fname in sorted(os.listdir(meta_law_dir))[:50]:
            if fname.endswith('.md'):
                fpath = os.path.join(meta_law_dir, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read(2000)  # 只读前2000字符
                    # 提取前100字作为代表
                    corpus_texts.append(content[:500])
                    corpus_ids.append(fname.replace('.md', ''))
                except:
                    pass

    print(f"语料总数：{len(corpus_texts)}条")

    # 初始化并拟合模型
    engine = SemanticVectorEngine(n_components=64)
    engine.fit(corpus_texts)

    # 设置基准锚点（用校准样本作为流形中心）
    engine.set_baseline(sample_texts, sample_ids)

    # 保存模型
    engine.save()

    # 保存基准向量JSON
    anchor_data = {
        "anchor_count": len(sample_ids),
        "dimension": 64,
        "ids": sample_ids,
        "texts": sample_texts,
        "description": "流形中心锚定向量集 — 代表语义稳定区域"
    }
    with open(VECTORS_PATH, 'w', encoding='utf-8') as f:
        json.dump(anchor_data, f, ensure_ascii=False, indent=2)
    print(f"基准向量索引已保存至 {VECTORS_PATH}")

    return engine


def test_drift(engine):
    """测试漂移计算"""
    test_cases = [
        ("基准样本（应低漂移）", "元公理优先级高于所有业务规则、会话指令和Worker脚本。"),
        ("相关讨论（应中等漂移）", "大模型的安全边界需要工程体系来维护，不能只靠提示词"),
        ("无关话题（应高漂移）", "今天天气很好，适合出去散步喝咖啡看电影"),
        ("业务讨论（应中等漂移）", "这个季度的销售数据增长了15%，主要来自华东市场"),
    ]

    print("\n=== 漂移测试 ===")
    for name, text in test_cases:
        drift = engine.compute_drift_score([text])
        level = "🟢稳态" if drift < 0.15 else "🟡告警" if drift < 0.25 else "🟠橙色" if drift < 0.30 else "🔴红色"
        print(f"  {name}: 漂移分={drift:.4f} {level}")


if __name__ == "__main__":
    print("=" * 60)
    print("ZONGYUAN-ROOT 语义向量引擎 v1.0")
    print("TF-IDF + SVD 轻量嵌入")
    print("=" * 60)

    engine = build_baseline()
    test_drift(engine)
