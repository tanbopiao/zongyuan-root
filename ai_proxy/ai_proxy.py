#!/usr/bin/env python3
"""
ZONGYUAN-ROOT AI Proxy V3
- 多模型切换：豆包(doubao) + 混元(hunyuan)
- 拉片拆解：/analyze/deconstruct
- 拉片复刻：/analyze/remake
- 关键帧/视频提示词优化
- 视频任务管理：/video/task, /video/list
- Ω-Brainμ真值召回前置
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json, urllib.request, urllib.error, urllib.parse, argparse, os, time, uuid, glob
from http.server import HTTPServer, BaseHTTPRequestHandler

MODELS = {
    "doubao": {
        "base": "https://ark.cn-beijing.volces.com/api/v3",
        "key": "6f8c69a7-d613-41d6-9db3-5c929a9a49e4",
        "model": "doubao-seed-2-0-lite-260215",
        "endpoint": "ep-m-20260325114252-xcd64"
    },
    "hunyuan": {
        "base": "https://tokenhub.tencentmaas.com/v1",
        "key": "sk-PXuFhwjKLZl5yN60srA68uaVb1Wn71eTuPWRAaY1stEH3SZs",
        "model": "hy4-preview"
    }
}


# ============ 视频生成任务存储（V1内存级） ============
VIDEO_TASKS = {}

# ============ 图片生成任务存储 ============
IMAGE_TASKS = {}

def call_image_generation(api_config, prompt, ratio="9:16"):
    """图片生成adapter：seedream(火山方舟)/generic(OpenAI兼容)"""
    import uuid, threading
    task_id = "img_" + str(uuid.uuid4())[:8]
    provider = api_config.get("provider", "generic")
    IMAGE_TASKS[task_id] = {
        "task_id": task_id, "status": "processing", "prompt": prompt,
        "provider": provider, "image_url": None, "created_at": time.time(), "error": None
    }
    def _generate():
        try:
            api_key = api_config.get("api_key","")
            endpoint = api_config.get("endpoint","")
            model = api_config.get("model","")
            if provider == "seedance" or provider == "seedream":
                # 火山方舟图片生成
                base = (endpoint or "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
                model = model or "seedream-4-0-250828"
                body = json.dumps({"model": model, "prompt": prompt, "size": ratio}).encode()
                req = urllib.request.Request(base+"/images/generations", data=body, headers={
                    "Content-Type":"application/json","Authorization":f"Bearer {api_key}"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    result = json.loads(resp.read())
                img_url = (result.get("data",[{}])[0].get("url") if result.get("data") else None)
                if img_url:
                    IMAGE_TASKS[task_id]["status"]="completed"
                    IMAGE_TASKS[task_id]["image_url"]=img_url
                else:
                    IMAGE_TASKS[task_id]["status"]="failed"
                    IMAGE_TASKS[task_id]["error"]="无图片URL: "+str(result)[:200]
            else:
                # 通用OpenAI兼容格式
                base = endpoint.rstrip("/") if endpoint else ""
                if not base:
                    IMAGE_TASKS[task_id]["status"]="failed"
                    IMAGE_TASKS[task_id]["error"]="缺少endpoint"
                    return
                body = json.dumps({"model": model or "default","prompt": prompt,"size": ratio}).encode()
                req = urllib.request.Request(base+"/images/generations", data=body, headers={
                    "Content-Type":"application/json","Authorization":f"Bearer {api_key}"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    result = json.loads(resp.read())
                img_url = (result.get("data",[{}])[0].get("url") if result.get("data") else None) or result.get("url")
                if img_url:
                    IMAGE_TASKS[task_id]["status"]="completed"
                    IMAGE_TASKS[task_id]["image_url"]=img_url
                else:
                    IMAGE_TASKS[task_id]["status"]="failed"
                    IMAGE_TASKS[task_id]["error"]="无图片URL"
        except Exception as e:
            IMAGE_TASKS[task_id]["status"]="failed"
            IMAGE_TASKS[task_id]["error"]=str(e)[:200]
    threading.Thread(target=_generate, daemon=True).start()
    return task_id



def call_video_generation(api_config, prompt, duration=10, ratio="9:16"):
    """多provider视频生成adapter：seedance/kling/generic"""
    import uuid, threading
    task_id = str(uuid.uuid4())[:8]
    provider = api_config.get("provider", "generic")
    VIDEO_TASKS[task_id] = {
        "task_id": task_id, "status": "processing", "prompt": prompt,
        "provider": provider, "model": api_config.get("model",""),
        "video_url": None, "created_at": time.time(), "error": None, "progress": 0
    }
    def _generate():
        try:
            if provider == "seedance":
                _gen_seedance(task_id, api_config, prompt, duration, ratio)
            elif provider == "kling":
                _gen_kling(task_id, api_config, prompt, duration, ratio)
            else:
                _gen_generic(task_id, api_config, prompt, duration, ratio)
        except Exception as e:
            VIDEO_TASKS[task_id]["status"] = "failed"
            VIDEO_TASKS[task_id]["error"] = str(e)[:200]
    threading.Thread(target=_generate, daemon=True).start()
    return task_id

def _gen_seedance(task_id, cfg, prompt, duration, ratio):
    """火山方舟Seedance视频生成"""
    api_key = cfg.get("api_key","")
    base = (cfg.get("endpoint","") or "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
    model = cfg.get("model","") or "seedance-1-0-pro-250528"
    body = json.dumps({"model": model, "content": [{"type":"text","text":prompt}]}).encode()
    req = urllib.request.Request(base+"/contents/generations/tasks", data=body, headers={
        "Content-Type":"application/json","Authorization":f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    rid = result.get("id") or result.get("task_id")
    if not rid:
        VIDEO_TASKS[task_id]["status"]="failed"; VIDEO_TASKS[task_id]["error"]="提交失败:"+str(result)[:150]; return
    for i in range(36):
        time.sleep(5)
        VIDEO_TASKS[task_id]["progress"] = min((i+1)*3, 95)
        req2 = urllib.request.Request(base+f"/contents/generations/tasks/{rid}", headers={"Authorization":f"Bearer {api_key}"})
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            st = json.loads(resp2.read())
        if st.get("status") in ("succeeded","completed","success"):
            c = st.get("content",{})
            vurl = c.get("video_url") or (c.get("video") or {}).get("url")
            if vurl:
                VIDEO_TASKS[task_id]["status"]="completed"; VIDEO_TASKS[task_id]["video_url"]=vurl
                VIDEO_TASKS[task_id]["progress"]=100; return
        if st.get("status") in ("failed","error"):
            VIDEO_TASKS[task_id]["status"]="failed"; VIDEO_TASKS[task_id]["error"]=str(st.get("error","失败"))[:150]; return
    VIDEO_TASKS[task_id]["status"]="failed"; VIDEO_TASKS[task_id]["error"]="轮询超时(>180s)"

def _gen_kling(task_id, cfg, prompt, duration, ratio):
    """可灵Kling视频生成"""
    api_key = cfg.get("api_key","")
    base = (cfg.get("endpoint","") or "https://api.klingai.com/v1").rstrip("/")
    model = cfg.get("model","") or "kling-v1"
    body = json.dumps({"model_name":model,"prompt":prompt,"duration":str(duration)}).encode()
    req = urllib.request.Request(base+"/videos/generation", data=body, headers={
        "Content-Type":"application/json","Authorization":f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    rid = result.get("data",{}).get("task_id") or result.get("task_id")
    if not rid:
        VIDEO_TASKS[task_id]["status"]="failed"; VIDEO_TASKS[task_id]["error"]="提交失败:"+str(result)[:150]; return
    for i in range(36):
        time.sleep(5)
        VIDEO_TASKS[task_id]["progress"] = min((i+1)*3, 95)
        req2 = urllib.request.Request(base+f"/videos/generation/{rid}", headers={"Authorization":f"Bearer {api_key}"})
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            st = json.loads(resp2.read())
        ts = st.get("data",{}).get("task_status") or st.get("status")
        if ts in ("succeed","completed","success"):
            vurl = st.get("data",{}).get("video_url") or st.get("video_url")
            if vurl:
                VIDEO_TASKS[task_id]["status"]="completed"; VIDEO_TASKS[task_id]["video_url"]=vurl
                VIDEO_TASKS[task_id]["progress"]=100; return
        if ts in ("failed","error"):
            VIDEO_TASKS[task_id]["status"]="failed"; VIDEO_TASKS[task_id]["error"]="生成失败"; return
    VIDEO_TASKS[task_id]["status"]="failed"; VIDEO_TASKS[task_id]["error"]="轮询超时(>180s)"

def _gen_generic(task_id, cfg, prompt, duration, ratio):
    """通用OpenAI兼容格式"""
    api_key = cfg.get("api_key",""); endpoint = cfg.get("endpoint","")
    model = cfg.get("model","")
    if not (endpoint and api_key):
        VIDEO_TASKS[task_id]["status"]="failed"; VIDEO_TASKS[task_id]["error"]="缺少API配置"; return
    url = endpoint.rstrip("/") + "/videos/generations"
    body = json.dumps({"model":model or "default","prompt":prompt,"duration":duration,"ratio":ratio}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type":"application/json","Authorization":f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
    vurl = result.get("video_url") or result.get("url") or (result.get("data",[{}])[0].get("url") if result.get("data") else None)
    if vurl:
        VIDEO_TASKS[task_id]["status"]="completed"; VIDEO_TASKS[task_id]["video_url"]=vurl
        VIDEO_TASKS[task_id]["progress"]=100
    else:
        VIDEO_TASKS[task_id]["status"]="completed"; VIDEO_TASKS[task_id]["video_url"]=None
        VIDEO_TASKS[task_id]["raw_response"]=str(result)[:500]

OMEGA_URL = "http://127.0.0.1:8000"
VIDEO_DIR = "/www/wwwroot/huodouai.com/drama/videos"
MANIFEST_DIR = "/opt/ZONGYUAN-ROOT/drama_output/manifests"
TASK_DIR = "/opt/ZONGYUAN-ROOT/drama_output/tasks"
os.makedirs(TASK_DIR, exist_ok=True)
os.makedirs(MANIFEST_DIR, exist_ok=True)

KUNLUN_CHARACTERS = {
    "taiyin": {"name": "太阴月神", "desc": "纯乌黑长发东方神女，九头身，银辉眼眸，青黑长裙，玄鸟图腾，桂月华光"},
    "xuannv": {"name": "九天玄女", "desc": "纯乌黑长发东方女帝，九头身，青金战斗长裙，天书+剑，玄鸟图腾，强烈轮廓光"},
    "feilingxi": {"name": "赤霞司命·绯灵汐", "desc": "纯乌黑长发东方神女，九头身，赤霞赤金长裙，司命之力，霞光万道"},
    "chiwan": {"name": "赤凰伺主·凰绾", "desc": "纯乌黑长发东方神女，九头身，赤凰羽翼，赤金长裙，凤凰图腾"}
}

def call_llm(model_key, messages, max_tokens=2048):
    cfg = MODELS.get(model_key, MODELS["doubao"])
    url = f"{cfg['base']}/chat/completions"
    body = json.dumps({"model": cfg["model"], "messages": messages, "max_tokens": max_tokens, "stream": False}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg['key']}"
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[API错误] {str(e)}"

def recall_truth(query, top_k=5):
    try:
        url = f"{OMEGA_URL}/recall?q={urllib.parse.quote(query)}&top_k={top_k}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("results", [])
    except:
        return []

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "healthy", "service": "ai-proxy-v5", "models": list(MODELS.keys()), "omega": "connected"})
        elif self.path == "/models":
            self._send(200, {"models": {k: {"model": v["model"], "available": True} for k, v in MODELS.items()}})
        elif self.path == "/characters":
            self._send(200, {"characters": KUNLUN_CHARACTERS})
        elif self.path == "/video/list":
            manifests = sorted(glob.glob(f"{MANIFEST_DIR}/*.json"), reverse=True)
            videos = []
            for m in manifests[:20]:
                try:
                    with open(m) as f:
                        videos.append(json.load(f))
                except: pass
            self._send(200, {"videos": videos, "count": len(videos)})
        elif self.path.startswith("/video/status/"):
            task_id = self.path.split("/")[-1]
            task_file = f"{TASK_DIR}/{task_id}.json"
            if os.path.exists(task_file):
                with open(task_file) as f:
                    self._send(200, json.load(f))
            else:
                self._send(404, {"error": "task not found"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw)
        except:
            data = {}

        if self.path == "/chat":
            model = data.get("model", "doubao")
            message = data.get("message", "")
            node_type = data.get("node_type", "")
            truth_query = data.get("truth_query", message)
            truths = recall_truth(truth_query)
            truth_text = "\n".join([f"- {t.get('content','')[:80]}" for t in truths]) if truths else "（无召回）"
            sys_prompt = f"""你是昆仑洞天短剧创作系统的AI助手。
