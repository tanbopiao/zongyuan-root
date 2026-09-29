"""
短剧流水线实际对接模块
将教育分镜表实际输入drama-pipeline的storyboard_generator.py
实现教育视频与短剧工业化流水线的真实链路打通
"""
import os
import sys
import json
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from config.settings import DATA_DIR, DID, ANCHOR
from src.common.utils import setup_logger, generate_asset_id

logger = setup_logger("drama_bridge", "video_pipeline.log")

# 短剧流水线路径
DRAMA_PIPELINE_DIR = "/home/user/.doubao/agent_mode/workspace/.user_skills/drama-pipeline"
DRAMA_SCRIPT_PATH = os.path.join(DRAMA_PIPELINE_DIR, "scripts", "storyboard_generator.py")


class DramaPipelineBridge:
    """
    短剧流水线桥接器
    实现教育视频通道与昆仑洞天短剧工业化流水线的实际对接
    """

    def __init__(self):
        self.bridge_dir = os.path.join(DATA_DIR, "drama_bridge")
        os.makedirs(self.bridge_dir, exist_ok=True)
        self.drama_available = self._check_drama_pipeline()
        logger.info(f"短剧流水线桥接器初始化，流水线可用: {self.drama_available}")

    def _check_drama_pipeline(self):
        """检查短剧流水线是否可用"""
        return os.path.exists(DRAMA_SCRIPT_PATH)

    def convert_edu_to_drama_outline(self, script, storyboard):
        """
        将教育脚本+分镜表转换为短剧流水线大纲格式
        短剧流水线需要：分集大纲（剧情节拍+场景列表）
        """
        outline = {
            "title": script["title"],
            "episode": 1,
            "genre": "educational",
            "style": "education_modern",
            "logline": f"教学视频：{script['title']}",
            "beats": [],
            "scenes": []
        }

        # 将教学环节转换为剧情节拍
        for seg in script["segments"]:
            outline["beats"].append({
                "beat_num": seg["segment_num"],
                "name": seg["name"],
                "type": seg["type"],
                "description": seg["narration"][:100],
                "duration": seg["duration"]
            })

        # 将分镜转换为场景
        for shot in storyboard["shots"]:
            outline["scenes"].append({
                "scene_num": shot["shot_num"],
                "location": shot.get("scene_template", "虚拟教室"),
                "description": shot["visual_description"],
                "duration": shot["duration"],
                "characters": shot.get("characters", [])
            })

        return outline

    def export_drama_compatible_storyboard(self, storyboard, output_name="edu_drama_storyboard"):
        """
        导出短剧流水线兼容格式分镜表
        可直接输入 drama-pipeline/scripts/storyboard_generator.py
        """
        asset_id = generate_asset_id("DRAMA-SB")
        filename = f"{asset_id}_{output_name}.json"
        output_path = os.path.join(self.bridge_dir, filename)

        # 短剧流水线标准格式
        drama_format = {
            "episode_title": storyboard.get("title", "教学视频"),
            "episode": 1,
            "format_version": "drama-pipeline-v1.2",
            "style": "education_modern_16x9",
            "total_shots": storyboard["total_shots"],
            "total_duration": storyboard["total_duration"],
            "shots": []
        }

        for shot in storyboard["shots"]:
            drama_format["shots"].append({
                "镜号": shot["shot_num"],
                "画面描述": shot["visual_description"],
                "时长": shot["duration"],
                "关键帧提示词": shot["keyframe_prompt"],
                "视频提示词": shot["video_prompt"],
                "音效配乐": shot["audio"],
                "转场方式": shot["transition"]
            })

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(drama_format, f, ensure_ascii=False, indent=2)

        logger.info(f"短剧兼容分镜表已导出: {output_path}")
        return {
            "status": "completed",
            "file_path": output_path,
            "asset_id": asset_id,
            "total_shots": storyboard["total_shots"],
            "drama_pipeline_available": self.drama_available,
            "usage": f"python3 {DRAMA_SCRIPT_PATH} --input {output_path} --episode 1"
        }

    def call_drama_storyboard_generator(self, input_file, episode=1):
        """
        实际调用短剧流水线的storyboard_generator.py
        这是真实链路打通的核心：教育分镜表 → 短剧流水线 → 短剧标准分镜输出
        """
        if not self.drama_available:
            return {
                "status": "unavailable",
                "error": "短剧流水线脚本不存在",
                "expected_path": DRAMA_SCRIPT_PATH
            }

        if not os.path.exists(input_file):
            return {"status": "failed", "error": f"输入文件不存在: {input_file}"}

        output_dir = os.path.join(self.bridge_dir, "drama_output")
        os.makedirs(output_dir, exist_ok=True)

        cmd = [
            "python3", DRAMA_SCRIPT_PATH,
            "--input", input_file,
            "--episode", str(episode)
        ]

        try:
            logger.info(f"调用短剧流水线: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=DRAMA_PIPELINE_DIR
            )

            return {
                "status": "completed" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "stdout": result.stdout[-2000:] if result.stdout else "",
                "stderr": result.stderr[-2000:] if result.stderr else "",
                "input_file": input_file
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "短剧流水线调用超时（120秒）"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def get_bridge_status(self):
        """获取桥接器状态"""
        return {
            "drama_pipeline_available": self.drama_available,
            "drama_script_path": DRAMA_SCRIPT_PATH,
            "bridge_dir": self.bridge_dir,
            "conversion_capability": "edu_script + storyboard -> drama_outline + drama_storyboard",
            "actual_call_capability": self.drama_available
        }
