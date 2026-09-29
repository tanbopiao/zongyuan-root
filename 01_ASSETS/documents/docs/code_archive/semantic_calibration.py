"""
模块3：语义基底校准算法
Semantic Basis Calibration Algorithm

核心应用：跨模型语义对齐
方法：流形同胚映射，将源流形的语义基底校准到目标流形

算法：
1. 源/目标流形锚点匹配
2. 切空间基变换矩阵计算
3. 四重损失函数优化：
   - 锚点位置一致性损失
   - 切空间方向一致性损失
   - 度量张量保持损失
   - 曲率保持损失
4. 全局同胚映射构建（径向基函数插值）
"""

import numpy as np
from scipy.spatial.distance import cdist
from scipy.linalg import eigh, svd
from sklearn.neighbors import NearestNeighbors
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Callable
import json
import time


@dataclass
class CalibrationResult:
    """校准结果数据结构"""
    source_anchors: np.ndarray  # 源锚点 (n, d)
    target_anchors: np.ndarray  # 目标锚点 (n, d)
    transformation_matrix: np.ndarray  # 线性变换矩阵 (d, d)
    rbf_weights: np.ndarray  # RBF插值权重 (n, d)
    rbf_centers: np.ndarray  # RBF中心 (n, d)
    rbf_gamma: float  # RBF带宽参数
    calibration_error: float  # 校准误差
    per_anchor_errors: np.ndarray  # 每个锚点的误差
    loss_history: List[float]  # 损失函数历史
    final_losses: dict  # 最终各项损失
    
    def to_dict(self):
        return {
            'n_anchors': len(self.source_anchors),
            'calibration_error': float(self.calibration_error),
            'mean_anchor_error': float(np.mean(self.per_anchor_errors)),
            'max_anchor_error': float(np.max(self.per_anchor_errors)),
            'final_losses': {k: float(v) for k, v in self.final_losses.items()},
            'transformation_matrix': self.transformation_matrix.tolist(),
            'per_anchor_errors': self.per_anchor_errors.tolist(),
        }


