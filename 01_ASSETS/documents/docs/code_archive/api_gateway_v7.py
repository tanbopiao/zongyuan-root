
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import time
import uuid
import requests
import json

app = FastAPI(title="火斗云智元内核API", version="v7.0")

# ===== 客户API Key库 =====
API_KEYS = {
    "huodou-free-001": {"name": "免费测试用户", "tier": "free", "quota": 1000, "used": 0},
    "huodou-pro-001": {"name": "专业版用户", "tier": "pro", "quota": 100000, "used": 0},
}

# ===== 外部API配置 =====
LLM_CONFIG = {
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "api_key": "d63c880c0e1b424d8ad242f686e83451.vhHr5d5OQUY5UHNp",
    "model": "glm-4-flash",
}

VIDEO_CONFIG = {
    "base_url": "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks",
    "api_key": "ark-f7b61c6f-41d2-406f-8c44-a801830e8a55-82e36",
    "model": "ep-20260912023827-d2jc4",
}

class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    stream: bool = False

class VideoRequest(BaseModel):
    prompt: str
    size: str = "768x1344"

def check_auth(api_key: str):
    if api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    user = API_KEYS[api_key]
    if user["used"] >= user["quota"]:
        raise HTTPException(status_code=429, detail="Quota exceeded")
    return user

@app.post("/v1/chat")
def chat(req: ChatRequest, authorization: str = Header(None)):
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

    # 流式响应
    if req.stream:
        def generate():
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
                    stream=True,
                    timeout=30
                )
                
                for line in resp.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.start('data: '):
                            data_str = line_str[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    yield f"data: {json.dumps({'content': content})}\n\n"
                            except:
                                pass
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")

    # 普通响应
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
        else:
            answer = f"AI服务暂时不可用。({resp.status_code})"
    except Exception as e:
        answer = f"AI服务暂时不可用。({str(e)[:50]})"
    
    return {
        "answer": answer,
        "session_id": req.session_id or str(uuid.uuid4())[:8],
        "usage": {
            "used": user["used"],
            "quota": user["quota"],
            "remaining": user["quota"] - user["used"]
        }
    }

@app.post("/v1/video/generate")
def generate_video(req: VideoRequest, authorization: str = Header(None)):
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
            return {
                "task_id": task_id,
                "status": "processing",
                "message": "视频生成中，请稍后查询任务状态"
            }
        else:
            return {"error": f"视频生成失败: {resp.status_code}"}
    except Exception as e:
        return {"error": f"视频生成失败: {str(e)[:50]}"}

@app.get("/v1/video/status/{task_id}")
def video_status(task_id: str, authorization: str = Header(None)):
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)

    try:
        resp = requests.get(
            f"{VIDEO_CONFIG['base_url']}/{task_id}",
            headers={
                "Authorization": f"Bearer {VIDEO_CONFIG['api_key']}",
            },
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            return data
        else:
            return {"error": f"查询失败: {resp.status_code}"}
    except Exception as e:
        return {"error": f"查询失败: {str(e)[:50]}"}

@app.get("/v1/status")
def status(authorization: str = Header(None)):
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)
    return {
        "service": "火斗云智元内核API",
        "version": "7.0.0",
        "features": ["chat", "chat_stream", "video_generate"],
        "user": user["name"],
        "tier": user["tier"],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
