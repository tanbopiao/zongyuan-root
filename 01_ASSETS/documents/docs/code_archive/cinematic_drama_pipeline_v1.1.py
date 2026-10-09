#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
昆仑洞天 · 电影级短剧生产流水线 V1.1
功能：TTS语音合成 + 字幕生成 + 音视频合成 + 电影级调色 + 三版本输出
零成本运行：edge-tts(免费) + ffmpeg(开源) + Noto CJK字体(开源)
确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import os
import sys
import json
import time
import asyncio
import subprocess
import hashlib
import shutil
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

# TTS语音配置
TTS_VOICES = {
    "narrator": "zh-CN-YunxiNeural",
    "female_elegant": "zh-CN-XiaoxiaoNeural",
    "female_soft": "zh-CN-XiaoyiNeural",
    "male_powerful": "zh-CN-YunyangNeural",
    "male_youth": "zh-CN-YunjianNeural"
}

# ========== 工具函数 ==========
def ensure_dirs():
    for d in [VIDEO_DIR, AUDIO_DIR, SUBTITLE_DIR, OUTPUT_DIR]:
        os.makedirs(d, exist_ok=True)

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def run_cmd(cmd, timeout=300):
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
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
    ok, out, err = run_cmd(cmd)
    if ok and out.strip():
        return float(out.strip())
    return 0

