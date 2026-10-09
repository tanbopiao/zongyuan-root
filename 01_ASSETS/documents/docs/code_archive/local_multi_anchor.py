"""
模块1：连续流形局部多锚点策略
Local Multi-Anchor Strategy for Continuous Manifolds

解决阶段一问题：连续流形只能提取1个大锚点
方法：在流形上均匀采样多个局部锚点，构建锚点图

算法：
1. Farthest Point Sampling (FPS) - 流形上均匀采样
2. 局部邻域分析 - 每个采样点周围的局部结构
3. 局部切空间/法空间估计
4. 锚点图构建 - 锚点间拓扑关系
5. 锚点质量评估 - 稳定性/代表性评分
"""

import numpy as np
from scipy.spatial.distance import cdist, pdist, squareform
from scipy.linalg import eigh
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import KMeans
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import json
import time


@dataclass
class LocalAnchor:
    """局部锚点数据结构"""
    anchor_id: str
    center: np.ndarray  # 锚点中心点 (d,)
    tangent_basis: np.ndarray  # 切空间基 (d, k)
    normal_basis: np.ndarray  # 法空间基 (d, d-k)
    metric_tensor: np.ndarray  # 局部度量张量 (k, k)
    intrinsic_dim: int  # 本征维度 k
    basin_radius: float  # 局部吸引子盘半径
    stability_score: float  # 稳定性评分
    representativeness: float  # 代表性评分（邻域密度）
    curvature: float  # 局部曲率
    n_neighbors: int  # 邻域点数
    neighbors_idx: np.ndarray  # 邻域点索引
    
    def to_dict(self):
        return {
            'anchor_id': self.anchor_id,
            'center': self.center.tolist(),
            'intrinsic_dim': int(self.intrinsic_dim),
            'basin_radius': float(self.basin_radius),
            'stability_score': float(self.stability_score),
            'representativeness': float(self.representativeness),
            'curvature': float(self.curvature),
            'n_neighbors': int(self.n_neighbors),
        }


@dataclass
class AnchorGraph:
    """锚点图数据结构"""
    anchors: List[LocalAnchor]
    adjacency_matrix: np.ndarray  # 锚点邻接矩阵 (n_anchors, n_anchors)
    edge_weights: np.ndarray  # 边权重 (测地线距离)
    graph_laplacian: np.ndarray  # 图拉普拉斯矩阵
    
    def to_dict(self):
        return {
            'n_anchors': len(self.anchors),
            'anchors': [a.to_dict() for a in self.anchors],
            'adjacency_matrix': self.adjacency_matrix.tolist(),
            'edge_weights': self.edge_weights.tolist(),
            'mean_degree': float(np.mean(np.sum(self.adjacency_matrix, axis=1))),
        }


