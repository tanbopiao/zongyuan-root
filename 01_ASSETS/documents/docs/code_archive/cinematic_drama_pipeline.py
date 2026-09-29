#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
昆仑洞天 · 电影级短剧生产流水线 V1.0
功能：TTS语音合成 + 字幕生成 + 音视频合成 + 电影级调色 + 三版本输出
零成本运行：edge-tts(免费) + ffmpeg(开源) + Noto CJK字体(开源)
作者：ZONGYUAN-ROOT 元极恒一自治体系
确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import os
import sys
import json
import time
import asyncio
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime

# ========== 配置 ==========
BASE_DIR = "/www/wwwroot/huodouai.com/drama"
VIDEO_DIR = f"{BASE_DIR}/videos"
AUDIO_DIR = f"{BASE_DIR}/audios"
SUBTITLE_DIR = f"{BASE_DIR}/subtitles"
OUTPUT_DIR = f"{BASE_DIR}/output"
FONT_PATH = "/usr/share/fonts/google-noto-cjk/NotoSerifCJK-Bold.ttc"
BGM_PATH = "/opt/ZONGYUAN-ROOT/media_pipeline/asset_output/audio_bgm/kunlun_narration.wav"

# 三版本配置
VERSIONS = {
    "free": {
        "name": "免费体验版",
        "resolution": "1280x720",
        "bitrate": "2M",
        "watermark": True,
        "max_duration": 60,
        "subtitle_style": "basic",
        "audio_quality": "128k",
        "color_grade": "basic"
    },
    "pro": {
        "name": "专业版",
        "resolution": "1920x1080",
        "bitrate": "5M",
        "watermark": False,
        "max_duration": 180,
        "subtitle_style": "professional",
        "audio_quality": "192k",
        "color_grade": "cinematic"
    },
    "director": {
        "name": "导演版",
        "resolution": "3840x2160",
        "bitrate": "15M",
        "watermark": False,
        "max_duration": 300,
        "subtitle_style": "cinematic",
        "audio_quality": "320k",
        "color_grade": "director"
    }
}

# TTS语音配置（edge-tts中文语音）
TTS_VOICES = {
    "narrator": "zh-CN-YunxiNeural",      # 旁白男声
    "female_elegant": "zh-CN-XiaoxiaoNeural",  # 优雅女声（九天玄女）
    "female_soft": "zh-CN-XiaoyiNeural",    # 柔美女声
    "male_powerful": "zh-CN-YunyangNeural", # 威严男声
    "male_youth": "zh-CN-YunjianNeural"     # 青年男声
}

# ========== 工具函数 ==========
def ensure_dirs():
    """确保所有目录存在"""
    for d in [VIDEO_DIR, AUDIO_DIR, SUBTITLE_DIR, OUTPUT_DIR]:
        os.makedirs(d, exist_ok=True)

def sha256_file(filepath):
    """计算文件SHA256"""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def run_cmd(cmd, timeout=300):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"
    except Exception as e:
        return False, "", str(e)

def get_video_duration(video_path):
    """获取视频时长（秒）"""
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
    ok, out, err = run_cmd(cmd)
    if ok and out.strip():
        return float(out.strip())
    return 0

# ========== S4: TTS语音合成 ==========
async def tts_generate(text, voice="narrator", output_path=None, rate="+0%"):
    """
    使用edge-tts生成语音
    :param text: 文本内容
    :param voice: 语音类型
    :param output_path: 输出路径
    :param rate: 语速调整
    :return: 输出文件路径
    """
    import edge_tts
    
    if output_path is None:
        timestamp = int(time.time())
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        output_path = f"{AUDIO_DIR}/tts_{voice}_{timestamp}_{text_hash}.mp3"
    
    voice_name = TTS_VOICES.get(voice, TTS_VOICES["narrator"])
    
    communicate = edge_tts.Communicate(text, voice_name, rate=rate)
    await communicate.save(output_path)
    
    return output_path

