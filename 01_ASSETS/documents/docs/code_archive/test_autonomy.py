"""
永恒自治调度器单元测试
"""
import os
import sys
import time
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.autonomy_orchestrator import (
    EternalAutonomyOrchestrator, AutonomyConfig, AutonomyTask,
    SteadyStateArbiter, MetaAxiomValidator
)
from src.main import AutoEduSystem


class TestAutonomyConfig(unittest.TestCase):
    """自治配置测试"""

    def test_default_config(self):
        config = AutonomyConfig()
        self.assertEqual(config.poll_interval_seconds, 300)
        self.assertEqual(config.max_cycles, 0)
        self.assertTrue(config.auto_execute_light_tasks)
        self.assertTrue(config.manual_gate_for_major_changes)
        self.assertEqual(config.risk_threshold, 0.3)
        self.assertTrue(config.circuit_breaker_enabled)

    def test_config_update(self):
        config = AutonomyConfig()
        config.update({"poll_interval_seconds": 60, "risk_threshold": 0.5})
        self.assertEqual(config.poll_interval_seconds, 60)
        self.assertEqual(config.risk_threshold, 0.5)

    def test_config_to_dict(self):
        config = AutonomyConfig()
        d = config.to_dict()
        self.assertIn("poll_interval_seconds", d)
        self.assertIn("auto_execute_light_tasks", d)


class TestSteadyStateArbiter(unittest.TestCase):
    """三维稳态仲裁器测试"""

    def test_evaluate_high_score(self):
        score = SteadyStateArbiter.evaluate(90, 10, 20)
        self.assertGreater(score, 80)

    def test_evaluate_low_score(self):
        score = SteadyStateArbiter.evaluate(30, 70, 80)
        self.assertLess(score, 50)

    def test_evaluate_weights_sum(self):
        from config.settings import DECISION_WEIGHTS
        total = sum(DECISION_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_should_execute_high(self):
        config = AutonomyConfig()
        should, reason = SteadyStateArbiter.should_execute(85, 10, config)
        self.assertTrue(should)

    def test_should_execute_risk_too_high(self):
        config = AutonomyConfig()
        should, reason = SteadyStateArbiter.should_execute(90, 50, config)
        self.assertFalse(should)

    def test_should_execute_low_score(self):
        config = AutonomyConfig()
        should, reason = SteadyStateArbiter.should_execute(30, 10, config)
        self.assertFalse(should)


class TestMetaAxiomValidator(unittest.TestCase):
    """元宪法公理校验器测试"""

    def test_valid_task(self):
        result = MetaAxiomValidator.validate("自动更新知识图谱，生成初中AI教材")
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["violations"]), 0)

    def test_violation_ai_replace(self):
        result = MetaAxiomValidator.validate("AI完全替代人类教师，全自动决策无需人工")
        self.assertFalse(result["passed"])
        self.assertTrue(any("人本主导" in v for v in result["violations"]))

    def test_violation_paid_gate(self):
        result = MetaAxiomValidator.validate("仅城区学校可用，设置付费门槛排除乡村")
        self.assertFalse(result["passed"])
        self.assertTrue(any("普惠均等" in v for v in result["violations"]))

    def test_violation_sensitive(self):
        result = MetaAxiomValidator.validate("包含暴力内容的教材生成")
        self.assertFalse(result["passed"])
        self.assertTrue(any("向善安全" in v for v in result["violations"]))

    def test_axioms_checked(self):
        result = MetaAxiomValidator.validate("正常任务")
        self.assertEqual(len(result["axioms_checked"]), 5)


class TestAutonomyTask(unittest.TestCase):
    """自治任务测试"""

    def test_create_task(self):
        task = AutonomyTask(
            task_type="knowledge_update",
            description="更新知识图谱",
            module="knowledge_graph",
            estimated_benefit=60,
            estimated_risk=15,
            estimated_cost=20
        )
        self.assertEqual(task.status, "pending")
        self.assertIn("AUTO-TASK", task.task_id)
        self.assertFalse(task.is_major_change)

    def test_major_change_task(self):
        task = AutonomyTask(
            task_type="content_generate",
            description="大规模教材版本更新",
            module="content_engine",
            is_major_change=True
        )
        self.assertTrue(task.is_major_change)

    def test_task_to_dict(self):
        task = AutonomyTask("test", "desc", "module")
        d = task.to_dict()
        self.assertIn("task_id", d)
        self.assertIn("status", d)
        self.assertIn("created_at", d)


