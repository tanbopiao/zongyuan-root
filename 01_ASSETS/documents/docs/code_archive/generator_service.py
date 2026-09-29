"""
生成服务抽象层
定义统一的图像/视频/音频生成接口
支持仿真模式（可独立运行）和API模式（调用真实生成服务）
可工程化落地核心：所有生成能力通过统一接口调用，可插拔替换
"""
import os
import sys
import json
import time
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from config.settings import DATA_DIR, DID, ANCHOR
from src.common.utils import setup_logger, generate_asset_id

logger = setup_logger("generator_service", "video_pipeline.log")

# 生成输出目录
GENERATOR_OUTPUT_DIR = os.path.join(DATA_DIR, "generated_media")
os.makedirs(os.path.join(GENERATOR_OUTPUT_DIR, "keyframes"), exist_ok=True)
os.makedirs(os.path.join(GENERATOR_OUTPUT_DIR, "videos"), exist_ok=True)
os.makedirs(os.path.join(GENERATOR_OUTPUT_DIR, "audio"), exist_ok=True)
os.makedirs(os.path.join(GENERATOR_OUTPUT_DIR, "subtitles"), exist_ok=True)
os.makedirs(os.path.join(GENERATOR_OUTPUT_DIR, "final"), exist_ok=True)


class BaseGenerator(ABC):
    """生成器基类"""

    def __init__(self, mode="simulation"):
        self.mode = mode  # simulation / api
        self.output_dir = GENERATOR_OUTPUT_DIR

    @abstractmethod
    def generate(self, *args, **kwargs):
        """生成方法，子类实现"""
        pass

    def _get_output_path(self, subdir, filename):
        """获取输出文件路径"""
        path = os.path.join(self.output_dir, subdir, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path


class KeyframeGenerator(BaseGenerator):
    """关键帧图像生成器"""

    def generate(self, prompt, shot_num="S01", width=1920, height=1080, style="edu"):
        """
        生成关键帧图像
        prompt: 图像生成提示词
        返回: 图像文件路径
        """
        asset_id = generate_asset_id("KEYFRAME")
        filename = f"{asset_id}_{shot_num}.png"
        output_path = self._get_output_path("keyframes", filename)

        if self.mode == "simulation":
            return self._simulate_keyframe(prompt, output_path, width, height, shot_num)
        else:
            return self._api_generate_keyframe(prompt, output_path, width, height)

    def _simulate_keyframe(self, prompt, output_path, width, height, shot_num):
        """仿真模式：用ffmpeg生成带文字的占位图像"""
        # 生成纯色背景+文字的占位图
        text = f"Keyframe {shot_num}"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=1a3a5c:s={width}x{height}:d=1",
            "-vf", f"drawtext=text='{text}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
            "-frames:v", "1",
            output_path
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
            logger.info(f"[仿真] 关键帧已生成: {output_path}")
            return {
                "status": "completed",
                "mode": "simulation",
                "file_path": output_path,
                "prompt": prompt,
                "width": width,
                "height": height,
                "asset_id": os.path.basename(output_path).split("_")[0]
            }
        except Exception as e:
            logger.error(f"关键帧仿真生成失败: {e}")
            return {"status": "failed", "error": str(e)}

    def _api_generate_keyframe(self, prompt, output_path, width, height):
        """API模式：调用图像生成API（预留接口，可对接image_gen/Seedream等）"""
        # 工程化预留：通过HTTP调用图像生成服务
        # 实际部署时配置API端点和密钥
        logger.info(f"[API模式] 关键帧生成调用（预留接口）: prompt长度={len(prompt)}")
        return {
            "status": "api_pending",
            "mode": "api",
            "prompt": prompt,
            "output_path": output_path,
            "note": "API模式需配置图像生成服务端点，当前返回仿真占位"
        }


class VideoGenerator(BaseGenerator):
    """视频片段生成器"""

    def generate(self, keyframe_path=None, video_prompt="", shot_num="S01",
                 duration=5, width=1920, height=1080, fps=30):
        """
        生成视频片段
        keyframe_path: 关键帧图像路径（图生视频）
        video_prompt: 视频运动描述
        返回: 视频文件路径
        """
        asset_id = generate_asset_id("VIDEOSEG")
        filename = f"{asset_id}_{shot_num}.mp4"
        output_path = self._get_output_path("videos", filename)

        if self.mode == "simulation":
            return self._simulate_video(keyframe_path, video_prompt, output_path,
                                         duration, width, height, fps, shot_num)
        else:
            return self._api_generate_video(keyframe_path, video_prompt, output_path, duration)

    def _simulate_video(self, keyframe_path, video_prompt, output_path,
                        duration, width, height, fps, shot_num):
        """仿真模式：用ffmpeg生成占位视频（关键帧缩放+文字）"""
        if keyframe_path and os.path.exists(keyframe_path):
            # 基于关键帧生成视频（缩放动画）
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", keyframe_path,
                "-vf", f"scale={width}:{height},zoompan=z='min(zoom+0.0015,1.5)':d={duration*fps}:s={width}x{height}:fps={fps}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-t", str(duration),
                output_path
            ]
        else:
            # 纯色背景+文字
            text = f"Video Segment {shot_num}"
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=0d1b2a:s={width}x{height}:d={duration}:r={fps}",
                "-vf", f"drawtext=text='{text}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                output_path
            ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=60)
            logger.info(f"[仿真] 视频片段已生成: {output_path}（{duration}秒）")
            return {
                "status": "completed",
                "mode": "simulation",
                "file_path": output_path,
                "duration": duration,
                "width": width,
                "height": height,
                "fps": fps,
                "video_prompt": video_prompt,
                "asset_id": os.path.basename(output_path).split("_")[0]
            }
        except Exception as e:
            logger.error(f"视频仿真生成失败: {e}")
            return {"status": "failed", "error": str(e)}

    def _api_generate_video(self, keyframe_path, video_prompt, output_path, duration):
        """API模式：调用视频生成API（预留接口，可对接Seedance/图生视频等）"""
        logger.info(f"[API模式] 视频生成调用（预留接口）: duration={duration}s")
        return {
            "status": "api_pending",
            "mode": "api",
            "video_prompt": video_prompt,
            "keyframe_path": keyframe_path,
            "output_path": output_path,
            "duration": duration,
            "note": "API模式需配置视频生成服务端点，当前返回仿真占位"
        }