class LocalMultiAnchorExtractor:
    """
    连续流形局部多锚点提取器
    
    算法流程：
    1. Farthest Point Sampling (FPS) 初始采样
    2. 局部邻域分析
    3. 局部切空间/法空间估计
    4. 锚点质量评估与筛选
    5. 锚点图构建
    """
    
    def __init__(self, 
                 n_anchors=10,
                 n_neighbors=20,
                 intrinsic_dim=None,
                 min_neighbors=10,
                 stability_threshold=0.3,
                 verbose=True):
        """
        Args:
            n_anchors: 目标锚点数
            n_neighbors: 局部邻域大小
            intrinsic_dim: 本征维度，None则自动估计
            min_neighbors: 最小邻域点数（少于此则合并）
            stability_threshold: 稳定性阈值
            verbose: 是否打印进度
        """
        self.n_anchors = n_anchors
        self.n_neighbors = n_neighbors
        self.intrinsic_dim = intrinsic_dim
        self.min_neighbors = min_neighbors
        self.stability_threshold = stability_threshold
        self.verbose = verbose
        self.anchors_ = []
        self.anchor_graph_ = None
        
    def _log(self, msg):
        if self.verbose:
            print(f"  [{time.strftime('%H:%M:%S')}] {msg}")
    
    def fit(self, X):
        """
        从连续流形中提取多个局部锚点
        
        Args:
            X: 数据点 (n, d)
            
        Returns:
            anchors: 局部锚点列表
            anchor_graph: 锚点图
        """
        self.X_ = X
        n, d = X.shape
        self._log(f"开始提取局部多锚点，数据形状: {X.shape}")
        
        # 步骤1：自动估计本征维度
        if self.intrinsic_dim is None:
            self.intrinsic_dim = self._estimate_intrinsic_dim(X)
            self._log(f"自动估计本征维度: k={self.intrinsic_dim}")
        
        # 步骤2：Farthest Point Sampling初始采样
        self._log("步骤1: Farthest Point Sampling初始采样...")
        fps_indices = self._farthest_point_sampling(X, self.n_anchors * 2)
        self._log(f"  FPS采样点: {len(fps_indices)}个")
        
        # 步骤3：对每个采样点构建局部锚点
        self._log("步骤2: 局部锚点构建...")
        candidate_anchors = []
        for i, idx in enumerate(fps_indices):
            anchor = self._build_local_anchor(X, idx, i)
            if anchor is not None:
                candidate_anchors.append(anchor)
        
        self._log(f"  候选锚点数: {len(candidate_anchors)}")
        
        # 步骤4：锚点质量评估与筛选
        self._log("步骤3: 锚点质量评估与筛选...")
        selected_anchors = self._select_anchors(candidate_anchors, X)
        self._log(f"  筛选后锚点数: {len(selected_anchors)}")
        
        # 步骤5：构建锚点图
        self._log("步骤4: 构建锚点图...")
        self.anchor_graph_ = self._build_anchor_graph(selected_anchors, X)
        self._log(f"  锚点图: {len(selected_anchors)}个节点, "
                 f"平均度={np.mean(np.sum(self.anchor_graph_.adjacency_matrix, axis=1)):.1f}")
        
        self.anchors_ = selected_anchors
        self._log(f"局部多锚点提取完成，共 {len(self.anchors_)} 个锚点")
        
        return self.anchors_, self.anchor_graph_
    
    def _estimate_intrinsic_dim(self, X):
        """自动估计本征维度"""
        n, d = X.shape
        nn = NearestNeighbors(n_neighbors=min(self.n_neighbors + 1, n))
        nn.fit(X)
        
        # 采样100个点估计维度
        sample_size = min(100, n)
        indices = np.random.choice(n, sample_size, replace=False)
        
        all_eigenvalues = []
        for idx in indices:
            _, neighbors_idx = nn.kneighbors(X[idx:idx+1])
            neighbors = X[neighbors_idx[0, 1:]]
            centered = neighbors - X[idx]
            cov = centered.T @ centered / len(centered)
            eigenvalues = np.linalg.eigvalsh(cov)[::-1]
            all_eigenvalues.append(eigenvalues)
        
        avg_eigenvalues = np.mean(all_eigenvalues, axis=0)
        # 找特征值下降拐点
        ratios = avg_eigenvalues[1:] / (avg_eigenvalues[:-1] + 1e-10)
        intrinsic_dim = np.argmax(ratios < 0.1) + 1
        intrinsic_dim = max(1, min(intrinsic_dim, d - 1))
        
        return intrinsic_dim
    
    def _farthest_point_sampling(self, X, n_samples):
        """
        Farthest Point Sampling (FPS)
        在流形上均匀采样点
        """
        n = len(X)
        n_samples = min(n_samples, n)
        
        # 随机选择第一个点
        selected = [np.random.randint(n)]
        distances = np.full(n, np.inf)
        
        for _ in range(1, n_samples):
            # 更新到最近已选点的距离
            last_point = X[selected[-1]]
            new_distances = np.linalg.norm(X - last_point, axis=1)
            distances = np.minimum(distances, new_distances)
            
            # 选择最远的点
            farthest = np.argmax(distances)
            selected.append(farthest)
        
        return np.array(selected)
    
    def _build_local_anchor(self, X, center_idx, anchor_idx):
        """构建单个局部锚点"""
        n, d = X.shape
        center = X[center_idx]
        
        # 找局部邻域
        nn = NearestNeighbors(n_neighbors=min(self.n_neighbors + 1, n))
        nn.fit(X)
        _, neighbors_idx = nn.kneighbors(center.reshape(1, -1))
        neighbors_idx = neighbors_idx[0, 1:]  # 排除自身
        
        if len(neighbors_idx) < self.min_neighbors:
            return None
        
        neighbors = X[neighbors_idx]
        centered = neighbors - center
        
        # 局部PCA估计切空间
        cov = centered.T @ centered / len(centered)
        cov += 1e-8 * np.eye(d)
        eigenvalues, eigenvectors = eigh(cov)
        
        # 按特征值降序
        idx = np.argsort(eigenvalues)[::-1]
        eigenvectors = eigenvectors[:, idx]
        eigenvalues = eigenvalues[idx]
        
        k = self.intrinsic_dim
        tangent_basis = eigenvectors[:, :k]  # (d, k)
        normal_basis = eigenvectors[:, k:]    # (d, d-k)
        
        # 局部度量张量（切空间协方差的逆）
        tangent_coords = centered @ tangent_basis
        cov_tangent = tangent_coords.T @ tangent_coords / len(tangent_coords)
        cov_tangent += 1e-8 * np.eye(k)
        metric_tensor = np.linalg.inv(cov_tangent)
        
        # 局部吸引子盘半径（法向距离的85百分位）
        normal_dists = np.linalg.norm(centered @ normal_basis, axis=1)
        basin_radius = np.percentile(normal_dists, 85)
        basin_radius = max(basin_radius, 1e-6)
        
        # 稳定性评分（法向距离方差小=稳定）
        normal_var = np.var(normal_dists)
        tangent_var = np.var(np.linalg.norm(centered @ tangent_basis, axis=1))
        stability = 1.0 / (1.0 + normal_var / (tangent_var + 1e-10))
        stability = float(np.clip(stability, 0, 1))
        
        # 代表性评分（邻域密度）
        avg_distance = np.mean(np.linalg.norm(centered, axis=1))
        representativeness = 1.0 / (1.0 + avg_distance)
        representativeness = float(np.clip(representativeness, 0, 1))
        
        # 局部曲率（法向距离与切向距离的比值）
        tangent_norms = np.linalg.norm(centered @ tangent_basis, axis=1)
        valid = tangent_norms > 1e-8
        if np.sum(valid) > 3:
            curvature = np.mean(normal_dists[valid] / (tangent_norms[valid]**2 + 1e-8))
        else:
            curvature = 0.0
        curvature = float(np.clip(curvature, -100, 100))
        
        anchor = LocalAnchor(
            anchor_id=f"LOCAL-ANCHOR-{anchor_idx:04d}",
            center=center,
            tangent_basis=tangent_basis,
            normal_basis=normal_basis,
            metric_tensor=metric_tensor,
            intrinsic_dim=k,
            basin_radius=basin_radius,
            stability_score=stability,
            representativeness=representativeness,
            curvature=curvature,
            n_neighbors=len(neighbors_idx),
            neighbors_idx=neighbors_idx,
        )
        
        return anchor
    
    def _select_anchors(self, candidates, X):
        """锚点质量评估与筛选"""
        if len(candidates) <= self.n_anchors:
            return candidates
        
        # 综合评分 = 稳定性*0.4 + 代表性*0.3 + 曲率适中度*0.3
        scores = []
        for anchor in candidates:
            # 曲率适中度（曲率太大=边界，太小=平坦）
            curvature_score = 1.0 / (1.0 + abs(anchor.curvature - 1.0))
            score = (anchor.stability_score * 0.4 + 
                    anchor.representativeness * 0.3 + 
                    curvature_score * 0.3)
            scores.append(score)
        
        # 按评分排序，选择top n_anchors，但要保证空间覆盖
        scores = np.array(scores)
        sorted_indices = np.argsort(scores)[::-1]
        
        selected = []
        selected_centers = []
        min_distance = np.percentile(pdist(X), 20)  # 最小间距为20百分位
        
        for idx in sorted_indices:
            anchor = candidates[idx]
            
            # 检查与已选锚点的距离
            if len(selected_centers) > 0:
                distances = np.linalg.norm(np.array(selected_centers) - anchor.center, axis=1)
                if np.min(distances) < min_distance:
                    continue
            
            selected.append(anchor)
            selected_centers.append(anchor.center)
            
            if len(selected) >= self.n_anchors:
                break
        
        return selected
    
    def _build_anchor_graph(self, anchors, X):
        """构建锚点图"""
        n_anchors = len(anchors)
        centers = np.array([a.center for a in anchors])
        
        # 计算锚点间距离
        distances = squareform(pdist(centers))
        
        # 构建邻接矩阵（k近邻）
        k_neighbors = min(5, n_anchors - 1)
        adjacency = np.zeros((n_anchors, n_anchors))
        edge_weights = np.zeros((n_anchors, n_anchors))
        
        for i in range(n_anchors):
            # 找最近的k个邻居
            neighbor_indices = np.argsort(distances[i])[1:k_neighbors+1]
            for j in neighbor_indices:
                adjacency[i, j] = 1
                adjacency[j, i] = 1
                # 边权重 = 距离的倒数（越近权重越大）
                weight = 1.0 / (distances[i, j] + 1e-10)
                edge_weights[i, j] = weight
                edge_weights[j, i] = weight
        
        # 图拉普拉斯矩阵
        degree_matrix = np.diag(np.sum(adjacency, axis=1))
        graph_laplacian = degree_matrix - adjacency
        
        return AnchorGraph(
            anchors=anchors,
            adjacency_matrix=adjacency,
            edge_weights=edge_weights,
            graph_laplacian=graph_laplacian,
        )
    
    def get_anchor_summary(self):
        """获取锚点摘要"""
        summary = []
        for i, anchor in enumerate(self.anchors_):
            summary.append({
                'index': i,
                'anchor_id': anchor.anchor_id,
                'intrinsic_dim': anchor.intrinsic_dim,
                'stability_score': round(anchor.stability_score, 4),
                'representativeness': round(anchor.representativeness, 4),
                'basin_radius': round(anchor.basin_radius, 6),
                'curvature': round(anchor.curvature, 4),
                'n_neighbors': anchor.n_neighbors,
            })
        return summary
    
    def save(self, filepath):
        """保存锚点和锚点图"""
        data = {
            'version': '2.0',
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'n_anchors': len(self.anchors_),
            'intrinsic_dim': self.intrinsic_dim,
            'anchors': [a.to_dict() for a in self.anchors_],
            'anchor_graph': self.anchor_graph_.to_dict() if self.anchor_graph_ else None,
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=lambda o: float(o) if hasattr(o, "item") else str(o))
        return filepath


