"""
吸引子盘理论验证实验
Attractor Basin Theory Verification Experiment

验证内容：
1. 黎曼流形假设验证：测地线距离 vs 欧氏距离
2. 吸引子存在性验证：提取的锚点是否为稳态吸引子
3. 吸引子盘估计验证：估计的盘半径是否准确
4. 切空间/法空间分解验证
5. 李雅普诺夫稳定性验证
6. 高维锚点维度估计准确性
"""

import numpy as np
import sys
import os
import json
import time
from datetime import datetime

# 添加src路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from riemannian_manifold import (
    RiemannianMetric, TangentSpace, GeodesicCalculator, 
    CurvatureEstimator, compute_pairwise_geodesic_distances
)
from high_dim_anchor import HighDimensionalAnchorExtractor, HighDimensionalAnchor

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from sklearn.datasets import make_swiss_roll, make_s_curve
from sklearn.neighbors import NearestNeighbors
from scipy.spatial.distance import pdist, squareform


class SyntheticDatasetGenerator:
    """合成数据集生成器"""
    
    @staticmethod
    def swiss_roll(n_samples=1000, noise=0.1, seed=42):
        """瑞士卷（2维流形嵌入3维空间）"""
        X, t = make_swiss_roll(n_samples=n_samples, noise=noise, random_state=seed)
        return X, {'name': 'swiss_roll', 'intrinsic_dim': 2, 'n_samples': n_samples}
    
    @staticmethod
    def s_curve(n_samples=1000, noise=0.1, seed=42):
        """S形曲线（2维流形嵌入3维空间）"""
        X, t = make_s_curve(n_samples=n_samples, noise=noise, random_state=seed)
        return X, {'name': 's_curve', 'intrinsic_dim': 2, 'n_samples': n_samples}
    
    @staticmethod
    def torus(n_samples=1000, R=2, r=1, noise=0.05, seed=42):
        """环面（2维流形嵌入3维空间）"""
        np.random.seed(seed)
        u = np.random.uniform(0, 2*np.pi, n_samples)
        v = np.random.uniform(0, 2*np.pi, n_samples)
        X = np.column_stack([
            (R + r * np.cos(v)) * np.cos(u),
            (R + r * np.cos(v)) * np.sin(u),
            r * np.sin(v)
        ]) + noise * np.random.randn(n_samples, 3)
        return X, {'name': 'torus', 'intrinsic_dim': 2, 'n_samples': n_samples}
    
    @staticmethod
    def sphere(n_samples=1000, radius=1, noise=0.05, seed=42):
        """球面（2维流形嵌入3维空间）"""
        np.random.seed(seed)
        phi = np.random.uniform(0, np.pi, n_samples)
        theta = np.random.uniform(0, 2*np.pi, n_samples)
        X = np.column_stack([
            radius * np.sin(phi) * np.cos(theta),
            radius * np.sin(phi) * np.sin(theta),
            radius * np.cos(phi)
        ]) + noise * np.random.randn(n_samples, 3)
        return X, {'name': 'sphere', 'intrinsic_dim': 2, 'n_samples': n_samples}
    
    @staticmethod
    def gaussian_mixture(n_samples=1000, n_clusters=3, n_dims=3, seed=42):
        """高斯混合（多个0维锚点）"""
        np.random.seed(seed)
        centers = np.random.randn(n_clusters, n_dims) * 5
        X = []
        for i in range(n_clusters):
            n_i = n_samples // n_clusters
            X.append(centers[i] + np.random.randn(n_i, n_dims) * 0.5)
        X = np.vstack(X)
        return X, {'name': 'gaussian_mixture', 'intrinsic_dim': 0, 
                   'n_clusters': n_clusters, 'n_samples': n_samples}
    
    @staticmethod
    def circle_1d(n_samples=500, radius=3, noise=0.1, seed=42):
        """1维圆环（1维流形嵌入2维/3维空间）"""
        np.random.seed(seed)
        theta = np.random.uniform(0, 2*np.pi, n_samples)
        X = np.column_stack([
            radius * np.cos(theta),
            radius * np.sin(theta),
            np.zeros(n_samples)
        ]) + noise * np.random.randn(n_samples, 3)
        return X, {'name': 'circle_1d', 'intrinsic_dim': 1, 'n_samples': n_samples}