async def tts_batch_generate(dialogues):
    """
    批量生成对话语音
    :param dialogues: [{"text": "...", "voice": "narrator", "speaker": "旁白"}]
    :return: 语音文件列表
    """
    results = []
    for i, d in enumerate(dialogues):
        text = d.get("text", "")
        voice = d.get("voice", "narrator")
        speaker = d.get("speaker", "旁白")
        
        if not text.strip():
            continue
        
        print(f"  [TTS] {i+1}/{len(dialogues)} {speaker}: {text[:30]}...")
        audio_path = await tts_generate(text, voice)
        results.append({
            "index": i,
            "speaker": speaker,
            "text": text,
            "audio_path": audio_path,
            "duration": get_video_duration(audio_path)
        })
    
    return results

# ========== S5: 字幕生成 ==========
def generate_srt(dialogues, output_path=None):
    """
    生成SRT字幕文件
    :param dialogues: [{"text": "...", "start": 0.0, "end": 5.0}]
    :param output_path: 输出路径
    :return: 字幕文件路径
    """
    if output_path is None:
        timestamp = int(time.time())
        output_path = f"{SUBTITLE_DIR}/subtitle_{timestamp}.srt"
    
    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, d in enumerate(dialogues, 1):
            start = d.get("start", 0)
            end = d.get("end", start + 3)
            text = d.get("text", "")
            
            f.write(f"{i}\n")
            f.write(f"{format_time(start)} --> {format_time(end)}\n")
            f.write(f"{text}\n\n")
    
    return output_path

