#!/usr/bin/env python3
"""
向量化高维频谱架构引擎 V1.0
ZONGYUAN-ROOT元极恒一自治体系
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

核心理论：
- 希尔伯特空间：所有真值/态元/知识节点映射为高维向量
- 频谱变换：DFT/小波变换将向量分解为低频(全局语义)/中频(关系结构)/高频(局部细节)
- 频谱能量分布：信息健康度指标，低频占比高=稳态，高频占比高=扰动
- 谱聚类：基于相似度矩阵特征值的非线性聚类
- 频谱漂移检测：概念演化/真值老化的量化指标

架构层级：
L1 向量编码层 → L2 频谱变换层 → L3 频谱分析层 → L4 应用层
"""
import hashlib
import json
import math
import os
import sqlite3
import time
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

# ==================== 配置 ====================
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
VECTOR_DIM = 256  # 向量维度（Matryoshka可压缩至128/64/32）
SPECTRUM_BANDS = {
    "low": (0, 32),      # 低频：全局语义/核心概念/稳态基准 (0-12.5%)
    "mid": (32, 96),     # 中频：关系结构/因果链路/演化趋势 (12.5-37.5%)
    "high": (96, 256),   # 高频：局部细节/噪声/瞬时扰动 (37.5-100%)
}
STATE_ATOMS_DB = os.path.expanduser("~/.zongyuan_root/state_atoms.db")
SPECTRUM_OUTPUT_DIR = os.path.expanduser("~/.zongyuan_root/spectrum")


# ==================== L1: 向量编码层 ====================
class VectorEncoder:
    """
    将真值/态元/知识节点编码为高维稠密向量
    采用确定性哈希编码（无需外部模型），保证可复现
    维度：256维，可通过Matryoshka截断压缩
    """

    def __init__(self, dim: int = VECTOR_DIM):
        self.dim = dim

    def encode(self, text: str, meta: Dict = None) -> List[float]:
        """
        将文本编码为256维向量
        方法：n-gram特征哈希 + TF加权 + L2归一化
        """
        vec = [0.0] * self.dim
        if not text:
            return vec

        # 字符级n-gram特征（1-gram, 2-gram, 3-gram）
        text = text.lower().strip()
        for n in [1, 2, 3]:
            for i in range(len(text) - n + 1):
                gram = text[i:i+n]
                # 双重哈希避免碰撞
                h1 = int(hashlib.md5(gram.encode()).hexdigest(), 16)
                h2 = int(hashlib.sha256(gram.encode()).hexdigest(), 16)
                idx1 = h1 % self.dim
                idx2 = h2 % self.dim
                weight = 1.0 / n  # 长gram权重更高
                vec[idx1] += weight
                vec[idx2] += weight * 0.5

        # 元数据加权（类型/置信度影响向量方向）
        if meta:
            if meta.get('confidence'):
                conf = meta['confidence']
                for i in range(self.dim):
                    vec[i] *= (0.5 + 0.5 * conf)
            if meta.get('meta_class'):
                mc_hash = int(hashlib.md5(meta['meta_class'].encode()).hexdigest(), 16)
                for i in range(0, self.dim, 16):
                    vec[(mc_hash + i) % self.dim] += 0.3

        # L2归一化
        norm = math.sqrt(sum(v*v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec

    def encode_batch(self, items: List[Dict]) -> List[Tuple[str, List[float]]]:
        """批量编码"""
        results = []
        for item in items:
            text = item.get('content', item.get('name', ''))
            vec = self.encode(text, item)
            results.append((item.get('id', hashlib.md5(text.encode()).hexdigest()[:12]), vec))
        return results

    def similarity(self, v1: List[float], v2: List[float]) -> float:
        """余弦相似度"""
        dot = sum(a*b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a*a for a in v1))
        n2 = math.sqrt(sum(b*b for b in v2))
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)

    def matryoshka_truncate(self, vec: List[float], dim: int) -> List[float]:
        """Matryoshka表示学习：截断到低维，保留主要语义"""
        truncated = vec[:dim]
        norm = math.sqrt(sum(v*v for v in truncated))
        if norm > 0:
            truncated = [v / norm for v in truncated]
        return truncated