class AttractorBasinVerifier:
    """吸引子盘验证器"""
    
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.results = {}
        
    def _log(self, msg):
        if self.verbose:
            print(f"    {msg}")
    
    def verify_geodesic_vs_euclidean(self, X, info):
        """
        验证1：测地线距离 vs 欧氏距离
        假设：在弯曲流形上，测地线距离应大于欧氏距离，且比值反映曲率
        """
        self._log("验证1: 测地线距离 vs 欧氏距离...")
        
        n = len(X)
        sample_size = min(200, n)
        idx = np.random.choice(n, sample_size, replace=False)
        X_sample = X[idx]
        
        # 欧氏距离
        euclidean_dist = squareform(pdist(X_sample))
        
        # 测地线距离（Isomap近似）
        geodesic_dist = compute_pairwise_geodesic_distances(X_sample, n_neighbors=10)
        
        # 计算比值
        valid = (euclidean_dist > 1e-8) & (geodesic_dist > 1e-8)
        ratio = geodesic_dist[valid] / euclidean_dist[valid]
        
        result = {
            'mean_ratio': float(np.mean(ratio)),
            'median_ratio': float(np.median(ratio)),
            'max_ratio': float(np.max(ratio)),
            'min_ratio': float(np.min(ratio)),
            'ratio_std': float(np.std(ratio)),
            'geodesic_gt_euclidean_ratio': float(np.mean(ratio > 1.01)),
            'interpretation': ''
        }
        
        if result['mean_ratio'] > 1.1:
            result['interpretation'] = '流形弯曲明显，测地线距离显著大于欧氏距离，黎曼流形假设成立'
        elif result['mean_ratio'] > 1.01:
            result['interpretation'] = '流形有一定弯曲，测地线距离略大于欧氏距离'
        else:
            result['interpretation'] = '流形近似平坦，测地线距离与欧氏距离接近'
        
        self._log(f"  平均比值: {result['mean_ratio']:.4f}")
        self._log(f"  测地线>欧氏比例: {result['geodesic_gt_euclidean_ratio']*100:.1f}%")
        self._log(f"  结论: {result['interpretation']}")
        
        return result
    
    def verify_anchor_extraction(self, X, info):
        """
        验证2：高维锚点提取
        验证提取的锚点维度是否与真实本征维度一致
        """
        self._log("验证2: 高维锚点提取与维度估计...")
        
        extractor = HighDimensionalAnchorExtractor(
            n_neighbors=15, min_samples=10, max_dimension=5, verbose=False
        )
        anchors = extractor.fit(X)
        
        true_dim = info.get('intrinsic_dim', 2)
        estimated_dims = [a.dimension for a in anchors]
        
        result = {
            'n_anchors_extracted': len(anchors),
            'true_intrinsic_dim': true_dim,
            'estimated_dims': estimated_dims,
            'mean_estimated_dim': float(np.mean(estimated_dims)) if estimated_dims else 0,
            'dim_accuracy': float(np.mean([abs(d - true_dim) <= 1 for d in estimated_dims])) if estimated_dims else 0,
            'anchor_stabilities': [float(a.stability_score) for a in anchors],
            'mean_stability': float(np.mean([a.stability_score for a in anchors])) if anchors else 0,
            'basin_radii': [float(a.basin_radius) for a in anchors],
        }
        
        self._log(f"  提取锚点数: {result['n_anchors_extracted']}")
        self._log(f"  真实维度: {true_dim}, 估计维度: {estimated_dims}")
        self._log(f"  维度估计准确率(±1): {result['dim_accuracy']*100:.1f}%")
        self._log(f"  平均稳定性评分: {result['mean_stability']:.4f}")
        
        return result, anchors
    
    def verify_attractor_basin(self, X, anchors, info):
        """
        验证3：吸引子盘验证
        验证锚点周围的点是否会"收敛"到锚点（用密度梯度模拟）
        """
        self._log("验证3: 吸引子盘验证...")
        
        n = len(X)
        results = []
        
        for anchor_idx, anchor in enumerate(anchors[:3]):  # 只验证前3个锚点
            center = anchor.center_point
            basin_r = anchor.basin_radius
            
            # 计算所有点到锚点中心的距离
            dists = np.linalg.norm(X - center, axis=1)
            
            # 盘内点和盘外点
            inside_mask = dists < basin_r
            outside_mask = ~inside_mask
            
            n_inside = np.sum(inside_mask)
            n_outside = np.sum(outside_mask)
            
            # 验证：盘内点密度应高于盘外（吸引子区域密度高）
            if n_inside > 0 and n_outside > 0:
                # 计算局部密度
                nn = NearestNeighbors(n_neighbors=5)
                nn.fit(X)
                densities = 1.0 / (nn.kneighbors(X)[0][:, -1] + 1e-8)
                
                density_inside = np.mean(densities[inside_mask])
                density_outside = np.mean(densities[outside_mask])
                density_ratio = density_inside / (density_outside + 1e-10)
            else:
                density_ratio = 1.0
            
            # 验证：法向距离分布
            T = np.column_stack(anchor.tangent_basis)
            N = np.column_stack(anchor.normal_basis)
            diffs = X - center
            normal_dists = np.linalg.norm(diffs @ N, axis=1)
            tangent_dists = np.linalg.norm(diffs @ T, axis=1)
            
            # 盘内点的法向距离应较小
            if n_inside > 0:
                mean_normal_inside = np.mean(normal_dists[inside_mask])
                mean_tangent_inside = np.mean(tangent_dists[inside_mask])
                normal_tangent_ratio = mean_normal_inside / (mean_tangent_inside + 1e-10)
            else:
                normal_tangent_ratio = 1.0
            
            result = {
                'anchor_idx': anchor_idx,
                'anchor_name': anchor.name,
                'basin_radius': float(basin_r),
                'n_inside': int(n_inside),
                'n_outside': int(n_outside),
                'inside_ratio': float(n_inside / n),
                'density_ratio_inside_outside': float(density_ratio),
                'normal_tangent_ratio_inside': float(normal_tangent_ratio),
                'basin_valid': bool(density_ratio > 1.1 and normal_tangent_ratio < 0.8)
            }
            results.append(result)
            
            self._log(f"  锚点{anchor_idx+1}: 盘内点数={n_inside}({result['inside_ratio']*100:.1f}%), "
                     f"密度比={density_ratio:.2f}, 法切比={normal_tangent_ratio:.3f}, "
                     f"有效={'✅' if result['basin_valid'] else '⚠️'}")
        
        return results
    
    def verify_lyapunov_stability(self, X, anchors, info):
        """
        验证4：李雅普诺夫稳定性验证
        法向李雅普诺夫指数应为负（稳定），切向可为零或微正
        """
        self._log("验证4: 李雅普诺夫稳定性验证...")
        
        results = []
        for anchor_idx, anchor in enumerate(anchors[:3]):
            lyap = anchor.lyapunov_exponents
            k = anchor.dimension
            d = X.shape[1]
            
            # 切向指数（前k个）和法向指数（后d-k个）
            tangent_lyap = lyap[:k]
            normal_lyap = lyap[k:]
            
            result = {
                'anchor_idx': anchor_idx,
                'tangent_lyapunov': [float(x) for x in tangent_lyap],
                'normal_lyapunov': [float(x) for x in normal_lyap],
                'mean_tangent_lyap': float(np.mean(tangent_lyap)),
                'mean_normal_lyap': float(np.mean(normal_lyap)),
                'normal_negative_ratio': float(np.mean([x < 0 for x in normal_lyap])),
                'tangent_near_zero_ratio': float(np.mean([abs(x) < 0.5 for x in tangent_lyap])),
                'stability_score': float(anchor.stability_score),
                'stable': bool(np.mean(normal_lyap) < 0 and anchor.stability_score > 0.3)
            }
            results.append(result)
            
            self._log(f"  锚点{anchor_idx+1}: 法向Lyap均值={result['mean_normal_lyap']:.4f}, "
                     f"切向Lyap均值={result['mean_tangent_lyap']:.4f}, "
                     f"稳定性={anchor.stability_score:.3f}, "
                     f"稳定={'✅' if result['stable'] else '⚠️'}")
        
        return results
    
    def verify_tangent_normal_decomposition(self, X, anchors, info):
        """
        验证5：切空间/法空间分解验证
        切空间应捕获数据的主要变化方向，法空间应捕获噪声/约束方向
        """
        self._log("验证5: 切空间/法空间分解验证...")
        
        results = []
        for anchor_idx, anchor in enumerate(anchors[:3]):
            center = anchor.center_point
            T = np.column_stack(anchor.tangent_basis)
            N = np.column_stack(anchor.normal_basis)
            
            # 找锚点附近的点
            nn = NearestNeighbors(n_neighbors=50)
            nn.fit(X)
            _, indices = nn.kneighbors(center.reshape(1, -1))
            local_X = X[indices[0]]
            centered = local_X - center
            
            # 投影到切空间和法空间
            tangent_var = np.var(centered @ T, axis=0)
            normal_var = np.var(centered @ N, axis=0)
            
            total_var = np.sum(tangent_var) + np.sum(normal_var)
            tangent_var_ratio = np.sum(tangent_var) / (total_var + 1e-10)
            
            result = {
                'anchor_idx': anchor_idx,
                'tangent_variance_explained': float(tangent_var_ratio),
                'normal_variance_explained': float(1 - tangent_var_ratio),
                'tangent_variances': [float(x) for x in tangent_var],
                'normal_variances': [float(x) for x in normal_var],
                'decomposition_valid': bool(tangent_var_ratio > 0.6)
            }
            results.append(result)
            
            self._log(f"  锚点{anchor_idx+1}: 切空间方差解释={tangent_var_ratio*100:.1f}%, "
                     f"法空间={ (1-tangent_var_ratio)*100:.1f}%, "
                     f"有效={'✅' if result['decomposition_valid'] else '⚠️'}")
        
        return results
    
    def run_full_verification(self, X, info):
        """运行完整验证流程"""
        print(f"\n  数据集: {info['name']} ({info['n_samples']}点, 真实维度={info.get('intrinsic_dim', '?')})")
        print("  " + "-" * 50)
        
        results = {'dataset_info': info}
        
        # 验证1：测地线 vs 欧氏
        results['geodesic_vs_euclidean'] = self.verify_geodesic_vs_euclidean(X, info)
        
        # 验证2：锚点提取
        results['anchor_extraction'], anchors = self.verify_anchor_extraction(X, info)
        
        if anchors:
            # 验证3：吸引子盘
            results['attractor_basin'] = self.verify_attractor_basin(X, anchors, info)
            
            # 验证4：李雅普诺夫稳定性
            results['lyapunov_stability'] = self.verify_lyapunov_stability(X, anchors, info)
            
            # 验证5：切空间/法空间分解
            results['tangent_normal_decomposition'] = self.verify_tangent_normal_decomposition(X, anchors, info)
        
        # 总体评分
        scores = []
        if 'geodesic_vs_euclidean' in results:
            scores.append(min(results['geodesic_vs_euclidean']['mean_ratio'] / 2.0, 1.0))
        if 'anchor_extraction' in results:
            scores.append(results['anchor_extraction']['dim_accuracy'])
            scores.append(results['anchor_extraction']['mean_stability'])
        if 'attractor_basin' in results:
            scores.append(np.mean([r['basin_valid'] for r in results['attractor_basin']]))
        if 'lyapunov_stability' in results:
            scores.append(np.mean([r['stable'] for r in results['lyapunov_stability']]))
        if 'tangent_normal_decomposition' in results:
            scores.append(np.mean([r['decomposition_valid'] for r in results['tangent_normal_decomposition']]))
        
        results['overall_score'] = float(np.mean(scores)) if scores else 0.0
        results['overall_verdict'] = (
            '✅ 理论验证通过' if results['overall_score'] > 0.6 
            else '⚠️ 部分验证通过，需改进' if results['overall_score'] > 0.4
            else '❌ 理论验证未通过'
        )
        
        print(f"\n  总体评分: {results['overall_score']*100:.1f}%")
        print(f"  总体结论: {results['overall_verdict']}")
        
        return results, anchors
    
    def visualize_results(self, X, info, anchors, results, save_path):
        """可视化验证结果"""
        fig = plt.figure(figsize=(18, 12))
        fig.suptitle(f"吸引子盘理论验证 - {info['name']}", fontsize=16, fontweight='bold')
        
        # 子图1：3D数据分布+锚点
        ax1 = fig.add_subplot(231, projection='3d')
        ax1.scatter(X[:, 0], X[:, 1], X[:, 2], c='lightblue', s=5, alpha=0.5, label='数据点')
        for i, anchor in enumerate(anchors[:5]):
            center = anchor.center_point
            ax1.scatter(center[0], center[1], center[2], c='red', s=100, marker='*', 
                       zorder=5, label=f'锚点{i+1}' if i == 0 else '')
            # 画吸引子盘（简化为球面）
            u, v = np.mgrid[0:2*np.pi:20j, 0:np.pi:10j]
            r = anchor.basin_radius * 0.5
            x = center[0] + r * np.cos(u) * np.sin(v)
            y = center[1] + r * np.sin(u) * np.sin(v)
            z = center[2] + r * np.cos(v)
            ax1.plot_wireframe(x, y, z, color='red', alpha=0.2)
        ax1.set_title('数据分布与高维锚点')
        ax1.legend()
        
        # 子图2：测地线 vs 欧氏距离
        ax2 = fig.add_subplot(232)
        if 'geodesic_vs_euclidean' in results:
            geo_result = results['geodesic_vs_euclidean']
            categories = ['平均比值', '中位数比值', '最大比值']
            values = [geo_result['mean_ratio'], geo_result['median_ratio'], geo_result['max_ratio']]
            bars = ax2.bar(categories, values, color=['steelblue', 'lightgreen', 'salmon'])
            ax2.axhline(y=1.0, color='red', linestyle='--', label='y=x (欧氏距离)')
            ax2.set_ylabel('距离比值 (测地线/欧氏)')
            ax2.set_title('测地线距离 vs 欧氏距离')
            ax2.legend()
            for bar, val in zip(bars, values):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
                        f'{val:.3f}', ha='center', va='bottom')
        
        # 子图3：锚点稳定性评分
        ax3 = fig.add_subplot(233)
        if anchors:
            names = [f'锚点{i+1}' for i in range(len(anchors))]
            stability = [a.stability_score for a in anchors]
            dimensions = [a.dimension for a in anchors]
            bars = ax3.bar(names, stability, color='purple', alpha=0.7)
            ax3.set_ylabel('稳定性评分')
            ax3.set_title(f'锚点稳定性评分 (真实维度={info.get("intrinsic_dim", "?")})')
            ax3.set_ylim(0, 1)
            for i, (bar, dim) in enumerate(zip(bars, dimensions)):
                ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
                        f'k={dim}', ha='center', va='bottom', fontsize=9)
        
        # 子图4：吸引子盘验证
        ax4 = fig.add_subplot(234)
        if 'attractor_basin' in results:
            basin_results = results['attractor_basin']
            names = [f'锚点{r["anchor_idx"]+1}' for r in basin_results]
            density_ratios = [r['density_ratio_inside_outside'] for r in basin_results]
            normal_tangent_ratios = [r['normal_tangent_ratio_inside'] for r in basin_results]
            x = np.arange(len(names))
            width = 0.35
            ax4.bar(x - width/2, density_ratios, width, label='盘内/盘外密度比', color='steelblue')
            ax4.bar(x + width/2, normal_tangent_ratios, width, label='盘内法向/切向比', color='orange')
            ax4.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)
            ax4.set_xticks(x)
            ax4.set_xticklabels(names)
            ax4.set_title('吸引子盘验证')
            ax4.legend()
        
        # 子图5：李雅普诺夫指数
        ax5 = fig.add_subplot(235)
        if 'lyapunov_stability' in results:
            lyap_results = results['lyapunov_stability']
            for r in lyap_results:
                all_lyap = r['tangent_lyapunov'] + r['normal_lyapunov']
                ax5.plot(range(len(all_lyap)), all_lyap, 'o-', 
                        label=f'锚点{r["anchor_idx"]+1}', markersize=4)
            ax5.axhline(y=0, color='red', linestyle='--', label='稳定性边界')
            ax5.set_xlabel('李雅普诺夫指数序号 (前切向后法向)')
            ax5.set_ylabel('李雅普诺夫指数')
            ax5.set_title('李雅普诺夫稳定性验证')
            ax5.legend()
        
        # 子图6：切空间方差解释
        ax6 = fig.add_subplot(236)
        if 'tangent_normal_decomposition' in results:
            decomp_results = results['tangent_normal_decomposition']
            names = [f'锚点{r["anchor_idx"]+1}' for r in decomp_results]
            tangent_ratios = [r['tangent_variance_explained'] for r in decomp_results]
            normal_ratios = [r['normal_variance_explained'] for r in decomp_results]
            ax6.bar(names, tangent_ratios, label='切空间方差解释', color='green', alpha=0.7)
            ax6.bar(names, normal_ratios, bottom=tangent_ratios, label='法空间方差解释', color='red', alpha=0.7)
            ax6.set_ylabel('方差解释比例')
            ax6.set_title('切空间/法空间分解验证')
            ax6.legend()
            ax6.set_ylim(0, 1.1)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        return save_path