def generate_ass(dialogues, style="professional", output_path=None):
    """
    生成ASS高级字幕文件（电影级样式）
    :param dialogues: 对话列表
    :param style: 样式类型 (basic/professional/cinematic)
    :param output_path: 输出路径
    :return: 字幕文件路径
    """
    if output_path is None:
        timestamp = int(time.time())
        output_path = f"{SUBTITLE_DIR}/subtitle_{timestamp}_{style}.ass"
    
    # 样式配置
    styles = {
        "basic": {
            "fontname": "Noto Sans CJK SC",
            "fontsize": "24",
            "primaryColour": "&H00FFFFFF",
            "outlineColour": "&H00000000",
            "backColour": "&H80000000",
            "outline": "2",
            "shadow": "1",
            "alignment": "2"
        },
        "professional": {
            "fontname": "Noto Serif CJK SC",
            "fontsize": "28",
            "primaryColour": "&H00FFFFFF",
            "outlineColour": "&H00000000",
            "backColour": "&H00000000",
            "outline": "3",
            "shadow": "2",
            "alignment": "2"
        },
        "cinematic": {
            "fontname": "Noto Serif CJK SC",
            "fontsize": "36",
            "primaryColour": "&H00F0E6D2",
            "outlineColour": "&H00000000",
            "backColour": "&H00000000",
            "outline": "4",
            "shadow": "3",
            "alignment": "2"
        }
    }
    
    s = styles.get(style, styles["professional"])
    
    def format_time_ass(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        sec = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("[Script Info]\n")
        f.write("Title: 昆仑洞天电影级字幕\n")
        f.write("ScriptType: v4.00+\n")
        f.write("PlayResX: 1920\n")
        f.write("PlayResY: 1080\n")
        f.write("WrapStyle: 0\n")
        f.write("ScaledBorderAndShadow: yes\n\n")
        
        f.write("[V4+ Styles]\n")
        f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
        f.write(f"Style: Default,{s['fontname']},{s['fontsize']},{s['primaryColour']},&H000000FF,{s['outlineColour']},{s['backColour']},-1,0,0,0,100,100,0,0,1,{s['outline']},{s['shadow']},{s['alignment']},10,10,30,1\n\n")
        
        f.write("[Events]\n")
        f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        
        for d in dialogues:
            start = d.get("start", 0)
            end = d.get("end", start + 3)
            text = d.get("text", "").replace("\n", "\\N")
            speaker = d.get("speaker", "")
            
            if speaker and speaker != "旁白":
                text = f"{{\\b1}}{speaker}：{{\\b0}}{text}"
            
            f.write(f"Dialogue: 0,{format_time_ass(start)},{format_time_ass(end)},Default,,0,0,0,,{text}\n")
    
    return output_path

# ========== S6: 音视频合成 ==========
def merge_audio_video(video_path, audio_files, bgm_path=None, output_path=None, 
                       version="pro", subtitle_path=None):
    """
    音视频合成（视频+语音+背景音乐+字幕+调色+音频标准化）
    :param video_path: 视频文件路径
    :param audio_files: 语音文件列表 [{"path": "...", "start": 0.0}]
    :param bgm_path: 背景音乐路径
    :param output_path: 输出路径
    :param version: 版本 (free/pro/director)
    :param subtitle_path: 字幕文件路径
    :return: 输出文件路径
    """
    v = VERSIONS.get(version, VERSIONS["pro"])
    
    if output_path is None:
        timestamp = int(time.time())
        output_path = f"{OUTPUT_DIR}/drama_{version}_{timestamp}.mp4"
    
    # 构建ffmpeg命令
    inputs = [f'-i "{video_path}"']
    
    # 添加语音输入
    audio_delays = []
    for i, af in enumerate(audio_files):
        inputs.append(f'-i "{af["path"]}"')
        delay = int(af.get("start", 0) * 1000)
        audio_delays.append(f'[{i+1}:a]adelay={delay}|{delay}[a{i+1}]')
    
    # 添加背景音乐
    bgm_index = len(audio_files) + 1
    if bgm_path and os.path.exists(bgm_path):
        inputs.append(f'-i "{bgm_path}"')
    
    # 构建滤镜
    filters = []
    
    # 音频混合
    if audio_files:
        mix_inputs = ''.join([f'[a{i+1}]' for i in range(len(audio_files))])
        filters.append(f'{mix_inputs}amix=inputs={len(audio_files)}:duration=longest[avoice]')
        
        if bgm_path and os.path.exists(bgm_path):
            filters.append(f'[{bgm_index}:a]volume=0.3[abgm]')
            filters.append(f'[avoice][abgm]amix=inputs=2:duration=first[aout]')
        else:
            filters.append(f'[avoice]anull[aout]')
    elif bgm_path and os.path.exists(bgm_path):
        filters.append(f'[{bgm_index}:a]volume=0.5[aout]')
    else:
        filters.append(f'[0:a]anull[aout]')
    
    # 音频标准化（EBU R128响度标准化）
    filters.append(f'[aout]loudnorm=I=-16:TP=-1.5:LRA=11[aout_norm]')
    
    # 视频调色
    if v["color_grade"] == "cinematic":
        filters.append(f'[0:v]eq=contrast=1.1:brightness=-0.02:saturation=1.15,curves=preset=cinema[vout]')
    elif v["color_grade"] == "director":
        filters.append(f'[0:v]eq=contrast=1.15:brightness=-0.03:saturation=1.2,curves=preset=cinema,colorbalance=rs=0.05:gs=-0.02:bs=-0.05[vout]')
    else:
        filters.append(f'[0:v]eq=contrast=1.05:saturation=1.1[vout]')
    
    # 字幕渲染
    if subtitle_path and os.path.exists(subtitle_path):
        if subtitle_path.endswith('.ass'):
            filters.append(f'[vout]ass="{subtitle_path}"[vfinal]')
        else:
            filters.append(f'[vout]subtitles="{subtitle_path}":force_style=\'FontName=Noto Serif CJK SC,FontSize=28,Outline=3,Shadow=2\'[vfinal]')
    else:
        filters.append(f'[vout]anull[vfinal]')
    
    # 水印
    if v["watermark"]:
        filters.append(f'[vfinal]drawtext=fontfile={FONT_PATH}:text="火斗云智 AIOS":fontsize=36:fontcolor=white@0.5:x=w-tw-20:y=20[vwater]')
        final_video = "[vwater]"
    else:
        final_video = "[vfinal]"
    
    filter_complex = ';'.join(audio_delays + filters)
    
    # 构建完整命令
    cmd = (
        f'ffmpeg -y {" ".join(inputs)} '
        f'-filter_complex "{filter_complex}" '
        f'-map {final_video} -map "[aout_norm]" '
        f'-c:v libopenh264 -b:v {v["bitrate"]} '
        f'-c:a aac -b:a {v["audio_quality"]} '
        f'-movflags +faststart '
        f'-shortest '
        f'"{output_path}"'
    )
    
    print(f"  [合成] 开始音视频合成...")
    print(f"  [合成] 版本: {v['name']} | 分辨率: {v['resolution']} | 码率: {v['bitrate']}")
    
    ok, out, err = run_cmd(cmd, timeout=600)
    
    if ok and os.path.exists(output_path):
        file_size = os.path.getsize(output_path) / (1024*1024)
        duration = get_video_duration(output_path)
        print(f"  [合成] ✅ 成功！文件大小: {file_size:.1f}MB | 时长: {duration:.1f}秒")
        return output_path
    else:
        print(f"  [合成] ❌ 失败！错误: {err[:200]}")
        return None

# ========== S7: 三版本批量输出 ==========
def generate_all_versions(video_path, audio_files, dialogues, bgm_path=None):
    """
    生成三个版本的输出
    :return: 三个版本的输出文件路径
    """
    results = {}
    
    for version in ["free", "pro", "director"]:
        v = VERSIONS[version]
        print(f"\n{'='*60}")
        print(f"  生成版本: {v['name']}")
        print(f"{'='*60}")
        
        # 生成对应版本的字幕
        subtitle_path = generate_ass(dialogues, style=v["subtitle_style"])
        
        # 音视频合成
        output_path = merge_audio_video(
            video_path, audio_files, bgm_path,
            version=version, subtitle_path=subtitle_path
        )
        
        if output_path:
            results[version] = {
                "path": output_path,
                "name": v["name"],
                "resolution": v["resolution"],
                "size_mb": round(os.path.getsize(output_path) / (1024*1024), 1),
                "duration": get_video_duration(output_path),
                "sha256": sha256_file(output_path)
            }
    
    return results

# ========== 完整流水线 ==========
def run_full_cinematic_pipeline(
    video_path,
    dialogues,
    bgm_path=None,
    version="pro",
    output_name=None
):
    """
    运行完整的电影级生产流水线
    :param video_path: 原始视频路径
    :param dialogues: 对话列表 [{"text": "...", "voice": "narrator", "speaker": "旁白", "start": 0.0}]
    :param bgm_path: 背景音乐路径
    :param version: 输出版本
    :param output_name: 输出文件名
    :return: 结果字典
    """
    start_time = time.time()
    
    print(f"\n{'='*70}")
    print(f"  昆仑洞天 · 电影级短剧生产流水线 V1.0")
    print(f"  确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print(f"{'='*70}\n")
    
    ensure_dirs()
    
    # 检查输入
    if not os.path.exists(video_path):
        return {"status": "error", "message": f"视频文件不存在: {video_path}"}
    
    print(f"【输入】视频: {video_path}")
    print(f"【输入】对话数: {len(dialogues)}")
    print(f"【输入】版本: {VERSIONS[version]['name']}")
    print()
    
    # S4: TTS语音合成
    print(f"【S4】TTS语音合成")
    print(f"{'-'*50}")
    audio_results = asyncio.run(tts_batch_generate(dialogues))
    print(f"  ✅ 生成 {len(audio_results)} 个语音文件")
    
    # 计算语音时间轴
    current_time = 0
    audio_files = []
    subtitle_dialogues = []
    
    for ar in audio_results:
        start = current_time
        end = current_time + ar["duration"] + 0.3  # 加0.3秒间隔
        
        audio_files.append({
            "path": ar["audio_path"],
            "start": start
        })
        
        subtitle_dialogues.append({
            "text": ar["text"],
            "speaker": ar["speaker"],
            "start": start,
            "end": end
        })
        
        current_time = end
    
    print(f"  总语音时长: {current_time:.1f}秒")
    print()
    
    # S5: 字幕生成
    print(f"【S5】字幕生成")
    print(f"{'-'*50}")
    subtitle_style = VERSIONS[version]["subtitle_style"]
    subtitle_path = generate_ass(subtitle_dialogues, style=subtitle_style)
    print(f"  ✅ 字幕文件: {subtitle_path}")
    print(f"  样式: {subtitle_style}")
    print()
    
    # S6: 音视频合成
    print(f"【S6】音视频合成（电影级调色+音频标准化）")
    print(f"{'-'*50}")
    
    if output_name:
        output_path = f"{OUTPUT_DIR}/{output_name}"
    else:
        output_path = None
    
    final_video = merge_audio_video(
        video_path, audio_files, bgm_path,
        output_path=output_path,
        version=version,
        subtitle_path=subtitle_path
    )
    
    if not final_video:
        return {"status": "error", "message": "音视频合成失败"}
    
    print()
    
    # 计算耗时
    elapsed = time.time() - start_time
    
    # 生成结果
    result = {
        "status": "success",
        "pipeline": "cinematic_v1.0",
        "version": version,
        "version_name": VERSIONS[version]["name"],
        "input_video": video_path,
        "output_video": final_video,
        "subtitle_file": subtitle_path,
        "audio_files": [a["path"] for a in audio_files],
        "dialogue_count": len(dialogues),
        "audio_count": len(audio_files),
        "output_size_mb": round(os.path.getsize(final_video) / (1024*1024), 1),
        "output_duration": get_video_duration(final_video),
        "sha256": sha256_file(final_video),
        "elapsed_seconds": round(elapsed, 1),
        "did": "DID-BR-000002",
        "anchor": "Ω₀⊂⊙∞⊂Ω",
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"\n{'='*70}")
    print(f"  ✅ 电影级短剧生产完成！")
    print(f"{'='*70}")
    print(f"  输出文件: {final_video}")
    print(f"  文件大小: {result['output_size_mb']}MB")
    print(f"  视频时长: {result['output_duration']:.1f}秒")
    print(f"  耗时: {elapsed:.1f}秒")
    print(f"  SHA256: {result['sha256'][:16]}...")
    print(f"{'='*70}\n")
    
    return result

# ========== 主函数 ==========
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="昆仑洞天电影级短剧生产流水线")
    parser.add_argument("--video", required=True, help="输入视频路径")
    parser.add_argument("--dialogues", help="对话JSON文件路径")
    parser.add_argument("--bgm", help="背景音乐路径")
    parser.add_argument("--version", default="pro", choices=["free", "pro", "director"], help="输出版本")
    parser.add_argument("--output", help="输出文件名")
    parser.add_argument("--all-versions", action="store_true", help="生成所有三个版本")
    
    args = parser.parse_args()
    
    # 加载对话
    dialogues = []
    if args.dialogues and os.path.exists(args.dialogues):
        with open(args.dialogues, 'r', encoding='utf-8') as f:
            dialogues = json.load(f)
    else:
        # 默认测试对话
        dialogues = [
            {"text": "昆仑之巅，云雾缭绕。", "voice": "narrator", "speaker": "旁白"},
            {"text": "九天玄女降临人间。", "voice": "female_elegant", "speaker": "九天玄女"},
            {"text": "天道轮回，因果报应。", "voice": "narrator", "speaker": "旁白"}
        ]
    
    bgm = args.bgm if args.bgm and os.path.exists(args.bgm) else BGM_PATH
    
    if args.all_versions:
        # 生成所有版本
        # 先生成语音和字幕
        ensure_dirs()
        audio_results = asyncio.run(tts_batch_generate(dialogues))
        
        current_time = 0
        audio_files = []
        subtitle_dialogues = []
        for ar in audio_results:
            start = current_time
            end = current_time + ar["duration"] + 0.3
            audio_files.append({"path": ar["audio_path"], "start": start})
            subtitle_dialogues.append({
                "text": ar["text"], "speaker": ar["speaker"],
                "start": start, "end": end
            })
            current_time = end
        
        results = generate_all_versions(args.video, audio_files, subtitle_dialogues, bgm)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        # 生成单个版本
        result = run_full_cinematic_pipeline(
            args.video, dialogues, bgm, args.version, args.output
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
