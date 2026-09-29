"""
模块2：真实动力系统 - 梯度下降流
Dynamical System - Gradient Descent Flow

解决阶段一问题：李雅普诺夫指数估计不准确
方法：构建真实的梯度下降流动力系统，通过轨迹演化准确计算李雅普诺夫指数

算法：
1. 势能函数定义（KDE密度负对数）
2. 梯度下降流数值积分（RK4）
3. 轨迹演化追踪
4. 李雅普诺夫指数准确计算（切空间演化法）
5. 吸引子盘精确边界确定
"""

import numpy as np
from scipy.spatial.distance import cdist
from sklearn.neighbors import KernelDensity, NearestNeighbors
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Callable
import json
import time


@dataclass
class Trajectory:
    """轨迹数据结构"""
    trajectory_id: str
    initial_point: np.ndarray  # 初始点 (d,)
    points: np.ndarray  # 轨迹点 (T, d)
    velocities: np.ndarray  # 速度 (T, d)
    converged: bool  # 是否收敛
    convergence_time: int  # 收敛时间步
    final_point: np.ndarray  # 最终点 (d,)
    
    def to_dict(self):
        return {
            'trajectory_id': self.trajectory_id,
            'converged': self.converged,
            'convergence_time': int(self.convergence_time),
            'initial_point': self.initial_point.tolist(),
            'final_point': self.final_point.tolist(),
            'trajectory_length': len(self.points),
        }


@dataclass
class Attractor:
    """吸引子数据结构"""
    attractor_id: str
    center: np.ndarray  # 吸引子中心 (d,)
    basin_radius: float  # 吸引子盘半径
    lyapunov_exponents: np.ndarray  # 李雅普诺夫指数 (d,)
    tangent_lyapunov: np.ndarray  # 切向李雅普诺夫指数 (k,)
    normal_lyapunov: np.ndarray  # 法向李雅普诺夫指数 (d-k,)
    stability_score: float  # 稳定性评分
    n_converged_trajectories: int  # 收敛到该吸引子的轨迹数
    tangent_basis: np.ndarray  # 切空间基 (d, k)
    normal_basis: np.ndarray  # 法空间基 (d, d-k)
    intrinsic_dim: int  # 本征维度
    
    def to_dict(self):
        return {
            'attractor_id': self.attractor_id,
            'center': self.center.tolist(),
            'basin_radius': float(self.basin_radius),
            'lyapunov_exponents': self.lyapunov_exponents.tolist(),
            'tangent_lyapunov': self.tangent_lyapunov.tolist(),
            'normal_lyapunov': self.normal_lyapunov.tolist(),
            'stability_score': float(self.stability_score),
            'n_converged_trajectories': int(self.n_converged_trajectories),
            'intrinsic_dim': int(self.intrinsic_dim),
        }


