"""
视频教学内容生产通道测试
对接短剧流水线的教育视频工业化生产
"""
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.main import AutoEduSystem
from src.video_pipeline.script_generator import TeachingScriptGenerator
from src.video_pipeline.storyboard_generator import EduStoryboardGenerator
from src.video_pipeline.asset_manager import VideoAssetManager
from src.video_pipeline.pipeline import VideoTeachingPipeline


class TestScriptGenerator(unittest.TestCase):
    """教学脚本生成器测试"""

    @classmethod
    def setUpClass(cls):
        cls.system = AutoEduSystem()
        cls.system.initialize_demo_data()
        cls.gen = TeachingScriptGenerator(cls.system.kg)
        cls.first_entity_id = list(cls.system.kg.entities.keys())[0]

    def test_01_generate_script(self):
        script = self.gen.generate_script(self.first_entity_id, "初中", 3)
        self.assertIsNotNone(script)
        self.assertIn("script_id", script)
        self.assertIn("title", script)
        self.assertIn("segments", script)
        self.assertEqual(len(script["segments"]), 5)
        self.assertGreater(script["target_duration_seconds"], 0)

    def test_02_script_segments_structure(self):
        script = self.gen.generate_script(self.first_entity_id, "初中", 3)
        for seg in script["segments"]:
            self.assertIn("segment_num", seg)
            self.assertIn("name", seg)
            self.assertIn("type", seg)
            self.assertIn("duration", seg)
            self.assertIn("narration", seg)
            self.assertIn("visual_description", seg)

    def test_03_different_stages(self):
        for stage in ["小学", "初中", "高中", "中职"]:
            script = self.gen.generate_script(self.first_entity_id, stage, 3)
            self.assertEqual(script["stage"], stage)
            self.assertIn(stage, script["title"])

    def test_04_teaching_objectives(self):
        script = self.gen.generate_script(self.first_entity_id, "初中", 3)
        self.assertIn("teaching_objectives", script)
        self.assertGreaterEqual(len(script["teaching_objectives"]), 3)

    def test_05_characters_selection(self):
        script = self.gen.generate_script(self.first_entity_id, "小学", 3)
        self.assertIn("characters", script)
        self.assertGreater(len(script["characters"]), 0)

    def test_06_full_narration(self):
        script = self.gen.generate_script(self.first_entity_id, "初中", 3)
        self.assertIn("full_narration", script)
        self.assertGreater(len(script["full_narration"]), 100)

    def test_07_script_stats(self):
        self.gen.generate_script(self.first_entity_id, "初中", 3)
        stats = self.gen.get_script_stats()
        self.assertIn("total_scripts", stats)
        self.assertGreater(stats["total_scripts"], 0)

    def test_08_save_scripts(self):
        filepath = self.gen.save_all()
        self.assertTrue(os.path.exists(filepath))


