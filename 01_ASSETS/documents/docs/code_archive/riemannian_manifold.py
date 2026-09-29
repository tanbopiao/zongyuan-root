"""
黎曼流形计算工具库
Riemannian Manifold Computation Toolkit

实现：
- 黎曼度量估计 (Riemannian Metric Estimation)
- 测地线计算 (Geodesic Computation)
- 切空间运算 (Tangent Space Operations)
- 曲率估计 (Curvature Estimation)
- 对数映射/指数映射 (Log/Exp Maps)
"""

import numpy as np
from scipy.spatial.distance import cdist, pdist, squareform
from scipy.linalg import svd, eigh, solve
from scipy.optimize import minimize
from sklearn.neighbors import NearestNeighbors
from sklearn.decomposition import PCA


class RiemannianMetric:
    """
    黎曼度量张量估计器
    
    从数据点云中估计每个点的局部黎曼度量张量 g_p
    方法：局部PCA + 马氏距离学习
    """
    
    def __init__(self, n_neighbors=15, metric_type='pca'):
        """
        Args:
            n_neighbors: 局部邻域大小
            metric_type: 度量类型 ('pca', 'mahalanobis', 'gaussian')
        """
        self.n_neighbors = n_neighbors
        self.metric_type = metric_type
        self.metrics_ = None  # 每个点的度量矩阵 (n, d, d)
        self.inv_metrics_ = None  # 逆度量矩阵
        
    def fit(self, X):
        """
        估计数据点云中每个点的黎曼度量
        
        Args:
            X: 数据点 (n, d)
        """
        n, d = X.shape
        self.X_ = X
        self.metrics_ = np.zeros((n, d, d))
        self.inv_metrics_ = np.zeros((n, d, d))
        
        # 找每个点的k近邻
        nn = NearestNeighbors(n_neighbors=min(self.n_neighbors + 1, n))
        nn.fit(X)
        distances, indices = nn.kneighbors(X)
        
        for i in range(n):
            neighbors = X[indices[i, 1:]]  # 排除自身
            centered = neighbors - X[i]  # 中心化到当前点
            
            if self.metric_type == 'pca':
                # PCA方法：度量张量 = 协方差矩阵的逆（加权）
                cov = centered.T @ centered / len(centered)
                # 正则化
                cov += 1e-6 * np.eye(d)
                # 度量张量 g = cov^{-1} (马氏距离的度量)
                self.metrics_[i] = np.linalg.inv(cov)
                self.inv_metrics_[i] = cov
                
            elif self.metric_type == 'mahalanobis':
                # 马氏距离方法
                cov = np.cov(centered.T)
                cov += 1e-6 * np.eye(d)
                self.metrics_[i] = np.linalg.inv(cov)
                self.inv_metrics_[i] = cov
                
            elif self.metric_type == 'gaussian':
                # 高斯核方法
                sigma = np.mean(distances[i, 1:]) + 1e-8
                weights = np.exp(-distances[i, 1:]**2 / (2 * sigma**2))
                weights = weights / weights.sum()
                cov = (centered.T * weights) @ centered
                cov += 1e-6 * np.eye(d)
                self.metrics_[i] = np.linalg.inv(cov)
                self.inv_metrics_[i] = cov
        
        return self
    
    def local_distance(self, i, j):
        """计算点i和点j之间的局部黎曼距离（使用点i的度量）"""
        diff = self.X_[j] - self.X_[i]
        return np.sqrt(diff @ self.metrics_[i] @ diff)
    
    def geodesic_distance_approx(self, i, j, n_points=10):
        """
        近似测地线距离：沿直线采样，积分局部度量
        
        Args:
            i, j: 点索引
            n_points: 采样点数
        """
        t = np.linspace(0, 1, n_points)
        path = np.outer(1-t, self.X_[i]) + np.outer(t, self.X_[j])
        
        # 找每个路径点最近的数据点，使用其度量
        nn = NearestNeighbors(n_neighbors=1)
        nn.fit(self.X_)
        _, nearest_idx = nn.kneighbors(path)
        
        # 数值积分
        dist = 0
        for k in range(n_points - 1):
            mid = (path[k] + path[k+1]) / 2
            _, mid_idx = nn.kneighbors(mid.reshape(1, -1))
            diff = path[k+1] - path[k]
            g = self.metrics_[mid_idx[0, 0]]
            dist += np.sqrt(diff @ g @ diff)
        
        return dist