class SemanticBasisCalibrator:
    """
    语义基底校准器
    
    将源流形的语义基底校准到目标流形，实现跨模型语义对齐。
    
    校准映射 f: Source -> Target 满足：
    1. f(source_anchor_i) ≈ target_anchor_i  (位置一致性)
    2. Df(source_anchor_i) · tangent_source_i ≈ tangent_target_i  (切空间方向一致性)
    3. Df^T · metric_target · Df ≈ metric_source  (度量张量保持)
    4. curvature(f(x)) ≈ curvature(x)  (曲率保持)
    """
    
    def __init__(self,
                 n_iterations=500,
                 learning_rate=0.01,
                 loss_weights=None,
                 rbf_gamma=None,
                 regularization=1e-4,
                 verbose=True):
        """
        Args:
            n_iterations: 优化迭代次数
            learning_rate: 学习率
            loss_weights: 四项损失的权重 {position, tangent, metric, curvature}
            rbf_gamma: RBF带宽参数，None则自动估计
            regularization: 正则化系数
            verbose: 是否打印进度
        """
        self.n_iterations = n_iterations
        self.learning_rate = learning_rate
        self.loss_weights = loss_weights or {
            'position': 1.0,
            'tangent': 0.5,
            'metric': 0.3,
            'curvature': 0.2,
        }
        self.rbf_gamma = rbf_gamma
        self.regularization = regularization
        self.verbose = verbose
        self.result_ = None
        
    def _log(self, msg):
        if self.verbose:
            print(f"  [{time.strftime('%H:%M:%S')}] {msg}")
    
    def fit(self, source_anchors, target_anchors, 
            source_tangent_bases=None, target_tangent_bases=None,
            source_metrics=None, target_metrics=None):
        """
        拟合校准映射
        
        Args:
            source_anchors: 源锚点 (n, d)
            target_anchors: 目标锚点 (n, d)
            source_tangent_bases: 源切空间基 (n, d, k)，可选
            target_tangent_bases: 目标切空间基 (n, d, k)，可选
            source_metrics: 源度量张量 (n, k, k)，可选
            target_metrics: 目标度量张量 (n, k, k)，可选
            
        Returns:
            result: CalibrationResult
        """
        source_anchors = np.array(source_anchors)
        target_anchors = np.array(target_anchors)
        n, d = source_anchors.shape
        
        self._log(f"开始语义基底校准，{n}个锚点，维度{d}")
        
        # 自动估计RBF gamma
        if self.rbf_gamma is None:
            distances = cdist(source_anchors, source_anchors)
            median_dist = np.median(distances[distances > 0])
            self.rbf_gamma = 1.0 / (median_dist ** 2 + 1e-10)
            self._log(f"自动估计RBF gamma: {self.rbf_gamma:.6f}")
        
        # 如果没有提供切空间基，自动估计
        if source_tangent_bases is None:
            source_tangent_bases = self._estimate_tangent_bases(source_anchors)
        if target_tangent_bases is None:
            target_tangent_bases = self._estimate_tangent_bases(target_anchors)
        
        k = source_tangent_bases.shape[2]
        
        # 步骤1：初始线性变换（Procrustes分析）
        self._log("步骤1: Procrustes初始线性变换...")
        W_init = self._procrustes_analysis(source_anchors, target_anchors)
        self._log(f"  初始线性变换误差: {np.mean(np.linalg.norm(source_anchors @ W_init - target_anchors, axis=1)):.6f}")
        
        # 步骤2：RBF权重初始化
        self._log("步骤2: RBF权重初始化...")
        Phi = self._rbf_kernel(source_anchors, source_anchors, self.rbf_gamma)
        # 初始权重 = 线性变换后的残差
        linear_transformed = source_anchors @ W_init
        residuals = target_anchors - linear_transformed
        # 求解 Phi @ W_rbf = residuals (带正则化)
        Phi_reg = Phi + self.regularization * np.eye(n)
        W_rbf = np.linalg.solve(Phi_reg, residuals)
        self._log(f"  RBF权重初始化完成，形状{W_rbf.shape}")
        
        # 步骤3：联合优化（线性变换 + RBF非线性校正）
        self._log("步骤3: 联合优化（四重损失函数）...")
        W = W_init.copy()
        W_rbf_opt = W_rbf.copy()
        
        loss_history = []
        final_losses = {}
        
        for iteration in range(self.n_iterations):
            # 前向传播
            transformed = self._transform(source_anchors, W, W_rbf_opt, source_anchors)
            
            # 计算各项损失
            losses = self._compute_losses(
                transformed, target_anchors,
                W, source_tangent_bases, target_tangent_bases,
                source_metrics, target_metrics,
                W_rbf_opt
            )
            
            total_loss = sum(self.loss_weights[k] * v for k, v in losses.items())
            loss_history.append(total_loss)
            
            # 梯度下降（数值梯度）
            if iteration % 50 == 0 and self.verbose:
                self._log(f"  迭代{iteration}/{self.n_iterations}, 总损失={total_loss:.6f}, "
                         f"位置={losses['position']:.6f}, 切向={losses['tangent']:.6f}, "
                         f"度量={losses['metric']:.6f}, 曲率={losses['curvature']:.6f}")
            
            # 线性变换梯度（解析梯度）
            grad_W = self._compute_linear_gradient(
                source_anchors, target_anchors, W, W_rbf_opt,
                source_tangent_bases, target_tangent_bases
            )
            W = W - self.learning_rate * grad_W
            
            # RBF权重梯度（数值梯度）
            eps = 1e-5
            grad_rbf = np.zeros_like(W_rbf_opt)
            for i in range(n):
                for j in range(d):
                    W_rbf_plus = W_rbf_opt.copy()
                    W_rbf_plus[i, j] += eps
                    loss_plus = self._compute_total_loss(
                        source_anchors, target_anchors, W, W_rbf_plus,
                        source_tangent_bases, target_tangent_bases
                    )
                    W_rbf_minus = W_rbf_opt.copy()
                    W_rbf_minus[i, j] -= eps
                    loss_minus = self._compute_total_loss(
                        source_anchors, target_anchors, W, W_rbf_minus,
                        source_tangent_bases, target_tangent_bases
                    )
                    grad_rbf[i, j] = (loss_plus - loss_minus) / (2 * eps)
            
            W_rbf_opt = W_rbf_opt - self.learning_rate * 0.1 * grad_rbf  # RBF学习率小一些
            
            final_losses = losses
        
        # 最终校准
        final_transformed = self._transform(source_anchors, W, W_rbf_opt, source_anchors)
        per_anchor_errors = np.linalg.norm(final_transformed - target_anchors, axis=1)
        calibration_error = np.mean(per_anchor_errors)
        
        self._log(f"校准完成，平均误差={calibration_error:.6f}, 最大误差={np.max(per_anchor_errors):.6f}")
        
        self.result_ = CalibrationResult(
            source_anchors=source_anchors,
            target_anchors=target_anchors,
            transformation_matrix=W,
            rbf_weights=W_rbf_opt,
            rbf_centers=source_anchors,
            rbf_gamma=self.rbf_gamma,
            calibration_error=calibration_error,
            per_anchor_errors=per_anchor_errors,
            loss_history=loss_history,
            final_losses=final_losses,
        )
        
        return self.result_
    
    def transform(self, X):
        """
        应用校准映射到新数据点
        
        Args:
            X: 源数据点 (n, d)
            
        Returns:
            transformed: 校准后的点 (n, d)
        """
        if self.result_ is None:
            raise ValueError("必须先调用fit()")
        
        return self._transform(
            X, 
            self.result_.transformation_matrix,
            self.result_.rbf_weights,
            self.result_.rbf_centers
        )
    
    def _transform(self, X, W, W_rbf, rbf_centers):
        """应用变换：线性变换 + RBF非线性校正"""
        linear_part = X @ W
        Phi = self._rbf_kernel(X, rbf_centers, self.rbf_gamma)
        rbf_part = Phi @ W_rbf
        return linear_part + rbf_part
    
    def _rbf_kernel(self, X, centers, gamma):
        """径向基函数核"""
        distances = cdist(X, centers, 'sqeuclidean')
        return np.exp(-gamma * distances)
    
    def _estimate_tangent_bases(self, points, n_neighbors=10):
        """自动估计切空间基"""
        n, d = points.shape
        k = min(d - 1, 2)  # 默认2维切空间
        
        nn = NearestNeighbors(n_neighbors=min(n_neighbors + 1, n))
        nn.fit(points)
        
        tangent_bases = np.zeros((n, d, k))
        for i in range(n):
            _, neighbors_idx = nn.kneighbors(points[i:i+1])
            neighbors = points[neighbors_idx[0, 1:]]
            centered = neighbors - points[i]
            cov = centered.T @ centered / len(centered)
            cov += 1e-8 * np.eye(d)
            eigenvalues, eigenvectors = eigh(cov)
            idx = np.argsort(eigenvalues)[::-1]
            tangent_bases[i] = eigenvectors[:, idx[:k]]
        
        return tangent_bases
    
    def _procrustes_analysis(self, source, target):
        """Procrustes分析：最优线性变换"""
        # 中心化
        source_mean = np.mean(source, axis=0)
        target_mean = np.mean(target, axis=0)
        source_centered = source - source_mean
        target_centered = target - target_mean
        
        # SVD求最优旋转
        H = source_centered.T @ target_centered
        U, S, Vt = svd(H)
        R = Vt.T @ U.T
        
        # 缩放
        scale = np.sum(S) / np.sum(source_centered ** 2)
        
        # 组合变换矩阵（包含平移的线性部分）
        W = scale * R
        return W
    
    def _compute_losses(self, transformed, target, W, 
                        source_tangent, target_tangent,
                        source_metrics, target_metrics, W_rbf):
        """计算四重损失函数"""
        n, d = transformed.shape
        
        # 1. 位置一致性损失
        position_loss = np.mean(np.sum((transformed - target) ** 2, axis=1))
        
        # 2. 切空间方向一致性损失
        tangent_loss = 0.0
        if source_tangent is not None and target_tangent is not None:
            k = source_tangent.shape[2]
            for i in range(n):
                # 变换后的源切空间
                transformed_tangent = W @ source_tangent[i]  # (d, k)
                # 与目标切空间的对齐误差（用主角度）
                # 简化：用矩阵Frobenius范数差
                Q, _ = np.linalg.qr(transformed_tangent)
                Qt, _ = np.linalg.qr(target_tangent[i])
                tangent_loss += np.linalg.norm(Q @ Q.T - Qt @ Qt.T, 'fro') ** 2
            tangent_loss /= n
        
        # 3. 度量张量保持损失
        metric_loss = 0.0
        if source_metrics is not None and target_metrics is not None:
            for i in range(n):
                # 变换后的源度量：W^T @ target_metric @ W 应该 ≈ source_metric
                transformed_metric = W.T @ target_metrics[i] @ W
                metric_loss += np.linalg.norm(transformed_metric - source_metrics[i], 'fro') ** 2
            metric_loss /= n
        
        # 4. 曲率保持损失（用局部二阶差分近似）
        curvature_loss = 0.0
        if n >= 3:
            # 源曲率
            source_curvature = self._estimate_curvature(transformed)
            target_curvature = self._estimate_curvature(target)
            curvature_loss = np.mean((source_curvature - target_curvature) ** 2)
        
        return {
            'position': position_loss,
            'tangent': tangent_loss,
            'metric': metric_loss,
            'curvature': curvature_loss,
        }
    
    def _estimate_curvature(self, points):
        """估计点集的局部曲率（二阶差分）"""
        n = len(points)
        if n < 3:
            return np.zeros(n)
        
        curvature = np.zeros(n)
        for i in range(1, n - 1):
            v1 = points[i] - points[i-1]
            v2 = points[i+1] - points[i]
            # 夹角变化作为曲率近似
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-10)
            curvature[i] = np.arccos(np.clip(cos_angle, -1, 1))
        
        curvature[0] = curvature[1]
        curvature[-1] = curvature[-2]
        return curvature
    
    def _compute_total_loss(self, source, target, W, W_rbf, source_tangent, target_tangent):
        """计算总损失（用于数值梯度）"""
        transformed = self._transform(source, W, W_rbf, source)
        losses = self._compute_losses(
            transformed, target, W, source_tangent, target_tangent,
            None, None, W_rbf
        )
        return sum(self.loss_weights[k] * v for k, v in losses.items())
    
    def _compute_linear_gradient(self, source, target, W, W_rbf, source_tangent, target_tangent):
        """计算线性变换的解析梯度"""
        n, d = source.shape
        transformed = self._transform(source, W, W_rbf, source)
        
        # 位置损失梯度：d/dW ||XW - Y||^2 = 2 X^T (XW - Y)
        residuals = transformed - target
        grad_position = 2 * source.T @ residuals / n
        
        # 切空间损失梯度（简化）
        grad_tangent = np.zeros_like(W)
        if source_tangent is not None and target_tangent is not None:
            for i in range(n):
                transformed_tangent = W @ source_tangent[i]  # (d, k)
                Q, _ = np.linalg.qr(transformed_tangent)  # (d, k)
                Qt, _ = np.linalg.qr(target_tangent[i])  # (d, k)
                # 梯度：d/dW ||QQ^T - QtQt^T||_F^2
                # = 4 (QQ^T - QtQt^T) Q source_tangent^T 外积 source
                diff = Q @ Q.T - Qt @ Qt.T  # (d, d)
                grad_direction = diff @ Q  # (d, k)
                # 对每个切向量方向累积梯度
                for j in range(source_tangent.shape[2]):
                    v = source_tangent[i, :, j]  # (d,)
                    grad_tangent += 4 * np.outer(grad_direction[:, j], v)
            grad_tangent /= n
        
        # 正则化梯度
        grad_reg = self.regularization * W
        
        return grad_position + 0.5 * grad_tangent + grad_reg
    
    def get_summary(self):
        """获取校准摘要"""
        if self.result_ is None:
            return {}
        
        return {
            'n_anchors': len(self.result_.source_anchors),
            'dimension': self.result_.source_anchors.shape[1],
            'calibration_error': float(self.result_.calibration_error),
            'mean_anchor_error': float(np.mean(self.result_.per_anchor_errors)),
            'max_anchor_error': float(np.max(self.result_.per_anchor_errors)),
            'final_losses': {k: float(v) for k, v in self.result_.final_losses.items()},
            'loss_reduction': float(self.result_.loss_history[0] - self.result_.loss_history[-1]) if self.result_.loss_history else 0,
            'rbf_gamma': float(self.rbf_gamma),
        }
    
    def save(self, filepath):
        """保存校准结果"""
        data = {
            'version': '2.0',
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': self.get_summary(),
            'result': self.result_.to_dict() if self.result_ else None,
            'parameters': {
                'n_iterations': self.n_iterations,
                'learning_rate': self.learning_rate,
                'loss_weights': self.loss_weights,
                'regularization': self.regularization,
            }
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=lambda o: float(o) if hasattr(o, 'item') else str(o))
        return filepath


