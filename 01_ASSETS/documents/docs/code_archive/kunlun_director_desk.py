#!/usr/bin/env python3
"""
昆仑洞天·导演台3D场景布局器 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS

功能：
1. 3D场景布局（角色/道具/背景元素的位置/大小/旋转）
2. 多机位系统（8种预设机位+自定义机位）
3. 电影级灯光预设（伦勃朗光/逆光/柔光/硬光/黑金暗纹光）
4. 分镜表自动生成（场景+机位+灯光=完整分镜）
5. 镜头运动轨迹计算（推/拉/摇/移/跟/升/降）
6. 构图分析（三分法/黄金分割/对称/引导线）
7. JSON/MD/CSV导出

用法：
  python3 kunlun_director_desk.py --init          # 初始化示例场景
  python3 kunlun_director_desk.py --scene scene.json --export md
  python3 kunlun_director_desk.py --presets       # 列出所有预设
"""

import argparse
import hashlib
import json
import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


class DirectorDesk:
    """导演台3D场景布局器"""

    # 8种预设机位
    CAMERA_PRESETS = {
        "正面中景": {"fov": 50, "position": [0, 1.6, 5], "target": [0, 1.2, 0], "movement": "static"},
        "侧面全景": {"fov": 60, "position": [5, 2, 0], "target": [0, 1.5, 0], "movement": "static"},
        "俯视大全": {"fov": 70, "position": [0, 8, 3], "target": [0, 0, 0], "movement": "static"},
        "特写": {"fov": 35, "position": [0, 1.5, 2], "target": [0, 1.5, 0], "movement": "static"},
        "过肩镜头": {"fov": 45, "position": [0.8, 1.6, 1.5], "target": [0, 1.4, -2], "movement": "static"},
        "仰拍": {"fov": 55, "position": [0, 0.5, 3], "target": [0, 2.5, 0], "movement": "static"},
        "低角度": {"fov": 60, "position": [0, 0.3, 4], "target": [0, 1.8, 0], "movement": "static"},
        " Dutch角": {"fov": 50, "position": [2, 2, 4], "target": [0, 1.5, 0], "movement": "static", "roll": 15}
    }

    # 电影级灯光预设
    LIGHTING_PRESETS = {
        "伦勃朗光": {
            "key_light": {"position": [45, 30, -45], "intensity": 1.0, "color": "#ffd700", "type": "spot"},
            "fill_light": {"position": [-30, 20, 30], "intensity": 0.3, "color": "#4a9eff", "type": "point"},
            "rim_light": {"position": [0, 60, -60], "intensity": 0.5, "color": "#ffffff", "type": "spot"},
            "ambient": 0.15,
            "description": "经典人像布光，三角光区，立体感强"
        },
        "逆光剪影": {
            "key_light": {"position": [0, 45, -90], "intensity": 1.2, "color": "#ff6600", "type": "spot"},
            "fill_light": {"position": [0, 0, 0], "intensity": 0.0, "color": "#000000", "type": "none"},
            "rim_light": {"position": [0, 90, -90], "intensity": 0.8, "color": "#ffaa00", "type": "spot"},
            "ambient": 0.05,
            "description": "强逆光，主体剪影，边缘光勾勒轮廓"
        },
        "柔光漫射": {
            "key_light": {"position": [30, 60, 30], "intensity": 0.8, "color": "#fff5e6", "type": "area"},
            "fill_light": {"position": [-30, 40, -30], "intensity": 0.5, "color": "#e6f0ff", "type": "area"},
            "rim_light": {"position": [0, 80, 0], "intensity": 0.3, "color": "#ffffff", "type": "area"},
            "ambient": 0.3,
            "description": "大面积柔光，阴影柔和，适合情感戏"
        },
        "硬光高反差": {
            "key_light": {"position": [60, 20, -30], "intensity": 1.5, "color": "#ffffff", "type": "spot"},
            "fill_light": {"position": [0, 0, 0], "intensity": 0.0, "color": "#000000", "type": "none"},
            "rim_light": {"position": [-60, 40, -60], "intensity": 0.6, "color": "#4a9eff", "type": "spot"},
            "ambient": 0.05,
            "description": "强硬光，高反差，明暗对比强烈，悬疑/战斗场景"
        },
        "黑金暗纹风格": {
            "key_light": {"position": [45, 25, -45], "intensity": 0.9, "color": "#d4af37", "type": "spot"},
            "fill_light": {"position": [-20, 15, 20], "intensity": 0.15, "color": "#1a1a2e", "type": "point"},
            "rim_light": {"position": [0, 70, -70], "intensity": 0.4, "color": "#f0d060", "type": "spot"},
            "ambient": 0.08,
            "description": "昆仑洞天专属，金色主光+深色填充，黑金暗纹质感"
        },
        "月光冷调": {
            "key_light": {"position": [-45, 60, -45], "intensity": 0.7, "color": "#a0c4ff", "type": "spot"},
            "fill_light": {"position": [30, 20, 30], "intensity": 0.2, "color": "#4a6fa5", "type": "point"},
            "rim_light": {"position": [0, 80, -80], "intensity": 0.5, "color": "#c0d8ff", "type": "spot"},
            "ambient": 0.1,
            "description": "冷蓝月光，夜间场景，神秘氛围"
        },
        "烛火暖调": {
            "key_light": {"position": [0, 10, 0], "intensity": 0.6, "color": "#ff8c00", "type": "point"},
            "fill_light": {"position": [20, 30, 20], "intensity": 0.15, "color": "#ff6600", "type": "point"},
            "rim_light": {"position": [-20, 40, -20], "intensity": 0.2, "color": "#ff4500", "type": "point"},
            "ambient": 0.05,
            "description": "暖橙烛光，室内夜景，温暖亲密"
        },
        "史诗创世": {
            "key_light": {"position": [0, 90, 0], "intensity": 1.3, "color": "#fff8dc", "type": "spot"},
            "fill_light": {"position": [45, 30, 45], "intensity": 0.4, "color": "#ffd700", "type": "spot"},
            "rim_light": {"position": [-45, 60, -45], "intensity": 0.6, "color": "#ffa500", "type": "spot"},
            "ambient": 0.2,
            "description": "顶光为主，金色填充，史诗创世氛围，博物馆馆藏质感"
        }
    }

    # 镜头运动类型
    CAMERA_MOVEMENTS = {
        "推": {"type": "dolly_in", "speed": 0.5, "description": "镜头向前推进，聚焦主体"},
        "拉": {"type": "dolly_out", "speed": 0.5, "description": "镜头向后拉远，展示环境"},
        "摇": {"type": "pan", "speed": 15, "description": "水平旋转，展示横向空间"},
        "移": {"type": "truck", "speed": 0.8, "description": "水平平移，跟随主体"},
        "跟": {"type": "follow", "speed": 1.0, "description": "跟随主体移动，保持距离"},
        "升": {"type": "crane_up", "speed": 0.6, "description": "镜头上升，展示宏大场景"},
        "降": {"type": "crane_down", "speed": 0.6, "description": "镜头下降，聚焦细节"},
        "环绕": {"type": "orbit", "speed": 30, "description": "环绕主体，360度展示"}
    }

    # 构图法则
    COMPOSITION_RULES = {
        "三分法": {"description": "主体位于三分线交点，视觉平衡", "weight": 0.9},
        "黄金分割": {"description": "主体位于黄金比例点(0.618)，美学最优", "weight": 0.95},
        "对称构图": {"description": "左右对称，庄重稳定，适合神性角色", "weight": 0.85},
        "引导线": {"description": "利用线条引导视线至主体", "weight": 0.8},
        "框架构图": {"description": "利用前景框架突出主体", "weight": 0.75},
        "留白": {"description": "大面积留白，意境深远", "weight": 0.7},
        "对角线": {"description": "对角线构图，动感强烈", "weight": 0.75},
        "中心构图": {"description": "主体居中，强调权威", "weight": 0.8}
    }

    def __init__(self, data_dir="./director_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.scenes_file = self.data_dir / "scenes.json"
        self.shots_file = self.data_dir / "shots.json"
        self.scenes = self._load(self.scenes_file, [])
        self.shots = self._load(self.shots_file, [])

    def _load(self, path, default):
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default

    def _save(self, path, data):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _gen_id(self, prefix):
        return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

    def init_sample_scene(self):
        """初始化示例场景：玄女降临"""
        print("[初始化] 创建示例场景：玄女降临...")

        scene = {
            "scene_id": self._gen_id("SCENE"),
            "name": "玄女降临",
            "description": "九天玄女战争形态降临战场，红裙凤冠，神兵烈焰",
            "environment": {
                "type": "outdoor",
                "time": "黄昏",
                "weather": "战火硝烟",
                "ground": "焦土战场",
                "background": "远山+战旗+火光"
            },
            "elements": [
                {"id": "char_01", "type": "character", "name": "九天玄女-战争形态",
                 "position": [0, 0, 0], "rotation": [0, 0, 0], "scale": 1.0,
                 "role": "主体", "costume": "红裙凤冠战甲"},
                {"id": "prop_01", "type": "prop", "name": "神兵",
                 "position": [0.5, 1.2, 0.3], "rotation": [0, 0, -15], "scale": 1.2,
                 "role": "道具", "structure_law": "长兵器结构铁律V1.2"},
                {"id": "env_01", "type": "environment", "name": "战旗",
                 "position": [-3, 0, -2], "rotation": [0, 30, 0], "scale": 1.5,
                 "role": "背景"},
                {"id": "env_02", "type": "environment", "name": "火光",
                 "position": [2, 0.5, -3], "rotation": [0, 0, 0], "scale": 2.0,
                 "role": "氛围"},
                {"id": "env_03", "type": "environment", "name": "远山",
                 "position": [0, 0, -10], "rotation": [0, 0, 0], "scale": 5.0,
                 "role": "远景"}
            ],
            "default_camera": "正面中景",
            "default_lighting": "黑金暗纹风格",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "did": f"DID-BR-{uuid.uuid4().hex[:8].upper()}",
            "trace_mark": "Ω₀⊂⊙∞⊂Ω"
        }

        self.scenes.append(scene)
        self._save(self.scenes_file, self.scenes)

        # 自动生成分镜
        self.generate_storyboard(scene["scene_id"])
        print(f"[完成] 场景: {scene['name']} | DID: {scene['did']}")
        return scene

    def generate_storyboard(self, scene_id):
        """为场景自动生成分镜表（多机位+多灯光组合）"""
        scene = next((s for s in self.scenes if s["scene_id"] == scene_id), None)
        if not scene:
            print(f"[错误] 场景不存在: {scene_id}")
            return []

        print(f"[分镜] 为「{scene['name']}」生成分镜...")

        # 生成6个关键分镜
        shot_configs = [
            {"camera": "俯视大全", "lighting": "史诗创世", "movement": "降", "duration": 4, "composition": "引导线", "description": "俯拍战场，镜头下降聚焦玄女"},
            {"camera": "正面中景", "lighting": "黑金暗纹风格", "movement": "推", "duration": 5, "composition": "三分法", "description": "玄女正面，推进至中景"},
            {"camera": "特写", "lighting": "伦勃朗光", "movement": "static", "duration": 3, "composition": "黄金分割", "description": "玄女面部特写，威严眼神"},
            {"camera": "侧面全景", "lighting": "逆光剪影", "movement": "摇", "duration": 4, "composition": "对角线", "description": "侧面全景，展示神兵与战姿"},
            {"camera": "低角度", "lighting": "硬光高反差", "movement": "升", "duration": 4, "composition": "中心构图", "description": "低角度仰拍，神兵高举，镜头上升"},
            {"camera": " Dutch角", "lighting": "月光冷调", "movement": "环绕", "duration": 5, "composition": "框架构图", "description": "Dutch角环绕，战火中玄女"}
        ]

        shots = []
        for i, cfg in enumerate(shot_configs):
            cam = self.CAMERA_PRESETS[cfg["camera"]]
            light = self.LIGHTING_PRESETS[cfg["lighting"]]
            move = self.CAMERA_MOVEMENTS.get(cfg["movement"], {"type": "static", "speed": 0})
            comp = self.COMPOSITION_RULES[cfg["composition"]]

            shot = {
                "shot_id": self._gen_id("SHOT"),
                "scene_id": scene_id,
                "shot_number": f"S01-{i+1:03d}",
                "camera": cfg["camera"],
                "camera_params": cam,
                "lighting": cfg["lighting"],
                "lighting_params": light,
                "movement": cfg["movement"],
                "movement_params": move,
                "composition": cfg["composition"],
                "composition_score": comp["weight"],
                "duration": cfg["duration"],
                "description": cfg["description"],
                "prompt": self._generate_prompt(scene, cfg),
                "hash": "",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            shot["hash"] = hashlib.sha256(json.dumps(shot, sort_keys=True).encode()).hexdigest()
            shots.append(shot)

        self.shots.extend(shots)
        self._save(self.shots_file, self.shots)
        print(f"[完成] 生成 {len(shots)} 个分镜")
        return shots

    def _generate_prompt(self, scene, cfg):
        """根据场景+机位+灯光生成提示词"""
        light = self.LIGHTING_PRESETS[cfg["lighting"]]
        return (
            f"{scene['name']}，{cfg['camera']}，{cfg['lighting']}，"
            f"{cfg['movement']}镜头，{cfg['composition']}构图，"
            f"{scene['environment']['time']}{scene['environment']['weather']}，"
            f"黑金暗纹风格，国风仙侠写实厚涂，史诗创世氛围，"
            f"UE5.7全局光追，8K超清，博物馆馆藏质感，浮雕立体感，"
            f"9:16竖屏，右下角Ω₀⊂⊙∞⊂Ω"
        )

    def analyze_composition(self, shot_id):
        """分析分镜构图质量"""
        shot = next((s for s in self.shots if s["shot_id"] == shot_id), None)
        if not shot:
            return None

        score = shot["composition_score"] * 100
        # 机位适配度
        camera_fit = {"特写": 0.9, "正面中景": 0.85, "侧面全景": 0.8, "俯视大全": 0.75}.get(shot["camera"], 0.7)
        # 灯光氛围匹配
        light_fit = {"黑金暗纹风格": 0.95, "伦勃朗光": 0.9, "史诗创世": 0.88}.get(shot["lighting"], 0.8)

        total = round((score * 0.4 + camera_fit * 100 * 0.3 + light_fit * 100 * 0.3), 1)
        return {
            "shot_id": shot_id,
            "composition_score": score,
            "camera_fit": camera_fit * 100,
            "light_fit": light_fit * 100,
            "total_score": total,
            "rating": "S" if total >= 90 else "A" if total >= 80 else "B" if total >= 70 else "C"
        }

    def export(self, scene_id, format="md"):
        """导出生成结果"""
        scene = next((s for s in self.scenes if s["scene_id"] == scene_id), None)
        if not scene:
            print(f"[错误] 场景不存在: {scene_id}")
            return

        scene_shots = [s for s in self.shots if s["scene_id"] == scene_id]

        if format == "md":
            lines = [
                f"# {scene['name']} - 导演台分镜表",
                f"",
                f"> DID: {scene['did']} | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS",
                f"",
                f"## 场景设定",
                f"- **环境**: {scene['environment']['type']} / {scene['environment']['time']}",
                f"- **天气**: {scene['environment']['weather']}",
                f"- **地面**: {scene['environment']['ground']}",
                f"- **背景**: {scene['environment']['background']}",
                f"",
                f"## 场景元素",
                f"| ID | 类型 | 名称 | 位置 | 角色 |",
                f"|---|---|---|---|---|"
            ]
            for el in scene["elements"]:
                lines.append(f"| {el['id']} | {el['type']} | {el['name']} | {el['position']} | {el['role']} |")

            lines.extend(["", "## 分镜表", ""])
            lines.append("| 镜号 | 机位 | 灯光 | 运动 | 构图 | 时长 | 描述 |")
            lines.append("|---|---|---|---|---|---|---|")
            for shot in scene_shots:
                lines.append(f"| {shot['shot_number']} | {shot['camera']} | {shot['lighting']} | {shot['movement']} | {shot['composition']} | {shot['duration']}s | {shot['description']} |")

            lines.extend(["", "## 提示词", ""])
            for shot in scene_shots:
                lines.append(f"### {shot['shot_number']}")
                lines.append(f"```")
                lines.append(shot["prompt"])
                lines.append(f"```")
                lines.append("")

            path = self.data_dir / f"{scene['name']}_storyboard.md"
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print(f"[导出] {path}")

        elif format == "json":
            export_data = {"scene": scene, "shots": scene_shots, "exported_at": datetime.now(timezone.utc).isoformat()}
            path = self.data_dir / f"{scene['name']}_storyboard.json"
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            print(f"[导出] {path}")

        elif format == "csv":
            import csv
            path = self.data_dir / f"{scene['name']}_storyboard.csv"
            with open(path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["镜号", "机位", "灯光", "运动", "构图", "时长", "描述", "提示词"])
                for shot in scene_shots:
                    writer.writerow([shot["shot_number"], shot["camera"], shot["lighting"],
                                    shot["movement"], shot["composition"], shot["duration"],
                                    shot["description"], shot["prompt"]])
            print(f"[导出] {path}")

    def list_presets(self):
        """列出所有预设"""
        print("\n=== 机位预设 (8种) ===")
        for name, params in self.CAMERA_PRESETS.items():
            print(f"  {name}: FOV={params['fov']}°, pos={params['position']}")

        print("\n=== 灯光预设 (8种) ===")
        for name, params in self.LIGHTING_PRESETS.items():
            print(f"  {name}: {params['description']}")

        print("\n=== 镜头运动 (8种) ===")
        for name, params in self.CAMERA_MOVEMENTS.items():
            print(f"  {name}: {params['description']}")

        print("\n=== 构图法则 (8种) ===")
        for name, params in self.COMPOSITION_RULES.items():
            print(f"  {name}: {params['description']} (权重{params['weight']})")


def main():
    parser = argparse.ArgumentParser(description="昆仑洞天·导演台3D场景布局器 V1.0")
    parser.add_argument("--init", action="store_true", help="初始化示例场景")
    parser.add_argument("--presets", action="store_true", help="列出所有预设")
    parser.add_argument("--scene", type=str, help="场景ID")
    parser.add_argument("--export", choices=["md", "json", "csv"], help="导出格式")
    parser.add_argument("--data-dir", default="./director_data", help="数据目录")
    args = parser.parse_args()

    print("=" * 60)
    print("  昆仑洞天·导演台3D场景布局器 V1.0")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS")
    print("=" * 60)

    desk = DirectorDesk(args.data_dir)

    if args.presets:
        desk.list_presets()
    elif args.init:
        scene = desk.init_sample_scene()
        if args.export:
            desk.export(scene["scene_id"], args.export)
    elif args.scene and args.export:
        desk.export(args.scene, args.export)
    else:
        print("使用 --init 初始化 | --presets 查看预设 | --scene ID --export md/json/csv 导出")


if __name__ == "__main__":
    main()