class AudioGenerator(BaseGenerator):
    """配音音频生成器"""

    def generate(self, text, voice_style="clear_bright", shot_num="S01",
                 language="zh-CN", speed=1.0):
        """
        生成配音音频
        text: 配音文本
        voice_style: 语音风格
        返回: 音频文件路径
        """
        asset_id = generate_asset_id("AUDIO")
        filename = f"{asset_id}_{shot_num}.wav"
        output_path = self._get_output_path("audio", filename)

        if self.mode == "simulation":
            return self._simulate_audio(text, output_path, voice_style, shot_num)
        else:
            return self._api_generate_audio(text, output_path, voice_style)

    def _simulate_audio(self, text, output_path, voice_style, shot_num):
        """仿真模式：生成静音占位音频（时长按文本长度估算）"""
        # 按中文字数估算时长（约4字/秒）
        duration = max(2, len(text) / 4)
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
            "-t", str(duration),
            "-c:a", "pcm_s16le",
            output_path
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
            logger.info(f"[仿真] 配音音频已生成: {output_path}（{duration:.1f}秒）")
            return {
                "status": "completed",
                "mode": "simulation",
                "file_path": output_path,
                "duration": round(duration, 2),
                "text": text,
                "voice_style": voice_style,
                "asset_id": os.path.basename(output_path).split("_")[0]
            }
        except Exception as e:
            logger.error(f"音频仿真生成失败: {e}")
            return {"status": "failed", "error": str(e)}

    def _api_generate_audio(self, text, output_path, voice_style):
        """API模式：调用TTS API（预留接口，可对接text_to_audio_plus等）"""
        logger.info(f"[API模式] 配音生成调用（预留接口）: text长度={len(text)}")
        return {
            "status": "api_pending",
            "mode": "api",
            "text": text,
            "output_path": output_path,
            "voice_style": voice_style,
            "note": "API模式需配置TTS服务端点，当前返回仿真占位"
        }


