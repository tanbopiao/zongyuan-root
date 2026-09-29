"""
端到端工程化落地测试
验证从知识点到最终视频文件的完整链路
所有功能全面打通，不留链路，不留断点
"""
import os
import sys
import unittest
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.main import AutoEduSystem
from src.video_pipeline.generator_service import GeneratorService
from src.video_pipeline.drama_bridge import DramaPipelineBridge
from src.video_pipeline.end_to_end import EndToEndVideoProducer


class TestGeneratorService(unittest.TestCase):
    """生成服务测试（仿真模式）"""

    @classmethod
    def setUpClass(cls):
        cls.service = GeneratorService(mode="simulation")

    def test_01_service_initialization(self):
        status = self.service.get_service_status()
        self.assertEqual(status["mode"], "simulation")
        self.assertTrue(status["ffmpeg_available"])

    def test_02_keyframe_generation(self):
        result = self.service.generate_keyframe(
            prompt="虚拟教室中AI教师讲解人工智能概念",
            shot_num="S01"
        )
        self.assertEqual(result["status"], "completed")
        self.assertTrue(os.path.exists(result["file_path"]))
        self.assertGreater(os.path.getsize(result["file_path"]), 0)

    def test_03_video_segment_generation(self):
        # 先生成关键帧
        kf = self.service.generate_keyframe(prompt="test", shot_num="S01")
        # 基于关键帧生成视频
        result = self.service.generate_video_segment(
            keyframe_path=kf["file_path"],
            video_prompt="镜头缓慢推进",
            shot_num="S01",
            duration=3
        )
        self.assertEqual(result["status"], "completed")
        self.assertTrue(os.path.exists(result["file_path"]))
        self.assertGreater(os.path.getsize(result["file_path"]), 0)

    def test_04_audio_generation(self):
        result = self.service.generate_audio(
            text="同学们好，今天我们来学习人工智能的基本概念。",
            shot_num="S01"
        )
        self.assertEqual(result["status"], "completed")
        self.assertTrue(os.path.exists(result["file_path"]))
        self.assertGreater(os.path.getsize(result["file_path"]), 0)

    def test_05_subtitle_generation(self):
        shots = [
            {"shot_num": "S01", "duration": 5, "narration": "同学们好"},
            {"shot_num": "S02", "duration": 5, "narration": "今天学习AI"}
        ]
        result = self.service.generate_subtitles(shots, "test_video")
        self.assertEqual(result["status"], "completed")
        self.assertTrue(os.path.exists(result["file_path"]))
        # 验证SRT格式
        with open(result["file_path"], 'r') as f:
            content = f.read()
        self.assertIn("1", content)
        self.assertIn("-->", content)

    def test_06_video_concatenation(self):
        # 生成两个视频片段
        v1 = self.service.generate_video_segment(shot_num="S01", duration=2)
        v2 = self.service.generate_video_segment(shot_num="S02", duration=2)
        # 拼接
        result = self.service.concatenate_videos(
            [v1["file_path"], v2["file_path"]],
            "test_concat"
        )
        self.assertEqual(result["status"], "completed")
        self.assertTrue(os.path.exists(result["file_path"]))
        self.assertGreater(os.path.getsize(result["file_path"]), 0)

    def test_07_audio_mixing(self):
        # 生成视频和音频
        v = self.service.generate_video_segment(shot_num="S01", duration=3)
        a = self.service.generate_audio(text="测试配音", shot_num="S01")
        # 混合
        result = self.service.mix_audio(
            v["file_path"], [a["file_path"]],
            "test_mix"
        )
        self.assertIn(result["status"], ["completed", "completed_fallback"])
        self.assertTrue(os.path.exists(result["file_path"]))

    def test_08_subtitle_burning(self):
        # 生成视频和字幕
        v = self.service.generate_video_segment(shot_num="S01", duration=3)
        shots = [{"shot_num": "S01", "duration": 3, "narration": "测试字幕"}]
        sub = self.service.generate_subtitles(shots, "test_sub")
        # 烧录字幕
        result = self.service.burn_subtitles(
            v["file_path"], sub["file_path"],
            "test_burn"
        )
        self.assertIn(result["status"], ["completed", "completed_fallback"])
        self.assertTrue(os.path.exists(result["file_path"]))


