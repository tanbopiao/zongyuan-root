#!/usr/bin/env python3
"""
昆仑洞天短剧半自动增强流水线 v1.0
在现有real_pipeline.py基础上增加：
- S1剧本生成：全自动（免费文本生成）
- S2关键帧生成：提示词全自动，图片生成需人工确认（零成本策略）
- S3视频生成：提示词全自动，视频生成需人工确认（零成本策略）
- 统一配置管理（API key从secrets.json读取）
- 状态追踪 + 9120上报
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import json
import time
import sys
import os
import requests

# ========== 配置 ==========
SECRETS_FILE = "/opt/ZONGYUAN-ROOT/config/secrets.json"
WORKS_FILE = "/opt/ZONGYUAN-ROOT/drama-admin-api/works.json"
TASKS_FILE = "/opt/ZONGYUAN-ROOT/drama-admin-api/tasks.json"
STATE_FILE = "/opt/ZONGYUAN-ROOT/data/drama_semiauto_state.json"
GATEWAY_URL = "http://127.0.0.1:9120/api/truth/upsert"

# L0角色约束
L0_PROMPT = "single young Chinese goddess, one person only, one single head, pure black long hair to waist, nine-head body, cold white/gold/black/red colors, strong rim light, UE5 ray tracing, cinematic, 9:16 vertical, no western elements, no masculine features"

def load_config():
    """从secrets.json加载API配置"""
    try:
        with open(SECRETS_FILE) as f:
            s = json.load(f)
        return s.get("api_keys", {})
    except:
        return {}

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {"tasks": {}}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def report_to_gateway(truth_type, content):
    """上报记忆网关"""
    try:
        requests.post(GATEWAY_URL, json={
            "key": f"DRAMA.{truth_type}.{int(time.time())}",
            "value": content,
            "source": "drama_semiauto_pipeline",
            "did": "DID-BR-000002",
            "truth_type": "drama_production",
            "confidence": 0.9
        }, timeout=5)
    except Exception as e:
        print(f"  [网关上报失败] {e}")

# ========== S1: 剧本生成（免费全自动） ==========
def step1_generate_script(topic, title):
    """S1: 智谱GLM生成剧本（免费文本生成）"""
    print("\n" + "="*50)
    print(f"  [S1] 剧本自动生成")
    print(f"  主题: {topic}")
    print(f"  标题: {title}")
    print("="*50)

    config = load_config()
    api_key = config.get("zhipu", {}).get("api_key", "") or config.get("zhipu_api_key", "")

    if not api_key:
        # 尝试从real_pipeline.py的默认key
        api_key = "d63c880c0e1b424d8ad242f686e83451.vhHr5d5OQUY5UHNp"
        print("  [提示] 使用默认智谱API key（建议配置到secrets.json）")

    try:
        resp = requests.post(
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "glm-4-flash",
                "messages": [
                    {"role": "system", "content": '只输出纯JSON：{"scenes":[{"name":"","desc":""},{"name":"","desc":""},{"name":"","desc":""},{"name":"","desc":""}],"narration":""}'},
                    {"role": "user", "content": f"主题：{topic}。生成4个场景名和描述，国风仙侠风格。"}
                ],
                "temperature": 0.7
            }, timeout=30
        )
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        start = content.find("{")
        end = content.rfind("}") + 1
        script = json.loads(content[start:end])

        if "scenes" not in script:
            raise Exception("格式错误")

        print(f"  ✅ 剧本生成成功：{len(script['scenes'])}个场景")
        for i, scene in enumerate(script["scenes"]):
            print(f"     场景{i+1}: {scene['name']} - {scene['desc'][:50]}")

        report_to_gateway("S1_SCRIPT", f"{title}剧本生成成功，{len(script['scenes'])}个场景")
        return script

    except Exception as e:
        print(f"  ❌ 剧本生成失败: {e}")
        # 降级：使用模板
        script = {
            "scenes": [
                {"name": "觉醒", "desc": "goddess awakening in ancient temple"},
                {"name": "聚气", "desc": "goddess gathering cosmic energy"},
                {"name": "显威", "desc": "goddess showing divine power"},
                {"name": "加冕", "desc": "goddess crowned as eternal ruler"}
            ],
            "narration": "天道无常，唯我永恒"
        }
        print(f"  ⚠️ 使用降级模板")
        return script

# ========== S2: 关键帧提示词生成（免费全自动） ==========
def step2_generate_keyframe_prompts(script):
    """S2: 为每个场景生成关键帧提示词（免费，不实际生成图片）"""
    print("\n" + "="*50)
    print(f"  [S2] 关键帧提示词自动生成")
    print("="*50)

    keyframes = []
    for i, scene in enumerate(script["scenes"]):
        prompt = f"{L0_PROMPT}, scene: {scene['desc']}, epic fantasy, detailed face, dynamic pose"
        keyframe = {
            "id": f"kf{i+1:02d}",
            "name": scene["name"],
            "prompt": prompt,
            "negative_prompt": "low quality, blurry, deformed, white hair, modern clothing, western style, multiple people",
            "model": "seedream-4.5",
            "width": 720,
            "height": 1280,
            "status": "pending_confirmation",
            "estimated_cost": "需人工确认后生成（零成本策略）"
        }
        keyframes.append(keyframe)
        print(f"  ✅ 关键帧{i+1}提示词: {scene['name']}")
        print(f"     {prompt[:80]}...")

    print(f"\n  📋 共生成{len(keyframes)}个关键帧提示词")
    print(f"  ⚠️ 图片生成需人工确认（调用 /confirm/keyframe 触发）")
    report_to_gateway("S2_KEYFRAME_PROMPTS", f"生成{len(keyframes)}个关键帧提示词，待人工确认")
    return keyframes

# ========== S3: 视频提示词生成（免费全自动） ==========
def step3_generate_video_prompts(keyframes):
    """S3: 为每个关键帧生成视频提示词（免费，不实际生成视频）"""
    print("\n" + "="*50)
    print(f"  [S3] 视频提示词自动生成")
    print("="*50)

    video_tasks = []
    for kf in keyframes:
        video_prompt = f"{kf['prompt']}, slow camera push-in, subtle movement, flowing robes, swirling mist, 15 seconds"
        video_task = {
            "keyframe_id": kf["id"],
            "video_prompt": video_prompt,
            "model": "seedance_2.0_fast",
            "duration": 15,
            "status": "pending_confirmation",
            "estimated_cost": "需人工确认后生成（零成本策略）"
        }
        video_tasks.append(video_task)
        print(f"  ✅ 视频{kf['id']}提示词已生成")

    print(f"\n  📋 共生成{len(video_tasks)}个视频任务提示词")
    print(f"  ⚠️ 视频生成需人工确认（调用 /confirm/video 触发）")
    report_to_gateway("S3_VIDEO_PROMPTS", f"生成{len(video_tasks)}个视频提示词，待人工确认")
    return video_tasks

# ========== 主流程：S1-S3半自动 ==========
def run_semiauto(topic, title, auto_confirm_s2=False, auto_confirm_s3=False):
    """运行半自动流水线：S1全自动，S2/S3提示词生成，生成需确认"""
    task_id = f"SEMI-{int(time.time())}"
    print(f"\n{'#'*60}")
    print(f"# 昆仑洞天半自动增强流水线")
    print(f"# 任务ID: {task_id}")
    print(f"# 主题: {topic}")
    print(f"# 标题: {title}")
    print(f"{'#'*60}")

    # S1: 剧本生成（免费全自动）
    script = step1_generate_script(topic, title)

    # S2: 关键帧提示词（免费全自动）
    keyframes = step2_generate_keyframe_prompts(script)

    # S3: 视频提示词（免费全自动）
    video_tasks = step3_generate_video_prompts(keyframes)

    # 保存状态
    state = load_state()
    state["tasks"][task_id] = {
        "task_id": task_id,
        "topic": topic,
        "title": title,
        "status": "s3_prompts_done",
        "current_step": "awaiting_confirmation",
        "script": script,
        "keyframes": keyframes,
        "video_tasks": video_tasks,
        "s2_confirmed": auto_confirm_s2,
        "s3_confirmed": auto_confirm_s3,
        "created_at": time.time(),
        "next_actions": [
            "确认关键帧提示词后，调用 /confirm/keyframe/{task_id} 触发生图",
            "确认视频提示词后，调用 /confirm/video/{task_id} 触发视频生成",
            "生成完成后自动触发S4-S8（转码/COS/归档/对账）"
        ]
    }
    save_state(state)

    result = {
        "task_id": task_id,
        "status": "s3_prompts_done",
        "title": title,
        "s1": {"scenes": len(script["scenes"]), "status": "completed"},
        "s2": {"keyframes": len(keyframes), "status": "prompts_done", "action_required": "人工确认后触发生图"},
        "s3": {"videos": len(video_tasks), "status": "prompts_done", "action_required": "人工确认后触发视频"},
        "zero_cost_note": "S1-S3提示词生成全部免费；图片/视频生成需人工确认，遵守零成本策略",
        "next_actions": state["tasks"][task_id]["next_actions"]
    }

    print(f"\n{'='*50}")
    print(f"  半自动流水线S1-S3完成！")
    print(f"  任务ID: {task_id}")
    print(f"  剧本: {len(script['scenes'])}场景")
    print(f"  关键帧提示词: {len(keyframes)}个（待确认）")
    print(f"  视频提示词: {len(video_tasks)}个（待确认）")
    print(f"{'='*50}\n")

    return result

# ========== CLI入口 ==========
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 drama_semiauto_pipeline.py <主题> <标题>")
        print("示例: python3 drama_semiauto_pipeline.py '太阴月神觉醒' '第26集·月华降临'")
        sys.exit(1)

    topic = sys.argv[1]
    title = sys.argv[2]
    result = run_semiauto(topic, title)
    print(json.dumps(result, ensure_ascii=False, indent=2))
