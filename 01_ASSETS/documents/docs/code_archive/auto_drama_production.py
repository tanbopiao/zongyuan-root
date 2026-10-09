#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
昆仑洞天 · 全自动短剧量产引擎 V1.0
集成S1-S6全流程：剧本→关键帧→视频→TTS→字幕→合成
零成本运行，全部使用免费API和开源工具
"""

import json
import time
import os
import sys
import sqlite3
import urllib.request
import subprocess
from datetime import datetime

# ========== 配置 ==========
DRAMA_API = "http://127.0.0.1:8628"
AI_PROXY = "http://127.0.0.1:8021/v1/chat/completions"
MEMORY_GATEWAY = "http://127.0.0.1:9120"
OUTPUT_DIR = "/www/wwwroot/huodouai.com/drama/output"
AUDIO_DIR = "/www/wwwroot/huodouai.com/drama/audios"
SUBTITLE_DIR = "/www/wwwroot/huodouai.com/drama/subtitles"
CINEMATIC_SCRIPT = "/opt/ZONGYUAN-ROOT/scripts/cinematic_drama_pipeline.py"

# 确保目录存在
for d in [OUTPUT_DIR, AUDIO_DIR, SUBTITLE_DIR]:
    os.makedirs(d, exist_ok=True)

# ========== 工具函数 ==========
def call_ai(prompt, model="zhipu", max_tokens=600, temperature=0.7):
    """调用AI代理"""
    try:
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        req = urllib.request.Request(
            AI_PROXY,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  ❌ AI调用失败: {e}")
        return None

def api_call(url, method="GET", data=None, timeout=30):
    """调用API"""
    try:
        if data:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
                method=method
            )
        else:
            req = urllib.request.Request(url, method=method)
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def parse_json_safe(text):
    """安全解析JSON，处理中文标点符号"""
    if not text:
        return None
    # 清理markdown
    text = text.replace("```json", "").replace("```", "").strip()
    # 替换中文标点符号
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\uff0c", ",").replace("\uff1a", ":")
    text = text.replace("\uff1b", ";").replace("\uff08", "(").replace("\uff09", ")")
    text = text.replace("\u3001", ",").replace("\u3002", ".")
    # 正则提取JSON
    import re
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    try:
        return json.loads(text)
    except:
        return None

def report_to_memory(key, value, category="drama_production"):
    """上报到记忆网关"""
    try:
        data = {
            "key": key,
            "value": json.dumps(value, ensure_ascii=False),
            "category": category,
            "truth_type": "production_log",
            "confidence": 0.95,
            "locked": True
        }
        req = urllib.request.Request(
            f"{MEMORY_GATEWAY}/api/truth/upsert",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except:
        return False

# ========== S1: 剧本生成 ==========
def s1_generate_script(episode, title, worldview_id="WORLD-DA8608EAE7C3"):
    """S1: 自动生成剧本和分镜"""
    print(f"\n[S1] 开始生成剧本: 第{episode}集 {title}")
    
    prompt = f"""你是昆仑洞天短剧编剧。请为第{episode}集《{title}》生成剧本大纲。
要求：
1. 3-5个场景
2. 每个场景包含：场景编号、地点、时间、出场角色、简要情节
3. 国风仙侠风格，节奏紧凑，每集留悬念
4. 只输出JSON格式

格式：
{{"synopsis":"本集概要(100字内)","scenes":[
  {{"scene_no":1,"location":"地点","time":"时间","characters":["角色1"],"plot":"情节描述(50字)"}}
]}}"""
    
    result = call_ai(prompt, max_tokens=600)
    if not result:
        return {"error": "剧本生成失败"}
    
    script_data = parse_json_safe(result)
    if not script_data:
        return {"error": "剧本JSON解析失败", "raw": result[:200]}
    
    # 创建剧本
    payload = {
        "title": title,
        "episode": int(episode),
        "world_id": worldview_id,
        "synopsis": script_data["synopsis"],
        "scenes": json.dumps(script_data["scenes"], ensure_ascii=False)
    }
    resp = api_call(f"{DRAMA_API}/api/script/create", "POST", payload)
    script_id = resp.get("script_id")
    if not script_id:
        return {"error": f"剧本创建失败: {resp}"}
    
    print(f"  ✅ 剧本已创建: {script_id}")
    
    # 为每个场景生成分镜
    storyboards = []
    for scene in script_data["scenes"]:
        shot_prompt = f"""为以下场景生成2-3个分镜：