class TestDramaBridge(unittest.TestCase):
    """短剧流水线对接测试"""

    @classmethod
    def setUpClass(cls):
        cls.bridge = DramaPipelineBridge()

    def test_01_bridge_initialization(self):
        status = self.bridge.get_bridge_status()
        self.assertIn("drama_pipeline_available", status)
        self.assertIn("bridge_dir", status)

    def test_02_export_drama_storyboard(self):
        storyboard = {
            "title": "测试教学视频",
            "total_shots": 2,
            "total_duration": 10,
            "shots": [
                {
                    "shot_num": "S01",
                    "visual_description": "虚拟教室",
                    "duration": 5,
                    "keyframe_prompt": "test kf1",
                    "video_prompt": "test vid1",
                    "audio": "test audio1",
                    "transition": "硬切"
                },
                {
                    "shot_num": "S02",
                    "visual_description": "知识空间",
                    "duration": 5,
                    "keyframe_prompt": "test kf2",
                    "video_prompt": "test vid2",
                    "audio": "test audio2",
                    "transition": "硬切"
                }
            ]
        }
        result = self.bridge.export_drama_compatible_storyboard(storyboard, "test")
        self.assertEqual(result["status"], "completed")
        self.assertTrue(os.path.exists(result["file_path"]))
        # 验证短剧标准字段
        with open(result["file_path"], 'r') as f:
            data = json.load(f)
        self.assertIn("shots", data)
        self.assertIn("镜号", data["shots"][0])
        self.assertIn("画面描述", data["shots"][0])
        self.assertIn("关键帧提示词", data["shots"][0])
        self.assertIn("视频提示词", data["shots"][0])
        self.assertIn("音效配乐", data["shots"][0])
        self.assertIn("转场方式", data["shots"][0])


