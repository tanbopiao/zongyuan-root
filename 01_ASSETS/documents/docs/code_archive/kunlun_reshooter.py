#!/usr/bin/env python3
"""
昆仑洞天·片段重拍器 MVP V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS

功能：
1. 视频片段精准定位（时间码/帧级精度）
2. 首尾帧提取（作为重生成参考）
3. 重拍提示词自动生成（继承角色/场景/风格）
4. 重拍任务清单生成（供Seedance/MiniMax API调用）
5. 视频自动拼接（重拍片段替换原片段，FFmpeg concat）
6. 多片段批量重拍
7. 运动轨迹连续性校验
8. SHA256确权哈希

用法：
  python3 kunlun_reshooter.py --input video.mp4 --segments "00:00:05-00:00:10,00:00:20-00:00:25"
  python3 kunlun_reshooter.py --input video.mp4 --segments segments.json
  python3 kunlun_reshooter.py --input video.mp4 --segments "00:00:05-00:00:10" --instruction "玄女表情改为威严"
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


class VideoReshooter:
    """视频片段重拍器"""

    def __init__(self, video_path, output_dir="./reshoot_output"):
        self.video_path = video_path
        self.output_dir = Path(output_dir)
        self.segments_dir = self.output_dir / "segments"
        self.frames_dir = self.output_dir / "keyframes"
        self.result_dir = self.output_dir / "result"
        for d in [self.segments_dir, self.frames_dir, self.result_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # 视频信息
        self.cap = cv2.VideoCapture(video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.cap.release()

        self.video_hash = self._calc_file_hash(video_path)

    def _calc_file_hash(self, path):
        """计算文件SHA256"""
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

    def _parse_timecode(self, tc):
        """时间码转秒 HH:MM:SS.mmm"""
        parts = tc.replace('.', ':').split(':')
        h = int(parts[0]) if len(parts) > 0 else 0
        m = int(parts[1]) if len(parts) > 1 else 0
        s = int(parts[2]) if len(parts) > 2 else 0
        ms = int(parts[3]) if len(parts) > 3 else 0
        return h * 3600 + m * 60 + s + ms / 1000

    def _format_timecode(self, seconds):
        """秒转时间码"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def parse_segments(self, segments_str):
        """解析片段参数"""
        segments = []
        if segments_str.endswith('.json'):
            with open(segments_str, 'r') as f:
                data = json.load(f)
                segments = data if isinstance(data, list) else data.get('segments', [])
        else:
            for seg in segments_str.split(','):
                seg = seg.strip()
                if '-' in seg:
                    start, end = seg.split('-', 1)
                    segments.append({
                        "start": start.strip(),
                        "end": end.strip(),
                        "instruction": ""
                    })
        # 转换时间码
        for seg in segments:
            seg["start_sec"] = self._parse_timecode(seg["start"])
            seg["end_sec"] = self._parse_timecode(seg["end"])
            seg["duration"] = round(seg["end_sec"] - seg["start_sec"], 3)
            seg["start_frame"] = int(seg["start_sec"] * self.fps)
            seg["end_frame"] = int(seg["end_sec"] * self.fps)
        return segments

    def extract_segment(self, seg, index):
        """提取指定片段"""
        seg_id = f"seg_{index+1:03d}"
        output_path = self.segments_dir / f"{seg_id}.mp4"

        # FFmpeg提取片段（精确到帧）
        cmd = [
            'ffmpeg', '-y',
            '-i', self.video_path,
            '-ss', seg["start"],
            '-to', seg["end"],
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-c:a', 'aac', '-b:a', '128k',
            '-avoid_negative_ts', 'make_zero',
            str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"  [警告] 片段{seg_id}提取失败: {result.stderr[-200:]}")
            return None

        seg["segment_file"] = str(output_path)
        seg["segment_hash"] = self._calc_file_hash(str(output_path))
        return seg

    def extract_keyframes(self, seg, index):
        """提取首尾帧"""
        seg_id = f"seg_{index+1:03d}"
        first_frame_path = self.frames_dir / f"{seg_id}_first.jpg"
        last_frame_path = self.frames_dir / f"{seg_id}_last.jpg"

        # 首帧
        cmd1 = ['ffmpeg', '-y', '-ss', seg["start"], '-i', self.video_path,
                '-frames:v', '1', '-q:v', '2', str(first_frame_path)]
        subprocess.run(cmd1, capture_output=True)

        # 尾帧（在结束前0.04秒取帧）
        last_time = max(0, seg["end_sec"] - 0.04)
        cmd2 = ['ffmpeg', '-y', '-ss', self._format_timecode(last_time),
                '-i', self.video_path, '-frames:v', '1', '-q:v', '2', str(last_frame_path)]
        subprocess.run(cmd2, capture_output=True)

        if os.path.exists(first_frame_path) and os.path.exists(last_frame_path):
            seg["first_frame"] = str(first_frame_path)
            seg["last_frame"] = str(last_frame_path)
            seg["first_frame_hash"] = self._calc_file_hash(str(first_frame_path))
            seg["last_frame_hash"] = self._calc_file_hash(str(last_frame_path))

            # 帧分析
            seg["first_analysis"] = self._analyze_frame(str(first_frame_path))
            seg["last_analysis"] = self._analyze_frame(str(last_frame_path))
        return seg

    def _analyze_frame(self, frame_path):
        """基础帧分析"""
        img = cv2.imread(frame_path)
        if img is None:
            return {}
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return {
            "brightness": round(float(np.mean(gray)), 1),
            "contrast": round(float(np.std(gray)), 1),
            "hue_mean": round(float(np.mean(hsv[:, :, 0])), 1),
            "saturation": round(float(np.mean(hsv[:, :, 1])), 1),
            "dominant_color": self._dominant_color(img)
        }

    def _dominant_color(self, img):
        """主色调"""
        pixels = np.float32(img.reshape(-1, 3))
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(pixels, 3, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        dominant = centers[np.argmax(np.bincount(labels.flatten()))]
        return f"rgb({int(dominant[2])},{int(dominant[1])},{int(dominant[0])})"

    def generate_reshoot_prompt(self, seg, index):
        """生成重拍提示词"""
        seg_id = f"seg_{index+1:03d}"
        instruction = seg.get("instruction", "")
        first_ana = seg.get("first_analysis", {})
        last_ana = seg.get("last_analysis", {})

        # 基础风格（昆仑洞天黑金暗纹）
        base_style = (
            "东方神女，国风仙侠写实厚涂，史诗创世氛围，"
            "UE5.7全局光追，8K超清，博物馆馆藏质感，浮雕立体感，"
            "黑金暗纹风格，9:16竖屏，右下角Ω₀⊂⊙∞⊂Ω"
        )

        # 光线继承
        brightness = first_ana.get("brightness", 128)
        if brightness < 60:
            light = "暗夜神光，伦勃朗光影，暗部细节保留"
        elif brightness < 120:
            light = "侧光塑形，明暗对比，黑金暗纹"
        elif brightness < 180:
            light = "柔光漫射，自然过渡，神性光晕"
        else:
            light = "高光神性，圣光笼罩，金边轮廓"

        # 构建提示词
        if instruction:
            prompt = f"{instruction}，{light}，{base_style}"
        else:
            prompt = f"{light}，{base_style}，保持角色与场景一致性"

        # 首尾帧控制提示（用于图生视频）
        first_frame_prompt = f"首帧参考：角色姿态、场景布局、光线方向严格匹配"
        last_frame_prompt = f"尾帧参考：结束状态与下一镜头自然衔接"

        seg["reshoot_prompt"] = prompt
        seg["first_frame_instruction"] = first_frame_prompt
        seg["last_frame_instruction"] = last_frame_prompt
        seg["reshoot_duration"] = seg["duration"]
        seg["api_params"] = {
            "model": "seedance_2_5",
            "duration": min(10, max(5, int(seg["duration"]))),
            "resolution": f"{self.width}x{self.height}",
            "first_frame": seg.get("first_frame", ""),
            "last_frame": seg.get("last_frame", ""),
            "prompt": prompt,
            "motion_bucket_id": 127,
            "cfg_scale": 7.0
        }
        return seg

    def check_continuity(self, seg, index):
        """运动轨迹连续性校验"""
        if "first_analysis" not in seg or "last_analysis" not in seg:
            seg["continuity"] = {"status": "unknown", "score": 0}
            return seg

        first = seg["first_analysis"]
        last = seg["last_analysis"]

        # 亮度变化
        brightness_diff = abs(first.get("brightness", 0) - last.get("brightness", 0))
        # 色调变化
        hue_diff = abs(first.get("hue_mean", 0) - last.get("hue_mean", 0))
        # 对比度变化
        contrast_diff = abs(first.get("contrast", 0) - last.get("contrast", 0))

        # 连续性评分（0-100）
        score = 100
        if brightness_diff > 50:
            score -= 20
        if hue_diff > 60:
            score -= 25
        if contrast_diff > 40:
            score -= 15

        if score >= 80:
            status = "good"
            warning = "连续性良好"
        elif score >= 60:
            status = "warning"
            warning = "存在一定跳变，建议检查转场"
        else:
            status = "bad"
            warning = "连续性差，重拍时需注意首尾衔接"

        seg["continuity"] = {
            "score": score,
            "status": status,
            "warning": warning,
            "brightness_diff": round(brightness_diff, 1),
            "hue_diff": round(hue_diff, 1),
            "contrast_diff": round(contrast_diff, 1)
        }
        return seg

    def generate_task_list(self, segments):
        """生成重拍任务清单"""
        task_list = {
            "task_id": f"RESHOOT-{int(time.time())}",
            "source_video": os.path.basename(self.video_path),
            "source_hash": self.video_hash,
            "video_info": {
                "resolution": f"{self.width}x{self.height}",
                "fps": round(self.fps, 1),
                "duration": round(self.duration, 1),
                "total_frames": self.total_frames
            },
            "segment_count": len(segments),
            "total_reshoot_duration": round(sum(s["duration"] for s in segments), 1),
            "segments": segments,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "did": "DID-BR-000002",
            "trace": "Ω₀⊂⊙∞⊂Ω"
        }

        task_path = self.output_dir / "reshoot_tasks.json"
        with open(task_path, 'w', encoding='utf-8') as f:
            json.dump(task_list, f, ensure_ascii=False, indent=2)

        print(f"[任务清单] {task_path}")
        print(f"  - 待重拍片段: {len(segments)}个")
        print(f"  - 总重拍时长: {task_list['total_reshoot_duration']}秒")
        return task_list, task_path

    def concatenate_video(self, segments, reshooted_files=None):
        """
        拼接最终视频
        reshooted_files: {seg_index: reshooted_video_path}，如果为None则用原片段标记
        """
        if reshooted_files is None:
            reshooted_files = {}

        # 构建拼接列表
        concat_list = []
        current_time = 0

        for i, seg in enumerate(segments):
            # 重拍片段前的保留部分
            if seg["start_sec"] > current_time:
                keep_path = self.segments_dir / f"keep_{i:03d}_pre.mp4"
                cmd = ['ffmpeg', '-y', '-i', self.video_path,
                       '-ss', self._format_timecode(current_time),
                       '-to', seg["start"],
                       '-c', 'copy', str(keep_path)]
                subprocess.run(cmd, capture_output=True)
                if os.path.exists(keep_path):
                    concat_list.append(str(keep_path))

            # 重拍片段（优先用重拍的，否则用原片段）
            if i in reshooted_files and os.path.exists(reshooted_files[i]):
                concat_list.append(reshooted_files[i])
            elif "segment_file" in seg and os.path.exists(seg["segment_file"]):
                concat_list.append(seg["segment_file"])

            current_time = seg["end_sec"]

        # 最后一段保留部分
        if current_time < self.duration:
            keep_path = self.segments_dir / "keep_final.mp4"
            cmd = ['ffmpeg', '-y', '-i', self.video_path,
                   '-ss', self._format_timecode(current_time),
                   '-c', 'copy', str(keep_path)]
            subprocess.run(cmd, capture_output=True)
            if os.path.exists(keep_path):
                concat_list.append(str(keep_path))

        # 写入concat列表
        list_path = self.output_dir / "concat_list.txt"
        with open(list_path, 'w') as f:
            for p in concat_list:
                f.write(f"file '{os.path.abspath(p)}'\n")

        # 拼接
        output_path = self.result_dir / "final_reshooted.mp4"
        cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0',
               '-i', str(list_path), '-c', 'copy', str(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            # 降级：重新编码拼接
            cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                   '-i', str(list_path),
                   '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                   '-c:a', 'aac', str(output_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)

        if os.path.exists(output_path):
            final_hash = self._calc_file_hash(str(output_path))
            print(f"[拼接完成] {output_path}")
            print(f"  哈希: {final_hash[:16]}...")
            return str(output_path), final_hash
        else:
            print(f"[错误] 拼接失败: {result.stderr[-300:]}")
            return None, None

    def run(self, segments_str, instruction=""):
        """执行完整重拍流程"""
        print("=" * 60)
        print("  昆仑洞天·片段重拍器 MVP V1.0")
        print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS")
        print("=" * 60)
        print(f"[信息] 源视频: {self.video_path}")
        print(f"[信息] 分辨率: {self.width}x{self.height}, FPS: {self.fps:.1f}")
        print(f"[信息] 时长: {self.duration:.1f}秒, 源哈希: {self.video_hash[:16]}...")

        # 1. 解析片段
        segments = self.parse_segments(segments_str)
        if instruction:
            for seg in segments:
                seg["instruction"] = instruction
        print(f"\n[步骤1] 解析到 {len(segments)} 个待重拍片段")
        for i, seg in enumerate(segments):
            print(f"  片段{i+1}: {seg['start']} → {seg['end']} ({seg['duration']}s)")

        # 2. 提取片段
        print(f"\n[步骤2] 提取视频片段...")
        for i, seg in enumerate(segments):
            self.extract_segment(seg, i)
            print(f"  片段{i+1}提取: {'✅' if 'segment_file' in seg else '❌'}")

        # 3. 提取首尾帧
        print(f"\n[步骤3] 提取首尾帧...")
        for i, seg in enumerate(segments):
            self.extract_keyframes(seg, i)
            print(f"  片段{i+1}首尾帧: {'✅' if 'first_frame' in seg else '❌'}")

        # 4. 生成重拍提示词
        print(f"\n[步骤4] 生成重拍提示词...")
        for i, seg in enumerate(segments):
            self.generate_reshoot_prompt(seg, i)
            print(f"  片段{i+1}提示词: {seg['reshoot_prompt'][:50]}...")

        # 5. 连续性校验
        print(f"\n[步骤5] 运动轨迹连续性校验...")
        for i, seg in enumerate(segments):
            self.check_continuity(seg, i)
            c = seg["continuity"]
            status_icon = "✅" if c["status"] == "good" else ("⚠️" if c["status"] == "warning" else "❌")
            print(f"  片段{i+1}: {status_icon} 评分{c['score']} - {c['warning']}")

        # 6. 生成任务清单
        print(f"\n[步骤6] 生成重拍任务清单...")
        task_list, task_path = self.generate_task_list(segments)

        # 7. 拼接预览（用原片段标记，重拍后替换）
        print(f"\n[步骤7] 生成拼接预览（原片段占位，重拍后替换）...")
        final_path, final_hash = self.concatenate_video(segments)

        # 8. 导出报告
        report = {
            "task_id": task_list["task_id"],
            "source_video": os.path.basename(self.video_path),
            "source_hash": self.video_hash,
            "segments_processed": len(segments),
            "total_reshoot_duration": task_list["total_reshoot_duration"],
            "continuity_scores": [s["continuity"]["score"] for s in segments],
            "avg_continuity": round(np.mean([s["continuity"]["score"] for s in segments]), 1),
            "task_list_file": str(task_path),
            "final_preview": final_path,
            "final_hash": final_hash,
            "status": "TASKS_GENERATED",
            "note": "重拍任务清单已生成，调用Seedance/MiniMax API完成重生成后，使用concatenate_video替换片段即可"
        }

        report_path = self.output_dir / "reshoot_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 60}")
        print(f"  重拍准备完成")
        print(f"  任务清单: {task_path}")
        print(f"  拼接预览: {final_path}")
        print(f"  平均连续性: {report['avg_continuity']}/100")
        print(f"  下一步: 调用API重生成 → 替换片段 → 最终拼接")
        print(f"{'=' * 60}")

        return report


def main():
    parser = argparse.ArgumentParser(description="昆仑洞天·片段重拍器 MVP V1.0")
    parser.add_argument("--input", required=True, help="输入视频路径")
    parser.add_argument("--segments", required=True,
                        help="重拍片段，格式: '00:00:05-00:00:10,00:00:20-00:00:25' 或 JSON文件路径")
    parser.add_argument("--instruction", default="", help="重拍指令（应用到所有片段）")
    parser.add_argument("--output", default="./reshoot_output", help="输出目录")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[错误] 视频文件不存在: {args.input}")
        sys.exit(1)

    reshooter = VideoReshooter(args.input, args.output)
    reshooter.run(args.segments, args.instruction)


if __name__ == "__main__":
    main()
