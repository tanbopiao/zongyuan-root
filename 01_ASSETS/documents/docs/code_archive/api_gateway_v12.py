
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import time
import uuid
import requests
import json
import asyncio
import edge_tts
import os
import sqlite3
from datetime import datetime

app = FastAPI(title="火斗云智元内核API", version="v13.0")

# ===== SQLite数据库初始化 =====
DB_PATH = "/opt/ZONGYUAN-ROOT/api_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 用户表
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            api_key TEXT PRIMARY KEY,
            name TEXT,
            tier TEXT,
            quota INTEGER,
            used INTEGER,
            email TEXT,
            created_at TEXT
        )
    ''')
    
    # 调用日志表
    c.execute('''
        CREATE TABLE IF NOT EXISTS call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            endpoint TEXT,
            user_name TEXT,
            tier TEXT,
            status TEXT,
            duration_ms INTEGER
        )
    ''')
    
    # 激活码表
    c.execute('''
        CREATE TABLE IF NOT EXISTS redeem_codes (
            code TEXT PRIMARY KEY,
            tier TEXT,
            quota INTEGER,
            duration_days INTEGER,
            used INTEGER DEFAULT 0,
            used_by TEXT,
            used_at TEXT,
            created_at TEXT
        )
    ''')
    
    # 初始化默认用户
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("huodou-free-001", "免费测试用户", "free", 1000, 0, "test@huodouai.com", datetime.now().isoformat()))
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("huodou-pro-001", "专业版用户", "pro", 100000, 0, "pro@huodouai.com", datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user(api_key: str):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)).fetchone()
    conn.close()
    if not user:
        return None
    return dict(user)

def update_user_used(api_key: str, used: int):
    conn = get_db()
    conn.execute("UPDATE users SET used = ? WHERE api_key = ?", (used, api_key))
    conn.commit()
    conn.close()

def add_user(api_key: str, name: str, tier: str, quota: int, email: str):
    conn = get_db()
    conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (api_key, name, tier, quota, 0, email, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_by_email(email: str):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(user) if user else None

def count_users():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return count

def add_call_log(endpoint: str, user_name: str, tier: str, status: str, duration_ms: int):
    conn = get_db()
    conn.execute("INSERT INTO call_logs (timestamp, endpoint, user_name, tier, status, duration_ms) VALUES (?, ?, ?, ?, ?, ?)",
                 (datetime.now().isoformat(), endpoint, user_name, tier, status, duration_ms))
    conn.commit()
    conn.close()

def get_call_logs(limit: int = 100):
    conn = get_db()
    logs = conn.execute("SELECT * FROM call_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(log) for log in logs]

# ===== 外部API配置 =====
LLM_CONFIG = {
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "api_key": "d63c880c0e1b424d8ad242f686e83451.vhHr5d5OQUY5UHNp",
    "model": "glm-4-flash",
}

IMAGE_CONFIG = {
    "base_url": "https://open.bigmodel.cn/api/paas/v4/images/generations",
    "api_key": "d63c880c0e1b424d8ad242f686e83451.vhHr5d5OQUY5UHNp",
    "model": "cogview-3-flash",
}

VIDEO_CONFIG = {
    "base_url": "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks",
    "api_key": "ark-f7b61c6f-41d2-406f-8c44-a801830e8a55-82e36",
    "model": "ep-20260912023827-d2jc4",
}

class ChatRequest(BaseModel):
    message: str
    session_id: str = ""

class ImageRequest(BaseModel):
    prompt: str
    size: str = "768x1344"

class VideoRequest(BaseModel):
    prompt: str
    size: str = "768x1344"

class TTSRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"

class RegisterRequest(BaseModel):
    email: str
    name: str = ""

class RedeemRequest(BaseModel):
    code: str

def check_auth(api_key: str):
    user = get_user(api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    if user["used"] >= user["quota"]:
        raise HTTPException(status_code=429, detail="Quota exceeded")
    return user

def log_call(endpoint, user, status, duration_ms):
    add_call_log(endpoint, user["name"], user["tier"], status, duration_ms)

@app.post("/v1/register")
def register(req: RegisterRequest):
    existing = get_user_by_email(req.email)
    if existing:
        return {
            "success": False,
            "message": "该邮箱已注册",
            "api_key": existing["api_key"]
        }
    
    user_count = count_users()
    new_key = f"huodou-free-{str(user_count + 1).zfill(3)}"
    add_user(new_key, req.name or req.email.split("@")[0], "free", 1000, req.email)
    
    return {
        "success": True,
        "message": "注册成功",
        "api_key": new_key,
        "tier": "free",
        "quota": 1000,
        "note": "免费版1000次/月，如需更多请升级专业版"
    }

@app.post("/v1/chat")
def chat(req: ChatRequest, authorization: str = Header(None)):
    start_time = time.time()
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)
    update_user_used(api_key, user["used"] + 1)

    system_prompt = """你是火斗云智元内核AI，由ZONGYUAN-ROOT元极恒一自治体系驱动。
回答要求：
1. 使用Markdown格式排版，支持粗体、列表、标题
2. 段落清晰，重点内容用**粗体**突出
3. 分点回答时用列表，层次分明
4. 专业简洁，体现元内核的规则驱动能力
5. 始终记得你是火斗云智的元内核AI

请用中文回答问题。"""

    try:
        resp = requests.post(
            f"{LLM_CONFIG['base_url']}/chat/completions",
            headers={
                "Authorization": f"Bearer {LLM_CONFIG['api_key']}",
                "Content-Type": "application/json"
            },
            json={
                "model": LLM_CONFIG["model"],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": req.message}
                ],
                "max_tokens": 500,
                "temperature": 0.7
            },
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            answer = data["choices"][0]["message"]["content"]
            status = "success"
        else:
            answer = f"AI服务暂时不可用。({resp.status_code})"
            status = "error"
    except Exception as e:
        answer = f"AI服务暂时不可用。({str(e)[:50]})"
        status = "error"

    duration = int((time.time() - start_time) * 1000)
    log_call("chat", user, status, duration)
    
    updated_user = get_user(api_key)
    return {
        "answer": answer,
        "session_id": req.session_id or str(uuid.uuid4())[:8],
        "usage": {
            "used": updated_user["used"],
            "quota": updated_user["quota"],
            "remaining": updated_user["quota"] - updated_user["used"]
        }
    }

@app.post("/v1/chat/stream")
async def chat_stream(req: ChatRequest, authorization: str = Header(None)):
    start_time = time.time()
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)
    update_user_used(api_key, user["used"] + 1)

    system_prompt = """你是火斗云智元内核AI，由ZONGYUAN-ROOT元极恒一自治体系驱动。
回答要求：
1. 使用Markdown格式排版，支持粗体、列表、标题
2. 段落清晰，重点内容用**粗体**突出
3. 分点回答时用列表，层次分明
4. 专业简洁，体现元内核的规则驱动能力
5. 始终记得你是火斗云智的元内核AI

请用中文回答问题。"""

    async def generate():
        try:
            resp = requests.post(
                f"{LLM_CONFIG['base_url']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {LLM_CONFIG['api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": LLM_CONFIG["model"],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": req.message}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7,
                    "stream": True
                },
                timeout=30,
                stream=True
            )
            
            for line in resp.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield f"data: {json.dumps({'content': delta})}\n\n"
                        except:
                            pass
            status = "success"
        except Exception as e:
            err_msg = "\n\n服务暂时不可用: " + str(e)[:50]
            yield "data: " + json.dumps({'content': err_msg}) + "\n\n"
            status = "error"
        
        duration = int((time.time() - start_time) * 1000)
        log_call("chat_stream", user, status, duration)

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/v1/image/generate")
def image_generate(req: ImageRequest, authorization: str = Header(None)):
    start_time = time.time()
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)
    update_user_used(api_key, user["used"] + 1)

    try:
        resp = requests.post(
            IMAGE_CONFIG["base_url"],
            headers={
                "Authorization": f"Bearer {IMAGE_CONFIG['api_key']}",
                "Content-Type": "application/json"
            },
            json={
                "model": IMAGE_CONFIG["model"],
                "prompt": req.prompt,
                "size": req.size
            },
            timeout=60
        )
        
        if resp.status_code == 200:
            data = resp.json()
            image_url = data["data"][0]["url"]
            status = "success"
        else:
            image_url = ""
            status = "error"
    except Exception as e:
        image_url = ""
        status = "error"

    duration = int((time.time() - start_time) * 1000)
    log_call("image_generate", user, status, duration)
    
    return {"image_url": image_url, "status": status}

@app.post("/v1/video/generate")
def video_generate(req: VideoRequest, authorization: str = Header(None)):
    start_time = time.time()
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)
    update_user_used(api_key, user["used"] + 1)

    try:
        resp = requests.post(
            VIDEO_CONFIG["base_url"],
            headers={
                "Authorization": f"Bearer {VIDEO_CONFIG['api_key']}",
                "Content-Type": "application/json"
            },
            json={
                "model": VIDEO_CONFIG["model"],
                "content": [
                    {"type": "text", "text": req.prompt}
                ]
            },
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            task_id = data["id"]
            status = "success"
        else:
            task_id = ""
            status = "error"
    except Exception as e:
        task_id = ""
        status = "error"

    duration = int((time.time() - start_time) * 1000)
    log_call("video_generate", user, status, duration)
    
    return {"task_id": task_id, "status": status}

@app.get("/v1/video/status/{task_id}")
def video_status(task_id: str, authorization: str = Header(None)):
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)
    
    try:
        resp = requests.get(
            f"{VIDEO_CONFIG['base_url']}/{task_id}",
            headers={
                "Authorization": f"Bearer {VIDEO_CONFIG['api_key']}"
            },
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            status = data["status"]
            video_url = data.get("content", {}).get("video_url", "")
        else:
            status = "unknown"
            video_url = ""
    except Exception as e:
        status = "error"
        video_url = ""
    
    return {"status": status, "video_url": video_url}

@app.post("/v1/tts")
async def tts(req: TTSRequest, authorization: str = Header(None)):
    start_time = time.time()
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)
    update_user_used(api_key, user["used"] + 1)

    try:
        communicate = edge_tts.Communicate(req.text, req.voice)
        audio_path = f"/tmp/tts_{uuid.uuid4()[:8]}.mp3"
        await communicate.save(audio_path)
        status = "success"
    except Exception as e:
        audio_path = ""
        status = "error"

    duration = int((time.time() - start_time) * 1000)
    log_call("tts", user, status, duration)
    
    if status == "success":
        return FileResponse(audio_path, media_type="audio/mpeg")
    else:
        return {"error": "TTS service unavailable"}

@app.get("/v1/analytics")
def analytics(authorization: str = Header(None)):
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)
    if user["tier"] != "pro":
        raise HTTPException(status_code=403, detail="Pro tier required")
    
    logs = get_call_logs(100)
    total_calls = len(logs)
    success_calls = len([l for l in logs if l["status"] == "success"])
    
    return {
        "total_calls": total_calls,
        "success_rate": f"{success_calls/total_calls*100:.1f}%" if total_calls > 0 else "0%",
        "recent_logs": logs[:20]
    }

@app.post("/v1/redeem")
def redeem(req: RedeemRequest, authorization: str = Header(None)):
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)
    
    conn = get_db()
    code_row = conn.execute("SELECT * FROM redeem_codes WHERE code = ?", (req.code,)).fetchone()
    
    if not code_row:
        conn.close()
        raise HTTPException(status_code=404, detail="激活码不存在")
    
    code = dict(code_row)
    if code["used"]:
        conn.close()
        raise HTTPException(status_code=400, detail="激活码已被使用")
    
    # 激活码生效
    new_quota = user["quota"] + code["quota"]
    new_tier = "pro" if code["tier"] == "pro" else user["tier"]
    
    conn.execute("UPDATE users SET tier = ?, quota = ? WHERE api_key = ?", 
                 (new_tier, new_quota, api_key))
    conn.execute("UPDATE redeem_codes SET used = 1, used_by = ?, used_at = ? WHERE code = ?",
                 (user["name"], datetime.now().isoformat(), req.code))
    conn.commit()
    conn.close()
    
    updated_user = get_user(api_key)
    return {
        "success": True,
        "message": f"激活成功！升级为{new_tier}版，额度增加{code['quota']}次",
        "tier": updated_user["tier"],
        "quota": updated_user["quota"],
        "remaining": updated_user["quota"] - updated_user["used"]
    }

@app.post("/v1/admin/create-code")
def create_code(authorization: str = Header(None)):
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = get_user(api_key)
    if not user or user["tier"] != "pro":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    import string
    import random
    code = "HUODOU-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    
    conn = get_db()
    conn.execute("INSERT INTO redeem_codes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (code, "pro", 100000, 30, 0, None, None, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "code": code,
        "tier": "pro",
        "quota": 100000,
        "duration_days": 30,
        "price": "99元"
    }

@app.get("/v1/status")
def status():
    return {
        "service": "火斗云智元内核API",
        "version": "v13.0",
        "status": "running",
        "database": "sqlite_persistent",
        "users": count_users(),
        "features": ["chat", "stream", "image", "video", "tts", "redeem"]
    }