def main():
    print("=" * 70)
    print("  黎曼流形吸引子盘与高维锚点理论验证实验")
    print("  Riemannian Attractor Basin & High-Dim Anchor Verification")
    print("=" * 70)
    print(f"\n实验时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 创建结果目录
    results_dir = "/home/user/Doubao/chats/38439832899843586/high_dim_anchor/results"
    os.makedirs(results_dir, exist_ok=True)
    
    # 生成多个合成数据集
    datasets = [
        SyntheticDatasetGenerator.swiss_roll(n_samples=800, noise=0.1),
        SyntheticDatasetGenerator.torus(n_samples=800, noise=0.05),
        SyntheticDatasetGenerator.sphere(n_samples=800, noise=0.05),
        SyntheticDatasetGenerator.gaussian_mixture(n_samples=600, n_clusters=3),
        SyntheticDatasetGenerator.circle_1d(n_samples=500, noise=0.1),
    ]
    
    verifier = AttractorBasinVerifier(verbose=True)
    all_results = {}
    
    for X, info in datasets:
        results, anchors = verifier.run_full_verification(X, info)
        all_results[info['name']] = results
        
        # 可视化
        if X.shape[1] == 3 and anchors:
            viz_path = os.path.join(results_dir, f"verification_{info['name']}.png")
            verifier.visualize_results(X, info, anchors, results, viz_path)
            print(f"  可视化已保存: {viz_path}")
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("  实验结果汇总")
    print("=" * 70)
    
    summary = []
    for name, results in all_results.items():
        score = results['overall_score']
        verdict = results['overall_verdict']
        n_anchors = results['anchor_extraction']['n_anchors_extracted']
        true_dim = results['dataset_info'].get('intrinsic_dim', '?')
        est_dim = results['anchor_extraction'].get('mean_estimated_dim', 0)
        stability = results['anchor_extraction'].get('mean_stability', 0)
        
        summary.append({
            'dataset': name,
            'true_dim': true_dim,
            'n_anchors': n_anchors,
            'est_dim': round(est_dim, 2),
            'stability': round(stability, 4),
            'overall_score': round(score, 4),
            'verdict': verdict
        })
        
        print(f"\n  {name}:")
        print(f"    真实维度: {true_dim}, 提取锚点: {n_anchors}个, 估计维度均值: {est_dim:.2f}")
        print(f"    平均稳定性: {stability:.4f}, 总体评分: {score*100:.1f}%")
        print(f"    结论: {verdict}")
    
    # 计算总体平均
    avg_score = np.mean([s['overall_score'] for s in summary])
    print(f"\n  {'='*50}")
    print(f"  所有数据集平均总体评分: {avg_score*100:.1f}%")
    print(f"  总体结论: {'✅ 黎曼流形吸引子盘理论验证通过' if avg_score > 0.6 else '⚠️ 部分验证通过'}")
    
    # 保存完整结果
    output_file = os.path.join(results_dir, "attractor_basin_verification_results.json")
    
    # 转换为可序列化格式
    def convert(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert(item) for item in obj]
        return obj
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(convert(all_results), f, ensure_ascii=False, indent=2)
    
    print(f"\n  完整结果已保存: {output_file}")
    print("=" * 70)
    
    return all_results, summary


if __name__ == '__main__':
    main()
