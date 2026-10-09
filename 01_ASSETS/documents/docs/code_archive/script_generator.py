"""
视频教学脚本生成器
将知识图谱中的知识点转换为结构化教学视频脚本
支持小学/初中/高中/中职四学段分层
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

logger = setup_logger("video_script", "video_pipeline.log")


class TeachingScriptGenerator:
    """教学视频脚本生成器"""

    # 教学环节模板
    TEACHING_SEGMENTS = {
        "小学": [
            {"name": "趣味导入", "duration": 15, "type": "hook"},
            {"name": "概念讲解", "duration": 45, "type": "explain"},
            {"name": "动画演示", "duration": 30, "type": "demo"},
            {"name": "互动问答", "duration": 20, "type": "quiz"},
            {"name": "口诀总结", "duration": 10, "type": "summary"}
        ],
        "初中": [
            {"name": "情境导入", "duration": 15, "type": "hook"},
            {"name": "概念解析", "duration": 50, "type": "explain"},
            {"name": "实例演示", "duration": 35, "type": "demo"},
            {"name": "例题讲解", "duration": 30, "type": "example"},
            {"name": "方法总结", "duration": 15, "type": "summary"}
        ],
        "高中": [
            {"name": "问题导入", "duration": 15, "type": "hook"},
            {"name": "原理推导", "duration": 60, "type": "explain"},
            {"name": "模型构建", "duration": 40, "type": "demo"},
            {"name": "高考真题", "duration": 35, "type": "example"},
            {"name": "思维拓展", "duration": 20, "type": "summary"}
        ],
        "中职": [
            {"name": "岗位情境", "duration": 15, "type": "hook"},
            {"name": "技能讲解", "duration": 45, "type": "explain"},
            {"name": "实操演示", "duration": 50, "type": "demo"},
            {"name": "故障排查", "duration": 25, "type": "example"},
            {"name": "岗位规范", "duration": 15, "type": "summary"}
        ]
    }

    # 教育风格角色库
    EDU_CHARACTERS = {
        "AI教师": {
            "name": "小智老师",
            "appearance": "亲和力虚拟教师形象，简洁现代服装，温和微笑",
            "voice": "清晰明亮，语速适中，富有感染力"
        },
        "知识精灵": {
            "name": "知知",
            "appearance": "可爱的3D卡通小精灵，发光的知识球体，灵动活泼",
            "voice": "清脆童声，活泼有趣"
        },
        "学生代表": {
            "name": "同学小明",
            "appearance": "中学生形象，校服，好奇求知的眼神",
            "voice": "青涩少年音，充满好奇"
        },
        "实训导师": {
            "name": "工导师",
            "appearance": "专业工装，安全装备，干练专业的技师形象",
            "voice": "沉稳有力，专业严谨"
        }
    }

    def __init__(self, knowledge_graph=None):
        self.kg = knowledge_graph
        self.scripts = []

    def generate_script(self, entity_id, stage="初中", duration_minutes=3):
        """
        生成教学视频脚本
        entity_id: 知识图谱实体ID
        stage: 学段（小学/初中/高中/中职）
        duration_minutes: 目标时长（分钟）
        """
        entity = None
        if self.kg:
            entity = self.kg.get_entity_by_id(entity_id)
        if not entity:
            entity = {
                "id": entity_id,
                "name": entity_id,
                "domain": "通用",
                "description": "",
                "mastery_level": "了解"
            }

        # 获取教学环节模板
        segments_template = self.TEACHING_SEGMENTS.get(stage, self.TEACHING_SEGMENTS["初中"])

        # 根据目标时长调整环节时长
        total_template_duration = sum(s["duration"] for s in segments_template)
        target_duration = duration_minutes * 60
        scale_factor = target_duration / total_template_duration if total_template_duration > 0 else 1

        # 生成各环节脚本
        segments = []
        for i, seg_template in enumerate(segments_template):
            segment = self._generate_segment(
                seg_template, entity, stage, i + 1,
                int(seg_template["duration"] * scale_factor)
            )
            segments.append(segment)

        # 组装完整脚本
        script = {
            "script_id": generate_asset_id("EDU-SCRIPT"),
            "title": f"{entity['name']} - {stage}教学视频",
            "knowledge_point_id": entity_id,
            "knowledge_point_name": entity["name"],
            "domain": entity.get("domain", "通用"),
            "stage": stage,
            "target_duration_seconds": sum(s["duration"] for s in segments),
            "teaching_objectives": self._generate_objectives(entity, stage),
            "key_points": self._generate_key_points(entity),
            "characters": self._select_characters(stage),
            "segments": segments,
            "full_narration": self._assemble_narration(segments),
            "created_at": datetime.now().isoformat(),
            "version": "1.0"
        }

        self.scripts.append(script)
        logger.info(f"教学脚本已生成：{script['title']}，时长{script['target_duration_seconds']}秒，{len(segments)}个环节")
        return script

    def _generate_segment(self, template, entity, stage, segment_num, duration):
        """生成单个教学环节脚本"""
        seg_type = template["type"]
        seg_name = template["name"]

        if seg_type == "hook":
            content = self._generate_hook(entity, stage)
        elif seg_type == "explain":
            content = self._generate_explanation(entity, stage)
        elif seg_type == "demo":
            content = self._generate_demo(entity, stage)
        elif seg_type == "quiz":
            content = self._generate_quiz(entity, stage)
        elif seg_type == "example":
            content = self._generate_example(entity, stage)
        elif seg_type == "summary":
            content = self._generate_summary(entity, stage)
        else:
            content = {"narration": f"接下来学习{entity['name']}。", "visual": "标准教学画面"}

        return {
            "segment_num": f"S{segment_num:02d}",
            "name": seg_name,
            "type": seg_type,
            "duration": duration,
            "narration": content.get("narration", ""),
            "visual_description": content.get("visual", ""),
            "key_concepts": content.get("key_concepts", []),
            "interactions": content.get("interactions", []),
            "on_screen_text": content.get("on_screen_text", "")
        }

    def _generate_hook(self, entity, stage):
        """生成导入环节"""
        hooks = {
            "小学": [
                f"小朋友们好！今天小智老师要带大家认识一个神奇的新朋友——{entity['name']}！它就藏在我们身边，猜猜它在哪里？",
                f"哇！看这是什么？{entity['name']}来啦！它有什么神奇的本领呢？让我们一起探索吧！"
            ],
            "初中": [
                f"同学们，在生活中你有没有想过：{entity['name']}到底是什么？它为什么这么重要？今天我们就来一探究竟。",
                f"先来看一个问题：如果没有{entity['name']}，我们的生活会变成什么样？带着这个问题，进入今天的学习。"
            ],
            "高中": [
                f"我们已经学习了相关基础知识，那么{entity['name']}的深层原理是什么？它如何应用于复杂问题？本节课深入探讨。",
                f"从高考真题出发，{entity['name']}是高频考点。今天我们从原理到应用，彻底攻克这个知识点。"
            ],
            "中职": [
                f"在实际工作中，{entity['name']}是岗位必备技能。今天我们就从真实岗位场景出发，掌握这项技能。",
                f"师傅常说，{entity['name']}不过关，岗位就上不了手。今天我们就来攻克这个实操难点。"
            ]
        }
        narration = random.choice(hooks.get(stage, hooks["初中"]))
        return {
            "narration": narration,
            "visual": f"充满好奇心的导入画面，{entity['name']}以趣味方式登场，背景明亮活泼",
            "on_screen_text": f"今日主题：{entity['name']}"
        }

    def _generate_explanation(self, entity, stage):
        """生成讲解环节"""
        difficulty = {
            "小学": "用最简单的话来说",
            "初中": "从基本概念出发",
            "高中": "深入原理层面",
            "中职": "结合岗位实际"
        }
        narration = (
            f"{difficulty.get(stage, difficulty['初中'])}，{entity['name']}就是"
            f"{entity.get('description', '一个重要的知识概念')}。"
            f"它的核心要点包括：定义、特征、应用场景。"
            f"理解{entity['name']}，关键是抓住它的本质特征。"
        )
        return {
            "narration": narration,
            "visual": f"AI教师在虚拟教室中讲解{entity['name']}，配合动态板书和概念图，重点内容高亮显示",
            "key_concepts": ["定义", "核心特征", "应用场景"],
            "on_screen_text": f"什么是{entity['name']}？"
        }

    def _generate_demo(self, entity, stage):
        """生成演示环节"""
        narration = (
            f"光说不练假把式，让我们看看{entity['name']}是怎么工作的。"
            f"注意观察关键步骤，每一步都很重要！"
            f"第一步...第二步...第三步...看到了吗？这就是{entity['name']}的完整过程。"
        )
        return {
            "narration": narration,
            "visual": f"3D动画演示{entity['name']}的工作原理，步骤分解，关键环节慢放+标注，视觉效果清晰直观",
            "key_concepts": ["操作步骤", "关键环节", "注意事项"],
            "on_screen_text": f"{entity['name']}演示"
        }

    def _generate_quiz(self, entity, stage):
        """生成问答环节"""
        narration = (
            f"学了这么多，来检验一下吧！"
            f"问题一：{entity['name']}的核心特征是什么？"
            f"问题二：{entity['name']}可以应用在哪些场景？"
            f"你答对了吗？答错了也没关系，我们再复习一遍！"
        )
        return {
            "narration": narration,
            "visual": "互动问答界面，题目弹出，选项高亮，答对有鼓励动画，答错有提示",
            "interactions": [
                {"question": f"{entity['name']}的核心特征是什么？", "type": "choice"},
                {"question": f"{entity['name']}的应用场景？", "type": "multiple_choice"}
            ],
            "on_screen_text": "随堂小测"
        }

    def _generate_example(self, entity, stage):
        """生成例题环节"""
        narration = (
            f"理论结合实际，来看一道典型例题。"
            f"题目是关于{entity['name']}的应用。"
            f"先读题，找关键信息，然后一步步分析。"
            f"第一步...第二步...第三步...得出答案。"
            f"这道题的解题思路，你掌握了吗？"
        )
        return {
            "narration": narration,
            "visual": "例题展示界面，题目逐行显示，解题步骤逐步展开，关键公式高亮，最终答案醒目显示",
            "key_concepts": ["审题", "解题思路", "关键步骤"],
            "on_screen_text": "典型例题"
        }

    def _generate_summary(self, entity, stage):
        """生成总结环节"""
        narration = (
            f"今天的学习就到这里，让我们总结一下："
            f"第一，{entity['name']}的定义和核心特征；"
            f"第二，{entity['name']}的工作原理和应用场景；"
            f"第三，解题思路和注意事项。"
            f"课后记得复习哦！我们下节课再见！"
        )
        return {
            "narration": narration,
            "visual": "知识思维导图总结，核心要点以卡片形式弹出，配合鼓励性结尾画面",
            "key_concepts": ["核心定义", "工作原理", "应用场景", "解题方法"],
            "on_screen_text": f"本课总结：{entity['name']}"
        }

    def _generate_objectives(self, entity, stage):
        """生成教学目标"""
        return [
            f"理解{entity['name']}的基本概念和核心特征",
            f"掌握{entity['name']}的工作原理和应用方法",
            f"能够运用{entity['name']}解决实际问题",
            f"培养{entity.get('domain', '通用')}领域的思维能力"
        ]

    def _generate_key_points(self, entity):
        """生成重点难点"""
        return [
            f"{entity['name']}的定义和本质特征",
            f"{entity['name']}的工作原理和关键步骤",
            f"{entity['name']}在实际场景中的应用方法"
        ]

    def _select_characters(self, stage):
        """选择适合学段的角色"""
        if stage == "小学":
            return [self.EDU_CHARACTERS["AI教师"], self.EDU_CHARACTERS["知识精灵"]]
        elif stage == "中职":
            return [self.EDU_CHARACTERS["实训导师"], self.EDU_CHARACTERS["学生代表"]]
        else:
            return [self.EDU_CHARACTERS["AI教师"], self.EDU_CHARACTERS["学生代表"]]

    def _assemble_narration(self, segments):
        """组装完整旁白文本"""
        return "\n\n".join([
            f"【{s['name']}】{s['narration']}"
            for s in segments
        ])

    def get_script_stats(self):
        """获取脚本统计"""
        return {
            "total_scripts": len(self.scripts),
            "by_stage": self._count_by_field("stage"),
            "by_domain": self._count_by_field("domain"),
            "avg_duration": sum(s["target_duration_seconds"] for s in self.scripts) / len(self.scripts) if self.scripts else 0
        }

    def _count_by_field(self, field):
        counts = {}
        for s in self.scripts:
            key = s.get(field, "unknown")
            counts[key] = counts.get(key, 0) + 1
        return counts

    def save_all(self):
        """保存所有脚本"""
        filepath = os.path.join(DATA_DIR, "video_scripts.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.scripts, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存{len(self.scripts)}个教学脚本至{filepath}")
        return filepath