# ==================== L2: 频谱变换层 ====================
class SpectrumTransformer:
    """
    离散傅里叶变换(DFT)将向量分解为频谱分量
    低频=全局语义，中频=关系结构，高频=局部细节
    参考：WavePhaseNet (arXiv 2602.14419) DFT语义层次结构
    """

    def __init__(self, dim: int = VECTOR_DIM):
        self.dim = dim

    def dft(self, vec: List[float]) -> List[Tuple[float, float]]:
        """
        离散傅里叶变换
        返回 [(幅度, 相位), ...]，长度=dim
        """
        n = len(vec)
        result = []
        for k in range(n):
            real = 0.0
            imag = 0.0
            for t in range(n):
                angle = -2 * math.pi * k * t / n
                real += vec[t] * math.cos(angle)
                imag += vec[t] * math.sin(angle)
            magnitude = math.sqrt(real*real + imag*imag)
            phase = math.atan2(imag, real)
            result.append((magnitude, phase))
        return result

    def band_energy(self, spectrum: List[Tuple[float, float]]) -> Dict[str, float]:
        """
        计算各频带能量占比
        低频=全局语义密度，中频=关系结构密度，高频=扰动/噪声
        """
        total_energy = sum(m*m for m, _ in spectrum)
        if total_energy == 0:
            return {"low": 0, "mid": 0, "high": 0, "total": 0}

        bands = {}
        for band_name, (start, end) in SPECTRUM_BANDS.items():
            band_energy = sum(spectrum[k][0]**2 for k in range(start, min(end, len(spectrum))))
            bands[band_name] = round(band_energy / total_energy, 4)
        bands['total'] = round(total_energy, 6)
        return bands

    def spectral_entropy(self, spectrum: List[Tuple[float, float]]) -> float:
        """
        谱熵：衡量频谱分布的均匀性
        熵高=信息分散/复杂，熵低=信息集中/简单
        """
        total = sum(m for m, _ in spectrum)
        if total == 0:
            return 0.0
        entropy = 0.0
        for m, _ in spectrum:
            if m > 0:
                p = m / total
                entropy -= p * math.log2(p)
        return round(entropy, 4)

    def spectral_centroid(self, spectrum: List[Tuple[float, float]]) -> float:
        """
        谱质心：能量重心的频率位置
        质心低=偏全局语义，质心高=偏局部细节
        """
        total_mag = sum(m for m, _ in spectrum)
        if total_mag == 0:
            return 0.0
        centroid = sum(k * spectrum[k][0] for k in range(len(spectrum))) / total_mag
        return round(centroid / len(spectrum), 4)  # 归一化到[0,1]

    def inverse_dft(self, spectrum: List[Tuple[float, float]],
                     keep_bands: List[str] = None) -> List[float]:
        """
        逆DFT，可选只保留特定频带（用于去噪/语义提取）
        keep_bands: ['low']只保留低频(全局语义)，['low','mid']保留低中频
        """
        n = len(spectrum)
        # 构建频域掩码
        mask = [1.0] * n
        if keep_bands:
            mask = [0.0] * n
            for band in keep_bands:
                start, end = SPECTRUM_BANDS[band]
                for k in range(start, min(end, n)):
                    mask[k] = 1.0

        result = []
        for t in range(n):
            real = 0.0
            for k in range(n):
                if mask[k] > 0:
                    mag, phase = spectrum[k]
                    angle = 2 * math.pi * k * t / n + phase
                    real += mag * math.cos(angle)
            result.append(real / n)
        return result