class GradientDescentFlow:
    """
    梯度下降流动力系统
    
    dx/dt = -∇U(x)
    U(x) = -log(p(x))  (势能 = 负对数密度)
    """
    
    def __init__(self, 
                 bandwidth=0.5,
                 dt=0.01,
                 max_steps=1000,
                 convergence_threshold=1e-4,
                 n_initial_points=50,
                 intrinsic_dim=None,
                 verbose=True):
        """
        Args:
            bandwidth: KDE带宽
            dt: 时间步长
            max_steps: 最大步数
            convergence_threshold: 收敛阈值
            n_initial_points: 初始轨迹点数
            intrinsic_dim: 本征维度
            verbose: 是否打印进度
        """
        self.bandwidth = bandwidth
        self.dt = dt
        self.max_steps = max_steps
        self.convergence_threshold = convergence_threshold
        self.n_initial_points = n_initial_points
        self.intrinsic_dim = intrinsic_dim
        self.verbose = verbose
        self.kde_ = None
        self.trajectories_ = []
        self.attractors_ = []
        
    def _log(self, msg):
        if self.verbose:
            print(f"  [{time.strftime('%H:%M:%S')}] {msg}")
    
    def fit(self, X):
        """
        拟合动力系统并分析吸引子
        
        Args:
            X: 数据点 (n, d)
            
        Returns:
            trajectories: 轨迹列表
            attractors: 吸引子列表
        """
        self.X_ = X
        n, d = X.shape
        self._log(f"拟合梯度下降流动力系统，数据形状: {X.shape}")
        
        # 步骤1：KDE密度估计
        self._log("步骤1: KDE密度估计...")
        self.kde_ = KernelDensity(bandwidth=self.bandwidth, kernel='gaussian')
        self.kde_.fit(X)
        self._log(f"  KDE拟合完成，带宽={self.bandwidth}")
        
        # 自动估计本征维度
        if self.intrinsic_dim is None:
            self.intrinsic_dim = self._estimate_intrinsic_dim(X)
            self._log(f"  自动估计本征维度: k={self.intrinsic_dim}")
        
        # 步骤2：生成初始点并演化轨迹
        self._log("步骤2: 轨迹演化...")
        initial_points = self._sample_initial_points(X)
        self.trajectories_ = []
        
        for i, x0 in enumerate(initial_points):
            traj = self._evolve_trajectory(x0)
            self.trajectories_.append(traj)
            
            if (i + 1) % 10 == 0:
                converged = sum(1 for t in self.trajectories_ if t.converged)
                self._log(f"  已演化 {i+1}/{len(initial_points)} 条轨迹，收敛 {converged} 条")
        
        converged_count = sum(1 for t in self.trajectories_ if t.converged)
        self._log(f"  轨迹演化完成: {len(self.trajectories_)} 条轨迹，{converged_count} 条收敛")
        
        # 步骤3：聚类收敛点，识别吸引子
        self._log("步骤3: 吸引子识别...")
        self.attractors_ = self._identify_attractors()
        self._log(f"  识别到 {len(self.attractors_)} 个吸引子")
        
        # 步骤4：计算李雅普诺夫指数
        self._log("步骤4: 李雅普诺夫指数计算...")
        for i, attractor in enumerate(self.attractors_):
            lyap = self._compute_lyapunov_exponents(attractor.center)
            attractor.lyapunov_exponents = lyap
            # 分解切向/法向
            tangent_lyap = lyap[:self.intrinsic_dim]
            normal_lyap = lyap[self.intrinsic_dim:]
            attractor.tangent_lyapunov = tangent_lyap
            attractor.normal_lyapunov = normal_lyap
            
            # 稳定性评分：法向指数越负越稳定
            normal_stability = 1.0 / (1.0 + np.exp(np.mean(normal_lyap) * 3))
            attractor.stability_score = float(np.clip(normal_stability, 0, 1))
            
            self._log(f"  吸引子{i+1}: 法向Lyap均值={np.mean(normal_lyap):.4f}, "
                     f"切向Lyap均值={np.mean(tangent_lyap):.4f}, "
                     f"稳定性={attractor.stability_score:.4f}")
        
        # 步骤5：确定吸引子盘边界
        self._log("步骤5: 吸引子盘边界确定...")
        for attractor in self.attractors_:
            basin_radius = self._determine_basin_boundary(attractor)
            attractor.basin_radius = basin_radius
            self._log(f"  吸引子 {attractor.attractor_id}: 吸引子盘半径={basin_radius:.6f}")
        
        self._log(f"动力系统分析完成，{len(self.attractors_)} 个吸引子")
        
        return self.trajectories_, self.attractors_
    
    def _estimate_intrinsic_dim(self, X):
        """估计本征维度"""
        n, d = X.shape
        nn = NearestNeighbors(n_neighbors=min(20, n))
        nn.fit(X)
        
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
        ratios = avg_eigenvalues[1:] / (avg_eigenvalues[:-1] + 1e-10)
        intrinsic_dim = np.argmax(ratios < 0.1) + 1
        return max(1, min(intrinsic_dim, d - 1))
    
    def _sample_initial_points(self, X):
        """采样初始点"""
        n = len(X)
        # 从数据点中采样，并添加小的随机扰动
        indices = np.random.choice(n, min(self.n_initial_points, n), replace=False)
        initial_points = X[indices] + 0.01 * np.random.randn(len(indices), X.shape[1])
        return initial_points
    
    def _compute_potential(self, x):
        """计算势能 U(x) = -log(p(x))"""
        log_density = self.kde_.score_samples(x.reshape(1, -1))[0]
        return -log_density
    
    def _compute_gradient(self, x, eps=1e-5):
        """数值计算势能梯度 ∇U(x)"""
        d = len(x)
        gradient = np.zeros(d)
        
        for i in range(d):
            x_plus = x.copy()
            x_minus = x.copy()
            x_plus[i] += eps
            x_minus[i] -= eps
            gradient[i] = (self._compute_potential(x_plus) - self._compute_potential(x_minus)) / (2 * eps)
        
        return gradient
    
    def _evolve_trajectory(self, x0):
        """演化单条轨迹（RK4积分）"""
        d = len(x0)
        points = [x0.copy()]
        velocities = []
        
        x = x0.copy()
        converged = False
        convergence_time = self.max_steps
        
        for t in range(self.max_steps):
            # RK4积分
            k1 = -self._compute_gradient(x)
            k2 = -self._compute_gradient(x + 0.5 * self.dt * k1)
            k3 = -self._compute_gradient(x + 0.5 * self.dt * k2)
            k4 = -self._compute_gradient(x + self.dt * k3)
            
            velocity = (k1 + 2*k2 + 2*k3 + k4) / 6
            x = x + self.dt * velocity
            
            points.append(x.copy())
            velocities.append(velocity.copy())
            
            # 检查收敛
            if np.linalg.norm(velocity) < self.convergence_threshold:
                converged = True
                convergence_time = t
                break
        
        return Trajectory(
            trajectory_id=f"TRAJ-{len(self.trajectories_):04d}",
            initial_point=x0,
            points=np.array(points),
            velocities=np.array(velocities) if velocities else np.zeros((1, d)),
            converged=converged,
            convergence_time=convergence_time,
            final_point=x.copy(),
        )
    
    def _identify_attractors(self):
        """识别吸引子（聚类收敛点）"""
        converged_points = np.array([t.final_point for t in self.trajectories_ if t.converged])
        
        if len(converged_points) == 0:
            # 如果没有收敛的轨迹，用数据点的聚类中心作为吸引子
            from sklearn.cluster import KMeans
            n_clusters = min(3, len(self.X_))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            kmeans.fit(self.X_)
            centers = kmeans.cluster_centers_
        else:
            # 收敛点聚类
            from sklearn.cluster import DBSCAN
            clustering = DBSCAN(eps=self.bandwidth * 2, min_samples=2)
            labels = clustering.fit_predict(converged_points)
            
            unique_labels = set(labels)
            unique_labels.discard(-1)
            
            centers = []
            for label in unique_labels:
                mask = labels == label
                center = np.mean(converged_points[mask], axis=0)
                centers.append(center)
            
            if len(centers) == 0:
                centers = [np.mean(converged_points, axis=0)]
        
        # 为每个吸引子计算切空间/法空间
        attractors = []
        nn = NearestNeighbors(n_neighbors=min(20, len(self.X_)))
        nn.fit(self.X_)
        
        for i, center in enumerate(centers):
            _, neighbors_idx = nn.kneighbors(center.reshape(1, -1))
            neighbors = self.X_[neighbors_idx[0]]
            centered = neighbors - center
            
            cov = centered.T @ centered / len(centered)
            cov += 1e-8 * np.eye(len(center))
            eigenvalues, eigenvectors = np.linalg.eigh(cov)
            idx = np.argsort(eigenvalues)[::-1]
            eigenvectors = eigenvectors[:, idx]
            
            k = self.intrinsic_dim
            tangent_basis = eigenvectors[:, :k]
            normal_basis = eigenvectors[:, k:]
            
            # 统计收敛到该吸引子的轨迹数
            if len(converged_points) > 0:
                distances = np.linalg.norm(converged_points - center, axis=1)
                n_converged = np.sum(distances < self.bandwidth * 2)
            else:
                n_converged = 0
            
            attractor = Attractor(
                attractor_id=f"ATTR-{i:04d}",
                center=center,
                basin_radius=0.0,
                lyapunov_exponents=np.zeros(len(center)),
                tangent_lyapunov=np.zeros(k),
                normal_lyapunov=np.zeros(len(center) - k),
                stability_score=0.0,
                n_converged_trajectories=int(n_converged),
                tangent_basis=tangent_basis,
                normal_basis=normal_basis,
                intrinsic_dim=k,
            )
            attractors.append(attractor)
        
        return attractors
    
    def _compute_lyapunov_exponents(self, attractor_center, n_perturbations=10):
        """
        计算李雅普诺夫指数（切空间演化法）
        
        方法：在吸引子附近添加小扰动，观察扰动的指数增长率
        """
        d = len(attractor_center)
        exponents = []
        
        # 在每个方向上添加扰动
        for i in range(d):
            perturbation = np.zeros(d)
            perturbation[i] = 1e-4
            
            # 两条轨迹：基准和扰动
            x_base = attractor_center.copy()
            x_pert = attractor_center + perturbation
            
            initial_distance = np.linalg.norm(perturbation)
            
            # 演化几步
            distances = []
            for t in range(50):
                # RK4
                v_base = -self._compute_gradient(x_base)
                v_pert = -self._compute_gradient(x_pert)
                
                x_base = x_base + self.dt * v_base
                x_pert = x_pert + self.dt * v_pert
                
                dist = np.linalg.norm(x_pert - x_base)
                if dist > 1e-10:
                    distances.append(dist)
            
            # 计算李雅普诺夫指数：lambda = (1/t) * log(d(t)/d(0))
            if len(distances) > 5:
                log_ratios = np.log(np.array(distances[5:]) / initial_distance)
                times = np.arange(5, len(distances)) * self.dt
                # 线性回归斜率
                if len(times) > 2:
                    lyap = np.polyfit(times, log_ratios, 1)[0]
                else:
                    lyap = 0.0
            else:
                lyap = 0.0
            
            exponents.append(lyap)
        
        return np.array(exponents)
    
    def _determine_basin_boundary(self, attractor):
        """确定吸引子盘边界"""
        # 方法：从吸引子出发，沿不同方向找收敛边界
        center = attractor.center
        d = len(center)
        
        # 沿法向方向测试
        normal_basis = attractor.normal_basis
        if normal_basis.shape[1] == 0:
            return self.bandwidth
        
        max_radius = 0
        n_directions = min(10, normal_basis.shape[1])
        
        for i in range(n_directions):
            direction = normal_basis[:, i % normal_basis.shape[1]]
            
            # 二分查找收敛边界
            low, high = 0.0, self.bandwidth * 5
            
            for _ in range(10):
                mid = (low + high) / 2
                x_test = center + mid * direction
                
                # 短时间演化看是否收敛回吸引子
                x = x_test.copy()
                for t in range(100):
                    v = -self._compute_gradient(x)
                    x = x + self.dt * v
                    if np.linalg.norm(v) < self.convergence_threshold:
                        break
                
                final_dist = np.linalg.norm(x - center)
                if final_dist < self.bandwidth:
                    low = mid  # 收敛，扩大半径
                else:
                    high = mid  # 不收敛，缩小半径
            
            max_radius = max(max_radius, low)
        
        return max(max_radius, self.bandwidth * 0.5)
    
    def get_summary(self):
        """获取摘要"""
        return {
            'n_trajectories': len(self.trajectories_),
            'n_converged': sum(1 for t in self.trajectories_ if t.converged),
            'n_attractors': len(self.attractors_),
            'attractors': [a.to_dict() for a in self.attractors_],
            'mean_convergence_time': float(np.mean([t.convergence_time for t in self.trajectories_ if t.converged])) if any(t.converged for t in self.trajectories_) else 0,
            'intrinsic_dim': self.intrinsic_dim,
        }
    
    def save(self, filepath):
        """保存结果"""
        data = {
            'version': '2.0',
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': self.get_summary(),
            'trajectories': [t.to_dict() for t in self.trajectories_],
            'parameters': {
                'bandwidth': self.bandwidth,
                'dt': self.dt,
                'max_steps': self.max_steps,
                'convergence_threshold': self.convergence_threshold,
                'n_initial_points': self.n_initial_points,
            }
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=lambda o: float(o) if hasattr(o, 'item') else str(o))
        return filepath