class TestStoryboardGenerator(unittest.TestCase):
    """教育风格分镜表生成器测试"""

    @classmethod
    def setUpClass(cls):
        cls.system = AutoEduSystem()
        cls.system.initialize_demo_data()
        cls.script_gen = TeachingScriptGenerator(cls.system.kg)
        cls.sb_gen = EduStoryboardGenerator()
        cls.first_entity_id = list(cls.system.kg.entities.keys())[0]
        cls.script = cls.script_gen.generate_script(cls.first_entity_id, "初中", 3)

    def test_01_generate_storyboard(self):
        sb = self.sb_gen.generate_storyboard(self.script)
        self.assertIsNotNone(sb)
        self.assertIn("storyboard_id", sb)
        self.assertIn("shots", sb)
        self.assertGreater(sb["total_shots"], 0)
        self.assertGreater(sb["total_duration"], 0)

    def test_02_shot_structure(self):
        sb = self.sb_gen.generate_storyboard(self.script)
        for shot in sb["shots"]:
            self.assertIn("shot_num", shot)
            self.assertIn("shot_type", shot)
            self.assertIn("duration", shot)
            self.assertIn("visual_description", shot)
            self.assertIn("keyframe_prompt", shot)
            self.assertIn("video_prompt", shot)
            self.assertIn("narration", shot)
            self.assertIn("audio", shot)
            self.assertIn("transition", shot)

    def test_03_drama_pipeline_compatible(self):
        sb = self.sb_gen.generate_storyboard(self.script)
        self.assertEqual(sb["format"], "drama-pipeline-compatible")

    def test_04_export_for_drama_pipeline(self):
        sb = self.sb_gen.generate_storyboard(self.script)
        drama_format = self.sb_gen.export_for_drama_pipeline(sb)
        self.assertIn("episode_title", drama_format)
        self.assertIn("shots", drama_format)
        self.assertIn("format_version", drama_format)
        # 短剧流水线标准字段
        for shot in drama_format["shots"]:
            self.assertIn("镜号", shot)
            self.assertIn("画面描述", shot)
            self.assertIn("时长", shot)
            self.assertIn("关键帧提示词", shot)
            self.assertIn("视频提示词", shot)
            self.assertIn("音效配乐", shot)
            self.assertIn("转场方式", shot)

    def test_05_edu_visual_styles(self):
        self.assertIn("虚拟教室", EduStoryboardGenerator.EDU_VISUAL_STYLES)
        self.assertIn("知识空间", EduStoryboardGenerator.EDU_VISUAL_STYLES)
        self.assertIn("实操实验室", EduStoryboardGenerator.EDU_VISUAL_STYLES)
        self.assertIn("动画演示", EduStoryboardGenerator.EDU_VISUAL_STYLES)

    def test_06_storyboard_stats(self):
        self.sb_gen.generate_storyboard(self.script)
        stats = self.sb_gen.get_storyboard_stats()
        self.assertIn("total_storyboards", stats)
        self.assertGreater(stats["total_storyboards"], 0)

    def test_07_save_storyboards(self):
        filepath = self.sb_gen.save_all()
        self.assertTrue(os.path.exists(filepath))


class TestAssetManager(unittest.TestCase):
    """视频资产管理器测试"""

    @classmethod
    def setUpClass(cls):
        cls.manager = VideoAssetManager()

    def test_01_register_asset(self):
        asset = self.manager.register_asset(
            "script",
            {"title": "测试脚本", "content": "测试内容"},
            {"knowledge_point_id": "test_kp", "stage": "初中"}
        )
        self.assertIsNotNone(asset)
        self.assertIn("asset_id", asset)
        self.assertEqual(asset["asset_type"], "script")
        self.assertEqual(asset["status"], "archived")

    def test_02_get_asset(self):
        asset = self.manager.register_asset("storyboard", {"test": True})
        found = self.manager.get_asset(asset["asset_id"])
        self.assertIsNotNone(found)
        self.assertEqual(found["asset_id"], asset["asset_id"])

    def test_03_get_assets_by_type(self):
        self.manager.register_asset("video", {"test": True})
        videos = self.manager.get_assets_by_type("video")
        self.assertGreater(len(videos), 0)

    def test_04_get_asset_content(self):
        asset = self.manager.register_asset("audio", {"narration": "测试旁白"})
        content = self.manager.get_asset_content(asset["asset_id"])
        self.assertIsNotNone(content)
        self.assertIn("narration", content)

    def test_05_verify_asset_integrity(self):
        asset = self.manager.register_asset("thumbnail", {"image": "test"})
        result = self.manager.verify_asset_integrity(asset["asset_id"])
        self.assertTrue(result["verified"])

    def test_06_asset_stats(self):
        stats = self.manager.get_asset_stats()
        self.assertIn("total_assets", stats)
        self.assertIn("by_type", stats)
        self.assertIn("by_status", stats)

    def test_07_export_manifest(self):
        manifest = self.manager.export_asset_manifest()
        self.assertIn("manifest_id", manifest)
        self.assertIn("manifest_hash", manifest)
        self.assertIn("assets", manifest)

    def test_08_save_all(self):
        filepath = self.manager.save_all()
        self.assertTrue(os.path.exists(filepath))