if __name__ == '__main__':
    print("=" * 60)
    print("  模块1测试：连续流形局部多锚点策略")
    print("=" * 60)
    
    # 生成瑞士卷数据（连续流形）
    np.random.seed(42)
    from sklearn.datasets import make_swiss_roll
    X, _ = make_swiss_roll(n_samples=1000, noise=0.1, random_state=42)
    print(f"\n测试数据: 瑞士卷 {X.shape}")
    
    # 提取局部多锚点
    extractor = LocalMultiAnchorExtractor(
        n_anchors=8,
        n_neighbors=20,
        verbose=True
    )
    anchors, anchor_graph = extractor.fit(X)
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("  锚点提取结果摘要")
    print("=" * 60)
    summary = extractor.get_anchor_summary()
    for s in summary:
        print(f"\n锚点 {s['index']+1}: {s['anchor_id']}")
        print(f"  本征维度: {s['intrinsic_dim']}")
        print(f"  稳定性: {s['stability_score']:.4f}")
        print(f"  代表性: {s['representativeness']:.4f}")
        print(f"  吸引子盘半径: {s['basin_radius']:.6f}")
        print(f"  曲率: {s['curvature']:.4f}")
        print(f"  邻域点数: {s['n_neighbors']}")
    
    print(f"\n锚点图: {len(anchors)}个节点, "
          f"平均度={np.mean(np.sum(anchor_graph.adjacency_matrix, axis=1)):.1f}")
    
    # 保存
    output_path = "/home/user/Doubao/chats/38439832899843586/high_dim_anchor/stage2/results/local_multi_anchor_test.json"
    extractor.save(output_path)
    print(f"\n✅ 结果已保存: {output_path}")
    print("\n✅ 模块1测试通过！")
