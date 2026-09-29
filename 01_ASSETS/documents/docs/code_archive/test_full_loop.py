#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全流程闭环测试脚本"""

import json
import time
import urllib.request

def api_call(url, method="GET", data=None, timeout=60):
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

print("=" * 70)
print("  全流程闭环测试")
print("=" * 70)
print()

# 1. 测试AI调用
print("【1/6】测试AI调用（智谱GLM-4-Flash）")
result = api_call("http://127.0.0.1:8021/v1/chat/completions", "POST", {
    "model": "zhipu",
    "messages": [{"role": "user", "content": "请用一句话介绍昆仑洞天"}],
    "max_tokens": 100
})
if "choices" in result:
    content = result["choices"][0]["message"]["content"]
    print("  ✅ AI调用成功！")
    print("  回复:", content[:80])
else:
    print("  ❌ AI调用失败:", json.dumps(result, ensure_ascii=False)[:200])
print()

# 2. 测试短剧API状态
print("【2/6】测试短剧API状态")
result = api_call("http://127.0.0.1:8628/api/status")
print("  状态:", result.get("status", "unknown"))
stats = result.get("stats", {})
print("  角色:", stats.get("characters", 0), "| 世界观:", stats.get("worldviews", 0))
print("  剧本:", stats.get("scripts", 0), "| 分镜:", stats.get("storyboards", 0))
print("  关键帧:", stats.get("keyframes", 0), "| 任务:", stats.get("tasks", 0))
print()

# 3. 创建测试剧本
print("【3/6】创建测试剧本")
result = api_call("http://127.0.0.1:8628/api/script/create", "POST", {
    "title": "全流程测试-玄女降临",
    "episode": 99,
    "worldview_id": "WORLD-DA8608EAE7C3",
    "content": "昆仑之巅，九天玄女降临人间，拯救苍生。"
})
print("  结果:", json.dumps(result, ensure_ascii=False)[:200])
print()

# 4. 测试自动编排器
print("【4/6】测试自动编排器（S1-S3）")
result = api_call("http://127.0.0.1:8102/api/orchestrator/run", "POST", {
    "episode": 99,
    "title": "全流程测试-玄女降临"
}, timeout=120)
print("  编排器结果:")
if "status" in result:
    print("    状态:", result.get("status"))
    print("    任务ID:", result.get("task_id", "N/A"))
    print("    当前步骤:", result.get("current_step", "N/A"))
    s1 = result.get("s1", {})
    s2 = result.get("s2", {})
    s3 = result.get("s3", {})
    print("    S1剧本:", s1.get("storyboards", "N/A"), "个分镜")
    print("    S2关键帧:", s2.get("keyframes", "N/A"), "个提示词")
    print("    S3视频:", s3.get("videos", "N/A"), "个任务")
else:
    print("    ", json.dumps(result, ensure_ascii=False)[:300])
print()

# 5. 测试电影级流水线（TTS+字幕+合成）
print("【5/6】测试电影级流水线（TTS+字幕+合成）")
import subprocess
import os

test_video = "/www/wwwroot/huodouai.com/drama/videos/EP001_Taiyin_Awakening.mp4"
test_dialogues = "/tmp/test_dialogues_full.json"

# 创建测试对话
dialogues = [
    {"text": "昆仑之巅，云雾缭绕，九天玄女降临人间。", "voice": "narrator", "speaker": "旁白"},
    {"text": "苍生有难，吾当救之。", "voice": "female_elegant", "speaker": "九天玄女"}
]
with open(test_dialogues, "w", encoding="utf-8") as f:
    json.dump(dialogues, f, ensure_ascii=False, indent=2)

if os.path.exists(test_video):
    cmd = f"cd /opt/ZONGYUAN-ROOT/scripts && python3 cinematic_drama_pipeline.py --video {test_video} --dialogues {test_dialogues} --version pro --output full_loop_test.mp4"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
    output_file = "/www/wwwroot/huodouai.com/drama/output/full_loop_test.mp4"
    if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
        size_mb = os.path.getsize(output_file) / (1024*1024)
        print(f"  ✅ 电影级流水线成功！")
        print(f"  输出: {output_file}")
        print(f"  大小: {size_mb:.1f}MB")
    else:
        print(f"  ❌ 电影级流水线失败")
        print(f"  错误: {result.stderr[-200:]}")
else:
    print(f"  ⚠️ 测试视频不存在: {test_video}")
print()

# 6. 检查真值库
print("【6/6】检查真值库状态")
result = api_call("http://127.0.0.1:9120/api/truths?limit=1")
print("  真值总数:", result.get("count", "unknown"))
print()

print("=" * 70)
print("  全流程闭环测试完成")
print("=" * 70)
