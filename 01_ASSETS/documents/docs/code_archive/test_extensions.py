"""
功能模块补齐扩展测试
覆盖知识图谱/内容引擎/自适应学习/师资培育/评估反馈/演化引擎/通用工具/主调度器的新增方法
"""
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.main import AutoEduSystem
from src.common.utils import (
    compliance_check_detail, batch_compliance_check,
    get_root_archives, get_sandbox_archives, verify_archive_hash,
    export_archives, archive_to_root, archive_to_sandbox, compute_hash
)


class TestKnowledgeGraphExtensions(unittest.TestCase):
    """知识图谱扩展测试"""

    @classmethod
    def setUpClass(cls):
        cls.system = AutoEduSystem()
        cls.system.initialize_demo_data()
        cls.kg = cls.system.kg
        cls.first_entity_id = list(cls.kg.entities.keys())[0]

    def test_01_get_entity_by_id(self):
        entity = self.kg.get_entity_by_id(self.first_entity_id)
        self.assertIsNotNone(entity)
        self.assertIn("name", entity)

    def test_02_get_entity_by_name(self):
        first_name = list(self.kg.entities.values())[0]["name"]
        entity = self.kg.get_entity_by_name(first_name)
        self.assertIsNotNone(entity)
        self.assertEqual(entity["name"], first_name)

    def test_03_update_entity(self):
        result = self.kg.update_entity(self.first_entity_id, mastery_level="掌握")
        self.assertTrue(result)
        entity = self.kg.get_entity_by_id(self.first_entity_id)
        self.assertEqual(entity["mastery_level"], "掌握")
        self.assertGreaterEqual(entity.get("version", 1), 2)

    def test_04_get_relations_for_entity(self):
        relations = self.kg.get_relations_for_entity(self.first_entity_id)
        self.assertIsInstance(relations, list)

    def test_05_search_entities(self):
        results = self.kg.search_entities("AI")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_06_get_domains(self):
        domains = self.kg.get_domains()
        self.assertIsInstance(domains, list)
        self.assertGreater(len(domains), 0)
        self.assertIn("domain", domains[0])
        self.assertIn("entity_count", domains[0])

    def test_07_export_graph(self):
        exported = self.kg.export_graph()
        self.assertIn("nodes", exported)
        self.assertIn("edges", exported)
        self.assertIn("stats", exported)
        self.assertGreater(len(exported["nodes"]), 0)

    def test_08_get_entity_count_by_stage(self):
        stats = self.kg.get_entity_count_by_stage()
        self.assertIsInstance(stats, dict)
        self.assertGreater(len(stats), 0)

    def test_09_delete_entity(self):
        # 先添加一个测试实体再删除（add_entity返回字符串id）
        entity_id = self.kg.add_entity("测试删除实体", "AI基础理论", stages=["初中"])
        result = self.kg.delete_entity(entity_id)
        self.assertTrue(result)
        self.assertIsNone(self.kg.get_entity_by_id(entity_id))


class TestContentEngineExtensions(unittest.TestCase):
    """内容引擎扩展测试"""

    @classmethod
    def setUpClass(cls):
        cls.system = AutoEduSystem()
        cls.system.initialize_demo_data()
        cls.system.run_content_generation(stage="初中", max_chapters=2)
        cls.content = cls.system.content
        # 获取一个生成的内容ID
        cls.test_content_id = None
        for items in cls.content.generated_content.values():
            if items:
                cls.test_content_id = items[0]["id"]
                break

    def test_01_get_content_by_id(self):
        if not self.test_content_id:
            self.skipTest("无生成内容")
        found = self.content.get_content_by_id(self.test_content_id)
        self.assertIsNotNone(found)
        self.assertIn("type", found)
        self.assertIn("content", found)

    def test_02_get_content_by_type(self):
        items = self.content.get_content_by_type("chapters")
        self.assertIsInstance(items, list)

    def test_03_get_content_by_stage(self):
        result = self.content.get_content_by_stage("初中")
        self.assertIsInstance(result, dict)

    def test_04_search_content(self):
        results = self.content.search_content("AI")
        self.assertIsInstance(results, list)

    def test_05_update_content(self):
        if not self.test_content_id:
            self.skipTest("无生成内容")
        result = self.content.update_content(self.test_content_id, title="更新后的标题")
        self.assertTrue(result)

    def test_06_review_content(self):
        if not self.test_content_id:
            self.skipTest("无生成内容")
        result = self.content.review_content(self.test_content_id, "测试审核员", True, "内容合格")
        self.assertTrue(result)
        found = self.content.get_content_by_id(self.test_content_id)
        self.assertEqual(found["content"]["status"], "approved")

    def test_07_get_pending_reviews(self):
        pending = self.content.get_pending_reviews()
        self.assertIsInstance(pending, list)

    def test_08_rate_content_quality(self):
        if not self.test_content_id:
            self.skipTest("无生成内容")
        score = self.content.rate_content_quality(self.test_content_id)
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_09_get_content_stats_detail(self):
        stats = self.content.get_content_stats_detail()
        self.assertIn("by_type", stats)
        self.assertIn("by_stage", stats)
        self.assertIn("by_status", stats)
        self.assertIn("total", stats)

    def test_10_delete_content(self):
        # 先生成一个内容并添加到存储中再删除
        entity = list(self.system.kg.entities.values())[0]
        chapter = self.content.generate_textbook_chapter(entity, "初中")
        self.content.generated_content["textbooks"].append(chapter)
        result = self.content.delete_content(chapter["chapter_id"])
        self.assertTrue(result)


