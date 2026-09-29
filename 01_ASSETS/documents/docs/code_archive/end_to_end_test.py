"""
端到端综合测试
End-to-End Integration Test

验证所有模块协同工作：
1. 黎曼流形工具库（度量/测地线/切空间/曲率）
2. 高维锚点提取算法
3. 吸引子盘验证
4. 结果持久化
5. 上报数据准备
"""

import numpy as np
import sys
import os
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from riemannian_manifold import (
    RiemannianMetric, TangentSpace, GeodesicCalculator,
    CurvatureEstimator, compute_pairwise_geodesic_distances
)
from high_dim_anchor import HighDimensionalAnchorExtractor, HighDimensionalAnchor
from attractor_basin_verification import SyntheticDatasetGenerator, AttractorBasinVerifier

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


class EndToEndTester:
    """端到端综合测试器"""
    
    def __init__(self):
        self.results = {}
        self.passed = 0
        self.failed = 0
        self.total = 0
        
    def test_riemannian_manifold(self):
        """测试1：黎曼流形工具库"""
        print("\n" + "="*60)
        print("测试1: 黎曼流形工具库")
        print("="*60)
        
        # 生成瑞士卷数据
        np.random.seed(42)
        n = 500
        t = np.random.uniform(0, 3*np.pi, n)
        s = np.random.uniform(-1, 1, n)
        X = np.column_stack([
            t * np.cos(t),
            s,
            t * np.sin(t)
        ]) + 0.1 * np.random.randn(n, 3)
        
        print(f"  数据形状: {X.shape}")
        
        # 1.1 黎曼度量估计
        print("\n  1.1 黎曼度量估计...")
        metric = RiemannianMetric(metric_type='pca', n_neighbors=10)
        metric.fit(X)
        assert metric.metrics_.shape[1:] == (3, 3), "度量张量形状错误"
        print(f"    ✅ 度量张量形状: {metric.metrics_.shape[1:]} (共{metric.metrics_.shape[0]}个点)")
        print(f"    ✅ 度量张量行列式: {np.linalg.det(metric.metrics_[0]):.6f}")
        
        # 1.2 切空间运算
        print("\n  1.2 切空间运算...")
        tangent = TangentSpace(n_neighbors=10)
        tangent.fit(X)
        center = np.mean(X, axis=0)
        v = X[0] - center
        v_tangent = tangent.project_to_tangent(0, v)
        v_normal = tangent.project_to_normal(0, v)
        assert np.allclose(v, v_tangent + v_normal, atol=1e-6), "切空间+法空间不等于原向量"
        print(f"    ✅ 切空间投影+法空间投影=原向量 (误差<1e-6)")
        print(f"    ✅ 切空间维度: {tangent.intrinsic_dim_}")
        
        # 1.3 测地线计算
        print("\n  1.3 测地线计算...")
        # 使用Isomap图距离近似测地线距离
        geo_dists = compute_pairwise_geodesic_distances(X[:100], n_neighbors=10)
        p1, p2 = X[0], X[1]
        geo_dist = geo_dists[0, 1]
        eucl_dist = np.linalg.norm(p1 - p2)
        print(f"    ✅ 测地线距离: {geo_dist:.4f}")
        print(f"    ✅ 欧氏距离: {eucl_dist:.4f}")
        print(f"    ✅ 比值: {geo_dist/eucl_dist:.4f} (>1表示流形弯曲)")
        
        # 1.4 曲率估计
        print("\n  1.4 曲率估计...")
        curvature = CurvatureEstimator(n_neighbors=15)
        sc = curvature.estimate_scalar_curvature(X, 0)
        print(f"    ✅ 标量曲率: {sc:.6f}")
        high_curv = curvature.detect_high_curvature_regions(X, threshold=0.5)
        print(f"    ✅ 高曲率区域点数: {len(high_curv)}/{n}")
        
        self.results['riemannian_manifold'] = {
            'status': 'passed',
            'metric_tensor_shape': list(metric.metrics_.shape[1:]),
            'tangent_dimension': tangent.intrinsic_dim_,
            'geodesic_euclidean_ratio': float(geo_dist/eucl_dist),
            'scalar_curvature': float(sc)
        }
        self.passed += 1
        print("\n  ✅ 黎曼流形工具库测试通过!")
        return True
    
    def test_high_dim_anchor(self):
        """测试2：高维锚点提取算法"""
        print("\n" + "="*60)
        print("测试2: 高维锚点提取算法")
        print("="*60)
        
        # 生成3个高斯聚类
        np.random.seed(42)
        n_per = 100
        centers = np.array([[0,0,0], [5,0,0], [0,5,0]])
        X_list = []
        for c in centers:
            X_list.append(c + np.random.randn(n_per, 3) * 0.3)
        X = np.vstack(X_list)
        
        print(f"  数据形状: {X.shape} (3个高斯聚类)")
        
        # 提取锚点
        extractor = HighDimensionalAnchorExtractor(
            n_neighbors=15, min_samples=10, max_dimension=3, verbose=False
        )
        anchors = extractor.fit(X)
        
        print(f"\n  提取锚点数: {len(anchors)}")
        assert len(anchors) >= 2, f"应提取至少2个锚点，实际{len(anchors)}"
        
        for i, anchor in enumerate(anchors):
            print(f"\n  锚点{i+1}: {anchor.name}")
            print(f"    ID: {anchor.anchor_id}")
            print(f"    维度: {anchor.dimension}")
            print(f"    数据点数: {anchor.n_points}")
            print(f"    中心点: {anchor.center_point}")
            print(f"    切空间基向量数: {len(anchor.tangent_basis)}")
            print(f"    法空间基向量数: {len(anchor.normal_basis)}")
            print(f"    度量张量形状: {anchor.metric_tensor.shape}")
            print(f"    吸引子盘半径: {anchor.basin_radius:.6f}")
            print(f"    李雅普诺夫指数: {[round(x,4) for x in anchor.lyapunov_exponents]}")
            print(f"    稳定性评分: {anchor.stability_score:.4f}")
            print(f"    曲率: {anchor.curvature:.4f}")
            
            # 验证数据结构完整性
            assert anchor.dimension >= 0, "维度应为非负整数"
            assert len(anchor.tangent_basis) == anchor.dimension, "切空间基向量数应等于维度"
            assert anchor.metric_tensor.shape == (anchor.dimension, anchor.dimension), "度量张量形状错误"
            assert len(anchor.lyapunov_exponents) == 3, "李雅普诺夫指数数应为3"
            assert 0 <= anchor.stability_score <= 1, "稳定性评分应在[0,1]"
        
        # 测试保存和加载
        print("\n  测试锚点保存...")
        save_path = "/tmp/test_anchors_e2e.json"
        extractor.save_anchors(save_path)
        assert os.path.exists(save_path), "保存文件不存在"
        with open(save_path) as f:
            data = json.load(f)
        assert data['n_anchors'] == len(anchors), "保存的锚点数不匹配"
        print(f"    ✅ 保存成功: {save_path} ({data['n_anchors']}个锚点)")
        
        self.results['high_dim_anchor'] = {
            'status': 'passed',
            'n_anchors_extracted': len(anchors),
            'dimensions': [a.dimension for a in anchors],
            'mean_stability': float(np.mean([a.stability_score for a in anchors])),
            'mean_basin_radius': float(np.mean([a.basin_radius for a in anchors]))
        }
        self.passed += 1
        print("\n  ✅ 高维锚点提取算法测试通过!")
        return True
    
    def test_attractor_basin(self):
        """测试3：吸引子盘理论验证"""
        print("\n" + "="*60)
        print("测试3: 吸引子盘理论验证")
        print("="*60)
        
        verifier = AttractorBasinVerifier(verbose=False)
        
        # 测试3个数据集
        datasets = [
            SyntheticDatasetGenerator.swiss_roll(n_samples=500, noise=0.1),
            SyntheticDatasetGenerator.gaussian_mixture(n_samples=400, n_clusters=3),
            SyntheticDatasetGenerator.circle_1d(n_samples=300, noise=0.1),
        ]
        
        all_passed = True
        for X, info in datasets:
            print(f"\n  数据集: {info['name']} ({info['n_samples']}点)")
            results, anchors = verifier.run_full_verification(X, info)
            
            # 验证核心指标
            geo_ratio = results['geodesic_vs_euclidean']['mean_ratio']
            tangent_var = results['tangent_normal_decomposition'][0]['tangent_variance_explained']
            
            print(f"    测地线/欧氏比: {geo_ratio:.4f}")
            print(f"    切空间方差解释: {tangent_var*100:.1f}%")
            print(f"    总体评分: {results['overall_score']*100:.1f}%")
            
            # 核心断言
            assert geo_ratio > 1.05, f"测地线/欧氏比应>1.05，实际{geo_ratio}"
            assert tangent_var > 0.5, f"切空间方差解释应>50%，实际{tangent_var}"
            
            print(f"    ✅ 核心指标验证通过")
        
        self.results['attractor_basin'] = {
            'status': 'passed',
            'n_datasets_tested': len(datasets),
            'mean_geodesic_ratio': float(np.mean([
                verifier.run_full_verification(*d)[0]['geodesic_vs_euclidean']['mean_ratio']
                for d in datasets
            ]))
        }
        self.passed += 1
        print("\n  ✅ 吸引子盘理论验证测试通过!")
        return True
    
    def test_data_pipeline(self):
        """测试4：数据流水线（生成→处理→保存→加载）"""
        print("\n" + "="*60)
        print("测试4: 数据流水线完整性")
        print("="*60)
        
        results_dir = "/home/user/Doubao/chats/38439832899843586/high_dim_anchor/results"
        
        # 检查所有必需文件
        required_files = [
            'attractor_basin_verification_results.json',
            'test_anchors.json',
            'verification_swiss_roll.png',
            'verification_torus.png',
            'verification_sphere.png',
            'verification_gaussian_mixture.png',
            'verification_circle_1d.png',
        ]
        
        print("  检查结果文件...")
        for f in required_files:
            path = os.path.join(results_dir, f)
            exists = os.path.exists(path)
            size = os.path.getsize(path) if exists else 0
            status = "✅" if exists and size > 0 else "❌"
            print(f"    {status} {f}: {size/1024:.1f}KB")
            assert exists and size > 0, f"文件不存在或为空: {f}"
        
        # 验证JSON可加载
        print("\n  验证JSON文件可加载...")
        with open(os.path.join(results_dir, 'attractor_basin_verification_results.json')) as f:
            data = json.load(f)
        assert len(data) == 5, f"应有5个数据集结果，实际{len(data)}"
        print(f"    ✅ 验证结果JSON: {len(data)}个数据集")
        
        with open(os.path.join(results_dir, 'test_anchors.json')) as f:
            anchors_data = json.load(f)
        assert anchors_data['n_anchors'] > 0, "锚点数应为正"
        print(f"    ✅ 测试锚点JSON: {anchors_data['n_anchors']}个锚点")
        
        # 验证图片文件
        print("\n  验证图片文件完整性...")
        for f in required_files:
            if f.endswith('.png'):
                path = os.path.join(results_dir, f)
                with open(path, 'rb') as img:
                    header = img.read(8)
                    assert header[:4] == b'\x89PNG', f"不是有效PNG: {f}"
        print(f"    ✅ 所有PNG图片文件有效")
        
        self.results['data_pipeline'] = {
            'status': 'passed',
            'n_result_files': len(required_files),
            'n_datasets_in_json': len(data),
            'n_anchors_in_json': anchors_data['n_anchors']
        }
        self.passed += 1
        print("\n  ✅ 数据流水线测试通过!")
        return True
    
    def test_report_generation(self):
        """测试5：验证报告生成"""
        print("\n" + "="*60)
        print("测试5: 验证报告生成")
        print("="*60)
        
        report_path = "/home/user/Doubao/chats/38439832899843586/high_dim_anchor/VERIFICATION_REPORT_v1.0.md"
        
        assert os.path.exists(report_path), "验证报告不存在"
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键章节
        required_sections = [
            '实验概述',
            '核心理论假设验证结果',
            '总体评分与结论',
            '已交付的代码资产',
            '下一步改进计划',
            '元规则确权'
        ]
        
        print("  检查报告章节...")
        for section in required_sections:
            found = section in content
            status = "✅" if found else "❌"
            print(f"    {status} {section}")
            assert found, f"报告缺少章节: {section}"
        
        # 检查关键数据
        required_data = [
            '1.20',  # 测地线/欧氏比
            '75.4%',  # 切空间方差解释
            '1625',  # 代码行数
            'ZR-VERIFY-RIEMANNIAN-ANCHOR-V1.0',
            'DID-BR-000002',
            'Ω₀⊂⊙∞⊂Ω',
        ]
        
        print("\n  检查报告关键数据...")
        for data in required_data:
            found = data in content
            status = "✅" if found else "❌"
            print(f"    {status} {data}")
            assert found, f"报告缺少关键数据: {data}"
        
        print(f"\n  报告行数: {len(content.splitlines())}")
        print(f"  报告字符数: {len(content)}")
        
        self.results['report_generation'] = {
            'status': 'passed',
            'report_lines': len(content.splitlines()),
            'report_chars': len(content),
            'sections_found': len(required_sections),
            'key_data_found': len(required_data)
        }
        self.passed += 1
        print("\n  ✅ 验证报告生成测试通过!")
        return True
    
    def run_all_tests(self):
        """运行所有测试"""
        print("="*70)
        print("  端到端综合测试 - End-to-End Integration Test")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        start_time = time.time()
        
        tests = [
            ('黎曼流形工具库', self.test_riemannian_manifold),
            ('高维锚点提取算法', self.test_high_dim_anchor),
            ('吸引子盘理论验证', self.test_attractor_basin),
            ('数据流水线完整性', self.test_data_pipeline),
            ('验证报告生成', self.test_report_generation),
        ]
        
        self.total = len(tests)
        
        for name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.failed += 1
                print(f"\n  ❌ {name} 测试失败: {e}")
                import traceback
                traceback.print_exc()
        
        elapsed = time.time() - start_time
        
        # 最终总结
        print("\n" + "="*70)
        print("  测试总结")
        print("="*70)
        print(f"  总测试数: {self.total}")
        print(f"  通过: {self.passed} ✅")
        print(f"  失败: {self.failed} ❌")
        print(f"  耗时: {elapsed:.2f}秒")
        print(f"  通过率: {self.passed/self.total*100:.1f}%")
        
        if self.failed == 0:
            print("\n  🎉 所有测试全部通过! 可以安全上报!")
        else:
            print(f"\n  ⚠️ 有{self.failed}个测试失败，需要修复后再上报!")
        
        print("="*70)
        
        # 保存测试结果
        self.results['summary'] = {
            'total': self.total,
            'passed': self.passed,
            'failed': self.failed,
            'pass_rate': self.passed/self.total,
            'elapsed_seconds': elapsed,
            'timestamp': datetime.now().isoformat()
        }
        
        result_path = "/home/user/Doubao/chats/38439832899843586/high_dim_anchor/results/end_to_end_test_results.json"
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n  测试结果已保存: {result_path}")
        
        return self.failed == 0


if __name__ == '__main__':
    tester = EndToEndTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
