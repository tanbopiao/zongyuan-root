
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import time
import uuid
import requests
import json
from datetime import datetime

app = FastAPI(title="火斗云智元内核API", version="v10.0")

# ===== 客户API Key库 =====
API_KEYS = {
    "huodou-free-001": {"name": "免费测试用户", "tier": "free", "quota": 1000, "used": 0, "email": "test@huodouai.com"},
    "huodou-pro-001": {"name": "专业版用户", "tier": "pro", "quota": 100000, "used": 0, "email": "pro@huodouai.com"},
}

# ===== 调用日志 =====
call_logs = []
MAX_LOGS = 1000

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

class RegisterRequest(BaseModel):
    email: str
    name: str = ""

def check_auth(api_key: str):
    if api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    user = API_KEYS[api_key]
    if user["used"] >= user["quota"]:
        raise HTTPException(status_code=429, detail="Quota exceeded")
    return user

def log_call(endpoint, user, status, duration_ms):
    call_logs.append({
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "user": user["name"],
        "tier": user["tier"],
        "status": status,
        "duration_ms": duration_ms
    })
    if len(call_logs) > MAX_LOGS:
        call_logs.pop(0)

@app.post("/v1/register")
def register(req: RegisterRequest):
    # 检查邮箱是否已注册
    for key, user in API_KEYS.items():
        if user["email"] == req.email:
            return {
                "success": False,
                "message": "该邮箱已注册",
                "api_key": key
            }
    
    # 生成新API Key
    new_key = f"huodou-free-{str(len(API_KEYS) + 1).zfill(3)}"
    API_KEYS[new_key] = {
        "name": req.name or req.email.split("@")[0],
        "tier": "free",
        "quota": 1000,
        "used": 0,
        "email": req.email
    }
    
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
    user["used"] += 1

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
    
    return {
        "answer": answer,
        "session_id": req.session_id or str(uuid.uuid4())[:8],
        "usage": {
            "used": user["used"],
            "quota": user["quota"],
            "remaining": user["quota"] - user["used"]
        }
    }

@app.post("/v1/image/generate")
def generate_image(req: ImageRequest, authorization: str = Header(None)):
    start_time = time.time()
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)
    user["used"] += 1

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
            result = {
                "image_url": image_url,
                "status": "success"
            }
        else:
            status = "error"
            result = {"error": f"图片生成失败: {resp.status_code}"}
    except Exception as e:
        status = "error"
        result = {"error": f"图片生成失败: {str(e)[:50]}"}

    duration = int((time.time() - start_time) * 1000)
    log_call("image_generate", user, status, duration)
    
    return result

@app.post("/v1/video/generate")
def generate_video(req: VideoRequest, authorization: str = Header(None)):
    start_time = time.time()
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)
    user["used"] += 1

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
            task_id = data.get("id")
            status = "success"
            result = {
                "task_id": task_id,
                "status": "processing",
                "message": "视频生成中，请稍后查询任务状态"
            }
        else:
            status = "error"
            result = {"error": f"视频生成失败: {resp.status_code}"}
    except Exception as e:
        status = "error"
        result = {"error": f"视频生成失败: {str(e)[:50]}"}

    duration = int((time.time() - start_time) * 1000)
    log_call("video_generate", user, status, duration)
    
    return result

@app.get("/v1/analytics")
def analytics(authorization: str = Header(None)):
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    if api_key != "huodou-pro-001":
        raise HTTPException(status_code=403, detail="Forbidden")

    total_calls = len(call_logs)
    success_calls = len([c for c in call_logs if c["status"] == "success"])
    error_calls = total_calls - success_calls
    avg_duration = sum([c["duration_ms"] for c in call_logs]) / total_calls if total_calls > 0 else 0

    user_stats = {}
    for key, user in API_KEYS.items():
        user_stats[key] = {
            "name": user["name"],
            "tier": user["tier"],
            "used": user["used"],
            "quota": user["quota"],
            "email": user["email"]
        }

    return {
        "total_calls": total_calls,
        "success_calls": success_calls,
        "error_calls": error_calls,
        "success_rate": round(success_calls / total_calls * 100, 1) if total_calls > 0 else 0,
        "avg_duration_ms": round(avg_duration, 0),
        "total_users": len(API_KEYS),
        "users": user_stats,
        "recent_calls": call_logs[-10:]
    }

@app.get("/v1/status")
def status(authorization: str = Header(None)):
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)
    return {
        "service": "火斗云智元内核API",
        "version": "10.0.0",
        "features": ["register", "chat", "image_generate", "video_generate", "analytics"],
        "user": user["name"],
        "tier": user["tier"],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