class TestVideoPipeline(unittest.TestCase):
    """视频教学内容生产通道主调度器测试"""

    @classmethod
    def setUpClass(cls):
        cls.system = AutoEduSystem()
        cls.system.initialize_demo_data()
        cls.pipeline = VideoTeachingPipeline(cls.system.kg)
        cls.first_entity_id = list(cls.system.kg.entities.keys())[0]

    def test_01_pipeline_initialization(self):
        self.assertIsNotNone(self.pipeline.script_gen)
        self.assertIsNotNone(self.pipeline.storyboard_gen)
        self.assertIsNotNone(self.pipeline.asset_manager)

    def test_02_produce_video_content(self):
        result = self.pipeline.produce_video_content(
            self.first_entity_id, "初中", 3,
            generate_keyframes=True, auto_archive=True
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "completed")
        self.assertIn("run_id", result)
        self.assertIn("stages", result)
        # 检查6个阶段
        self.assertIn("script_generation", result["stages"])
        self.assertIn("storyboard_generation", result["stages"])
        self.assertIn("keyframe_preparation", result["stages"])
        self.assertIn("video_generation", result["stages"])
        self.assertIn("audio_mixing", result["stages"])
        self.assertIn("archive_and_delivery", result["stages"])

    def test_03_script_stage_completed(self):
        result = self.pipeline.produce_video_content(self.first_entity_id, "初中", 3)
        self.assertEqual(result["stages"]["script_generation"]["status"], "completed")
        self.assertIn("script_id", result["stages"]["script_generation"])

    def test_04_storyboard_stage_completed(self):
        result = self.pipeline.produce_video_content(self.first_entity_id, "初中", 3)
        self.assertEqual(result["stages"]["storyboard_generation"]["status"], "completed")
        self.assertGreater(result["stages"]["storyboard_generation"]["total_shots"], 0)

    def test_05_drama_pipeline_ready(self):
        result = self.pipeline.produce_video_content(self.first_entity_id, "初中", 3)
        self.assertEqual(result["stages"]["video_generation"]["status"], "ready_for_drama_pipeline")
        self.assertTrue(result["stages"]["video_generation"]["drama_format_ready"])
        self.assertIn("video_spec", result["stages"]["video_generation"])

    def test_06_different_stages(self):
        for stage in ["小学", "初中", "高中", "中职"]:
            result = self.pipeline.produce_video_content(self.first_entity_id, stage, 2)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["stage"], stage)

    def test_07_batch_produce(self):
        entity_ids = list(self.system.kg.entities.keys())[:3]
        result = self.pipeline.batch_produce(entity_ids, "初中", 2)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["completed"], 3)

    def test_08_pipeline_stats(self):
        self.pipeline.produce_video_content(self.first_entity_id, "初中", 2)
        stats = self.pipeline.get_pipeline_stats()
        self.assertIn("total_runs", stats)
        self.assertGreater(stats["total_runs"], 0)
        self.assertIn("script_stats", stats)
        self.assertIn("storyboard_stats", stats)
        self.assertIn("asset_stats", stats)

    def test_09_run_history(self):
        self.pipeline.produce_video_content(self.first_entity_id, "初中", 2)
        history = self.pipeline.get_run_history(5)
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)

    def test_10_save_all(self):
        filepath = self.pipeline.save_all()
        self.assertTrue(os.path.exists(filepath))


class TestVideoPipelineIntegration(unittest.TestCase):
    """视频通道与主系统集成测试"""

    @classmethod
    def setUpClass(cls):
        cls.system = AutoEduSystem()
        cls.system.initialize_demo_data()
        cls.first_entity_id = list(cls.system.kg.entities.keys())[0]

    def test_01_system_has_video_pipeline(self):
        self.assertIsNotNone(self.system.video_pipeline)

    def test_02_produce_teaching_video(self):
        result = self.system.produce_teaching_video(self.first_entity_id, "初中", 2)
        self.assertEqual(result["status"], "completed")

    def test_03_batch_produce(self):
        entity_ids = list(self.system.kg.entities.keys())[:2]
        result = self.system.batch_produce_teaching_videos(entity_ids, "初中", 2)
        self.assertEqual(result["completed"], 2)

    def test_04_video_pipeline_status(self):
        status = self.system.get_video_pipeline_status()
        self.assertIn("total_runs", status)

    def test_05_system_status_includes_video(self):
        status = self.system.get_system_status()
        self.assertIn("video_pipeline", status["modules"])

    def test_06_save_all_includes_video(self):
        self.system.save_all_data()
        # 检查视频数据文件是否生成
        video_files = [
            "video_scripts.json",
            "video_storyboards.json",
            "video_assets_index.json",
            "video_pipeline_runs.json"
        ]
        data_dir = os.path.join(BASE_DIR, "data")
        for f in video_files:
            self.assertTrue(os.path.exists(os.path.join(data_dir, f)), f"缺少文件: {f}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