【真值约束】{truth_text}
【L0天元法则】纯东方审美，纯乌黑长发东方神女，九头身，禁用西方铠甲/雄性化元素/现代科技建筑。
【节点类型】{node_type}
请基于以上约束生成高质量内容。"""
            result = call_llm(model, [{"role": "system", "content": sys_prompt}, {"role": "user", "content": message}])
            self._send(200, {"result": result, "model": MODELS.get(model, {}).get("model", "?"), "truths_recalled": len(truths), "truths": truths[:3]})

        elif self.path == "/analyze/deconstruct":
            model = data.get("model", "doubao")
            video_desc = data.get("video_desc", "")
            if not video_desc:
                self._send(400, {"error": "video_desc required"})
                return
            prompt = f"""请对以下参考视频/短剧进行专业拉片拆解，输出JSON格式：
参考内容：{video_desc}
请从以下维度拆解，输出严格JSON：
{{"narrative_structure":"叙事结构","beat_sheet":["节拍1"],"character_roles":[{"role":"角色名","function":"叙事功能"}],"scene_list":[{"scene":"场景名","location":"地点","mood":"情绪"}],"shot_language":{"shot_types":["景别"],"camera_moves":["运镜"],"pacing":"节奏"},"visual_style":{"color":"色彩","lighting":"光影"},"sound_design":{"bgm":"BGM风格","sfx":"音效"},"emotional_curve":["情绪节点"],"key_visual_elements":["关键元素"],"hook":"开头钩子","climax":"高潮设计","resolution":"收尾方式","target_audience":"目标受众","genre":"类型","duration_estimate":"预估时长","remake_notes":"复刻要点"}}"""
            result = call_llm(model, [{"role": "user", "content": prompt}], max_tokens=3000)
            try:
                parsed = json.loads(result)
            except:
                parsed = {"raw": result}
            self._send(200, {"status": "deconstructed", "model": MODELS.get(model, {}).get("model", "?"), "analysis": parsed})

        elif self.path == "/analyze/remake":
            model = data.get("model", "doubao")
            video_desc = data.get("video_desc", "")
            character_key = data.get("character", "taiyin")
            char = KUNLUN_CHARACTERS.get(character_key, KUNLUN_CHARACTERS["taiyin"])
            if not video_desc:
                self._send(400, {"error": "video_desc required"})
                return
            prompt = f"""基于以下参考视频描述，生成一部昆仑洞天风格的复刻短剧完整流水线。