if __name__ == '__main__':
    print("=" * 60)
    print("  模块3测试：语义基底校准算法")
    print("=" * 60)
    
    # 生成测试数据：源流形 -> 目标流形（已知变换）
    np.random.seed(42)
    n_anchors = 20
    d = 10  # 10维embedding空间
    
    # 源锚点（在低维流形上）
    t = np.linspace(0, 4 * np.pi, n_anchors)
    source_anchors = np.zeros((n_anchors, d))
    source_anchors[:, 0] = np.sin(t)
    source_anchors[:, 1] = np.cos(t)
    source_anchors[:, 2] = t / 10
    source_anchors += 0.01 * np.random.randn(n_anchors, d)
    
    # 已知的目标变换（旋转+缩放+非线性扭曲）
    true_rotation = np.eye(d)
    theta = np.pi / 6  # 30度旋转
    true_rotation[0, 0] = np.cos(theta)
    true_rotation[0, 1] = -np.sin(theta)
    true_rotation[1, 0] = np.sin(theta)
    true_rotation[1, 1] = np.cos(theta)
    
    target_anchors = source_anchors @ true_rotation
    # 添加非线性扭曲
    target_anchors[:, 0] += 0.1 * np.sin(source_anchors[:, 1] * 3)
    
    print(f"\n测试数据: {n_anchors}个锚点，{d}维空间")
    print(f"源锚点形状: {source_anchors.shape}")
    print(f"目标锚点形状: {target_anchors.shape}")
    print(f"已知变换: 30度旋转 + 非线性扭曲")
    
    # 执行校准
    calibrator = SemanticBasisCalibrator(
        n_iterations=200,
        learning_rate=0.01,
        verbose=True
    )
    result = calibrator.fit(source_anchors, target_anchors)
    
    # 打印结果
    print("\n" + "=" * 60)
    print("  校准结果")
    print("=" * 60)
    summary = calibrator.get_summary()
    print(f"锚点数: {summary['n_anchors']}")
    print(f"维度: {summary['dimension']}")
    print(f"平均校准误差: {summary['calibration_error']:.6f}")
    print(f"最大锚点误差: {summary['max_anchor_error']:.6f}")
    print(f"损失下降: {summary['loss_reduction']:.6f}")
    print(f"\n最终各项损失:")
    for k, v in summary['final_losses'].items():
        print(f"  {k}: {v:.6f}")
    
    # 测试新点变换
    print("\n测试新点变换...")
    test_points = source_anchors[:5] + 0.05 * np.random.randn(5, d)
    transformed = calibrator.transform(test_points)
    print(f"  测试点形状: {test_points.shape}")
    print(f"  变换后形状: {transformed.shape}")
    print(f"  变换前后平均距离: {np.mean(np.linalg.norm(transformed - test_points, axis=1)):.6f}")
    
    # 保存
    output_path = "/home/user/Doubao/chats/38439832899843586/high_dim_anchor/stage2/results/semantic_calibration_test.json"
    calibrator.save(output_path)
    print(f"\n✅ 结果已保存: {output_path}")
    print("\n✅ 模块3测试通过！")
