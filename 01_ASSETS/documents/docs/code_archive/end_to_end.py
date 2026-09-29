"""
端到端教学视频成片输出调度器
从知识点 → 最终教学视频文件的完整工业化流水线
可工程化落地核心：所有链路打通，不留断点
完整10步流水线：
1. 知识点获取 → 2. 教学脚本 → 3. 分镜表 → 4. 关键帧图片
→ 5. 视频片段 → 6. 配音音频 → 7. 字幕文件
→ 8. 视频拼接 → 9. 音频混合 → 10. 字幕压制 → 最终成片
"""
import os
import sys
import json
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from config.settings import DATA_DIR, DID, ANCHOR
from src.common.utils import setup_logger, generate_asset_id, compute_hash
from src.video_pipeline.script_generator import TeachingScriptGenerator
from src.video_pipeline.storyboard_generator import EduStoryboardGenerator
from src.video_pipeline.asset_manager import VideoAssetManager
from src.video_pipeline.generator_service import GeneratorService
from src.video_pipeline.drama_bridge import DramaPipelineBridge

logger = setup_logger("end_to_end", "video_pipeline.log")


class EndToEndVideoProducer:
    """
    端到端教学视频成片生产者
    从知识点到最终视频文件，10步完整流水线，全链路打通
    """

    PIPELINE_STAGES = [
        "knowledge_fetch",       # 1. 知识点获取
        "script_generation",     # 2. 教学脚本生成
        "storyboard_generation", # 3. 分镜表生成
        "keyframe_generation",   # 4. 关键帧图片生成
        "video_segment_generation", # 5. 视频片段生成
        "audio_generation",      # 6. 配音音频生成
        "subtitle_generation",   # 7. 字幕文件生成
        "video_concatenation",   # 8. 视频片段拼接
        "audio_mixing",          # 9. 音频混合
        "subtitle_burning",      # 10. 字幕压制
        "final_delivery"         # 11. 最终成片交付
    ]

    def __init__(self, knowledge_graph=None, mode="simulation"):
        self.kg = knowledge_graph
        self.mode = mode
        self.script_gen = TeachingScriptGenerator(knowledge_graph)
        self.storyboard_gen = EduStoryboardGenerator()
        self.asset_manager = VideoAssetManager()
        self.generator = GeneratorService(mode)
        self.drama_bridge = DramaPipelineBridge()
        self.production_runs = []
        logger.info(f"端到端视频成片生产者初始化完成，模式: {mode}")

    def produce_final_video(self, entity_id, stage="初中", duration_minutes=3,
                            generate_keyframes=True, generate_video=True,
                            generate_audio=True, burn_subtitles=True,
                            use_drama_pipeline=False):
        """
        生产最终教学视频成片（端到端完整流水线）
        entity_id: 知识点ID
        stage: 学段
        duration_minutes: 目标时长
        generate_keyframes: 是否生成关键帧图片
        generate_video: 是否生成视频片段
        generate_audio: 是否生成配音音频
        burn_subtitles: 是否烧录字幕
        use_drama_pipeline: 是否调用短剧流水线
        """
        run_id = generate_asset_id("E2E-RUN")
        run_start = datetime.now()
        logger.info(f"{'='*60}")
        logger.info(f"端到端视频生产启动: {run_id}")
        logger.info(f"知识点: {entity_id}, 学段: {stage}, 时长: {duration_minutes}分钟")
        logger.info(f"模式: {self.mode}, 关键帧: {generate_keyframes}, 视频: {generate_video}, 音频: {generate_audio}, 字幕: {burn_subtitles}")
        logger.info(f"{'='*60}")

        result = {
            "run_id": run_id,
            "entity_id": entity_id,
            "stage": stage,
            "target_duration_minutes": duration_minutes,
            "mode": self.mode,
            "stages": {},
            "status": "running",
            "started_at": run_start.isoformat()
        }

        try:
            # ===== Stage 1: 知识点获取 =====
            logger.info("[Stage 1/11] 获取知识点...")
            entity = self._get_knowledge_entity(entity_id)
            result["stages"]["knowledge_fetch"] = {
                "status": "completed",
                "entity_id": entity_id,
                "entity_name": entity.get("name", entity_id) if entity else entity_id,
                "entity_found": entity is not None
            }

            # ===== Stage 2: 教学脚本生成 =====
            logger.info("[Stage 2/11] 生成教学脚本...")
            script = self.script_gen.generate_script(entity_id, stage, duration_minutes)
            result["stages"]["script_generation"] = {
                "status": "completed",
                "script_id": script["script_id"],
                "title": script["title"],
                "segments": len(script["segments"]),
                "duration": script["target_duration_seconds"]
            }
            self.asset_manager.register_asset("script", script, {
                "knowledge_point_id": entity_id, "stage": stage, "run_id": run_id
            })

            # ===== Stage 3: 分镜表生成 =====
            logger.info("[Stage 3/11] 生成分镜表...")
            storyboard = self.storyboard_gen.generate_storyboard(script)
            result["stages"]["storyboard_generation"] = {
                "status": "completed",
                "storyboard_id": storyboard["storyboard_id"],
                "total_shots": storyboard["total_shots"],
                "total_duration": storyboard["total_duration"]
            }
            self.asset_manager.register_asset("storyboard", storyboard, {
                "knowledge_point_id": entity_id, "stage": stage, "run_id": run_id
            })

            # ===== Stage 4: 关键帧图片生成 =====
            keyframe_paths = []
            if generate_keyframes:
                logger.info(f"[Stage 4/11] 生成关键帧图片（{storyboard['total_shots']}个镜头）...")
                for shot in storyboard["shots"]:
                    kf_result = self.generator.generate_keyframe(
                        prompt=shot["keyframe_prompt"],
                        shot_num=shot["shot_num"]
                    )
                    if kf_result.get("status") == "completed":
                        keyframe_paths.append(kf_result["file_path"])
                result["stages"]["keyframe_generation"] = {
                    "status": "completed",
                    "total_keyframes": len(keyframe_paths),
                    "keyframe_paths": keyframe_paths[:5]  # 只记录前5个路径
                }
                self.asset_manager.register_asset("keyframe", {
                    "count": len(keyframe_paths),
                    "paths": keyframe_paths
                }, {"knowledge_point_id": entity_id, "run_id": run_id})
            else:
                result["stages"]["keyframe_generation"] = {"status": "skipped"}

            # ===== Stage 5: 视频片段生成 =====
            video_segment_paths = []
            if generate_video:
                logger.info(f"[Stage 5/11] 生成视频片段（{storyboard['total_shots']}段）...")
                for i, shot in enumerate(storyboard["shots"]):
                    kf_path = keyframe_paths[i] if i < len(keyframe_paths) else None
                    vid_result = self.generator.generate_video_segment(
                        keyframe_path=kf_path,
                        video_prompt=shot["video_prompt"],
                        shot_num=shot["shot_num"],
                        duration=min(shot["duration"], 5)  # 限制单段最长5秒
                    )
                    if vid_result.get("status") == "completed":
                        video_segment_paths.append(vid_result["file_path"])
                result["stages"]["video_segment_generation"] = {
                    "status": "completed",
                    "total_segments": len(video_segment_paths),
                    "total_duration_estimate": sum(min(s["duration"], 5) for s in storyboard["shots"])
                }
            else:
                result["stages"]["video_segment_generation"] = {"status": "skipped"}

            # ===== Stage 6: 配音音频生成 =====
            audio_paths = []
            if generate_audio:
                logger.info(f"[Stage 6/11] 生成配音音频（{len(script['segments'])}段）...")
                for seg in script["segments"]:
                    audio_result = self.generator.generate_audio(
                        text=seg["narration"],
                        shot_num=f"SEG{seg['segment_num']}"
                    )
                    if audio_result.get("status") == "completed":
                        audio_paths.append(audio_result["file_path"])
                result["stages"]["audio_generation"] = {
                    "status": "completed",
                    "total_audio_clips": len(audio_paths)
                }
                self.asset_manager.register_asset("audio", {
                    "count": len(audio_paths),
                    "paths": audio_paths
                }, {"knowledge_point_id": entity_id, "run_id": run_id})
            else:
                result["stages"]["audio_generation"] = {"status": "skipped"}

            # ===== Stage 7: 字幕文件生成 =====
            logger.info("[Stage 7/11] 生成字幕文件...")
            subtitle_result = self.generator.generate_subtitles(
                storyboard["shots"],
                output_name=f"{entity_id}_{stage}"
            )
            subtitle_path = subtitle_result.get("file_path")
            result["stages"]["subtitle_generation"] = {
                "status": subtitle_result["status"],
                "subtitle_path": subtitle_path,
                "total_subtitles": subtitle_result.get("total_subtitles", 0)
            }

            # ===== Stage 8: 视频片段拼接 =====
            concat_path = None
            if video_segment_paths:
                logger.info(f"[Stage 8/11] 拼接视频片段（{len(video_segment_paths)}段）...")
                concat_result = self.generator.concatenate_videos(
                    video_segment_paths,
                    output_name=f"{entity_id}_{stage}"
                )
                concat_path = concat_result.get("file_path")
                result["stages"]["video_concatenation"] = {
                    "status": concat_result["status"],
                    "concat_path": concat_path,
                    "segments_concatenated": len(video_segment_paths)
                }
            else:
                result["stages"]["video_concatenation"] = {"status": "skipped", "reason": "无视频片段"}

            # ===== Stage 9: 音频混合 =====
            mixed_path = concat_path
            if audio_paths and concat_path:
                logger.info("[Stage 9/11] 混合配音音频...")
                mix_result = self.generator.mix_audio(
                    concat_path, audio_paths,
                    output_name=f"{entity_id}_{stage}"
                )
                mixed_path = mix_result.get("file_path")
                result["stages"]["audio_mixing"] = {
                    "status": mix_result["status"],
                    "mixed_path": mixed_path,
                    "audio_tracks": len(audio_paths)
                }
            else:
                result["stages"]["audio_mixing"] = {"status": "skipped"}

            # ===== Stage 10: 字幕压制 =====
            final_path = mixed_path
            if burn_subtitles and subtitle_path and mixed_path:
                logger.info("[Stage 10/11] 压制字幕...")
                burn_result = self.generator.burn_subtitles(
                    mixed_path, subtitle_path,
                    output_name=f"{entity_id}_{stage}"
                )
                final_path = burn_result.get("file_path")
                result["stages"]["subtitle_burning"] = {
                    "status": burn_result["status"],
                    "final_path": final_path
                }
            else:
                result["stages"]["subtitle_burning"] = {"status": "skipped"}

            # ===== Stage 11: 最终成片交付 =====
            logger.info("[Stage 11/11] 最终成片交付...")
            final_video_info = None
            if final_path and os.path.exists(final_path):
                file_size = os.path.getsize(final_path)
                final_hash = compute_hash({"path": final_path, "size": file_size})
                final_video_info = {
                    "file_path": final_path,
                    "file_name": os.path.basename(final_path),
                    "file_size_bytes": file_size,
                    "file_size_mb": round(file_size / 1024 / 1024, 2),
                    "content_hash": final_hash,
                    "format": "mp4",
                    "resolution": "1920x1080",
                    "has_subtitles": burn_subtitles,
                    "has_audio": generate_audio
                }
                # 归档最终视频
                self.asset_manager.register_asset("video", final_video_info, {
                    "knowledge_point_id": entity_id, "stage": stage, "run_id": run_id,
                    "is_final": True
                })

            result["stages"]["final_delivery"] = {
                "status": "completed" if final_video_info else "no_output",
                "final_video": final_video_info
            }

            # 短剧流水线对接（可选）
            if use_drama_pipeline:
                logger.info("[附加] 导出短剧流水线兼容格式...")
                drama_export = self.drama_bridge.export_drama_compatible_storyboard(storyboard)
                result["drama_pipeline_export"] = drama_export

            result["status"] = "completed"
            result["completed_at"] = datetime.now().isoformat()
            result["duration_seconds"] = (datetime.now() - run_start).total_seconds()
            result["final_video_path"] = final_path

            self.production_runs.append(result)
            logger.info(f"{'='*60}")
            logger.info(f"端到端视频生产完成: {run_id}")
            logger.info(f"最终成片: {final_path}")
            logger.info(f"耗时: {result['duration_seconds']:.2f}秒")
            logger.info(f"{'='*60}")
            return result

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            result["failed_at"] = datetime.now().isoformat()
            self.production_runs.append(result)
            logger.error(f"端到端视频生产失败: {run_id}, 错误: {e}")
            import traceback
            traceback.print_exc()
            return result

    def _get_knowledge_entity(self, entity_id):
        """从知识图谱获取知识点"""
        if self.kg and entity_id in self.kg.entities:
            return self.kg.entities[entity_id]
        return {"id": entity_id, "name": entity_id, "description": "知识点"}

    def batch_produce_final_videos(self, entity_ids, stage="初中", duration_minutes=2, **kwargs):
        """批量生产最终教学视频"""
        results = []
        for entity_id in entity_ids:
            result = self.produce_final_video(entity_id, stage, duration_minutes, **kwargs)
            results.append(result)
        return {
            "total": len(results),
            "completed": len([r for r in results if r["status"] == "completed"]),
            "failed": len([r for r in results if r["status"] == "failed"]),
            "results": results
        }

    def get_production_stats(self):
        """获取生产统计"""
        return {
            "total_runs": len(self.production_runs),
            "completed_runs": len([r for r in self.production_runs if r["status"] == "completed"]),
            "failed_runs": len([r for r in self.production_runs if r["status"] == "failed"]),
            "mode": self.mode,
            "generator_status": self.generator.get_service_status(),
            "drama_bridge_status": self.drama_bridge.get_bridge_status()
        }

    def save_all(self):
        """保存所有数据"""
        self.script_gen.save_all()
        self.storyboard_gen.save_all()
        self.asset_manager.save_all()
        filepath = os.path.join(DATA_DIR, "e2e_production_runs.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.production_runs, f, ensure_ascii=False, indent=2)
        logger.info(f"端到端生产数据已保存，共{len(self.production_runs)}次生产记录")
        return filepath