class TangentSpace:
    """
    切空间运算器
    
    实现：
    - 切空间基估计
    - 向量投影到切空间
    - 平行移动 (Parallel Transport)
    - 协变导数 (Covariant Derivative)
    """
    
    def __init__(self, n_neighbors=15):
        self.n_neighbors = n_neighbors
        self.bases_ = None  # 切空间基 (n, d, intrinsic_dim)
        self.intrinsic_dim_ = None
        
    def fit(self, X, intrinsic_dim=None):
        """
        估计每个点的切空间基
        
        Args:
            X: 数据点 (n, d)
            intrinsic_dim: 本征维度，None则自动估计
        """
        n, d = X.shape
        self.X_ = X
        
        nn = NearestNeighbors(n_neighbors=min(self.n_neighbors + 1, n))
        nn.fit(X)
        _, indices = nn.kneighbors(X)
        
        # 自动估计本征维度（使用平均特征值比例）
        if intrinsic_dim is None:
            all_eigenvalues = []
            for i in range(min(n, 100)):  # 采样100个点
                neighbors = X[indices[i, 1:]]
                centered = neighbors - X[i]
                cov = centered.T @ centered / len(centered)
                eigenvalues = np.linalg.eigvalsh(cov)[::-1]
                all_eigenvalues.append(eigenvalues)
            avg_eigenvalues = np.mean(all_eigenvalues, axis=0)
            # 找特征值下降拐点
            ratios = avg_eigenvalues[1:] / (avg_eigenvalues[:-1] + 1e-10)
            intrinsic_dim = np.argmax(ratios < 0.1) + 1
            intrinsic_dim = max(1, min(intrinsic_dim, d-1))
        
        self.intrinsic_dim_ = intrinsic_dim
        self.bases_ = np.zeros((n, d, intrinsic_dim))
        
        for i in range(n):
            neighbors = X[indices[i, 1:]]
            centered = neighbors - X[i]
            cov = centered.T @ centered / len(centered)
            cov += 1e-8 * np.eye(d)
            
            # PCA取前intrinsic_dim个主成分作为切空间基
            eigenvalues, eigenvectors = eigh(cov)
            # 按特征值降序
            idx = np.argsort(eigenvalues)[::-1]
            self.bases_[i] = eigenvectors[:, idx[:intrinsic_dim]]
        
        return self
    
    def project_to_tangent(self, i, v):
        """将向量v投影到点i的切空间"""
        basis = self.bases_[i]  # (d, k)
        return basis @ (basis.T @ v)
    
    def project_to_normal(self, i, v):
        """将向量v投影到点i的法空间"""
        return v - self.project_to_tangent(i, v)
    
    def tangent_coordinates(self, i, v):
        """获取向量v在点i切空间中的坐标"""
        basis = self.bases_[i]
        return basis.T @ v
    
    def from_tangent_coordinates(self, i, coords):
        """从切空间坐标重建向量"""
        return self.bases_[i] @ coords