class TestAdaptiveLearningExtensions(unittest.TestCase):
    """自适应学习扩展测试"""

    @classmethod
    def setUpClass(cls):
        cls.system = AutoEduSystem()
        cls.system.initialize_demo_data()
        cls.adaptive = cls.system.adaptive
        cls.first_learner_id = list(cls.adaptive.learners.keys())[0]

    def test_01_get_learner_by_id(self):
        learner = self.adaptive.get_learner_by_id(self.first_learner_id)
        self.assertIsNotNone(learner)
        self.assertIn("learner_id", learner)

    def test_02_get_learners_by_stage(self):
        learners = self.adaptive.get_learners_by_stage("初中")
        self.assertIsInstance(learners, list)

    def test_03_update_learner(self):
        result = self.adaptive.update_learner(self.first_learner_id, name="更新后的名字")
        self.assertTrue(result)
        learner = self.adaptive.get_learner_by_id(self.first_learner_id)
        self.assertEqual(learner["name"], "更新后的名字")

    def test_04_get_learning_history(self):
        # 先记录一个学习活动
        first_kp = list(self.system.kg.entities.keys())[0]
        self.adaptive.record_learning_activity(self.first_learner_id, first_kp, "学习", 30, 80)
        history = self.adaptive.get_learning_history(self.first_learner_id)
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)

    def test_05_get_learner_mastery_overview(self):
        overview = self.adaptive.get_learner_mastery_overview(self.first_learner_id)
        self.assertIsNotNone(overview)
        self.assertIn("avg_mastery", overview)
        self.assertIn("weak_points", overview)
        self.assertIn("strong_points", overview)
        self.assertIn("mastery_distribution", overview)

    def test_06_generate_weak_point_practice(self):
        practices = self.adaptive.generate_weak_point_practice(self.first_learner_id)
        self.assertIsInstance(practices, list)

    def test_07_compare_learners(self):
        learner_ids = list(self.adaptive.learners.keys())[:3]
        comparison = self.adaptive.compare_learners(learner_ids)
        self.assertIsInstance(comparison, list)
        self.assertEqual(len(comparison), 3)

    def test_08_get_learners_ranking(self):
        ranking = self.adaptive.get_learners_ranking(limit=5)
        self.assertIsInstance(ranking, list)
        self.assertLessEqual(len(ranking), 5)

    def test_09_delete_learner(self):
        learner = self.adaptive.create_learner("测试删除", "初中", "七年级")
        result = self.adaptive.delete_learner(learner.learner_id)
        self.assertTrue(result)
        self.assertIsNone(self.adaptive.get_learner_by_id(learner.learner_id))