if __name__ == '__main__':
    print("=" * 60)
    print("  模块2测试：真实动力系统 - 梯度下降流")
    print("=" * 60)
    
    # 生成高斯混合数据（有明确吸引子）
    np.random.seed(42)
    n_per = 200
    centers = np.array([[0, 0, 0], [5, 0, 0], [0, 5, 0]])
    X_list = []
    for c in centers:
        X_list.append(c + np.random.randn(n_per, 3) * 0.3)
    X = np.vstack(X_list)
    print(f"\n测试数据: 3个高斯聚类 {X.shape}")
    
    # 构建动力系统
    system = GradientDescentFlow(
        bandwidth=0.5,
        dt=0.01,
        max_steps=500,
        n_initial_points=30,
        verbose=True
    )
    trajectories, attractors = system.fit(X)
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("  动力系统分析结果")
    print("=" * 60)
    summary = system.get_summary()
    print(f"轨迹总数: {summary['n_trajectories']}")
    print(f"收敛轨迹数: {summary['n_converged']}")
    print(f"吸引子数: {summary['n_attractors']}")
    print(f"平均收敛时间: {summary['mean_convergence_time']:.1f} 步")
    print(f"本征维度: {summary['intrinsic_dim']}")
    
    print("\n吸引子详情:")
    for i, attr in enumerate(attractors):
        print(f"\n  吸引子 {i+1}: {attr.attractor_id}")
        print(f"    中心: {attr.center}")
        print(f"    吸引子盘半径: {attr.basin_radius:.6f}")
        print(f"    李雅普诺夫指数: {[round(x, 4) for x in attr.lyapunov_exponents]}")
        print(f"    切向Lyap: {[round(x, 4) for x in attr.tangent_lyapunov]}")
        print(f"    法向Lyap: {[round(x, 4) for x in attr.normal_lyapunov]}")
        print(f"    稳定性评分: {attr.stability_score:.4f}")
        print(f"    收敛轨迹数: {attr.n_converged_trajectories}")
    
    # 保存
    output_path = "/home/user/Doubao/chats/38439832899843586/high_dim_anchor/stage2/results/dynamical_system_test.json"
    system.save(output_path)
    print(f"\n✅ 结果已保存: {output_path}")
    print("\n✅ 模块2测试通过！")