# ========== S4: TTS语音合成 ==========
async def tts_generate(text, voice="narrator", output_path=None, rate="+0%", max_retries=3):
    import edge_tts
    
    if output_path is None:
        timestamp = int(time.time())
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        output_path = f"{AUDIO_DIR}/tts_{voice}_{timestamp}_{text_hash}.mp3"
    
    voice_name = TTS_VOICES.get(voice, TTS_VOICES["narrator"])
    
    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(text, voice_name, rate=rate)
            await communicate.save(output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                return output_path
        except Exception as e:
            print(f"    [TTS] 第{attempt+1}次尝试失败: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
    
    # 兜底：生成静音音频
    print(f"    [TTS] 所有重试失败，生成静音兜底音频")
    try:
        duration = max(2, len(text) * 0.3)
        cmd = f'ffmpeg -y -f lavfi -i anullsrc=r=24000:cl=mono -t {duration} -q:a 9 "{output_path}"'
        run_cmd(cmd, timeout=30)
    except:
        pass
    
    return output_path

async def tts_batch_generate(dialogues):
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
    if output_path is None:
        timestamp = int(time.time())
        output_path = f"{SUBTITLE_DIR}/subtitle_{timestamp}_{style}.ass"
    
    styles = {
        "basic": {"fontname": "Noto Sans CJK SC", "fontsize": "24", "primaryColour": "&H00FFFFFF", "outlineColour": "&H00000000", "backColour": "&H80000000", "outline": "2", "shadow": "1"},
        "professional": {"fontname": "Noto Serif CJK SC", "fontsize": "28", "primaryColour": "&H00FFFFFF", "outlineColour": "&H00000000", "backColour": "&H00000000", "outline": "3", "shadow": "2"},
        "cinematic": {"fontname": "Noto Serif CJK SC", "fontsize": "36", "primaryColour": "&H00F0E6D2", "outlineColour": "&H00000000", "backColour": "&H00000000", "outline": "4", "shadow": "3"}
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
        f.write(f"Style: Default,{s['fontname']},{s['fontsize']},{s['primaryColour']},&H000000FF,{s['outlineColour']},{s['backColour']},-1,0,0,0,100,100,0,0,1,{s['outline']},{s['shadow']},2,10,10,30,1\n\n")
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

# ========== S6: 音视频合成（简化分步版） ==========
def merge_audio_video(video_path, audio_files, bgm_path=None, output_path=None, 
                       version="pro", subtitle_path=None):
    v = VERSIONS.get(version, VERSIONS["pro"])
    
    if output_path is None:
        timestamp = int(time.time())
        output_path = f"{OUTPUT_DIR}/drama_{version}_{timestamp}.mp4"
    
    print(f"  [合成] 开始音视频合成...")
    print(f"  [合成] 版本: {v['name']} | 分辨率: {v['resolution']} | 码率: {v['bitrate']}")
    
    work_dir = f"/tmp/cinematic_work_{int(time.time())}"
    os.makedirs(work_dir, exist_ok=True)
    
    try:
        # 步骤1: 混合所有语音
        mixed_audio = f"{work_dir}/mixed_voice.mp3"
        if len(audio_files) == 1:
            shutil.copy(audio_files[0]["path"], mixed_audio)
        elif len(audio_files) > 1:
            inputs = []
            filters = []
            for i, af in enumerate(audio_files):
                inputs.append(f'-i "{af["path"]}"')
                delay = int(af.get("start", 0) * 1000)
                filters.append(f'[{i}:a]adelay={delay}|{delay}[a{i}]')
            mix_inputs = ''.join([f'[a{i}]' for i in range(len(audio_files))])
            filters.append(f'{mix_inputs}amix=inputs={len(audio_files)}:duration=longest[avoice]')
            filter_str = ';'.join(filters)
            
            cmd = f'ffmpeg -y {" ".join(inputs)} -filter_complex "{filter_str}" -map "[avoice]" -c:a libmp3lame -b:a 192k "{mixed_audio}"'
            ok, out, err = run_cmd(cmd, timeout=120)
            if not ok:
                print(f"  [合成] ⚠️ 多音频混合失败，使用第一个音频: {err[:100]}")
                shutil.copy(audio_files[0]["path"], mixed_audio)
        
        # 步骤2: 添加背景音乐
        final_audio = f"{work_dir}/final_audio.mp3"
        if bgm_path and os.path.exists(bgm_path):
            cmd = f'ffmpeg -y -i "{mixed_audio}" -i "{bgm_path}" -filter_complex "[0:a]volume=1.0[a1];[1:a]volume=0.3[a2];[a1][a2]amix=inputs=2:duration=shortest[aout]" -map "[aout]" -c:a libmp3lame -b:a 192k "{final_audio}"'
            ok, out, err = run_cmd(cmd, timeout=120)
            if not ok:
                print(f"  [合成] ⚠️ BGM混合失败，使用纯语音: {err[:100]}")
                shutil.copy(mixed_audio, final_audio)
        else:
            shutil.copy(mixed_audio, final_audio)
        
        # 步骤3: 音频标准化
        normalized_audio = f"{work_dir}/normalized_audio.mp3"
        cmd = f'ffmpeg -y -i "{final_audio}" -af "loudnorm=I=-16:TP=-1.5:LRA=11" -c:a libmp3lame -b:a {v["audio_quality"]} "{normalized_audio}"'
        ok, out, err = run_cmd(cmd, timeout=120)
        if ok:
            final_audio = normalized_audio
        else:
            print(f"  [合成] ⚠️ 音频标准化失败，跳过: {err[:100]}")
        
        # 步骤4: 视频调色+字幕+合成
        vf_filters = []
        
        if v["color_grade"] == "cinematic":
            vf_filters.append("eq=contrast=1.1:brightness=-0.02:saturation=1.15")
        elif v["color_grade"] == "director":
            vf_filters.append("eq=contrast=1.15:brightness=-0.03:saturation=1.2")
        else:
            vf_filters.append("eq=contrast=1.05:saturation=1.1")
        
        if subtitle_path and os.path.exists(subtitle_path):
            if subtitle_path.endswith(".ass"):
                vf_filters.append(f'ass="{subtitle_path}"')
            else:
                vf_filters.append(f'subtitles="{subtitle_path}"')
        
        if v["watermark"]:
            vf_filters.append(f'drawtext=fontfile={FONT_PATH}:text="火斗云智 AIOS":fontsize=36:fontcolor=white@0.5:x=w-tw-20:y=20')
        
        vf_str = ",".join(vf_filters)
        
        cmd = (
            f'ffmpeg -y -i "{video_path}" -i "{final_audio}" '
            f'-vf "{vf_str}" '
            f'-c:v libopenh264 -b:v {v["bitrate"]} '
            f'-c:a aac -b:a {v["audio_quality"]} '
            f'-movflags +faststart -shortest "{output_path}"'
        )
        
        ok, out, err = run_cmd(cmd, timeout=600)
        
        if ok and os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024*1024)
            duration = get_video_duration(output_path)
            print(f"  [合成] ✅ 成功！文件大小: {file_size:.1f}MB | 时长: {duration:.1f}秒")
            return output_path
        else:
            print(f"  [合成] ❌ 失败！错误: {err[:200]}")
            return None
            
    finally:
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)

# ========== 完整流水线 ==========
def run_full_cinematic_pipeline(video_path, dialogues, bgm_path=None, version="pro", output_name=None):
    start_time = time.time()
    
    print(f"\n{'='*70}")
    print(f"  昆仑洞天 · 电影级短剧生产流水线 V1.1")
    print(f"  确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print(f"{'='*70}\n")
    
    ensure_dirs()
    
    if not os.path.exists(video_path):
        return {"status": "error", "message": f"视频文件不存在: {video_path}"}
    
    print(f"【输入】视频: {video_path}")
    print(f"【输入】对话数: {len(dialogues)}")
    print(f"【输入】版本: {VERSIONS[version]['name']}")
    print()
    
    # S4: TTS
    print(f"【S4】TTS语音合成")
    print(f"{'-'*50}")
    audio_results = asyncio.run(tts_batch_generate(dialogues))
    print(f"  ✅ 生成 {len(audio_results)} 个语音文件")
    
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
    
    print(f"  总语音时长: {current_time:.1f}秒")
    print()
    
    # S5: 字幕
    print(f"【S5】字幕生成")
    print(f"{'-'*50}")
    subtitle_style = VERSIONS[version]["subtitle_style"]
    subtitle_path = generate_ass(subtitle_dialogues, style=subtitle_style)
    print(f"  ✅ 字幕文件: {subtitle_path}")
    print(f"  样式: {subtitle_style}")
    print()
    
    # S6: 合成
    print(f"【S6】音视频合成（电影级调色+音频标准化）")
    print(f"{'-'*50}")
    
    if output_name:
        output_path = f"{OUTPUT_DIR}/{output_name}"
    else:
        output_path = None
    
    final_video = merge_audio_video(
        video_path, audio_files, bgm_path,
        output_path=output_path, version=version,
        subtitle_path=subtitle_path
    )
    
    if not final_video:
        return {"status": "error", "message": "音视频合成失败"}
    
    elapsed = time.time() - start_time
    
    result = {
        "status": "success",
        "pipeline": "cinematic_v1.1",
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
    parser.add_argument("--version", default="pro", choices=["free", "pro", "director"])
    parser.add_argument("--output", help="输出文件名")
    
    args = parser.parse_args()
    
    dialogues = []
    if args.dialogues and os.path.exists(args.dialogues):
        with open(args.dialogues, 'r', encoding='utf-8') as f:
            dialogues = json.load(f)
    else:
        dialogues = [
            {"text": "昆仑之巅，云雾缭绕。", "voice": "narrator", "speaker": "旁白"},
            {"text": "九天玄女降临人间。", "voice": "female_elegant", "speaker": "九天玄女"}
        ]
    
    bgm = args.bgm if args.bgm and os.path.exists(args.bgm) else BGM_PATH
    
    result = run_full_cinematic_pipeline(
        args.video, dialogues, bgm, args.version, args.output
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