class TestTeacherTrainingExtensions(unittest.TestCase):
    """师资培育扩展测试"""

    @classmethod
    def setUpClass(cls):
        cls.system = AutoEduSystem()
        cls.system.initialize_demo_data()
        cls.teachers = cls.system.teachers
        cls.first_teacher_id = list(cls.teachers.teachers.keys())[0]

    def test_01_get_teacher_by_id(self):
        teacher = self.teachers.get_teacher_by_id(self.first_teacher_id)
        self.assertIsNotNone(teacher)
        self.assertIn("teacher_id", teacher)

    def test_02_get_teachers_by_subject(self):
        teachers = self.teachers.get_teachers_by_subject("语文")
        self.assertIsInstance(teachers, list)

    def test_03_get_teachers_by_school_type(self):
        teachers = self.teachers.get_teachers_by_school_type("城区")
        self.assertIsInstance(teachers, list)

    def test_04_update_teacher(self):
        result = self.teachers.update_teacher(self.first_teacher_id, name="更新后的老师")
        self.assertTrue(result)
        teacher = self.teachers.get_teacher_by_id(self.first_teacher_id)
        self.assertEqual(teacher["name"], "更新后的老师")

    def test_05_add_training_course(self):
        course = self.teachers.add_training_course("AI教学应用", "进阶级", "信息科技", 8, "AI工具在教学中的应用")
        self.assertIsNotNone(course)
        self.assertIn("id", course)
        self.assertEqual(course["name"], "AI教学应用")

    def test_06_get_training_courses(self):
        courses = self.teachers.get_training_courses()
        self.assertIsInstance(courses, list)

    def test_07_get_research_groups(self):
        groups = self.teachers.get_research_groups()
        self.assertIsInstance(groups, list)

    def test_08_get_teaching_cases(self):
        # 先生成一个教学案例
        self.teachers.generate_teaching_case(self.first_teacher_id, "AI辅助教学")
        cases = self.teachers.get_teaching_cases()
        self.assertIsInstance(cases, list)

    def test_09_get_teacher_skill_report(self):
        report = self.teachers.get_teacher_skill_report(self.first_teacher_id)
        self.assertIsNotNone(report)
        self.assertIn("avg_skill_score", report)
        self.assertIn("strong_skills", report)
        self.assertIn("weak_skills", report)
        self.assertIn("recommended_next_training", report)

    def test_10_get_teachers_ranking(self):
        ranking = self.teachers.get_teachers_ranking(limit=5)
        self.assertIsInstance(ranking, list)
        self.assertLessEqual(len(ranking), 5)

    def test_11_get_training_records(self):
        # 先完成一个培训
        self.teachers.complete_training(self.first_teacher_id, "AI基础", 85)
        records = self.teachers.get_training_records()
        self.assertIsInstance(records, list)

    def test_12_delete_teacher(self):
        teacher = self.teachers.create_teacher("测试删除", "数学", "城区")
        result = self.teachers.delete_teacher(teacher.teacher_id)
        self.assertTrue(result)
        self.assertIsNone(self.teachers.get_teacher_by_id(teacher.teacher_id))


class TestEvaluationExtensions(unittest.TestCase):
    """评估反馈扩展测试"""

    @classmethod
    def setUpClass(cls):
        cls.system = AutoEduSystem()
        cls.system.initialize_demo_data()
        cls.system.run_evaluation()
        cls.evaluation = cls.system.evaluation

    def test_01_get_evaluation_history(self):
        history = self.evaluation.get_evaluation_history()
        self.assertIsInstance(history, list)

    def test_02_get_quality_alerts(self):
        alerts = self.evaluation.get_quality_alerts()
        self.assertIsInstance(alerts, list)

    def test_03_get_evaluation_trend(self):
        trend = self.evaluation.get_evaluation_trend("learning_effect")
        self.assertIn("trend", trend)
        self.assertIn("current", trend)
        self.assertIn("periods", trend)

    def test_04_get_evaluation_detail(self):
        detail = self.evaluation.get_evaluation_detail("learning")
        self.assertIsNotNone(detail)

    def test_05_generate_evaluation_report(self):
        report = self.evaluation.generate_evaluation_report()
        self.assertIn("report_id", report)
        self.assertIn("overall_score", report)
        self.assertIn("learning_effect", report)
        self.assertIn("content_quality", report)
        self.assertIn("system_operation", report)

    def test_06_get_improvement_tasks(self):
        tasks = self.evaluation.get_improvement_tasks()
        self.assertIsInstance(tasks, list)

    def test_07_update_improvement_task(self):
        if self.evaluation.improvement_tasks:
            task_id = self.evaluation.improvement_tasks[0]["id"]
            result = self.evaluation.update_improvement_task(task_id, "处理中", "正在处理")
            self.assertTrue(result)
        else:
            self.skipTest("无改进任务")

    def test_08_acknowledge_alert(self):
        if self.evaluation.quality_alerts:
            alert_id = self.evaluation.quality_alerts[0].get("id", "")
            if alert_id:
                result = self.evaluation.acknowledge_alert(alert_id, "管理员", "已处理")
                self.assertTrue(result)
            else:
                self.skipTest("告警无ID")
        else:
            self.skipTest("无质量告警")


