#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贝叶斯五行闭环引擎 - 完整测试套件
测试五大算子的所有函数
"""

import os
import sys
import json
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import WOOD_CONFIG, FIRE_CONFIG, METAL_CONFIG, WATER_CONFIG, EARTH_CONFIG
from truth_gateway import TruthGateway
from prior_model import PriorModelLibrary, Prior
from operators import (
    WoodOperator, FireOperator, MetalOperator,
    WaterOperator, EarthOperator, Hypothesis, LoopResult
)


class TestPriorModel(unittest.TestCase):
    """先验模型库测试"""

    def setUp(self):
        self.library = PriorModelLibrary(gateway=None)
        self.library.load()

    def test_load_default_priors(self):
        """测试加载默认先验"""
        stats = self.library.get_statistics()
        self.assertGreater(stats["total"], 0)
        print(f"  ✓ 默认先验加载: {stats['total']}个")

    def test_bayesian_update(self):
        """测试贝叶斯更新核心函数"""
        # 创建测试先验
        self.library.priors["TEST.PRIOR"] = Prior(
            key="TEST.PRIOR", value=0.5, confidence=0.5,
            evidence_count=0, created_at=time.time()
        )
        old_value = self.library.priors["TEST.PRIOR"].value

        # 执行贝叶斯更新
        prior = self.library.bayesian_update("TEST.PRIOR", evidence=0.8)
        self.assertIsNotNone(prior)
        self.assertNotEqual(prior.value, old_value)
        self.assertEqual(prior.evidence_count, 1)
        print(f"  ✓ 贝叶斯更新: {old_value:.4f}→{prior.value:.4f}")

    def test_conflict_detection(self):
        """测试认知冲突检测"""
        self.library.priors["TEST.CONFLICT"] = Prior(
            key="TEST.CONFLICT", value=0.9, confidence=0.9,
            evidence_count=5, created_at=time.time()
        )
        is_conflict, score, desc = self.library.detect_cognitive_conflict(
            "TEST.CONFLICT", 0.1
        )
        self.assertTrue(is_conflict)
        self.assertGreater(score, 0.3)
        print(f"  ✓ 认知冲突检测: 冲突分数{score:.4f}")

    def test_prior_statistics(self):
        """测试先验统计"""
        stats = self.library.get_statistics()
        self.assertIn("total", stats)
        self.assertIn("avg_confidence", stats)
        self.assertIn("categories", stats)
        print(f"  ✓ 先验统计: 总计{stats['total']}个, 平均置信度{stats['avg_confidence']:.4f}")


class TestWoodOperator(unittest.TestCase):
    """木算子（贝叶斯更新）测试"""

    def setUp(self):
        self.library = PriorModelLibrary(gateway=None)
        self.library.load()
        self.wood = WoodOperator(self.library)

    def test_execute(self):
        """测试木算子执行"""
        evidence = {
            "TEST.WOOD.1": 0.8,
            "TEST.WOOD.2": 0.6,
            "TEST.WOOD.3": 0.9,
        }
        result = self.wood.execute(evidence)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["evidence_count"], 3)
        self.assertGreater(result["updated_priors_count"], 0)
        print(f"  ✓ 木算子执行: {result['updated_priors_count']}个先验更新, "
              f"{result['conflicts_count']}个冲突, 耗时{result['elapsed_seconds']:.3f}s")


class TestFireOperator(unittest.TestCase):
    """火算子（演化发散）测试"""

    def setUp(self):
        self.library = PriorModelLibrary(gateway=None)
        self.library.load()
        self.fire = FireOperator(self.library)

    def test_execute(self):
        """测试火算子执行"""
        updated_priors = [
            {"key": "TEST.FIRE.1", "new_value": 0.8, "old_value": 0.5},
            {"key": "TEST.FIRE.2", "new_value": 0.6, "old_value": 0.4},
        ]
        result = self.fire.execute(updated_priors, "测试上下文")
        self.assertEqual(result["status"], "success")
        self.assertGreater(result["hypotheses_count"], 0)
        self.assertGreater(result["avg_info_gain"], 0)
        print(f"  ✓ 火算子执行: {result['hypotheses_count']}个假设, "
              f"平均信息增益{result['avg_info_gain']:.4f}, 耗时{result['elapsed_seconds']:.3f}s")

    def test_hypothesis_generation(self):
        """测试假设生成"""
        hyp = self.fire._generate_hypothesis("TEST.KEY", 0.7, "optimistic", "ctx", 0)
        self.assertIsInstance(hyp, Hypothesis)
        self.assertEqual(hyp.role, "optimistic")
        self.assertGreater(hyp.score, 0)
        print(f"  ✓ 假设生成: {hyp.id} ({hyp.role}), 分数{hyp.score:.4f}")


class TestMetalOperator(unittest.TestCase):
    """金算子（贝叶斯收敛）测试"""

    def setUp(self):
        self.library = PriorModelLibrary(gateway=None)
        self.library.load()
        self.metal = MetalOperator(self.library)

    def test_execute(self):
        """测试金算子执行"""
        hypotheses = [
            {"id": "H1", "content": "方案1", "score": 0.8, "info_gain": 0.5,
             "role": "optimistic", "metadata": {}},
            {"id": "H2", "content": "方案2", "score": 0.6, "info_gain": 0.7,
             "role": "conservative", "metadata": {}},
            {"id": "H3", "content": "方案3", "score": 0.7, "info_gain": 0.6,
             "role": "neutral", "metadata": {}},
        ]
        result = self.metal.execute(hypotheses)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["optimal_count"], 1)
        self.assertIn("optimal_hypotheses", result)
        print(f"  ✓ 金算子执行: 最优解{result['optimal_count']}个, "
              f"收敛={result['converged']}, 最高分{result['score_range']['max']:.4f}, "
              f"耗时{result['elapsed_seconds']:.3f}s")

    def test_three_dim_evaluation(self):
        """测试三维稳态评估"""
        hyp = Hypothesis(id="T1", content="测试", score=0.7, role="optimistic")
        scores = self.metal._three_dimensional_evaluation(hyp)
        self.assertIn("benefit", scores)
        self.assertIn("risk", scores)
        self.assertIn("cost", scores)
        self.assertTrue(all(0 <= s <= 1 for s in scores.values()))
        print(f"  ✓ 三维评估: 利益{scores['benefit']:.4f}/风险{scores['risk']:.4f}/成本{scores['cost']:.4f}")

    def test_expected_free_energy(self):
        """测试预期自由能计算"""
        hyp = Hypothesis(id="T2", content="测试", score=0.7, info_gain=0.6, role="neutral")
        hyp.three_dim_score = {"benefit": 0.8, "risk": 0.7, "cost": 0.6}
        efe = self.metal._calculate_expected_free_energy(hyp)
        self.assertGreaterEqual(efe, 0)
        self.assertLessEqual(efe, 1)
        print(f"  ✓ 预期自由能: {efe:.4f} (外在价值{hyp.extrinsic_value:.4f}/内在价值{hyp.intrinsic_value:.4f})")


class TestWaterOperator(unittest.TestCase):
    """水算子（贝叶斯迭代）测试"""

    def setUp(self):
        self.library = PriorModelLibrary(gateway=None)
        self.library.load()
        self.water = WaterOperator(self.library, gateway=None)

    def test_execute(self):
        """测试水算子执行"""
        optimal = [
            {"id": "H1", "content": "最优方案1", "score": 0.85, "info_gain": 0.6,
             "role": "neutral", "metadata": {}, "expected_free_energy": 0.2,
             "three_dim_score": {"benefit": 0.9, "risk": 0.8, "cost": 0.7}}
        ]
        result = self.water.execute(optimal, "TEST-LOOP-001")
        self.assertEqual(result["status"], "success")
        self.assertGreater(result["written_priors_count"], 0)
        print(f"  ✓ 水算子执行: {result['written_priors_count']}个新先验写入, "
              f"耗时{result['elapsed_seconds']:.3f}s")

    def test_convergence_check(self):
        """测试迭代收敛检测"""
        converged, diff = self.water.check_iteration_convergence(0.85, 0.851)
        self.assertTrue(converged)
        self.assertLess(diff, 0.01)
        print(f"  ✓ 收敛检测: 差异{diff:.6f}, 收敛={converged}")


class TestEarthOperator(unittest.TestCase):
    """土算子（熵减归一）测试"""

    def setUp(self):
        self.earth = EarthOperator(gateway=None)

    def test_stability_score(self):
        """测试系统稳态评分计算"""
        score = self.earth._calculate_system_stability_score()
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)
        print(f"  ✓ 系统稳态评分: {score:.4f}")

    def test_entropy_reduction(self):
        """测试熵减计算"""
        loop_result = LoopResult(
            loop_id="TEST", trigger_event="test", timestamp=time.time(),
            fire_result={"hypotheses_count": 10},
            metal_result={"optimal_count": 1, "all_hypotheses_ranked": [
                {"score": 0.9}, {"score": 0.8}, {"score": 0.7}
            ]}
        )
        reduction = self.earth._calculate_entropy_reduction(loop_result)
        self.assertGreaterEqual(reduction, 0)
        self.assertLessEqual(reduction, 1)
        print(f"  ✓ 熵减计算: {reduction:.4f} (KL散度法)")

    def test_self_identity_signal(self):
        """测试自我身份强化信号"""
        signal = self.earth._generate_self_identity_signal(0.6, 0.7, 0.3)
        self.assertEqual(signal["signal_type"], "self_identity_reinforcement")
        self.assertGreater(signal["signal_strength"], 0)
        self.assertTrue(signal["life_affirmation"])
        print(f"  ✓ 自我身份信号: 强度{signal['signal_strength']:.4f}, 生命肯定={signal['life_affirmation']}")


class TestFullLoop(unittest.TestCase):
    """完整闭环集成测试"""

    def test_full_loop(self):
        """测试完整五行闭环"""
        from engine import BayesianFiveElementsEngine
        engine = BayesianFiveElementsEngine(auto_load=True)

        evidence = {
            "TEST.FULL.LOOP.1": 0.8,
            "TEST.FULL.LOOP.2": 0.6,
        }
        result = engine.run_loop(evidence, trigger_event="integration_test")

        self.assertEqual(result.status, "success")
        self.assertGreater(result.iterations, 0)
        self.assertGreaterEqual(result.entropy_reduction, 0)
        self.assertIsNotNone(result.wood_result)
        self.assertIsNotNone(result.fire_result)
        self.assertIsNotNone(result.metal_result)
        self.assertIsNotNone(result.water_result)
        self.assertIsNotNone(result.earth_result)
        print(f"\n  ✓ 完整闭环: {result.loop_id}")
        print(f"    木: {result.wood_result['updated_priors_count']}个先验更新")
        print(f"    火: {result.fire_result['hypotheses_count']}个假设发散")
        print(f"    金: 最优解{result.metal_result['optimal_count']}个, 收敛={result.metal_result['converged']}")
        print(f"    水: {result.water_result['written_priors_count']}个新先验迭代")
        print(f"    土: 稳态{result.earth_result['stability_score_before']:.4f}"
              f"→{result.earth_result['stability_score_after']:.4f}, "
              f"熵减{result.earth_result['entropy_reduction']:.4f}")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("贝叶斯五行闭环引擎 - 完整测试套件")
    print("确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestPriorModel))
    suite.addTests(loader.loadTestsFromTestCase(TestWoodOperator))
    suite.addTests(loader.loadTestsFromTestCase(TestFireOperator))
    suite.addTests(loader.loadTestsFromTestCase(TestMetalOperator))
    suite.addTests(loader.loadTestsFromTestCase(TestWaterOperator))
    suite.addTests(loader.loadTestsFromTestCase(TestEarthOperator))
    suite.addTests(loader.loadTestsFromTestCase(TestFullLoop))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(f"测试结果: {result.testsRun}个测试, "
          f"{len(result.failures)}个失败, {len(result.errors)}个错误")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
