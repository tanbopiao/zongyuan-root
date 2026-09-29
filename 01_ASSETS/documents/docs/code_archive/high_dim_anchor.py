"""
高维锚点提取算法
High-Dimensional Anchor Extraction Algorithm

实现：
- 密度聚类（DBSCAN/HDBSCAN简化版）
- 局部维度估计
- 流形学习（Isomap/PCA）
- 切空间估计
- 度量张量计算
- 吸引子盘估计
- 稳定性验证（李雅普诺夫指数）
"""

import numpy as np
from scipy.spatial.distance import cdist, pdist, squareform
from scipy.linalg import eigh, svd
from scipy.optimize import minimize
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import json
import time


@dataclass
class HighDimensionalAnchor:
    """
    高维锚点数据结构
    
    对应理论文档中的定义：
    A ⊂ M, dim(A) = k, 0 ≤ k ≤ d
    """
    anchor_id: str
    name: str
    dimension: int  # k: 子流形维度
    manifold_embedding: np.ndarray  # 锚点参数化表示 (n_points, d)
    tangent_basis: List[np.ndarray]  # 切空间基向量列表 (k, d)
    normal_basis: List[np.ndarray]  # 法空间基向量列表 (d-k, d)
    metric_tensor: np.ndarray  # 锚点上的诱导度量 (k, k)
    curvature: float  # 平均曲率
    basin_radius: float  # 吸引子盘半径
    lyapunov_exponents: List[float]  # 李雅普诺夫指数
    stability_score: float  # 稳定性评分 [0,1]
    semantic_tags: List[str] = field(default_factory=list)
    creation_time: str = ""
    version: str = "1.0"
    center_point: np.ndarray = None  # 锚点中心点
    n_points: int = 0  # 锚点包含的数据点数
    
    def to_dict(self):
        """转换为可序列化字典"""
        return {
            "anchor_id": self.anchor_id,
            "name": self.name,
            "dimension": self.dimension,
            "n_points": self.n_points,
            "center_point": self.center_point.tolist() if self.center_point is not None else None,
            "tangent_basis": [b.tolist() for b in self.tangent_basis],
            "normal_basis": [b.tolist() for b in self.normal_basis],
            "metric_tensor": self.metric_tensor.tolist(),
            "curvature": float(self.curvature),
            "basin_radius": float(self.basin_radius),
            "lyapunov_exponents": [float(x) for x in self.lyapunov_exponents],
            "stability_score": float(self.stability_score),
            "semantic_tags": self.semantic_tags,
            "creation_time": self.creation_time,
            "version": self.version
        }


