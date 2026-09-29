#!/usr/bin/env python3
"""
昆仑洞天短剧自动化编排器 v1.0
S1-S3半自动化：剧本/分镜/提示词全自动生成，图片/视频生成人工确认
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

S1: 剧本+分镜全自动（AI代理生成文本，零成本）
S2: 关键帧提示词全自动生成，图片生成人工确认触发
S3: 视频提示词全自动生成，视频生成人工确认触发
S4-S8: 已有自动化，完成后自动衔接
"""

import json
import time
import uuid
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

# ========== 配置 ==========
DRAMA_API = "http://127.0.0.1:8100"
AI_PROXY = "http://127.0.0.1:8021/v1/chat/completions"
PIPELINE_API = "http://127.0.0.1:8626"
PORT = 8101
DB_PATH = "/opt/ZONGYUAN-ROOT/data/drama_orchestrator.db"

# 角色母版（从现有作品提取的核心角色）
DEFAULT_CHARACTERS = {
    "九天玄女": "纯黑长发，单头单簪，纯东方神女，无白发，国风仙侠",
    "烛龙": "上古神兽，人面蛇身，赤色，睁眼为昼闭眼为夜",
    "女娲": "人首蛇身，五色石，造物女神，温婉庄严"
}

# 国风风格模板
STYLE_TEMPLATE = "国风仙侠，电影级画质，9:16竖屏，{character_desc}，{scene_desc}，{shot_type}，{lighting}"

# ========== 数据库 ==========
import sqlite3
import os

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS auto_tasks (
        task_id TEXT PRIMARY KEY,
        episode TEXT,
        title TEXT,
        status TEXT,
        current_step TEXT,
        script_id TEXT,
        storyboard_count INTEGER,
        keyframe_count INTEGER,
        video_count INTEGER,
        created_at REAL,
        updated_at REAL,
        metadata TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS generated_scripts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT,
        episode TEXT,
        title TEXT,
        synopsis TEXT,
        scenes TEXT,
        storyboard_json TEXT,
        created_at REAL
    )""")
    conn.commit()
    conn.close()

init_db()

# ========== AI调用 ==========
def call_ai(prompt, max_tokens=800, temperature=0.7):
    """调用AI代理生成文本"""
    try:
        req = urllib.request.Request(
            AI_PROXY,
            data=json.dumps({
                "model": "doubao-lite",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature
            }).encode(),
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[AI调用失败] {e}")
        return None

# ========== S1: 剧本+分镜生成 ==========
def generate_script(episode, title, world_id="WORLD-KUNLUN-001"):
    """S1: 自动生成剧本和分镜"""
    print(f"[S1] 开始生成剧本: 第{episode}集 {title}")

    # 1. 生成剧本大纲
    script_prompt = f"""你是昆仑洞天短剧编剧。请为第{episode}集《{title}》生成剧本大纲。
要求：
1. 3-5个场景
2. 每个场景包含：场景编号、地点、时间、出场角色、简要情节
3. 国风仙侠风格，节奏紧凑，每集留悬念
4. 只输出JSON格式，不要其他文字

格式：
{{"synopsis":"本集概要(100字内)","scenes":[
  {{"scene_no":1,"location":"地点","time":"时间","characters":["角色1"],"plot":"情节描述(50字)"}},
  ...
]}}"""

    script_result = call_ai(script_prompt, max_tokens=600)
    if not script_result:
        return {"error": "剧本生成失败"}

    # 解析JSON
    try:
        # 清理可能的markdown代码块
        script_result = script_result.replace("```json", "").replace("```", "").strip()
        script_data = json.loads(script_result)
    except:
        return {"error": "剧本JSON解析失败", "raw": script_result[:200]}

    # 2. 调用drama-api创建剧本
    try:
        payload = {
            "title": title,
            "episode": int(episode),
            "world_id": world_id,
            "synopsis": script_data["synopsis"],
            "scenes": json.dumps(script_data["scenes"], ensure_ascii=False)
        }
        req = urllib.request.Request(
            f"{DRAMA_API}/api/script/create",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        script_resp = json.loads(resp.read().decode())
        script_id = script_resp["script_id"]
        print(f"[S1] 剧本已创建: {script_id}")
    except Exception as e:
        return {"error": f"剧本创建失败: {e}"}

    # 3. 为每个场景生成分镜
    storyboards = []
    for scene in script_data["scenes"]:
        # 每个场景生成2-3个镜头
        shot_prompt = f"""为以下场景生成2-3个分镜：
场景{scene['scene_no']}: {scene['location']} - {scene['plot']}
角色: {', '.join(scene.get('characters', []))}