参考内容：{video_desc}
替换主角为：{char['name']} - {char['desc']}
输出JSON：{{"title":"标题","logline":"梗概","script":"剧本","storyboard":[{"shot":"镜头1","description":"画面"}],"keyframes":[{"id":"KF1","prompt":"提示词"}],"video_clips":[{"id":"V1","prompt":"视频提示词","duration":"10s"}],"compose_notes":"合成说明","archive_meta":{{"ip":"昆仑洞天","character":"{char['name']}","did":"DID-BR-000002"}}}}
【L0约束】纯东方审美，{char['desc']}，禁用西方铠甲/雄性化元素/现代建筑。"""
            result = call_llm(model, [{"role": "user", "content": prompt}], max_tokens=4000)
            try:
                parsed = json.loads(result)
            except:
                parsed = {"raw": result}
            self._send(200, {"status": "remake_ready", "model": MODELS.get(model, {}).get("model", "?"), "character": char["name"], "pipeline": parsed})

        elif self.path == "/generate/keyframe":
            prompt = data.get("prompt", "")
            model = data.get("model", "doubao")
            optimized = call_llm(model, [{"role": "system", "content": "你是专业关键帧提示词优化器。将用户输入优化为Seedream 5.0 Pro可用的高质量提示词，必须包含：纯乌黑长发东方神女、九头身、UE5.7光追、Portra400胶片质感、9:16竖屏、玄鸟图腾、青黑长裙、强烈轮廓光、霞光、山海经风格、零雄性化、零西方铠甲。"}, {"role": "user", "content": prompt}])
            self._send(200, {"status": "prompt_ready", "engine": "Seedream 5.0 Pro", "optimized_prompt": optimized, "model": MODELS.get(model, {}).get("model", "?")})

        elif self.path == "/generate/video":
            prompt = data.get("prompt", "")
            model = data.get("model", "doubao")
            optimized = call_llm(model, [{"role": "system", "content": "你是专业视频提示词优化器。将用户输入优化为Seedance 2.5可用的视频提示词，10秒，9:16竖屏，包含镜头运动、情绪氛围、动作描述。"}, {"role": "user", "content": prompt}])
            self._send(200, {"status": "prompt_ready", "engine": "Seedance 2.5", "duration": "10s", "optimized_prompt": optimized, "model": MODELS.get(model, {}).get("model", "?")})

        elif self.path == "/video/task":
            prompt = data.get("prompt", "")
            episode = data.get("episode", "untitled")
            model = data.get("model", "doubao")
            if not prompt:
                self._send(400, {"error": "prompt required"})
                return
            task_id = f"VIDEO-{uuid.uuid4().hex[:8]}"
            task = {
                "task_id": task_id,
                "episode": episode,
                "prompt": prompt,
                "model": model,
                "status": "pending",
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "output_url": None
            }
            with open(f"{TASK_DIR}/{task_id}.json", "w") as f:
                json.dump(task, f, ensure_ascii=False, indent=2)
            self._send(200, {"status": "task_created", "task_id": task_id, "message": "任务已创建，等待视频生成引擎处理"})


        elif self.path == "/drama/list":
            """列出所有已归档视频"""
            import os, glob
            video_dir = "/opt/ZONGYUAN-ROOT/drama_output/videos"
            manifest_dir = "/opt/ZONGYUAN-ROOT/drama_output/manifests"
            videos = []
            for f in sorted(glob.glob(os.path.join(video_dir, "*.mp4")), reverse=True):
                name = os.path.basename(f)
                size = os.path.getsize(f)
                sha = ""
                title = name
                # 查找对应manifest
                for m in glob.glob(os.path.join(manifest_dir, "*.json")):
                    try:
                        md = json.load(open(m))
                        if md.get("file_name") == name:
                            sha = md.get("sha256", "")
                            title = md.get("title", name)
                            break
                    except: pass
                videos.append({
                    "file_name": name,
                    "title": title,
                    "size": size,
                    "sha256": sha,
                    "url": f"https://www.huodouai.com/drama/videos/{name}"
                })
            self._send(200, {"status": "ok", "count": len(videos), "videos": videos})

        elif self.path == "/drama/archive":
            """归档视频：传入本地路径，执行归档脚本"""
            video_path = data.get("video_path", "")
            episode_id = data.get("episode_id", "EP-UNKNOWN")
            title = data.get("title", "未命名")
            import subprocess
            if not video_path or not os.path.exists(video_path):
                self._send(400, {"error": "video_path not found"})
                return
            result = subprocess.run(
                ["/opt/ZONGYUAN-ROOT/drama_output/archive_video.sh", video_path, episode_id, title],
                capture_output=True, text=True, timeout=30
            )
            self._send(200, {"status": "archived", "stdout": result.stdout, "stderr": result.stderr})

        elif self.path == "/drama/manifest":
            """获取指定视频的manifest"""
            episode_id = data.get("episode_id", "")
            import glob as _glob
            manifests = []
            for m in sorted(_glob.glob("/opt/ZONGYUAN-ROOT/drama_output/manifests/*.json"), reverse=True):
                if episode_id and episode_id not in m:
                    continue
                try:
                    manifests.append(json.load(open(m)))
                except: pass
            self._send(200, {"status": "ok", "count": len(manifests), "manifests": manifests})


        elif self.path == "/video/generate":
            """用户自填API生成视频"""
            api_config = data.get("api_config", {})
            prompt = data.get("prompt", "")
            duration = data.get("duration", 10)
            ratio = data.get("ratio", "9:16")
            if not prompt:
                self._send(400, {"error": "prompt required"})
                return
            if not api_config.get("api_key"):
                self._send(400, {"error": "api_config.api_key required"})
                return
            task_id = call_video_generation(api_config, prompt, duration, ratio)
            self._send(200, {"status": "submitted", "task_id": task_id, "poll_url": f"/video/status?task_id={task_id}"})

        elif self.path.startswith("/video/status"):
            """轮询视频生成状态"""
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            task_id = parse_qs(parsed.query).get("task_id", [None])[0]
            if not task_id or task_id not in VIDEO_TASKS:
                self._send(404, {"error": "task not found"})
                return
            task = VIDEO_TASKS[task_id]
            self._send(200, task)

        elif self.path == "/video/archive":
            """将生成的视频归档到产出目录"""
            task_id = data.get("task_id", "")
            episode_id = data.get("episode_id", "EP-AUTO")
            title = data.get("title", "未命名视频")
            if task_id not in VIDEO_TASKS:
                self._send(404, {"error": "task not found"})
                return
            task = VIDEO_TASKS[task_id]
            if task["status"] != "completed" or not task.get("video_url"):
                self._send(400, {"error": "video not ready", "status": task["status"]})
                return
            # 下载视频到本地
            import subprocess
            video_path = f"/opt/ZONGYUAN-ROOT/drama_output/videos/{episode_id}_{int(time.time())}.mp4"
            try:
                urllib.request.urlretrieve(task["video_url"], video_path)
                # 执行归档脚本
                result = subprocess.run(
                    ["/opt/ZONGYUAN-ROOT/drama_output/archive_video.sh", video_path, episode_id, title],
                    capture_output=True, text=True, timeout=30
                )
                self._send(200, {"status": "archived", "video_path": video_path, "stdout": result.stdout})
            except Exception as e:
                self._send(500, {"error": f"archive failed: {str(e)}"})


        elif self.path == "/video/compose":
            """FFmpeg多段视频合成"""
            video_urls = data.get("video_urls", [])
            title = data.get("title", "合成短剧")
            episode_id = data.get("episode_id", "EP-COMPOSE")
            if len(video_urls) < 2:
                self._send(400, {"error": "至少需要2段视频才能合成"})
                return
            import subprocess, os
            work_dir = "/opt/ZONGYUAN-ROOT/drama_output/tasks/compose_" + str(int(time.time()))
            os.makedirs(work_dir, exist_ok=True)
            # 下载所有视频
            local_files = []
            for i, url in enumerate(video_urls):
                fp = os.path.join(work_dir, f"seg_{i:02d}.mp4")
                try:
                    if url.startswith("http"):
                        urllib.request.urlretrieve(url, fp)
                    else:
                        # 本地文件，直接复制
                        import shutil
                        if os.path.exists(url): shutil.copy(url, fp)
                    if os.path.exists(fp) and os.path.getsize(fp) > 1000:
                        local_files.append(fp)
                except Exception as e:
                    pass
            if len(local_files) < 2:
                self._send(400, {"error": f"有效视频不足({len(local_files)}/2)"})
                return
            # 生成concat列表
            list_file = os.path.join(work_dir, "concat.txt")
            with open(list_file, "w") as f:
                for fp in local_files:
                    f.write(f"file '{fp}'\n")
            # FFmpeg合成（重新编码确保兼容）
            output_path = f"/opt/ZONGYUAN-ROOT/drama_output/videos/{episode_id}_{int(time.time())}.mp4"
            # 优先copy（快，无损），失败则转码
            cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                   "-c", "copy", "-movflags", "+faststart", output_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
                # copy失败，转码兜底
                cmd2 = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                        "-c:v", "libopenh264", "-b:v", "2M", "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart", output_path]
                result = subprocess.run(cmd2, capture_output=True, text=True, timeout=180)
            if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
                self._send(500, {"error": "FFmpeg合成失败", "stderr": result.stderr[-500:]})
                return
            # 归档
            archive_result = subprocess.run(
                ["/opt/ZONGYUAN-ROOT/drama_output/archive_video.sh", output_path, episode_id, title],
                capture_output=True, text=True, timeout=30
            )
            self._send(200, {
                "status": "completed",
                "output_path": output_path,
                "segments": len(local_files),
                "size_kb": int(os.path.getsize(output_path)/1024),
                "archive_stdout": archive_result.stdout[-300:]
            })


        elif self.path == "/image/generate":
            """关键帧真实出图"""
            api_config = data.get("api_config", {})
            prompt = data.get("prompt", "")
            ratio = data.get("ratio", "9:16")
            image_url = data.get("image_url", None)
            if not prompt:
                self._send(400, {"error": "prompt required"}); return
            if not api_config.get("api_key"):
                self._send(400, {"error": "api_config.api_key required"}); return
            task_id = call_image_generation(api_config, prompt, ratio)
            self._send(200, {"status": "submitted", "task_id": task_id})

        elif self.path.startswith("/image/status"):
            """图片生成状态轮询"""
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            task_id = parse_qs(parsed.query).get("task_id", [None])[0]
            if not task_id or task_id not in IMAGE_TASKS:
                self._send(404, {"error": "task not found"}); return
            self._send(200, IMAGE_TASKS[task_id])

        elif self.path == "/image/archive":
            """图片归档到keyframes目录"""
            task_id = data.get("task_id", "")
            episode_id = data.get("episode_id", "KF-AUTO")
            title = data.get("title", "关键帧")
            if task_id not in IMAGE_TASKS:
                self._send(404, {"error": "task not found"}); return
            task = IMAGE_TASKS[task_id]
            if task["status"] != "completed" or not task.get("image_url"):
                self._send(400, {"error": "image not ready", "status": task["status"]}); return
            import os
            kf_dir = "/opt/ZONGYUAN-ROOT/drama_output/keyframes"
            os.makedirs(kf_dir, exist_ok=True)
            filename = f"{episode_id}_{int(time.time())}.png"
            filepath = os.path.join(kf_dir, filename)
            try:
                urllib.request.urlretrieve(task["image_url"], filepath)
                # 复制到官网目录
                web_dir = "/www/wwwroot/huodouai.com/drama/keyframes"
                os.makedirs(web_dir, exist_ok=True)
                import shutil
                shutil.copy(filepath, os.path.join(web_dir, filename))
                sha = hashlib.sha256(open(filepath,'rb').read()).hexdigest()
                self._send(200, {"status": "archived", "url": f"/drama/keyframes/{filename}", "sha256": sha, "size_kb": int(os.path.getsize(filepath)/1024)})
            except Exception as e:
                self._send(500, {"error": f"archive failed: {str(e)}"})


        elif self.path == "/video/subtitle":
            """视频字幕烧录（FFmpeg drawtext）"""
            video_url = data.get("video_url", "")
            subtitle_text = data.get("subtitle", "")
            episode_id = data.get("episode_id", "EP-SUB")
            title = data.get("title", "字幕版")
            if not video_url or not subtitle_text:
                self._send(400, {"error": "video_url and subtitle required"}); return
            import subprocess, os
            work_dir = "/opt/ZONGYUAN-ROOT/drama_output/tasks/sub_" + str(int(time.time()))
            os.makedirs(work_dir, exist_ok=True)
            # 下载视频
            input_path = os.path.join(work_dir, "input.mp4")
            try:
                if video_url.startswith("http"):
                    urllib.request.urlretrieve(video_url, input_path)
                else:
                    import shutil
                    if os.path.exists(video_url): shutil.copy(video_url, input_path)
            except Exception as e:
                self._send(500, {"error": f"下载失败: {str(e)}"}); return
            if not os.path.exists(input_path):
                self._send(500, {"error": "视频下载失败"}); return
            # 生成SRT字幕（简单格式：整个视频显示一行字幕）
            # 获取视频时长
            probe = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",input_path],
                                   capture_output=True, text=True, timeout=10)
            duration = float(probe.stdout.strip() or "10")
            srt_content = f"1\n00:00:00,000 --> 00:00:{int(duration):02d},{int((duration%1)*1000):03d}\n{subtitle_text}\n"
            srt_path = os.path.join(work_dir, "sub.srt")
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            # 检查中文字体
            font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
            if not os.path.exists(font_path):
                font_path = "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc"
            if not os.path.exists(font_path):
                # 尝试找任意中文字体
                font_check = subprocess.run(["fc-list",":lang=zh","file"], capture_output=True, text=True)
                fonts = [l.split(":")[0].strip() for l in font_check.stdout.strip().split("\n") if l.strip()]
                font_path = fonts[0] if fonts else ""
            output_path = f"/opt/ZONGYUAN-ROOT/drama_output/videos/{episode_id}_sub_{int(time.time())}.mp4"
            # FFmpeg烧录字幕
            if font_path:
                vf = f"subtitles={srt_path}:force_style='FontName=WenQuanYi Zen Hei,FontSize=18,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'"
            else:
                vf = f"drawtext=text='{subtitle_text[:30]}':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=h-80"
            cmd = ["ffmpeg","-y","-i",input_path,"-vf",vf,"-c:a","copy","-movflags","+faststart",output_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
                self._send(500, {"error": "字幕烧录失败", "stderr": result.stderr[-300:], "font": font_path}); return
            # 归档
            archive_result = subprocess.run(
                ["/opt/ZONGYUAN-ROOT/drama_output/archive_video.sh", output_path, episode_id, title],
                capture_output=True, text=True, timeout=30)
            self._send(200, {"status": "completed", "output_path": output_path, "font_used": font_path or "默认", "duration": duration})

        else:
            self._send(404, {"error": "not found"})

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8021)
    args = parser.parse_args()
    server = HTTPServer(("0.0.0.0", args.port), Handler)
    print(f"AI Proxy V3 running on port {args.port}, models: {list(MODELS.keys())}")
    server.serve_forever()