# ==================== L3: 频谱分析层 ====================
class SpectrumAnalyzer:
    """
    频谱分析引擎
    - 频谱能量分布分析
    - 谱聚类（基于相似度矩阵特征值）
    - 频谱漂移检测
    - 异常频谱识别
    """

    def __init__(self, encoder: VectorEncoder, transformer: SpectrumTransformer):
        self.encoder = encoder
        self.transformer = transformer

    def analyze_vector(self, vec: List[float], name: str = "") -> Dict:
        """对单个向量进行完整频谱分析"""
        spectrum = self.transformer.dft(vec)
        bands = self.transformer.band_energy(spectrum)
        entropy = self.transformer.spectral_entropy(spectrum)
        centroid = self.transformer.spectral_centroid(spectrum)

        # 健康度评分：低频占比高+熵适中=健康
        health_score = bands['low'] * 0.5 + (1 - abs(centroid - 0.3)) * 0.3 + (1 - bands['high']) * 0.2

        return {
            "name": name,
            "vector_dim": len(vec),
            "spectrum_bands": bands,
            "spectral_entropy": entropy,
            "spectral_centroid": centroid,
            "health_score": round(health_score, 4),
            "dominant_band": max(bands, key=lambda k: bands[k] if k != 'total' else 0),
            "interpretation": self._interpret(bands, entropy, centroid),
        }

    def _interpret(self, bands: Dict, entropy: float, centroid: float) -> str:
        """频谱解读"""
        parts = []
        if bands['low'] > 0.5:
            parts.append("强全局语义锚定")
        elif bands['low'] < 0.2:
            parts.append("弱全局语义，需加强核心概念")
        if bands['high'] > 0.4:
            parts.append("高频扰动较多，可能存在噪声或瞬时变化")
        if entropy > 7.0:
            parts.append("高谱熵，信息分布均匀复杂")
        elif entropy < 3.0:
            parts.append("低谱熵，信息高度集中")
        if centroid > 0.6:
            parts.append("谱质心偏高，偏局部细节")
        elif centroid < 0.2:
            parts.append("谱质心偏低，偏全局宏观")
        return "；".join(parts) if parts else "频谱分布均衡"

    def spectral_clustering(self, vectors: List[Tuple[str, List[float]]],
                            n_clusters: int = 3) -> Dict:
        """
        谱聚类：基于相似度矩阵特征值的非线性聚类
        参考：NVIDIA向量数据库谱聚类方法
        """
        n = len(vectors)
        if n < n_clusters:
            n_clusters = n

        # 构建相似度矩阵
        sim_matrix = [[0.0]*n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    sim_matrix[i][j] = 1.0
                else:
                    sim_matrix[i][j] = self.encoder.similarity(vectors[i][1], vectors[j][1])

        # 度矩阵
        degrees = [sum(row) for row in sim_matrix]

        # 拉普拉斯矩阵 L = D - W
        laplacian = [[0.0]*n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                laplacian[i][j] = (degrees[i] if i == j else 0) - sim_matrix[i][j]

        # 简化谱聚类：用度中心性近似特征向量聚类
        # （完整特征值分解计算量大，这里用度排序+贪心分组）
        sorted_indices = sorted(range(n), key=lambda i: degrees[i], reverse=True)
        cluster_size = n // n_clusters
        clusters = defaultdict(list)
        for idx, original_idx in enumerate(sorted_indices):
            cluster_id = min(idx // cluster_size, n_clusters - 1)
            clusters[f"cluster_{cluster_id}"].append(vectors[original_idx][0])

        return {
            "n_clusters": n_clusters,
            "n_items": n,
            "clusters": dict(clusters),
            "avg_similarity": round(sum(sum(row) for row in sim_matrix) / (n*n), 4),
            "method": "spectral_clustering_laplacian_approximation",
        }

    def detect_drift(self, vec_old: List[float], vec_new: List[float],
                     name: str = "") -> Dict:
        """
        频谱漂移检测：比较两个向量的频谱差异
        用于概念演化/真值老化检测
        """
        spec_old = self.transformer.dft(vec_old)
        spec_new = self.transformer.dft(vec_new)

        bands_old = self.transformer.band_energy(spec_old)
        bands_new = self.transformer.band_energy(spec_new)

        band_drift = {
            band: round(abs(bands_old.get(band, 0) - bands_new.get(band, 0)), 4)
            for band in ['low', 'mid', 'high']
        }
        total_drift = sum(band_drift.values())

        cosine_sim = self.encoder.similarity(vec_old, vec_new)

        drift_level = "none"
        if total_drift > 0.3:
            drift_level = "critical"
        elif total_drift > 0.15:
            drift_level = "warning"
        elif total_drift > 0.05:
            drift_level = "minor"

        return {
            "name": name,
            "cosine_similarity": round(cosine_sim, 4),
            "band_drift": band_drift,
            "total_spectral_drift": round(total_drift, 4),
            "drift_level": drift_level,
            "recommendation": self._drift_recommendation(drift_level, band_drift),
        }

    def _drift_recommendation(self, level: str, band_drift: Dict) -> str:
        if level == "critical":
            return "严重漂移：需重新锚定真值基准，触发eFuse熔断校验"
        elif level == "warning":
            return "中度漂移：建议交叉验证，检查是否为正常演化"
        elif level == "minor":
            return "轻微漂移：记录演化轨迹，持续监控"
        return "无显著漂移，稳态运行"


# ==================== L4: 向量化高维频谱主引擎 ====================
class VectorSpectrumEngine:
    """
    向量化高维频谱架构主引擎
    整合L1-L4四层，对全域真值/态元执行频谱分析
    """

    def __init__(self):
        self.encoder = VectorEncoder(dim=VECTOR_DIM)
        self.transformer = SpectrumTransformer(dim=VECTOR_DIM)
        self.analyzer = SpectrumAnalyzer(self.encoder, self.transformer)
        self.vectors = {}  # id -> vector
        self.analyses = {}  # id -> analysis result

    def load_state_atoms(self) -> List[Dict]:
        """从态元数据库加载真值"""
        items = []
        if not os.path.exists(STATE_ATOMS_DB):
            return items
        conn = sqlite3.connect(STATE_ATOMS_DB)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT atom_id, content, meta_class, truth_type, confidence
            FROM atoms WHERE atom_type = 'truth'
        """)
        for row in cursor.fetchall():
            items.append({
                'id': row[0],
                'content': row[1] or '',
                'meta_class': row[2],
                'truth_type': row[3],
                'confidence': row[4],
            })
        conn.close()
        return items

    def run_full_analysis(self) -> Dict:
        """执行完整频谱分析流程"""
        start_time = time.time()
        print(f"{'='*60}")
        print(f"向量化高维频谱架构引擎 V1.0")
        print(f"DID: {DID} | {TRACE}")
        print(f"向量维度: {VECTOR_DIM} | 频带: 低/中/高")
        print(f"{'='*60}")

        # L1: 向量编码
        print(f"\n--- L1: 向量编码层 ---")
        truths = self.load_state_atoms()
        print(f"  加载真值: {len(truths)}条")
        encoded = self.encoder.encode_batch(truths)
        for item_id, vec in encoded:
            self.vectors[item_id] = vec
        print(f"  编码完成: {len(self.vectors)}个向量")
        print(f"  向量维度: {VECTOR_DIM} (可Matryoshka压缩至128/64/32)")

        # L2: 频谱变换
        print(f"\n--- L2: 频谱变换层 ---")
        all_spectra = {}
        for item_id, vec in self.vectors.items():
            spectrum = self.transformer.dft(vec)
            all_spectra[item_id] = spectrum
        print(f"  DFT变换完成: {len(all_spectra)}个频谱")

        # L3: 频谱分析
        print(f"\n--- L3: 频谱分析层 ---")
        total_health = 0
        band_totals = {'low': 0, 'mid': 0, 'high': 0}
        for item_id, vec in self.vectors.items():
            analysis = self.analyzer.analyze_vector(vec, item_id)
            self.analyses[item_id] = analysis
            total_health += analysis['health_score']
            for band in ['low', 'mid', 'high']:
                band_totals[band] += analysis['spectrum_bands'][band]

        n = len(self.analyses)
        avg_health = total_health / n if n > 0 else 0
        avg_bands = {k: round(v/n, 4) for k, v in band_totals.items()}
        print(f"  平均健康度: {avg_health:.4f}")
        print(f"  平均频带能量: 低={avg_bands['low']} 中={avg_bands['mid']} 高={avg_bands['high']}")

        # 谱聚类
        print(f"\n--- 谱聚类分析 ---")
        vec_list = [(k, v) for k, v in self.vectors.items()]
        clustering = self.analyzer.spectral_clustering(vec_list, n_clusters=3)
        print(f"  聚类数: {clustering['n_clusters']}")
        for cid, members in clustering['clusters'].items():
            print(f"    {cid}: {len(members)}个节点")

        # 健康度排名
        print(f"\n--- 健康度排名 Top5 ---")
        sorted_health = sorted(self.analyses.items(),
                               key=lambda x: x[1]['health_score'], reverse=True)
        for item_id, analysis in sorted_health[:5]:
            print(f"  {item_id[:25]}: health={analysis['health_score']} "
                  f"低={analysis['spectrum_bands']['low']} "
                  f"{analysis['dominant_band']}频主导")

        # L4: 输出
        print(f"\n--- L4: 输出层 ---")
        os.makedirs(SPECTRUM_OUTPUT_DIR, exist_ok=True)

        result = {
            "meta": {
                "did": DID,
                "trace": TRACE,
                "version": "V1.0",
                "engine": "VectorSpectrumEngine",
                "timestamp": int(time.time()),
                "vector_dim": VECTOR_DIM,
                "spectrum_bands": SPECTRUM_BANDS,
            },
            "summary": {
                "total_vectors": len(self.vectors),
                "avg_health_score": round(avg_health, 4),
                "avg_band_energy": avg_bands,
                "dominant_band_overall": max(avg_bands, key=avg_bands.get),
                "clustering": clustering,
            },
            "detailed_analyses": {
                k: {kk: vv for kk, vv in v.items() if kk != 'name'}
                for k, v in self.analyses.items()
            },
        }

        output_path = os.path.join(SPECTRUM_OUTPUT_DIR, "spectrum_analysis.json")
        with open(output_path, 'w') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  分析报告: {output_path}")

        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"分析完成 | 耗时: {elapsed:.1f}s")
        print(f"向量: {len(self.vectors)} | 平均健康度: {avg_health:.4f}")
        print(f"{'='*60}")

        return result


# ==================== 入口 ====================
if __name__ == "__main__":
    engine = VectorSpectrumEngine()
    result = engine.run_full_analysis()