每个分镜包含：镜头编号、镜头类型(近景/中景/远景/特写)、画面描述、台词(如有)、时长(秒)
只输出JSON数组：
[{{"shot_no":1,"shot_type":"近景","description":"画面描述","dialogue":"台词","duration":5}}, ...]"""

        shot_result = call_ai(shot_prompt, max_tokens=400)
        if shot_result:
            try:
                shot_result = shot_result.replace("```json", "").replace("```", "").strip()
                shots = json.loads(shot_result)
                for shot in shots:
                    # 调用drama-api创建分镜（自动生成关键帧提示词）
                    sb_payload = {
                        "script_id": script_id,
                        "episode": int(episode),
                        "scene_no": scene["scene_no"],
                        "shot_no": shot["shot_no"],
                        "shot_type": shot["shot_type"],
                        "description": shot["description"],
                        "dialogue": shot.get("dialogue", ""),
                        "duration": shot.get("duration", 5)
                    }
                    req = urllib.request.Request(
                        f"{DRAMA_API}/api/storyboard/create",
                        data=json.dumps(sb_payload).encode(),
                        headers={"Content-Type": "application/json"}
                    )
                    resp = urllib.request.urlopen(req, timeout=10)
                    sb_resp = json.loads(resp.read().decode())
                    storyboards.append({
                        "shot_id": sb_resp["shot_id"],
                        "keyframe_prompt": sb_resp["keyframe_prompt"],
                        "scene_no": scene["scene_no"],
                        "shot_no": shot["shot_no"]
                    })
            except Exception as e:
                print(f"[S1] 分镜生成失败: {e}")

    print(f"[S1] 完成: {len(storyboards)}个分镜")
    return {
        "script_id": script_id,
        "synopsis": script_data["synopsis"],
        "scenes": script_data["scenes"],
        "storyboards": storyboards,
        "storyboard_count": len(storyboards)
    }

# ========== S2: 关键帧提示词优化+生成任务 ==========
def generate_keyframes(script_id, episode):
    """S2: 为所有分镜生成关键帧任务（提示词优化，图片生成待人工确认）"""
    print(f"[S2] 开始生成关键帧任务: {script_id}")

    # 获取所有分镜
    try:
        req = urllib.request.Request(f"{DRAMA_API}/api/storyboard/list?script_id={script_id}")
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())
        storyboards = data.get("storyboards", [])
    except Exception as e:
        return {"error": f"获取分镜失败: {e}"}

    keyframes = []
    for sb in storyboards:
        shot_id = sb[0] if isinstance(sb, (list, tuple)) else sb.get("shot_id")
        base_prompt = sb[11] if isinstance(sb, (list, tuple)) else sb.get("keyframe_prompt", "")

        # 优化提示词（添加角色一致性约束）
        optimized_prompt = f"{base_prompt}，角色形象一致，纯东方美学，电影级光影，高细节"

        # 创建关键帧任务
        try:
            kf_payload = {
                "shot_id": shot_id,
                "script_id": script_id,
                "episode": int(episode),
                "prompt": optimized_prompt,
                "negative_prompt": "低质量，模糊，变形，白发，现代服装，西方风格",
                "model": "seedream-4.5",
                "width": 720,
                "height": 1280,
                "style": "国风仙侠"
            }
            req = urllib.request.Request(
                f"{DRAMA_API}/api/keyframe/create",
                data=json.dumps(kf_payload).encode(),
                headers={"Content-Type": "application/json"}
            )
            resp = urllib.request.urlopen(req, timeout=10)
            kf_resp = json.loads(resp.read().decode())
            keyframes.append({
                "keyframe_id": kf_resp["keyframe_id"],
                "prompt": optimized_prompt,
                "status": "pending_confirmation",
                "note": "提示词已生成，图片生成需人工确认触发（零成本策略）"
            })
        except Exception as e:
            print(f"[S2] 关键帧创建失败: {e}")

    print(f"[S2] 完成: {len(keyframes)}个关键帧任务（待人工确认生成）")
    return {
        "script_id": script_id,
        "keyframes": keyframes,
        "keyframe_count": len(keyframes),
        "next_action": "人工确认后调用 /api/keyframe/{id}/complete 上传图片，或触发生图API"
    }

# ========== S3: 视频生成任务 ==========
def generate_video_tasks(script_id, episode):
    """S3: 为所有关键帧生成视频任务（提示词生成，视频生成待人工确认）"""
    print(f"[S3] 开始生成视频任务: {script_id}")

    # 获取所有关键帧
    try:
        req = urllib.request.Request(f"{DRAMA_API}/api/keyframe/list?script_id={script_id}")
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())
        keyframes = data.get("keyframes", [])
    except Exception as e:
        return {"error": f"获取关键帧失败: {e}"}

    video_tasks = []
    for kf in keyframes:
        kf_id = kf[0] if isinstance(kf, (list, tuple)) else kf.get("keyframe_id")
        prompt = kf[4] if isinstance(kf, (list, tuple)) else kf.get("prompt", "")

        # 生成视频提示词
        video_prompt = f"{prompt}，镜头缓慢推进，人物微动，衣袂飘飘，烟雾缭绕，15秒"

        video_tasks.append({
            "keyframe_id": kf_id,
            "video_prompt": video_prompt,
            "model": "seedance_2.0_fast",
            "duration": 15,
            "status": "pending_confirmation",
            "note": "视频提示词已生成，视频生成需人工确认触发（零成本策略）"
        })

    print(f"[S3] 完成: {len(video_tasks)}个视频任务（待人工确认生成）")
    return {
        "script_id": script_id,
        "video_tasks": video_tasks,
        "video_count": len(video_tasks),
        "next_action": "人工确认后调用视频生成API，完成后触发S4-S8自动化"
    }

# ========== 全流程编排 ==========
def run_full_pipeline(episode, title):
    """运行S1-S3全流程"""
    task_id = f"AUTO-{int(time.time())}"
    print(f"\n{'='*50}")
    print(f"短剧自动化编排启动: {task_id}")
    print(f"第{episode}集 《{title}》")
    print(f"{'='*50}\n")

    # S1
    s1_result = generate_script(episode, title)
    if "error" in s1_result:
        return {"task_id": task_id, "status": "failed", "step": "S1", "error": s1_result["error"]}

    script_id = s1_result["script_id"]

    # S2
    s2_result = generate_keyframes(script_id, episode)

    # S3
    s3_result = generate_video_tasks(script_id, episode)

    # 保存任务记录
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO auto_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
              (task_id, episode, title, "s3_completed", "S3", script_id,
               s1_result["storyboard_count"], s2_result.get("keyframe_count", 0),
               s3_result.get("video_count", 0), time.time(), time.time(),
               json.dumps({"s1": s1_result, "s2": s2_result, "s3": s3_result}, ensure_ascii=False)))
    conn.commit()
    conn.close()

    return {
        "task_id": task_id,
        "status": "s3_completed",
        "episode": episode,
        "title": title,
        "script_id": script_id,
        "s1": {"storyboards": s1_result["storyboard_count"]},
        "s2": {"keyframes": s2_result.get("keyframe_count", 0), "status": "待人工确认生图"},
        "s3": {"videos": s3_result.get("video_count", 0), "status": "待人工确认生成视频"},
        "next_steps": [
            "1. 人工确认关键帧提示词，触发生图API",
            "2. 图片生成后调用 /api/keyframe/{id}/complete",
            "3. 人工确认视频提示词，触发视频生成API",
            "4. 视频完成后自动触发S4-S8（转码/COS/归档/对账）"
        ],
        "zero_cost_note": "S1文本生成全自动零成本；S2/S3图片视频生成需人工确认，遵守零成本策略"
    }

# ========== HTTP API ==========
class OrchestratorHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/health":
            self._send_json({"status": "ok", "service": "drama-auto-orchestrator", "port": PORT})
            return
        if path == "/api/tasks":
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT task_id, episode, title, status, current_step, created_at FROM auto_tasks ORDER BY created_at DESC LIMIT 20")
            tasks = [{"task_id": r[0], "episode": r[1], "title": r[2], "status": r[3], "step": r[4], "created_at": r[5]} for r in c.fetchall()]
            conn.close()
            self._send_json({"tasks": tasks, "count": len(tasks)})
            return
        self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._read_body()

        if path == "/api/orchestrate/run":
            # 运行全流程S1-S3
            episode = body.get("episode", "1")
            title = body.get("title", "未命名")
            result = run_full_pipeline(str(episode), title)
            self._send_json(result)
            return

        if path == "/api/orchestrate/s1":
            # 只运行S1
            episode = body.get("episode", "1")
            title = body.get("title", "未命名")
            result = generate_script(str(episode), title)
            self._send_json(result)
            return

        if path == "/api/orchestrate/s2":
            script_id = body.get("script_id", "")
            episode = body.get("episode", "1")
            if not script_id:
                self._send_json({"error": "缺少script_id"}, 400)
                return
            result = generate_keyframes(script_id, int(episode))
            self._send_json(result)
            return

        if path == "/api/orchestrate/s3":
            script_id = body.get("script_id", "")
            episode = body.get("episode", "1")
            if not script_id:
                self._send_json({"error": "缺少script_id"}, 400)
                return
            result = generate_video_tasks(script_id, int(episode))
            self._send_json(result)
            return

        self._send_json({"error": "not found"}, 404)

def main():
    server = HTTPServer(("0.0.0.0", PORT), OrchestratorHandler)
    print(f"昆仑洞天短剧自动化编排器 v1.0 启动于端口 {PORT}")
    print(f"S1剧本+分镜: 全自动(AI代理)")
    print(f"S2关键帧: 提示词全自动，图片生成人工确认")
    print(f"S3视频: 提示词全自动，视频生成人工确认")
    print(f"零成本策略: 文本生成免费，图片/视频生成需人工确认")
    print(f"确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    server.serve_forever()

if __name__ == "__main__":
    main()