class TestEvolutionExtensions(unittest.TestCase):
    """演化引擎扩展测试"""

    @classmethod
    def setUpClass(cls):
        cls.system = AutoEduSystem()
        cls.system.initialize_demo_data()
        cls.system.run_evolution_cycle()
        cls.evolution = cls.system.evolution

    def test_01_get_evolution_history(self):
        history = self.evolution.get_evolution_history()
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)

    def test_02_get_mechanism_detail(self):
        detail = self.evolution.get_mechanism_detail("knowledge_update")
        self.assertIn("mechanism", detail)
        self.assertIn("total_executions", detail)
        self.assertIn("recent_records", detail)

    def test_03_get_mechanism_stats(self):
        stats = self.evolution.get_mechanism_stats()
        self.assertIsInstance(stats, dict)
        self.assertGreater(len(stats), 0)

    def test_04_get_evolution_effect(self):
        effect = self.evolution.get_evolution_effect()
        self.assertIn("total_cycles", effect)
        self.assertIn("success_rate", effect)
        self.assertIn("evolution_score", effect)
        self.assertIn("assessment", effect)

    def test_05_get_axiom_status(self):
        status = self.evolution.get_axiom_status()
        self.assertIsInstance(status, dict)

    def test_06_run_single_mechanism(self):
        result = self.evolution.run_single_mechanism("knowledge_update")
        self.assertIsNotNone(result)
        self.assertNotIn("error", result)

    def test_07_run_invalid_mechanism(self):
        result = self.evolution.run_single_mechanism("invalid_mechanism")
        self.assertIn("error", result)
        self.assertIn("available", result)


class TestCommonUtilsExtensions(unittest.TestCase):
    """通用工具扩展测试"""

    def test_01_compliance_check_detail(self):
        result = compliance_check_detail("这是一段正常的教学内容", "textbook")
        self.assertIn("passed", result)
        self.assertIn("dimensions", result)
        self.assertIn("compliance_score", result)
        self.assertIn("level", result)
        self.assertIn("suggestions", result)

    def test_02_compliance_check_detail_with_issues(self):
        result = compliance_check_detail("这段内容包含暴力和AI完全替代人类", "general")
        self.assertFalse(result["passed"])
        self.assertLess(result["compliance_score"], 100)

    def test_03_batch_compliance_check(self):
        items = ["正常内容1", "正常内容2", "包含暴力的内容"]
        result = batch_compliance_check(items)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["passed"], 2)
        self.assertEqual(result["failed"], 1)
        self.assertIn("pass_rate", result)
        self.assertIn("failed_items", result)

    def test_04_archive_and_get_root(self):
        record = archive_to_root("test", {"key": "value"}, {"source": "test"})
        self.assertIn("asset_id", record)
        archives = get_root_archives()
        self.assertGreater(len(archives), 0)

    def test_05_archive_and_get_sandbox(self):
        record = archive_to_sandbox("test", {"key": "value"})
        self.assertIn("asset_id", record)
        archives = get_sandbox_archives()
        self.assertGreater(len(archives), 0)

    def test_06_verify_archive_hash(self):
        record = archive_to_root("verify_test", {"data": "hash_test"})
        result = verify_archive_hash(record["asset_id"])
        self.assertTrue(result["verified"])
        self.assertEqual(result["expected_hash"], result["actual_hash"])

    def test_07_verify_invalid_archive(self):
        result = verify_archive_hash("non_existent_id")
        self.assertFalse(result["verified"])

    def test_08_export_archives(self):
        filepath = export_archives("root")
        self.assertTrue(os.path.exists(filepath))

    def test_09_compute_hash(self):
        h1 = compute_hash({"a": 1, "b": 2})
        h2 = compute_hash({"b": 2, "a": 1})
        self.assertEqual(h1, h2)  # 排序后哈希一致
        self.assertEqual(len(h1), 64)  # SHA256长度


class TestMainSystemExtensions(unittest.TestCase):
    """主调度器扩展测试"""

    @classmethod
    def setUpClass(cls):
        cls.system = AutoEduSystem()
        cls.system.initialize_demo_data()

    def test_01_export_all_data(self):
        filepath = self.system.export_all_data()
        self.assertTrue(os.path.exists(filepath))

    def test_02_module_health_check(self):
        result = self.system.module_health_check()
        self.assertIn("all_healthy", result)
        self.assertIn("modules", result)
        self.assertIn("checked_at", result)
        self.assertEqual(len(result["modules"]), 6)

    def test_03_get_module_status(self):
        status = self.system.get_module_status("knowledge_graph")
        self.assertIsNotNone(status)
        self.assertIn("total_entities", status)

    def test_04_get_invalid_module_status(self):
        result = self.system.get_module_status("invalid_module")
        self.assertIn("error", result)
        self.assertIn("available", result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