class TestEndToEndProduction(unittest.TestCase):
    """端到端视频成片生产测试（核心：全链路打通验证）"""

    @classmethod
    def setUpClass(cls):
        cls.system = AutoEduSystem()
        cls.system.initialize_demo_data()
        cls.first_entity_id = list(cls.system.kg.entities.keys())[0]

    def test_01_e2e_full_pipeline(self):
        """端到端完整流水线：知识点→最终mp4"""
        result = self.system.produce_final_video(
            self.first_entity_id,
            stage="初中",
            duration_minutes=1,
            generate_keyframes=True,
            generate_video=True,
            generate_audio=True,
            burn_subtitles=True
        )
        self.assertEqual(result["status"], "completed")
        self.assertIn("run_id", result)

        # 验证11个阶段都有记录
        stages = result["stages"]
        expected_stages = [
            "knowledge_fetch", "script_generation", "storyboard_generation",
            "keyframe_generation", "video_segment_generation", "audio_generation",
            "subtitle_generation", "video_concatenation", "audio_mixing",
            "subtitle_burning", "final_delivery"
        ]
        for stage in expected_stages:
            self.assertIn(stage, stages, f"缺少阶段: {stage}")

        # 验证关键阶段完成
        self.assertEqual(stages["script_generation"]["status"], "completed")
        self.assertEqual(stages["storyboard_generation"]["status"], "completed")
        self.assertEqual(stages["keyframe_generation"]["status"], "completed")
        self.assertEqual(stages["video_segment_generation"]["status"], "completed")
        self.assertEqual(stages["audio_generation"]["status"], "completed")
        self.assertEqual(stages["subtitle_generation"]["status"], "completed")
        self.assertEqual(stages["video_concatenation"]["status"], "completed")
        self.assertEqual(stages["final_delivery"]["status"], "completed")

        # 验证最终视频文件存在
        final_video = stages["final_delivery"].get("final_video")
        self.assertIsNotNone(final_video)
        self.assertTrue(os.path.exists(final_video["file_path"]))
        self.assertGreater(final_video["file_size_bytes"], 0)
        self.assertEqual(final_video["format"], "mp4")

    def test_02_e2e_with_drama_pipeline_export(self):
        """端到端+短剧流水线导出"""
        result = self.system.produce_final_video(
            self.first_entity_id,
            stage="小学",
            duration_minutes=1,
            generate_keyframes=False,  # 跳过关键帧加速
            generate_video=True,
            generate_audio=False,
            burn_subtitles=False,
            use_drama_pipeline=True
        )
        self.assertEqual(result["status"], "completed")
        self.assertIn("drama_pipeline_export", result)
        self.assertEqual(result["drama_pipeline_export"]["status"], "completed")

    def test_03_e2e_different_stages(self):
        """四学段端到端生产验证"""
        for stage in ["小学", "初中", "高中", "中职"]:
            result = self.system.produce_final_video(
                self.first_entity_id,
                stage=stage,
                duration_minutes=1,
                generate_keyframes=False,
                generate_video=True,
                generate_audio=False,
                burn_subtitles=False
            )
            self.assertEqual(result["status"], "completed", f"{stage}学段生产失败")
            self.assertEqual(result["stage"], stage)

    def test_04_e2e_batch_production(self):
        """批量端到端生产"""
        entity_ids = list(self.system.kg.entities.keys())[:2]
        result = self.system.batch_produce_final_videos(
            entity_ids,
            stage="初中",
            duration_minutes=1,
            generate_keyframes=False,
            generate_video=True,
            generate_audio=False,
            burn_subtitles=False
        )
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["completed"], 2)

    def test_05_e2e_production_status(self):
        """端到端生产状态"""
        status = self.system.get_e2e_production_status()
        self.assertIn("total_runs", status)
        self.assertIn("mode", status)
        self.assertIn("generator_status", status)
        self.assertIn("drama_bridge_status", status)
        self.assertGreater(status["total_runs"], 0)

    def test_06_system_integration(self):
        """系统集成验证：主调度器包含端到端生产者"""
        self.assertIsNotNone(self.system.e2e_producer)
        status = self.system.get_system_status()
        self.assertIn("e2e_producer", status["modules"])

    def test_07_save_and_load(self):
        """数据保存验证"""
        filepath = self.system.e2e_producer.save_all()
        self.assertTrue(os.path.exists(filepath))
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)


class TestEngineeringMetaRule(unittest.TestCase):
    """可工程化落地元规则验证"""

    def test_01_no_broken_links(self):
        """验证所有链路无断点：每个生成阶段都有实际输出文件"""
        service = GeneratorService(mode="simulation")
        # 关键帧
        kf = service.generate_keyframe(prompt="test", shot_num="S01")
        self.assertTrue(os.path.exists(kf["file_path"]))
        # 视频
        vid = service.generate_video_segment(
            keyframe_path=kf["file_path"], shot_num="S01", duration=2
        )
        self.assertTrue(os.path.exists(vid["file_path"]))
        # 音频
        aud = service.generate_audio(text="test", shot_num="S01")
        self.assertTrue(os.path.exists(aud["file_path"]))
        # 字幕
        sub = service.generate_subtitles(
            [{"shot_num": "S01", "duration": 2, "narration": "test"}],
            "meta_test"
        )
        self.assertTrue(os.path.exists(sub["file_path"]))
        # 拼接
        concat = service.concatenate_videos([vid["file_path"]], "meta_test")
        self.assertTrue(os.path.exists(concat["file_path"]))
        # 最终成片
        final = service.burn_subtitles(concat["file_path"], sub["file_path"], "meta_test")
        self.assertTrue(os.path.exists(final["file_path"]))

    def test_02_all_modules_importable(self):
        """验证所有模块可正常导入（无依赖断裂）"""
        modules = [
            "src.video_pipeline.script_generator",
            "src.video_pipeline.storyboard_generator",
            "src.video_pipeline.asset_manager",
            "src.video_pipeline.generator_service",
            "src.video_pipeline.drama_bridge",
            "src.video_pipeline.end_to_end",
            "src.video_pipeline.pipeline"
        ]
        for mod in modules:
            try:
                __import__(mod)
            except ImportError as e:
                self.fail(f"模块导入失败: {mod}, 错误: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
