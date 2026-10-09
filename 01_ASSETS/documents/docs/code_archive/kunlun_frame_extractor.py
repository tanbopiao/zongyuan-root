#!/usr/bin/env python3
"""
昆仑洞天·逐帧拉片器 MVP V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS

功能：
1. 视频帧提取（场景变化检测 + 固定间隔）
2. 感知哈希去重（pHash）
3. 帧内容基础分析（亮度/色彩/构图）
4. 结构化分镜表生成（镜号/时间码/画面描述/提示词）
5. 导出JSON/Markdown/CSV

用法：
  python3 kunlun_frame_extractor.py --input video.mp4 --output ./output
  python3 kunlun_frame_extractor.py --input video.mp4 --mode scene --threshold 30
  python3 kunlun_frame_extractor.py --input video.mp4 --mode interval --interval 2
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


class FrameExtractor:
    """视频帧提取器"""

    def __init__(self, video_path, output_dir, mode="scene", interval=2.0, threshold=30.0):
        self.video_path = video_path
        self.output_dir = Path(output_dir)
        self.frames_dir = self.output_dir / "frames"
        self.mode = mode  # scene / interval / hybrid
        self.interval = interval  # 固定间隔秒数
        self.threshold = threshold  # 场景变化阈值
        self.frames_dir.mkdir(parents=True, exist_ok=True)

        # 视频信息
        self.cap = cv2.VideoCapture(video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def _phash(self, image):
        """感知哈希 pHash"""
        img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        img = img.resize((32, 32), Image.LANCZOS).convert("L")
        pixels = np.array(img, dtype=np.float32)
        # DCT
        from scipy.fft import dct
        dct_val = dct(dct(pixels, axis=0), axis=1)
        dct_low = dct_val[:8, :8]
        median = np.median(dct_low)
        hash_bits = (dct_low > median).flatten()
        return sum([bit << i for i, bit in enumerate(hash_bits)])

    def _hamming_distance(self, h1, h2):
        """汉明距离"""
        x = h1 ^ h2
        return bin(x).count("1")

    def _scene_change_score(self, frame1, frame2):
        """场景变化评分（直方图差异）"""
        hist1 = cv2.calcHist([frame1], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist2 = cv2.calcHist([frame2], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        cv2.normalize(hist1, hist1)
        cv2.normalize(hist2, hist2)
        diff = cv2.compareHist(hist1, hist2, cv2.HISTCMP_BHATTACHARYYA)
        return diff * 100  # 0-100

    def extract(self):
        """执行帧提取"""
        extracted = []
        prev_frame = None
        prev_phash = None
        frame_idx = 0
        last_interval_time = 0

        print(f"[信息] 视频: {self.video_path}")
        print(f"[信息] 分辨率: {self.width}x{self.height}, FPS: {self.fps:.1f}")
        print(f"[信息] 时长: {self.duration:.1f}秒, 总帧数: {self.total_frames}")
        print(f"[信息] 模式: {self.mode}, 阈值: {self.threshold}")

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            current_time = frame_idx / self.fps
            should_extract = False
            reason = ""

            if self.mode in ("scene", "hybrid"):
                if prev_frame is not None:
                    score = self._scene_change_score(prev_frame, frame)
                    if score > self.threshold:
                        should_extract = True
                        reason = f"场景变化(score={score:.1f})"

            if self.mode in ("interval", "hybrid"):
                if current_time - last_interval_time >= self.interval:
                    should_extract = True
                    reason = f"固定间隔({self.interval}s)"
                    last_interval_time = current_time

            if should_extract:
                # pHash去重
                current_phash = self._phash(frame)
                if prev_phash is not None:
                    dist = self._hamming_distance(current_phash, prev_phash)
                    if dist < 5:  # 太相似，跳过
                        frame_idx += 1
                        continue

                # 保存帧
                timecode = self._format_timecode(current_time)
                frame_name = f"frame_{len(extracted)+1:04d}_{timecode.replace(':', '-')}.jpg"
                frame_path = self.frames_dir / frame_name
                cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])

                # 帧分析
                analysis = self._analyze_frame(frame)

                extracted.append({
                    "index": len(extracted) + 1,
                    "frame_number": frame_idx,
                    "timecode": timecode,
                    "timestamp": round(current_time, 2),
                    "filename": frame_name,
                    "path": str(frame_path),
                    "reason": reason,
                    "phash": current_phash,
                    "analysis": analysis
                })

                prev_phash = current_phash
                if len(extracted) % 10 == 0:
                    print(f"[进度] 已提取 {len(extracted)} 帧...")

            prev_frame = frame.copy()
            frame_idx += 1

        self.cap.release()
        print(f"[完成] 共提取 {len(extracted)} 帧")
        return extracted

    def _analyze_frame(self, frame):
        """基础帧内容分析"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 亮度
        brightness = float(np.mean(gray))
        # 对比度
        contrast = float(np.std(gray))
        # 主色调
        hue_mean = float(np.mean(hsv[:, :, 0]))
        saturation = float(np.mean(hsv[:, :, 1]))
        # 色彩丰富度
        color_variance = float(np.std(hsv[:, :, 0]))

        # 构图分析（三分法）
        h, w = frame.shape[:2]
        third_h, third_w = h // 3, w // 3
        regions = {
            "top_left": gray[0:third_h, 0:third_w].mean(),
            "top_center": gray[0:third_h, third_w:2*third_w].mean(),
            "top_right": gray[0:third_h, 2*third_w:w].mean(),
            "center_left": gray[third_h:2*third_h, 0:third_w].mean(),
            "center": gray[third_h:2*third_h, third_w:2*third_w].mean(),
            "center_right": gray[third_h:2*third_h, 2*third_w:w].mean(),
            "bottom_left": gray[2*third_h:h, 0:third_w].mean(),
            "bottom_center": gray[2*third_h:h, third_w:2*third_w].mean(),
            "bottom_right": gray[2*third_h:h, 2*third_w:w].mean(),
        }

        # 判断明暗
        if brightness < 60:
            light_type = "暗调/夜景"
        elif brightness < 120:
            light_type = "低调/侧光"
        elif brightness < 180:
            light_type = "正常/柔光"
        else:
            light_type = "高调/过曝"

        # 判断色调
        if saturation < 30:
            color_type = "低饱和/灰度"
        elif hue_mean < 30 or hue_mean > 150:
            color_type = "暖色调"
        elif hue_mean < 90:
            color_type = "绿色调"
        else:
            color_type = "冷色调"

        return {
            "brightness": round(brightness, 1),
            "contrast": round(contrast, 1),
            "hue_mean": round(hue_mean, 1),
            "saturation": round(saturation, 1),
            "color_variance": round(color_variance, 1),
            "light_type": light_type,
            "color_type": color_type,
            "regions": {k: round(v, 1) for k, v in regions.items()}
        }

    def _format_timecode(self, seconds):
        """秒数转时间码 HH:MM:SS.mmm"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def generate_storyboard(self, frames):
        """生成结构化分镜表"""
        storyboard = []
        for i, frame in enumerate(frames):
            analysis = frame["analysis"]

            # 自动生成画面描述
            description = self._generate_description(frame, i, len(frames))

            # 自动生成提示词（昆仑洞天黑金暗纹风格）
            prompt = self._generate_prompt(frame, description)

            # 估算时长
            if i < len(frames) - 1:
                duration = round(frames[i+1]["timestamp"] - frame["timestamp"], 1)
            else:
                duration = round(self.duration - frame["timestamp"], 1)

            storyboard.append({
                "shot_id": f"S{len(str(len(frames)))}-{i+1:03d}",
                "timecode": frame["timecode"],
                "timestamp": frame["timestamp"],
                "duration": duration,
                "description": description,
                "prompt": prompt,
                "light": analysis["light_type"],
                "color": analysis["color_type"],
                "brightness": analysis["brightness"],
                "contrast": analysis["contrast"],
                "frame_file": frame["filename"],
                "extraction_reason": frame["reason"]
            })

        return storyboard

    def _generate_description(self, frame, index, total):
        """生成画面描述（基于分析数据的规则引擎）"""
        a = frame["analysis"]
        parts = []

        # 景别估算（基于构图区域亮度分布）
        regions = a["regions"]
        center_brightness = regions["center"]
        edge_brightness = (regions["top_left"] + regions["top_right"] +
                          regions["bottom_left"] + regions["bottom_right"]) / 4

        if abs(center_brightness - edge_brightness) > 30:
            parts.append("主体居中突出")
        elif a["contrast"] > 60:
            parts.append("大反差构图")
        else:
            parts.append("均衡构图")

        # 光线
        parts.append(a["light_type"])

        # 色调
        parts.append(a["color_type"])

        # 节奏
        if index == 0:
            parts.append("开场镜头")
        elif index == total - 1:
            parts.append("结尾镜头")
        elif frame["reason"].startswith("场景变化"):
            parts.append("场景切换")
        else:
            parts.append("连续镜头")

        return "，".join(parts)

    def _generate_prompt(self, frame, description):
        """生成昆仑洞天风格提示词"""
        a = frame["analysis"]

        # 光线映射
        light_map = {
            "暗调/夜景": "暗夜神光，伦勃朗光影，暗部细节保留",
            "低调/侧光": "侧光塑形，明暗对比，黑金暗纹",
            "正常/柔光": "柔光漫射，自然过渡，神性光晕",
            "高调/过曝": "高光神性，圣光笼罩，金边轮廓"
        }
        light_prompt = light_map.get(a["light_type"], "伦勃朗光影")

        # 色调映射
        color_map = {
            "低饱和/灰度": "低饱和灰度，水墨质感，玄黑基调",
            "暖色调": "暖金调，赤金光芒，烈焰氛围",
            "绿色调": "青绿山水，仙气缭绕，自然生机",
            "冷色调": "冷蓝玄黑，冰霜质感，幽冥氛围"
        }
        color_prompt = color_map.get(a["color_type"], "黑金暗纹")

        prompt = (
            f"东方神女，{description}，{light_prompt}，{color_prompt}，"
            f"国风仙侠写实厚涂，史诗创世氛围，UE5.7全局光追，8K超清，"
            f"博物馆馆藏质感，浮雕立体感，9:16竖屏，右下角Ω₀⊂⊙∞⊂Ω"
        )
        return prompt

    def export(self, storyboard, frames):
        """导出多种格式"""
        results = {}

        # JSON
        json_path = self.output_dir / "storyboard.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "source_video": os.path.basename(self.video_path),
                "video_info": {
                    "resolution": f"{self.width}x{self.height}",
                    "fps": round(self.fps, 1),
                    "duration": round(self.duration, 1),
                    "total_frames": self.total_frames
                },
                "extraction_config": {
                    "mode": self.mode,
                    "threshold": self.threshold,
                    "interval": self.interval
                },
                "frame_count": len(frames),
                "storyboard": storyboard
            }, f, ensure_ascii=False, indent=2)
        results["json"] = str(json_path)

        # Markdown
        md_path = self.output_dir / "storyboard.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# 昆仑洞天·逐帧拉片分镜表\n\n")
            f.write(f"> 源视频: {os.path.basename(self.video_path)}\n")
            f.write(f"> 分辨率: {self.width}x{self.height} | FPS: {self.fps:.1f} | 时长: {self.duration:.1f}s\n")
            f.write(f"> 提取帧数: {len(frames)} | 模式: {self.mode}\n")
            f.write(f"> DID-BR-000002 | Ω₀⊂⊙∞⊂Ω\n\n")
            f.write("| 镜号 | 时间码 | 时长 | 画面描述 | 光线 | 色调 |\n")
            f.write("|------|--------|------|----------|------|------|\n")
            for s in storyboard:
                f.write(f"| {s['shot_id']} | {s['timecode']} | {s['duration']}s | {s['description']} | {s['light']} | {s['color']} |\n")

            f.write("\n## 关键帧提示词\n\n")
            for s in storyboard:
                f.write(f"### {s['shot_id']} ({s['timecode']})\n")
                f.write(f"- **画面**: {s['description']}\n")
                f.write(f"- **提示词**: {s['prompt']}\n\n")
        results["markdown"] = str(md_path)

        # CSV
        csv_path = self.output_dir / "storyboard.csv"
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write("镜号,时间码,时长,画面描述,光线,色调,亮度,对比度\n")
            for s in storyboard:
                f.write(f"{s['shot_id']},{s['timecode']},{s['duration']},\"{s['description']}\",{s['light']},{s['color']},{s['brightness']},{s['contrast']}\n")
        results["csv"] = str(csv_path)

        # 计算整体哈希
        all_content = json.dumps(storyboard, ensure_ascii=False, sort_keys=True)
        content_hash = hashlib.sha256(all_content.encode()).hexdigest()
        results["content_hash"] = content_hash

        print(f"[导出] JSON: {json_path}")
        print(f"[导出] Markdown: {md_path}")
        print(f"[导出] CSV: {csv_path}")
        print(f"[确权] 内容哈希: {content_hash[:16]}...")

        return results


def main():
    parser = argparse.ArgumentParser(description="昆仑洞天·逐帧拉片器 MVP V1.0")
    parser.add_argument("--input", required=True, help="输入视频路径")
    parser.add_argument("--output", default="./frame_output", help="输出目录")
    parser.add_argument("--mode", choices=["scene", "interval", "hybrid"], default="hybrid",
                        help="提取模式: scene(场景变化)/interval(固定间隔)/hybrid(混合)")
    parser.add_argument("--interval", type=float, default=2.0, help="固定间隔秒数 (interval/hybrid模式)")
    parser.add_argument("--threshold", type=float, default=30.0, help="场景变化阈值 (scene/hybrid模式)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[错误] 视频文件不存在: {args.input}")
        sys.exit(1)

    print("=" * 60)
    print("  昆仑洞天·逐帧拉片器 MVP V1.0")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS")
    print("=" * 60)

    extractor = FrameExtractor(args.input, args.output, args.mode, args.interval, args.threshold)

    start_time = time.time()
    frames = extractor.extract()
    storyboard = extractor.generate_storyboard(frames)
    results = extractor.export(storyboard, frames)
    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print(f"  拉片完成 | 耗时: {elapsed:.1f}s | 提取: {len(frames)}帧")
    print(f"  分镜: {len(storyboard)}镜 | 哈希: {results['content_hash'][:16]}...")
    print("=" * 60)


if __name__ == "__main__":
    main()