class SubtitleGenerator(BaseGenerator):
    """字幕生成器"""

    def generate(self, shots, output_name="teaching_video"):
        """
        从分镜表生成SRT字幕文件
        shots: 分镜列表（含narration和duration）
        返回: 字幕文件路径
        """
        asset_id = generate_asset_id("SUBTITLE")
        filename = f"{asset_id}_{output_name}.srt"
        output_path = self._get_output_path("subtitles", filename)

        srt_content = []
        current_time = 0.0

        for i, shot in enumerate(shots, 1):
            duration = shot.get("duration", 5)
            narration = shot.get("narration", "")
            if not narration:
                continue

            start_time = current_time
            end_time = current_time + duration
            current_time = end_time

            srt_content.append(f"{i}")
            srt_content.append(f"{self._format_srt_time(start_time)} --> {self._format_srt_time(end_time)}")
            srt_content.append(narration)
            srt_content.append("")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(srt_content))

        logger.info(f"字幕文件已生成: {output_path}（{len(shots)}条）")
        return {
            "status": "completed",
            "file_path": output_path,
            "total_subtitles": len(shots),
            "asset_id": asset_id
        }

    def _format_srt_time(self, seconds):
        """格式化SRT时间"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class VideoEditor(BaseGenerator):
    """视频编辑器：拼接+字幕压制+音频混合"""

    def generate(self, *args, **kwargs):
        """视频编辑器不使用统一generate接口，使用具体方法"""
        raise NotImplementedError("VideoEditor使用具体方法: concatenate_videos/burn_subtitles/mix_audio")

    def concatenate_videos(self, video_paths, output_name="teaching_video"):
        """拼接多个视频片段"""
        asset_id = generate_asset_id("CONCAT")
        filename = f"{asset_id}_{output_name}_concat.mp4"
        output_path = self._get_output_path("final", filename)

        # 创建concat列表文件
        list_file = output_path + ".txt"
        with open(list_file, 'w') as f:
            for vp in video_paths:
                if os.path.exists(vp):
                    f.write(f"file '{vp}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            output_path
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
            os.remove(list_file)
            logger.info(f"视频拼接完成: {output_path}（{len(video_paths)}段）")
            return {"status": "completed", "file_path": output_path, "segments": len(video_paths)}
        except Exception as e:
            logger.error(f"视频拼接失败: {e}")
            return {"status": "failed", "error": str(e)}

    def burn_subtitles(self, video_path, subtitle_path, output_name="teaching_video"):
        """将字幕烧录到视频"""
        asset_id = generate_asset_id("SUBBED")
        filename = f"{asset_id}_{output_name}_subtitled.mp4"
        output_path = self._get_output_path("final", filename)

        # 转义字幕路径中的特殊字符
        sub_path_escaped = subtitle_path.replace("'", "'\\''")
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles='{sub_path_escaped}':force_style='FontSize=24,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=2'",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            output_path
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
            logger.info(f"字幕烧录完成: {output_path}")
            return {"status": "completed", "file_path": output_path}
        except Exception as e:
            logger.error(f"字幕烧录失败: {e}")
            # 降级：不烧录字幕，直接复制
            import shutil
            shutil.copy2(video_path, output_path)
            return {"status": "completed_fallback", "file_path": output_path, "note": "字幕烧录失败，已降级为无字幕版本"}

    def mix_audio(self, video_path, audio_paths, output_name="teaching_video",
                   video_volume=1.0, audio_volume=0.3):
        """混合视频音轨和配音音频"""
        asset_id = generate_asset_id("MIXED")
        filename = f"{asset_id}_{output_name}_mixed.mp4"
        output_path = self._get_output_path("final", filename)

        if not audio_paths:
            import shutil
            shutil.copy2(video_path, output_path)
            return {"status": "completed", "file_path": output_path, "note": "无配音音频，直接复制"}

        # 构建ffmpeg滤镜：混合多个音频
        inputs = ["-i", video_path]
        for ap in audio_paths:
            if os.path.exists(ap):
                inputs.extend(["-i", ap])

        n_audio = len([ap for ap in audio_paths if os.path.exists(ap)])
        if n_audio == 0:
            import shutil
            shutil.copy2(video_path, output_path)
            return {"status": "completed", "file_path": output_path}

        # 简单方案：用第一个配音替换视频音轨
        first_audio = [ap for ap in audio_paths if os.path.exists(ap)][0]
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", first_audio,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            output_path
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
            logger.info(f"音频混合完成: {output_path}")
            return {"status": "completed", "file_path": output_path, "audio_tracks": n_audio}
        except Exception as e:
            logger.error(f"音频混合失败: {e}")
            import shutil
            shutil.copy2(video_path, output_path)
            return {"status": "completed_fallback", "file_path": output_path, "note": "音频混合失败，已降级"}


class GeneratorService:
    """
    生成服务统一入口
    可工程化落地核心：统一调度所有生成能力，支持仿真/API双模式
    """

    def __init__(self, mode="simulation"):
        self.mode = mode
        self.keyframe_gen = KeyframeGenerator(mode)
        self.video_gen = VideoGenerator(mode)
        self.audio_gen = AudioGenerator(mode)
        self.subtitle_gen = SubtitleGenerator(mode)
        self.video_editor = VideoEditor(mode)
        logger.info(f"生成服务初始化完成，模式: {mode}")

    def generate_keyframe(self, prompt, shot_num="S01", **kwargs):
        return self.keyframe_gen.generate(prompt, shot_num, **kwargs)

    def generate_video_segment(self, keyframe_path=None, video_prompt="",
                                shot_num="S01", duration=5, **kwargs):
        return self.video_gen.generate(keyframe_path, video_prompt, shot_num, duration, **kwargs)

    def generate_audio(self, text, shot_num="S01", **kwargs):
        return self.audio_gen.generate(text, shot_num=shot_num, **kwargs)

    def generate_subtitles(self, shots, output_name="teaching_video"):
        return self.subtitle_gen.generate(shots, output_name)

    def concatenate_videos(self, video_paths, output_name="teaching_video"):
        return self.video_editor.concatenate_videos(video_paths, output_name)

    def burn_subtitles(self, video_path, subtitle_path, output_name="teaching_video"):
        return self.video_editor.burn_subtitles(video_path, subtitle_path, output_name)

    def mix_audio(self, video_path, audio_paths, output_name="teaching_video"):
        return self.video_editor.mix_audio(video_path, audio_paths, output_name)

    def get_service_status(self):
        return {
            "mode": self.mode,
            "output_dir": GENERATOR_OUTPUT_DIR,
            "services": {
                "keyframe": "available",
                "video": "available",
                "audio": "available",
                "subtitle": "available",
                "video_editor": "available"
            },
            "ffmpeg_available": self._check_ffmpeg()
        }

    def _check_ffmpeg(self):
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
