"""
教育风格分镜表生成器
将教学脚本转换为标准化分镜表，对接短剧流水线格式
教育风格：清新明亮、现代简约、科技感、校园氛围
"""
import os
import sys
import json
import random
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from config.settings import DATA_DIR
from src.common.utils import setup_logger, generate_asset_id

logger = setup_logger("storyboard", "video_pipeline.log")


class EduStoryboardGenerator:
    """教育风格分镜表生成器"""

    # 教育风格视觉模板
    EDU_VISUAL_STYLES = {
        "虚拟教室": {
            "background": "明亮现代的虚拟教室，白色主调，蓝色点缀，大屏幕显示教学内容",
            "lighting": "柔和均匀的教室照明，重点区域聚光",
            "atmosphere": "专注、有序、积极向上"
        },
        "知识空间": {
            "background": "沉浸式虚拟知识空间，漂浮的知识卡片和概念节点，深蓝色科技感背景",
            "lighting": "科技感冷光，知识节点自发光",
            "atmosphere": "探索、好奇、未来感"
        },
        "实操实验室": {
            "background": "现代化实验室/实训车间，设备齐全，安全标识清晰",
            "lighting": "明亮专业的工作照明，操作区重点照明",
            "atmosphere": "专业、严谨、动手实践"
        },
        "生活场景": {
            "background": "真实生活场景（家庭/校园/社区），自然温馨",
            "lighting": "自然光，温暖色调",
            "atmosphere": "亲切、自然、生活化"
        },
        "动画演示": {
            "background": "简洁的动画演示空间，白色或浅色背景，突出演示内容",
            "lighting": "均匀明亮，演示对象高亮",
            "atmosphere": "清晰、直观、易于理解"
        }
    }

    # 镜头类型库
    SHOT_TYPES = [
        {"type": "全景", "description": "展示完整场景和人物位置"},
        {"type": "中景", "description": "展示人物上半身和动作"},
        {"type": "近景", "description": "展示人物面部表情和细节"},
        {"type": "特写", "description": "突出关键细节或重点内容"},
        {"type": "过肩", "description": "从人物肩后拍摄，展示视角"},
        {"type": "俯拍", "description": "从上向下拍摄，展示全局"},
        {"type": "仰拍", "description": "从下向上拍摄，突出气势"},
        {"type": "移动镜头", "description": "镜头跟随移动，增强动感"}
    ]

    # 转场方式（教育风格，避免短剧流水线禁止的慢淡入淡出）
    TRANSITIONS = ["硬切", "快切", "闪白", "缩放转场", "滑动转场"]

    def __init__(self):
        self.storyboards = []

    def generate_storyboard(self, script):
        """
        从教学脚本生成分镜表
        对接短剧流水线标准格式：镜号/画面描述/时长/关键帧提示词/视频提示词/音效/转场
        """
        storyboard_id = generate_asset_id("EDU-SB")
        shots = []

        for segment in script["segments"]:
            segment_shots = self._generate_segment_shots(segment, script)
            shots.extend(segment_shots)

        # 编号
        for i, shot in enumerate(shots):
            shot["shot_num"] = f"S{i+1:03d}"

        storyboard = {
            "storyboard_id": storyboard_id,
            "script_id": script["script_id"],
            "title": script["title"],
            "stage": script["stage"],
            "knowledge_point": script["knowledge_point_name"],
            "total_shots": len(shots),
            "total_duration": sum(s["duration"] for s in shots),
            "characters": script["characters"],
            "visual_style": self._select_visual_style(script["stage"]),
            "shots": shots,
            "full_narration": script["full_narration"],
            "created_at": datetime.now().isoformat(),
            "format": "drama-pipeline-compatible"  # 标记为短剧流水线兼容格式
        }

        self.storyboards.append(storyboard)
        logger.info(f"分镜表已生成：{storyboard_id}，共{len(shots)}个镜头，总时长{storyboard['total_duration']}秒")
        return storyboard

    def _generate_segment_shots(self, segment, script):
        """为单个教学环节生成多个镜头"""
        shots = []
        seg_type = segment["type"]
        duration = segment["duration"]

        # 根据环节类型确定镜头数量和分配
        if seg_type == "hook":
            shot_count = 2
            durations = self._split_duration(duration, shot_count)
            shots.append(self._create_shot(
                "全景", segment, script, durations[0],
                "导入开场镜头，展示场景和主题",
                self.EDU_VISUAL_STYLES["虚拟教室"]
            ))
            shots.append(self._create_shot(
                "近景", segment, script, durations[1],
                "角色特写，提出问题，引发好奇",
                self.EDU_VISUAL_STYLES["虚拟教室"]
            ))

        elif seg_type == "explain":
            shot_count = 3
            durations = self._split_duration(duration, shot_count)
            shots.append(self._create_shot(
                "中景", segment, script, durations[0],
                "教师讲解开场，展示概念定义",
                self.EDU_VISUAL_STYLES["虚拟教室"]
            ))
            shots.append(self._create_shot(
                "特写", segment, script, durations[1],
                "重点内容特写，板书/屏幕显示核心概念",
                self.EDU_VISUAL_STYLES["知识空间"]
            ))
            shots.append(self._create_shot(
                "移动镜头", segment, script, durations[2],
                "概念图动态展开，知识点关联展示",
                self.EDU_VISUAL_STYLES["知识空间"]
            ))

        elif seg_type == "demo":
            shot_count = 3
            durations = self._split_duration(duration, shot_count)
            shots.append(self._create_shot(
                "全景", segment, script, durations[0],
                "演示场景全景，展示设备/环境",
                self.EDU_VISUAL_STYLES["实操实验室"]
            ))
            shots.append(self._create_shot(
                "特写", segment, script, durations[1],
                "操作步骤特写，关键动作慢放",
                self.EDU_VISUAL_STYLES["动画演示"]
            ))
            shots.append(self._create_shot(
                "中景", segment, script, durations[2],
                "演示结果展示，效果呈现",
                self.EDU_VISUAL_STYLES["动画演示"]
            ))

        elif seg_type == "quiz":
            shot_count = 2
            durations = self._split_duration(duration, shot_count)
            shots.append(self._create_shot(
                "中景", segment, script, durations[0],
                "问答界面，题目弹出",
                self.EDU_VISUAL_STYLES["虚拟教室"]
            ))
            shots.append(self._create_shot(
                "近景", segment, script, durations[1],
                "答案揭晓，鼓励反馈",
                self.EDU_VISUAL_STYLES["虚拟教室"]
            ))

        elif seg_type == "example":
            shot_count = 3
            durations = self._split_duration(duration, shot_count)
            shots.append(self._create_shot(
                "特写", segment, script, durations[0],
                "例题展示，题目逐行显示",
                self.EDU_VISUAL_STYLES["虚拟教室"]
            ))
            shots.append(self._create_shot(
                "移动镜头", segment, script, durations[1],
                "解题步骤逐步展开，关键公式高亮",
                self.EDU_VISUAL_STYLES["动画演示"]
            ))
            shots.append(self._create_shot(
                "特写", segment, script, durations[2],
                "最终答案醒目显示，解题思路总结",
                self.EDU_VISUAL_STYLES["虚拟教室"]
            ))

        elif seg_type == "summary":
            shot_count = 2
            durations = self._split_duration(duration, shot_count)
            shots.append(self._create_shot(
                "移动镜头", segment, script, durations[0],
                "知识思维导图展开，核心要点卡片弹出",
                self.EDU_VISUAL_STYLES["知识空间"]
            ))
            shots.append(self._create_shot(
                "全景", segment, script, durations[1],
                "鼓励性结尾，角色挥手告别",
                self.EDU_VISUAL_STYLES["虚拟教室"]
            ))

        else:
            shots.append(self._create_shot(
                "中景", segment, script, duration,
                segment["name"],
                self.EDU_VISUAL_STYLES["虚拟教室"]
            ))

        return shots

    def _create_shot(self, shot_type, segment, script, duration, description, visual_style):
        """创建单个镜头"""
        characters_desc = "、".join([c["name"] for c in script["characters"]])
        knowledge_point = script["knowledge_point_name"]

        # 画面描述
        visual_description = (
            f"{visual_style['background']}，{visual_style['lighting']}，"
            f"{characters_desc}出现在画面中，{description}，"
            f"主题：{knowledge_point}，{visual_style['atmosphere']}氛围"
        )

        # 关键帧提示词（教育风格，对接短剧流水线格式）
        keyframe_prompt = self._generate_keyframe_prompt(
            shot_type, visual_description, script["stage"]
        )

        # 视频提示词（运动描述）
        video_prompt = self._generate_video_prompt(shot_type, segment["type"])

        # 音效
        audio = self._generate_audio(segment["type"])

        # 转场
        transition = random.choice(self.TRANSITIONS)

        return {
            "shot_type": shot_type,
            "segment_name": segment["name"],
            "segment_type": segment["type"],
            "duration": duration,
            "visual_description": visual_description,
            "keyframe_prompt": keyframe_prompt,
            "video_prompt": video_prompt,
            "narration": segment["narration"],
            "on_screen_text": segment.get("on_screen_text", ""),
            "audio": audio,
            "transition": transition,
            "characters": [c["name"] for c in script["characters"]]
        }

    def _generate_keyframe_prompt(self, shot_type, visual_description, stage):
        """生成教育风格关键帧提示词"""
        # 教育风格基准（区别于短剧流水线的仙侠风格）
        edu_style_base = (
            "现代教育风格，清新明亮色调，扁平化插画与3D卡通混合，"
            "科技感校园氛围，简洁现代UI元素，高清画质，16:9横屏"
        )

        # 学段风格微调
        stage_style = {
            "小学": "色彩鲜艳活泼，卡通化程度高，圆角设计，童趣元素",
            "初中": "清新简约，适度卡通，科技感元素，青春活力",
            "高中": "专业严谨，写实与插画结合，深色科技感，学术氛围",
            "中职": "实操导向，写实风格，工业/职业场景，专业设备细节"
        }

        prompt = (
            f"{visual_description}，{shot_type}镜头，"
            f"{edu_style_base}，{stage_style.get(stage, stage_style['初中'])}，"
            f"画面干净整洁，文字清晰可读，教学内容突出"
        )
        return prompt

    def _generate_video_prompt(self, shot_type, segment_type):
        """生成视频运动提示词"""
        motions = {
            "全景": "镜头缓慢推进，展示场景全貌",
            "中景": "镜头稳定，人物自然动作和手势",
            "近景": "镜头微推，捕捉表情变化",
            "特写": "镜头聚焦关键细节，缓慢放大",
            "过肩": "镜头跟随人物视角移动",
            "俯拍": "镜头从上方缓慢下降",
            "仰拍": "镜头从下方向上缓慢移动",
            "移动镜头": "镜头平滑移动，跟随内容展开"
        }

        segment_motion = {
            "hook": "节奏稍快，富有动感",
            "explain": "平稳流畅，配合讲解节奏",
            "demo": "重点环节慢放，步骤清晰",
            "quiz": "问答节奏，有停顿和反馈",
            "example": "解题节奏，逐步展开",
            "summary": "舒缓收尾，思维导图展开"
        }

        return f"{motions.get(shot_type, '镜头稳定')}，{segment_motion.get(segment_type, '平稳流畅')}"

    def _generate_audio(self, segment_type):
        """生成音效配置"""
        audio_configs = {
            "hook": {"bgm": "轻快活泼的开场音乐", "sfx": ["叮~提示音", "好奇的音效"], "voice": "教师旁白"},
            "explain": {"bgm": "轻柔的背景音乐", "sfx": ["板书书写声", "重点提示音"], "voice": "教师讲解"},
            "demo": {"bgm": "节奏感强的演示音乐", "sfx": ["操作音效", "成功提示音"], "voice": "操作解说"},
            "quiz": {"bgm": "紧张有趣的问答音乐", "sfx": ["倒计时音效", "答对/答错反馈音"], "voice": "问答互动"},
            "example": {"bgm": "专注的解题音乐", "sfx": ["书写声", "思考提示音"], "voice": "例题讲解"},
            "summary": {"bgm": "温馨舒缓的收尾音乐", "sfx": ["总结提示音", "鼓励音效"], "voice": "总结旁白"}
        }
        return audio_configs.get(segment_type, audio_configs["explain"])

    def _split_duration(self, total, count):
        """将总时长分配给多个镜头"""
        base = total // count
        remainder = total % count
        durations = [base] * count
        for i in range(remainder):
            durations[i] += 1
        return durations

    def _select_visual_style(self, stage):
        """选择适合学段的视觉风格"""
        if stage == "小学":
            return "明亮卡通风"
        elif stage == "中职":
            return "实操写实风"
        elif stage == "高中":
            return "专业科技风"
        else:
            return "清新简约风"

    def export_for_drama_pipeline(self, storyboard):
        """
        导出为短剧流水线兼容格式
        可直接输入短剧流水线的storyboard_generator.py
        """
        drama_format = {
            "episode_title": storyboard["title"],
            "total_shots": storyboard["total_shots"],
            "total_duration": storyboard["total_duration"],
            "format_version": "drama-pipeline-v1.2",
            "shots": [
                {
                    "镜号": shot["shot_num"],
                    "画面描述": shot["visual_description"],
                    "时长": shot["duration"],
                    "关键帧提示词": shot["keyframe_prompt"],
                    "视频提示词": shot["video_prompt"],
                    "音效配乐": shot["audio"],
                    "转场方式": shot["transition"],
                    "旁白": shot["narration"],
                    "字幕": shot["on_screen_text"]
                }
                for shot in storyboard["shots"]
            ]
        }
        return drama_format

    def get_storyboard_stats(self):
        """获取分镜表统计"""
        return {
            "total_storyboards": len(self.storyboards),
            "total_shots": sum(s["total_shots"] for s in self.storyboards),
            "avg_shots_per_storyboard": sum(s["total_shots"] for s in self.storyboards) / len(self.storyboards) if self.storyboards else 0
        }

    def save_all(self):
        """保存所有分镜表"""
        filepath = os.path.join(DATA_DIR, "video_storyboards.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.storyboards, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存{len(self.storyboards)}个分镜表至{filepath}")
        return filepath