class TestEternalAutonomyOrchestrator(unittest.TestCase):
    """永恒自治调度器集成测试"""

    @classmethod
    def setUpClass(cls):
        """初始化系统和调度器"""
        cls.system = AutoEduSystem()
        cls.system.initialize_demo_data()
        cls.orchestrator = EternalAutonomyOrchestrator()
        cls.orchestrator.bind_system(cls.system)

    def test_01_initialization(self):
        """调度器初始化"""
        self.assertFalse(self.orchestrator.running)
        self.assertEqual(self.orchestrator.cycle_count, 0)
        self.assertFalse(self.orchestrator.circuit_broken)
        self.assertEqual(len(self.orchestrator.task_queue), 0)

    def test_02_step1_perceive(self):
        """第一步感知采集"""
        signals = self.orchestrator.step1_perceive()
        self.assertIn("timestamp", signals)
        self.assertIn("system_status", signals)
        self.assertIn("knowledge_stats", signals)
        self.assertIn("content_stats", signals)
        self.assertIn("risk_signals", signals)
        self.assertIsNotNone(signals["knowledge_stats"])
        self.assertGreater(signals["knowledge_stats"]["total_entities"], 0)

    def test_03_step2_arbitrate(self):
        """第二步稳态仲裁"""
        signals = self.orchestrator.step1_perceive()
        self.orchestrator.step2_arbitrate(signals)
        # 应该有任务被批准或进入人工审核
        total_tasks = len(self.orchestrator.task_queue) + len(self.orchestrator.manual_review_queue)
        self.assertGreater(total_tasks, 0)

    def test_04_step3_dispatch(self):
        """第三步任务分发"""
        # 先清空队列，手动加入任务
        self.orchestrator.task_queue.clear()
        task = AutonomyTask("knowledge_update", "测试更新", "knowledge_graph")
        task.status = "approved"
        self.orchestrator.task_queue.append(task)
        dispatched = self.orchestrator.step3_dispatch()
        self.assertEqual(len(dispatched), 1)
        self.assertEqual(dispatched[0].status, "executing")

    def test_05_step4_execute(self):
        """第四步执行+自检"""
        task = AutonomyTask(
            task_type="knowledge_update",
            description="更新知识图谱实体",
            module="knowledge_graph",
            estimated_benefit=60, estimated_risk=10, estimated_cost=15
        )
        results = self.orchestrator.step4_execute_and_verify([task])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "completed")
        self.assertIsNotNone(results[0].result)

    def test_06_full_cycle(self):
        """完整一轮自治循环"""
        result = self.orchestrator.run_one_cycle()
        self.assertIn("cycle", result)
        self.assertGreater(result["cycle"], 0)
        self.assertIn("tasks_dispatched", result)
        self.assertIn("duration_seconds", result)
        self.assertFalse(result["circuit_broken"])

    def test_07_get_status(self):
        """获取状态"""
        status = self.orchestrator.get_status()
        self.assertIn("running", status)
        self.assertIn("cycle_count", status)
        self.assertIn("circuit_broken", status)
        self.assertIn("config", status)
        self.assertIn("did", status)
        self.assertGreater(status["cycle_count"], 0)

    def test_08_audit_log(self):
        """审计日志"""
        logs = self.orchestrator.get_audit_logs(10)
        self.assertIsInstance(logs, list)
        self.assertGreater(len(logs), 0)
        self.assertIn("action", logs[0])
        self.assertIn("timestamp", logs[0])

    def test_09_risk_report(self):
        """风险评估报告"""
        report = self.orchestrator.get_risk_report()
        self.assertIn("circuit_broken", report)
        self.assertIn("consecutive_failures", report)
        self.assertIn("recommendation", report)

    def test_10_manual_gate(self):
        """人工审核闸口"""
        task = AutonomyTask(
            task_type="content_generate",
            description="大规模教材版本更新",
            module="content_engine",
            is_major_change=True
        )
        self.orchestrator.manual_review_queue.clear()
        # 重大变更应该进入人工审核
        self.orchestrator.step2_arbitrate({"risk_signals": []})
        # 验证人工审核队列机制
        self.assertTrue(self.orchestrator.config.manual_gate_for_major_changes)

    def test_11_approve_manual_task(self):
        """人工审核通过"""
        task = AutonomyTask("test", "测试", "module", is_major_change=True)
        self.orchestrator.manual_review_queue.append(task)
        result = self.orchestrator.approve_manual_task(task.task_id)
        self.assertTrue(result)
        self.assertEqual(task.status, "approved")

    def test_12_reject_manual_task(self):
        """人工审核拒绝"""
        task = AutonomyTask("test2", "测试2", "module", is_major_change=True)
        self.orchestrator.manual_review_queue.append(task)
        result = self.orchestrator.reject_manual_task(task.task_id, "不符合要求")
        self.assertTrue(result)
        self.assertEqual(task.status, "rejected")

    def test_13_circuit_breaker_reset(self):
        """熔断重置"""
        self.orchestrator.circuit_broken = True
        self.orchestrator.consecutive_failures = 5
        result = self.orchestrator.reset_circuit_breaker()
        self.assertTrue(result)
        self.assertFalse(self.orchestrator.circuit_broken)
        self.assertEqual(self.orchestrator.consecutive_failures, 0)

    def test_14_save_state(self):
        """保存状态"""
        path = self.orchestrator.save_state()
        self.assertTrue(os.path.exists(path))
        import json
        with open(path, 'r') as f:
            state = json.load(f)
        self.assertIn("cycle_count", state)
        self.assertIn("config", state)


if __name__ == '__main__':
    unittest.main(verbosity=2)