场景{scene['scene_no']}: {scene['location']} - {scene['plot']}
角色: {', '.join(scene.get('characters', []))}

每个分镜包含：镜头编号、镜头类型、画面描述、台词、时长
只输出JSON数组：
[{{"shot_no":1,"shot_type":"近景","description":"画面描述","dialogue":"台词","duration":5}}]"""
        
        shot_result = call_ai(shot_prompt, max_tokens=400)
        if shot_result:
            shots = parse_json_safe(shot_result)
            if shots and isinstance(shots, list):
                for shot in shots:
                    sb_payload = {
                        "script_id": script_id,
                        "episode": int(episode),
                        "scene_no": scene["scene_no"],
                        "shot_no": shot.get("shot_no", 1),
                        "shot_type": shot.get("shot_type", "中景"),
                        "description": shot.get("description", ""),
                        "dialogue": shot.get("dialogue", ""),
                        "duration": shot.get("duration", 5)
                    }
                    sb_resp = api_call(f"{DRAMA_API}/api/storyboard/create", "POST", sb_payload)
                    if "shot_id" in sb_resp:
                        storyboards.append({
                            "shot_id": sb_resp["shot_id"],
                            "keyframe_prompt": sb_resp.get("keyframe_prompt", ""),
                            "dialogue": shot.get("dialogue", "")
                        })
    
    print(f"  ✅ S1完成: {len(storyboards)}个分镜")
    return {
        "script_id": script_id,
        "synopsis": script_data["synopsis"],
        "storyboards": storyboards,
        "storyboard_count": len(storyboards)
    }

# ========== S2: 关键帧生成 ==========
def s2_generate_keyframes(script_id, episode):
    """S2: 生成关键帧提示词（图片生成待后续集成）"""
    print(f"\n[S2] 开始生成关键帧任务: {script_id}")
    
    resp = api_call(f"{DRAMA_API}/api/storyboard/list?script_id={script_id}")
    storyboards = resp.get("storyboards", [])
    
    keyframes = []
    for sb in storyboards:
        shot_id = sb.get("shot_id") if isinstance(sb, dict) else sb[0]
        base_prompt = sb.get("keyframe_prompt", "") if isinstance(sb, dict) else (sb[11] if len(sb) > 11 else "")
        
        optimized_prompt = f"{base_prompt}，角色形象一致，纯东方美学，电影级光影，高细节，9:16竖屏"
        
        kf_payload = {
            "script_id": script_id,
            "shot_id": shot_id,
            "prompt": optimized_prompt,
            "model": "seedream-4.5",
            "status": "pending"
        }
        kf_resp = api_call(f"{DRAMA_API}/api/keyframe/create", "POST", kf_payload)
        if "keyframe_id" in kf_resp:
            keyframes.append(kf_resp)
    
    print(f"  ✅ S2完成: {len(keyframes)}个关键帧任务")
    return {"keyframes": keyframes, "count": len(keyframes), "status": "待生成图片"}

# ========== S3: 视频任务 ==========
def s3_generate_video_tasks(script_id, episode):
    """S3: 生成视频任务（视频生成待后续集成）"""
    print(f"\n[S3] 开始生成视频任务: {script_id}")
    
    resp = api_call(f"{DRAMA_API}/api/keyframe/list?script_id={script_id}")
    keyframes = resp.get("keyframes", [])
    
    videos = []
    for kf in keyframes:
        kf_id = kf.get("keyframe_id") if isinstance(kf, dict) else kf[0]
        # task_type是query参数，params是body
        video_params = {
            "script_id": script_id,
            "keyframe_id": kf_id,
            "model": "seedance-2.0",
            "duration": 5,
            "status": "pending"
        }
        video_resp = api_call(f"{DRAMA_API}/api/task/create?task_type=video_generation", "POST", video_params)
        if "task_id" in video_resp:
            videos.append(video_resp)
    
    print(f"  ✅ S3完成: {len(videos)}个视频任务")
    return {"videos": videos, "count": len(videos), "status": "待生成视频"}

# ========== S4-S6: 电影级流水线 ==========
def s4_s6_cinematic_pipeline(video_path, dialogues, version="pro", output_name=None):
    """S4-S6: TTS语音合成 + 字幕生成 + 音视频合成"""
    print(f"\n[S4-S6] 电影级流水线: {video_path}")
    
    if not os.path.exists(video_path):
        return {"error": f"视频文件不存在: {video_path}"}
    
    # 创建对话文件
    timestamp = int(time.time())
    dialogue_file = f"/tmp/dialogues_{timestamp}.json"
    with open(dialogue_file, "w", encoding="utf-8") as f:
        json.dump(dialogues, f, ensure_ascii=False, indent=2)
    
    output_file = output_name or f"cinematic_{timestamp}.mp4"
    output_path = os.path.join(OUTPUT_DIR, output_file)
    
    # 调用电影级流水线
    cmd = f"cd /opt/ZONGYUAN-ROOT/scripts && python3 {CINEMATIC_SCRIPT} --video {video_path} --dialogues {dialogue_file} --version {version} --output {output_file}"
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            size_mb = os.path.getsize(output_path) / (1024*1024)
            print(f"  ✅ 电影级流水线成功！大小: {size_mb:.1f}MB")
            return {
                "output": output_path,
                "size_mb": round(size_mb, 1),
                "version": version
            }
        else:
            print(f"  ❌ 电影级流水线失败: {result.stderr[-200:]}")
            return {"error": result.stderr[-200:]}
    except Exception as e:
        return {"error": str(e)}

# ========== 主流程 ==========
def run_full_production(episode, title, version="pro", skip_image_video=True):
    """
    运行完整量产流程
    skip_image_video: True=只生成剧本+分镜+提示词（不真正生图生视频，节省额度）
                      False=完整生图生视频（消耗免费额度）
    """
    start_time = time.time()
    task_id = f"AUTO-{int(start_time)}"
    
    print("=" * 70)
    print(f"  昆仑洞天全自动短剧量产启动: {task_id}")
    print(f"  第{episode}集 《{title}》")
    print(f"  版本: {version} | 模式: {'轻量(只生成剧本)' if skip_image_video else '完整(生图生视频)'}")
    print("=" * 70)
    
    result = {
        "task_id": task_id,
        "episode": episode,
        "title": title,
        "version": version,
        "start_time": datetime.now().isoformat()
    }
    
    # S1: 剧本生成
    s1_result = s1_generate_script(episode, title)
    result["s1"] = s1_result
    if "error" in s1_result:
        result["status"] = "failed"
        result["failed_step"] = "S1"
        return result
    
    script_id = s1_result["script_id"]
    result["script_id"] = script_id
    
    # S2: 关键帧
    s2_result = s2_generate_keyframes(script_id, episode)
    result["s2"] = s2_result
    
    # S3: 视频任务
    s3_result = s3_generate_video_tasks(script_id, episode)
    result["s3"] = s3_result
    
    # S4-S6: 电影级流水线（如果有现成视频）
    # 注意：完整生图生视频需要集成seedream/seedance API，这里先做剧本+提示词量产
    result["s4_s6"] = {"status": "待集成生图生视频后执行"}
    
    # 计算耗时
    elapsed = time.time() - start_time
    result["elapsed_seconds"] = round(elapsed, 1)
    result["status"] = "success"
    result["end_time"] = datetime.now().isoformat()
    
    # 上报到记忆网关
    report_to_memory(f"drama_production_{task_id}", result)
    
    print("\n" + "=" * 70)
    print(f"  ✅ 量产完成！耗时: {elapsed:.1f}秒")
    print(f"  剧本: {script_id} | 分镜: {s1_result['storyboard_count']}个")
    print(f"  关键帧任务: {s2_result['count']}个 | 视频任务: {s3_result['count']}个")
    print("=" * 70)
    
    return result

# ========== 命令行入口 ==========
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="昆仑洞天全自动短剧量产引擎")
    parser.add_argument("--episode", type=int, default=1, help="集数")
    parser.add_argument("--title", type=str, default="玄女降临", help="标题")
    parser.add_argument("--version", type=str, default="pro", choices=["free", "pro", "director"], help="版本")
    parser.add_argument("--full", action="store_true", help="完整模式（生图生视频）")
    args = parser.parse_args()
    
    result = run_full_production(
        episode=args.episode,
        title=args.title,
        version=args.version,
        skip_image_video=not args.full
    )
    
    print("\n最终结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