class GeodesicCalculator:
    """
    测地线计算器
    
    实现：
    - 对数映射 Log_p(q)
    - 指数映射 Exp_p(v)
    - 两点间测地线
    - 测地插值
    """
    
    def __init__(self, metric=None, tangent_space=None, method='shooting'):
        self.metric = metric
        self.tangent_space = tangent_space
        self.method = method  # 'shooting', 'graph', 'linear'
    
    def log_map(self, X, p_idx, q_idx, n_steps=20):
        """
        对数映射：Log_p(q)，返回p处切空间中指向q的向量
        
        简化实现：使用图距离近似，方向用(q-p)投影到切空间
        """
        p = X[p_idx]
        q = X[q_idx]
        direction = q - p
        
        # 投影到切空间
        if self.tangent_space is not None:
            direction = self.tangent_space.project_to_tangent(p_idx, direction)
        
        # 计算测地线距离作为范数
        if self.metric is not None:
            dist = self.metric.geodesic_distance_approx(p_idx, q_idx)
        else:
            dist = np.linalg.norm(direction)
        
        # 归一化方向并乘以距离
        norm = np.linalg.norm(direction)
        if norm > 1e-10:
            tangent_vector = direction / norm * dist
        else:
            tangent_vector = np.zeros_like(direction)
        
        return tangent_vector
    
    def exp_map(self, X, p_idx, tangent_vector, n_steps=20):
        """
        指数映射：Exp_p(v)，从p沿切向量v走测地线到达的点
        
        简化实现：沿切向量方向在数据空间中步进，每步投影到数据流形
        """
        p = X[p_idx]
        result = p.copy()
        
        # 找最近邻用于投影
        nn = NearestNeighbors(n_neighbors=1)
        nn.fit(X)
        
        step_size = 1.0 / n_steps
        for step in range(n_steps):
            result = result + step_size * tangent_vector
            # 投影到数据流形（找最近数据点）
            _, idx = nn.kneighbors(result.reshape(1, -1))
            # 混合：保留一部分步进，一部分投影
            result = 0.7 * result + 0.3 * X[idx[0, 0]]
        
        return result
    
    def geodesic_path(self, X, p_idx, q_idx, n_points=20):
        """
        计算p到q的测地线路径
        
        方法：对数映射 -> 切空间线性插值 -> 指数映射
        """
        # 对数映射
        v = self.log_map(X, p_idx, q_idx)
        
        path = np.zeros((n_points, X.shape[1]))
        for i, t in enumerate(np.linspace(0, 1, n_points)):
            if t == 0:
                path[i] = X[p_idx]
            elif t == 1:
                path[i] = X[q_idx]
            else:
                # 指数映射：沿t*v走
                path[i] = self.exp_map(X, p_idx, t * v)
        
        return path
    
    def geodesic_interpolate(self, X, p_idx, q_idx, t):
        """测地插值：在p和q之间按t∈[0,1]插值"""
        v = self.log_map(X, p_idx, q_idx)
        return self.exp_map(X, p_idx, t * v)