class HighDimensionalAnchorExtractor:
    """
    高维锚点提取器
    
    算法流程（对应理论文档算法1）：
    1. 密度聚类（Density Clustering）
    2. 局部维度估计（Local Dimension Estimation）
    3. 流形学习（Manifold Learning）
    4. 切空间估计（Tangent Space Estimation）
    5. 度量张量计算（Metric Tensor Computation）
    6. 吸引子盘估计（Basin Estimation）
    7. 稳定性验证（Stability Verification）
    """
    
    def __init__(self, 
                 n_neighbors=15, 
                 eps=None, 
                 min_samples=5,
                 max_dimension=5,
                 stability_iterations=50,
                 verbose=True):
        """
        Args:
            n_neighbors: 局部邻域大小
            eps: DBSCAN邻域半径，None则自动估计
            min_samples: DBSCAN最小样本数
            max_dimension: 锚点最大维度
            stability_iterations: 稳定性验证迭代次数
            verbose: 是否打印进度
        """
        self.n_neighbors = n_neighbors
        self.eps = eps
        self.min_samples = min_samples
        self.max_dimension = max_dimension
        self.stability_iterations = stability_iterations
        self.verbose = verbose
        self.anchors_ = []
        
    def _log(self, msg):
        if self.verbose:
            print(f"  [{time.strftime('%H:%M:%S')}] {msg}")
    
    def fit(self, X, semantic_tags=None):
        """
        从数据中提取高维锚点
        
        Args:
            X: 数据点 (n, d)
            semantic_tags: 每个点的语义标签（可选）
            
        Returns:
            anchors: 高维锚点列表
        """
        self.X_ = X
        n, d = X.shape
        self._log(f"开始提取高维锚点，数据形状: {X.shape}")
        
        # 步骤1：密度聚类
        self._log("步骤1: 密度聚类...")
        clusters = self._density_clustering(X)
        self._log(f"  发现 {len(clusters)} 个聚类")
        
        # 步骤2-7：对每个聚类提取锚点
        self.anchors_ = []
        for i, cluster_idx in enumerate(clusters):
            self._log(f"处理聚类 {i+1}/{len(clusters)} ({len(cluster_idx)} 个点)...")
            anchor = self._extract_single_anchor(X, cluster_idx, i, semantic_tags)
            if anchor is not None:
                self.anchors_.append(anchor)
                self._log(f"  ✅ 提取锚点: {anchor.name}, 维度={anchor.dimension}, "
                         f"稳定性={anchor.stability_score:.3f}, 吸引子盘半径={anchor.basin_radius:.4f}")
        
        self._log(f"提取完成，共 {len(self.anchors_)} 个高维锚点")
        return self.anchors_
    
    def _density_clustering(self, X):
        """
        步骤1：密度聚类
        
        使用DBSCAN，自动估计eps
        """
        n = len(X)
        
        # 自动估计eps：使用k近邻距离的中位数
        if self.eps is None:
            nn = NearestNeighbors(n_neighbors=min(self.n_neighbors, n))
            nn.fit(X)
            distances, _ = nn.kneighbors(X)
            self.eps = np.median(distances[:, -1]) * 1.5
            self._log(f"  自动估计 eps = {self.eps:.4f}")
        
        # DBSCAN聚类
        clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples)
        labels = clustering.fit_predict(X)
        
        # 收集每个聚类的索引
        unique_labels = set(labels)
        unique_labels.discard(-1)  # 移除噪声点
        
        clusters = []
        for label in sorted(unique_labels):
            cluster_idx = np.where(labels == label)[0]
            if len(cluster_idx) >= self.min_samples:
                clusters.append(cluster_idx)
        
        return clusters
    
    def _estimate_local_dimension(self, X_cluster):
        """
        步骤2：局部维度估计
        
        使用PCA特征值比例法估计本征维度
        """
        n, d = X_cluster.shape
        
        # PCA
        pca = PCA()
        pca.fit(X_cluster)
        eigenvalues = pca.explained_variance_
        
        # 方法1：特征值下降拐点法
        ratios = eigenvalues[1:] / (eigenvalues[:-1] + 1e-10)
        dim1 = np.argmax(ratios < 0.1) + 1
        
        # 方法2：累计方差解释率法（95%）
        cumulative = np.cumsum(eigenvalues) / np.sum(eigenvalues)
        dim2 = np.argmax(cumulative >= 0.95) + 1
        
        # 取两者平均，限制在[1, max_dimension]
        dim = int(round((dim1 + dim2) / 2))
        dim = max(1, min(dim, self.max_dimension, d-1))
        
        return dim, eigenvalues
    
    def _learn_manifold(self, X_cluster, dimension):
        """
        步骤3：流形学习
        
        使用PCA+局部切空间对齐得到锚点的参数化表示
        """
        n, d = X_cluster.shape
        
        # 中心化
        center = np.mean(X_cluster, axis=0)
        centered = X_cluster - center
        
        # PCA得到低维表示
        pca = PCA(n_components=dimension)
        low_dim = pca.fit_transform(centered)
        
        # 重构高维表示（作为锚点的流形嵌入）
        manifold_embedding = pca.inverse_transform(low_dim) + center
        
        return manifold_embedding, center, pca
    
    def _estimate_tangent_space(self, X_cluster, center, dimension):
        """
        步骤4：切空间估计
        
        在锚点中心点估计切空间和法空间
        """
        n, d = X_cluster.shape
        
        # 局部邻域
        nn = NearestNeighbors(n_neighbors=min(self.n_neighbors, n))
        nn.fit(X_cluster)
        _, indices = nn.kneighbors(center.reshape(1, -1))
        
        neighbors = X_cluster[indices[0]]
        centered = neighbors - center
        
        # PCA得到切空间基
        cov = centered.T @ centered / len(centered)
        cov += 1e-8 * np.eye(d)
        eigenvalues, eigenvectors = eigh(cov)
        
        # 按特征值降序
        idx = np.argsort(eigenvalues)[::-1]
        eigenvectors = eigenvectors[:, idx]
        eigenvalues = eigenvalues[idx]
        
        # 切空间基（前dimension个）
        tangent_basis = [eigenvectors[:, i] for i in range(dimension)]
        
        # 法空间基（剩余d-dimension个）
        normal_basis = [eigenvectors[:, i] for i in range(dimension, d)]
        
        return tangent_basis, normal_basis, eigenvalues
    
    def _compute_metric_tensor(self, tangent_basis, X_cluster, center):
        """
        步骤5：度量张量计算
        
        在切空间基下计算诱导度量 g_A = J^T J
        """
        k = len(tangent_basis)
        d = tangent_basis[0].shape[0]
        
        # 构建雅可比矩阵（切空间基作为列）
        J = np.column_stack(tangent_basis)  # (d, k)
        
        # 诱导度量
        metric_tensor = J.T @ J  # (k, k)
        
        # 用局部邻域数据修正度量
        nn = NearestNeighbors(n_neighbors=min(self.n_neighbors, len(X_cluster)))
        nn.fit(X_cluster)
        _, indices = nn.kneighbors(center.reshape(1, -1))
        neighbors = X_cluster[indices[0]]
        centered = neighbors - center
        
        # 投影到切空间，计算切空间中的协方差
        tangent_coords = centered @ J  # (n, k)
        cov_tangent = tangent_coords.T @ tangent_coords / len(tangent_coords)
        cov_tangent += 1e-8 * np.eye(k)
        
        # 度量 = 协方差的逆（马氏距离度量）
        metric_tensor = np.linalg.inv(cov_tangent)
        
        return metric_tensor
    
    def _estimate_basin_radius(self, X, anchor_points, center, tangent_basis, normal_basis):
        """
        步骤6：吸引子盘估计
        
        估计锚点的吸引子盘半径
        方法：从锚点周围采样初始点，观察哪些点会"收敛"到锚点
        （简化版：用密度梯度估计吸引域边界）
        """
        d = X.shape[1]
        k = len(tangent_basis)
        
        # 构建切空间和法空间投影矩阵
        T = np.column_stack(tangent_basis)  # (d, k)
        N = np.column_stack(normal_basis)   # (d, d-k)
        
        # 计算所有点到锚点中心的法向距离和切向距离
        diffs = X - center  # (n, d)
        normal_dists = np.linalg.norm(diffs @ N, axis=1)  # 法向距离
        tangent_dists = np.linalg.norm(diffs @ T, axis=1)  # 切向距离
        
        # 法向距离的分布：吸引子盘内的点法向距离较小
        # 用法向距离的百分位数作为吸引子盘半径估计
        # 假设85%的邻域点在吸引子盘内
        nn = NearestNeighbors(n_neighbors=min(self.n_neighbors * 3, len(X)))
        nn.fit(X)
        _, local_indices = nn.kneighbors(center.reshape(1, -1))
        local_normal_dists = normal_dists[local_indices[0]]
        
        # 吸引子盘半径 = 法向距离的85百分位数
        basin_radius = np.percentile(local_normal_dists, 85)
        
        # 确保半径为正
        basin_radius = max(basin_radius, 1e-6)
        
        return basin_radius, normal_dists, tangent_dists
    
    def _verify_stability(self, X, center, tangent_basis, normal_basis, 
                          basin_radius, n_iterations=None):
        """
        步骤7：稳定性验证
        
        估计李雅普诺夫指数，验证锚点稳定性
        法向李雅普诺夫指数应为负（稳定），切向可为零或微正
        """
        if n_iterations is None:
            n_iterations = self.stability_iterations
        
        d = X.shape[1]
        k = len(tangent_basis)
        
        T = np.column_stack(tangent_basis)  # (d, k)
        N = np.column_stack(normal_basis)   # (d, d-k)
        
        # 简化的李雅普诺夫指数估计：
        # 观察邻域点随"时间"（用距离中心的远近模拟）的发散/收敛率
        
        nn = NearestNeighbors(n_neighbors=min(self.n_neighbors * 2, len(X)))
        nn.fit(X)
        distances, indices = nn.kneighbors(center.reshape(1, -1))
        distances = distances[0]
        indices = indices[0]
        
        # 法向李雅普诺夫指数：法向距离随整体距离的变化率
        diffs = X[indices] - center
        normal_dists = np.linalg.norm(diffs @ N, axis=1)
        total_dists = np.linalg.norm(diffs, axis=1)
        
        # 回归：log(normal_dist) ~ log(total_dist)，斜率即为法向李雅普诺夫指数
        valid = (normal_dists > 1e-8) & (total_dists > 1e-8)
        if np.sum(valid) > 3:
            log_normal = np.log(normal_dists[valid])
            log_total = np.log(total_dists[valid])
            # 线性回归斜率
            slope_normal = np.polyfit(log_total, log_normal, 1)[0]
            lyap_normal = slope_normal - 1  # 收敛率
        else:
            lyap_normal = -1.0  # 默认稳定
        
        # 切向李雅普诺夫指数
        tangent_dists = np.linalg.norm(diffs @ T, axis=1)
        valid_t = (tangent_dists > 1e-8) & (total_dists > 1e-8)
        if np.sum(valid_t) > 3:
            log_tangent = np.log(tangent_dists[valid_t])
            slope_tangent = np.polyfit(log_total[valid_t], log_tangent, 1)[0]
            lyap_tangent = slope_tangent - 1
        else:
            lyap_tangent = 0.0  # 默认中性
        
        # 组合李雅普诺夫指数
        lyapunov_exponents = [lyap_tangent] * k + [lyap_normal] * (d - k)
        
        # 稳定性评分：法向指数越负越稳定，切向指数接近0越好
        normal_stability = 1.0 / (1.0 + np.exp(lyap_normal * 3))  # sigmoid，lyap<0时接近1
        tangent_neutral = 1.0 - min(abs(lyap_tangent), 1.0)  # 越接近0越好
        stability_score = 0.7 * normal_stability + 0.3 * tangent_neutral
        stability_score = float(np.clip(stability_score, 0, 1))
        
        return lyapunov_exponents, stability_score
    
    def _estimate_curvature(self, X_cluster, center, tangent_basis):
        """估计锚点的平均曲率"""
        k = len(tangent_basis)
        d = tangent_basis[0].shape[0]
        
        T = np.column_stack(tangent_basis)
        
        # 局部邻域
        nn = NearestNeighbors(n_neighbors=min(self.n_neighbors, len(X_cluster)))
        nn.fit(X_cluster)
        _, indices = nn.kneighbors(center.reshape(1, -1))
        neighbors = X_cluster[indices[0]]
        centered = neighbors - center
        
        # 投影到切空间
        tangent_coords = centered @ T  # (n, k)
        
        # 法向分量
        normal_components = centered - tangent_coords @ T.T  # (n, d)
        
        # 曲率估计：法向分量与切向坐标的二次关系
        # 简化：用平均法向距离与切向距离的比值
        tangent_norms = np.linalg.norm(tangent_coords, axis=1)
        normal_norms = np.linalg.norm(normal_components, axis=1)
        
        valid = tangent_norms > 1e-8
        if np.sum(valid) > 3:
            curvature = np.mean(normal_norms[valid] / (tangent_norms[valid]**2 + 1e-8))
        else:
            curvature = 0.0
        
        return float(np.clip(curvature, -100, 100))
    
    def _extract_single_anchor(self, X, cluster_idx, cluster_id, semantic_tags=None):
        """从单个聚类中提取一个高维锚点"""
        X_cluster = X[cluster_idx]
        n, d = X_cluster.shape
        
        # 步骤2：局部维度估计
        dimension, eigenvalues = self._estimate_local_dimension(X_cluster)
        
        # 步骤3：流形学习
        manifold_embedding, center, pca = self._learn_manifold(X_cluster, dimension)
        
        # 步骤4：切空间估计
        tangent_basis, normal_basis, _ = self._estimate_tangent_space(
            X_cluster, center, dimension)
        
        # 步骤5：度量张量计算
        metric_tensor = self._compute_metric_tensor(tangent_basis, X_cluster, center)
        
        # 步骤6：吸引子盘估计
        basin_radius, normal_dists, tangent_dists = self._estimate_basin_radius(
            X, manifold_embedding, center, tangent_basis, normal_basis)
        
        # 步骤7：稳定性验证
        lyapunov_exponents, stability_score = self._verify_stability(
            X, center, tangent_basis, normal_basis, basin_radius)
        
        # 曲率估计
        curvature = self._estimate_curvature(X_cluster, center, tangent_basis)
        
        # 语义标签
        tags = []
        if semantic_tags is not None and len(semantic_tags) == len(X):
            cluster_tags = [semantic_tags[i] for i in cluster_idx if semantic_tags[i]]
            tags = list(set(cluster_tags))[:5]
        
        # 创建锚点对象
        anchor = HighDimensionalAnchor(
            anchor_id=f"ANCHOR-{cluster_id:04d}-{int(time.time())}",
            name=f"高维锚点_{cluster_id+1}(维度{dimension})",
            dimension=dimension,
            manifold_embedding=manifold_embedding,
            tangent_basis=tangent_basis,
            normal_basis=normal_basis,
            metric_tensor=metric_tensor,
            curvature=curvature,
            basin_radius=basin_radius,
            lyapunov_exponents=lyapunov_exponents,
            stability_score=stability_score,
            semantic_tags=tags,
            creation_time=time.strftime("%Y-%m-%d %H:%M:%S"),
            version="1.0",
            center_point=center,
            n_points=n
        )
        
        return anchor
    
    def get_anchor_summary(self):
        """获取锚点摘要信息"""
        summary = []
        for i, anchor in enumerate(self.anchors_):
            summary.append({
                "index": i,
                "anchor_id": anchor.anchor_id,
                "name": anchor.name,
                "dimension": anchor.dimension,
                "n_points": anchor.n_points,
                "stability_score": round(anchor.stability_score, 4),
                "basin_radius": round(anchor.basin_radius, 6),
                "curvature": round(anchor.curvature, 4),
                "lyapunov_exponents": [round(x, 4) for x in anchor.lyapunov_exponents],
                "semantic_tags": anchor.semantic_tags
            })
        return summary
    
    def save_anchors(self, filepath):
        """保存锚点到JSON文件"""
        data = {
            "version": "1.0",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "n_anchors": len(self.anchors_),
            "anchors": [anchor.to_dict() for anchor in self.anchors_]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath


if __name__ == '__main__':
    print("高维锚点提取算法测试")
    print("=" * 60)
    
    # 生成测试数据：3个高斯聚类（模拟3个概念锚点）
    np.random.seed(42)
    n_per_cluster = 100
    
    # 聚类1：低维流形（2维平面嵌入3维空间）
    t1 = np.random.uniform(0, 2*np.pi, n_per_cluster)
    s1 = np.random.uniform(-1, 1, n_per_cluster)
    cluster1 = np.column_stack([
        3 * np.cos(t1) + s1 * 0.1,
        3 * np.sin(t1) + s1 * 0.1,
        s1
    ])
    
    # 聚类2：另一个位置的聚类
    cluster2 = np.random.randn(n_per_cluster, 3) * 0.5 + np.array([8, 0, 2])
    
    # 聚类3：第三个聚类
    cluster3 = np.random.randn(n_per_cluster, 3) * 0.3 + np.array([0, 8, -2])
    
    X = np.vstack([cluster1, cluster2, cluster3])
    print(f"测试数据形状: {X.shape}")
    print(f"  聚类1: 环形流形 (维度≈2)")
    print(f"  聚类2: 高斯团 (维度≈3)")
    print(f"  聚类3: 紧致高斯团 (维度≈1-2)")
    
    # 提取锚点
    print("\n开始提取高维锚点...")
    extractor = HighDimensionalAnchorExtractor(
        n_neighbors=15, 
        min_samples=10,
        max_dimension=3,
        verbose=True
    )
    anchors = extractor.fit(X)
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("锚点提取结果摘要")
    print("=" * 60)
    summary = extractor.get_anchor_summary()
    for s in summary:
        print(f"\n锚点 {s['index']+1}: {s['name']}")
        print(f"  ID: {s['anchor_id']}")
        print(f"  维度: {s['dimension']}")
        print(f"  数据点数: {s['n_points']}")
        print(f"  稳定性评分: {s['stability_score']:.4f}")
        print(f"  吸引子盘半径: {s['basin_radius']:.6f}")
        print(f"  平均曲率: {s['curvature']:.4f}")
        print(f"  李雅普诺夫指数: {s['lyapunov_exponents']}")
    
    # 保存
    output_path = "/home/user/Doubao/chats/38439832899843586/high_dim_anchor/results/test_anchors.json"
    extractor.save_anchors(output_path)
    print(f"\n✅ 锚点已保存到: {output_path}")
    print("\n✅ 高维锚点提取算法测试通过！")