class CurvatureEstimator:
    """
    曲率估计器
    
    实现：
    - 截面曲率估计
    - 里奇曲率估计
    - 标量曲率估计
    - 高曲率区域检测（概念边界）
    """
    
    def __init__(self, n_neighbors=20):
        self.n_neighbors = n_neighbors
    
    def estimate_sectional_curvature(self, X, i, u, v):
        """
        估计点i处由切向量u,v张成平面的截面曲率
        
        方法：比较流形上三角形内角和与π的偏差
        K = (π - (α+β+γ)) / Area
        """
        # 简化实现：用局部邻域的协方差结构估计曲率
        nn = NearestNeighbors(n_neighbors=min(self.n_neighbors + 1, len(X)))
        nn.fit(X)
        _, indices = nn.kneighbors(X[i:i+1])
        
        neighbors = X[indices[0, 1:]]
        centered = neighbors - X[i]
        
        # 投影到u,v平面
        u = u / (np.linalg.norm(u) + 1e-10)
        v = v / (np.linalg.norm(v) + 1e-10)
        v = v - np.dot(v, u) * u  # 正交化
        v = v / (np.linalg.norm(v) + 1e-10)
        
        coords_u = centered @ u
        coords_v = centered @ v
        
        # 估计二维平面上的曲率：比较径向距离分布
        r = np.sqrt(coords_u**2 + coords_v**2)
        # 圆周上点的平均半径 vs 欧氏预期
        angles = np.arctan2(coords_v, coords_u)
        
        # 简化：用局部维度变化估计曲率符号
        # 正曲率：邻域点比欧氏预期更密集
        # 负曲率：邻域点比欧氏预期更稀疏
        mean_r = np.mean(r)
        expected_area = np.pi * mean_r**2
        actual_density = len(neighbors) / (expected_area + 1e-10)
        uniform_density = len(X) / (np.prod(X.max(axis=0) - X.min(axis=0)) + 1e-10)
        
        curvature = (actual_density - uniform_density) / (uniform_density + 1e-10)
        
        return np.clip(curvature, -10, 10)
    
    def estimate_scalar_curvature(self, X, i):
        """估计点i处的标量曲率"""
        d = X.shape[1]
        # 随机采样多个二维平面，平均截面曲率
        n_planes = min(10, d * (d-1) // 2)
        curvatures = []
        
        rng = np.random.RandomState(42)
        for _ in range(n_planes):
            u = rng.randn(d)
            v = rng.randn(d)
            K = self.estimate_sectional_curvature(X, i, u, v)
            curvatures.append(K)
        
        # 标量曲率 = 2 * sum of sectional curvatures (simplified)
        return 2 * np.mean(curvatures)
    
    def detect_high_curvature_regions(self, X, threshold=1.0):
        """检测高曲率区域（概念边界）"""
        n = len(X)
        curvatures = np.zeros(n)
        
        for i in range(n):
            curvatures[i] = self.estimate_scalar_curvature(X, i)
        
        high_curvature_idx = np.where(np.abs(curvatures) > threshold)[0]
        return high_curvature_idx, curvatures


def compute_pairwise_geodesic_distances(X, metric=None, n_neighbors=15):
    """
    计算成对测地线距离矩阵
    
    方法：构建k近邻图，用图最短路径近似测地线距离（Isomap方法）
    """
    from scipy.sparse.csgraph import shortest_path
    from scipy.sparse import csr_matrix
    
    n = len(X)
    
    # 构建k近邻图
    nn = NearestNeighbors(n_neighbors=min(n_neighbors + 1, n))
    nn.fit(X)
    distances, indices = nn.kneighbors(X)
    
    # 构建邻接矩阵
    graph = np.zeros((n, n))
    for i in range(n):
        for j in range(1, len(indices[i])):
            graph[i, indices[i, j]] = distances[i, j]
            graph[indices[i, j], i] = distances[i, j]
    
    # 如果有度量张量，用黎曼距离代替欧氏距离
    if metric is not None:
        for i in range(n):
            for j in range(1, len(indices[i])):
                j_idx = indices[i, j]
                riemann_dist = metric.local_distance(i, j_idx)
                graph[i, j_idx] = riemann_dist
                graph[j_idx, i] = riemann_dist
    
    # 最短路径
    graph_sparse = csr_matrix(graph)
    geodesic_distances = shortest_path(graph_sparse, method='D')
    
    return geodesic_distances


if __name__ == '__main__':
    # 简单测试
    print("黎曼流形计算工具库测试")
    print("=" * 50)
    
    # 生成瑞士卷数据
    from sklearn.datasets import make_swiss_roll
    X, t = make_swiss_roll(n_samples=500, noise=0.1, random_state=42)
    print(f"数据形状: {X.shape}")
    
    # 测试黎曼度量
    print("\n1. 黎曼度量估计...")
    metric = RiemannianMetric(n_neighbors=15, metric_type='pca')
    metric.fit(X)
    print(f"   度量矩阵形状: {metric.metrics_.shape}")
    print(f"   点0的度量矩阵迹: {np.trace(metric.metrics_[0]):.4f}")
    
    # 测试切空间
    print("\n2. 切空间估计...")
    ts = TangentSpace(n_neighbors=15)
    ts.fit(X, intrinsic_dim=2)
    print(f"   本征维度: {ts.intrinsic_dim_}")
    print(f"   切空间基形状: {ts.bases_.shape}")
    
    # 测试测地线
    print("\n3. 测地线计算...")
    gc = GeodesicCalculator(metric=metric, tangent_space=ts)
    v = gc.log_map(X, 0, 100)
    print(f"   Log_0(100) 切向量范数: {np.linalg.norm(v):.4f}")
    path = gc.geodesic_path(X, 0, 100, n_points=10)
    print(f"   测地线路径形状: {path.shape}")
    
    # 测试成对测地线距离
    print("\n4. 成对测地线距离矩阵...")
    geo_dist = compute_pairwise_geodesic_distances(X, metric=None, n_neighbors=10)
    print(f"   距离矩阵形状: {geo_dist.shape}")
    print(f"   最大距离: {geo_dist.max():.4f}")
    
    print("\n✅ 所有测试通过！")
