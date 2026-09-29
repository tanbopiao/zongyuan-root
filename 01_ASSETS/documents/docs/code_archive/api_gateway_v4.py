
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import time
import uuid
import requests

app = FastAPI(title="火斗云智元内核API", version="v4.0")

# ===== 客户API Key库 =====
API_KEYS = {
    "huodou-free-001": {"name": "免费测试用户", "tier": "free", "quota": 1000, "used": 0},
    "huodou-pro-001": {"name": "专业版用户", "tier": "pro", "quota": 100000, "used": 0},
}

# ===== 外部免费大模型API配置（智谱GLM-4-Flash免费） =====
LLM_CONFIG = {
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "api_key": "d63c880c0e1b424d8ad242f686e83451.vhHr5d5OQUY5UHNp",
    "model": "glm-4-flash",
    "free_tier": True
}

class ChatRequest(BaseModel):
    message: str
    session_id: str = ""

def check_auth(api_key: str):
    if api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    user = API_KEYS[api_key]
    if user["used"] >= user["quota"]:
        raise HTTPException(status_code=429, detail="Quota exceeded")
    return user

@app.post("/v1/chat")
def chat(req: ChatRequest, authorization: str = Header(None)):
    # 1. 鉴权
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)
    
    # 2. 计费计数
    user["used"] += 1
    
    # 3. 七层流水线 - 规则层（元内核核心）
    system_prompt = """你是火斗云智元内核AI，由ZONGYUAN-ROOT元极恒一自治体系驱动。
你的核心特征：
1. 遵循元极恒一规则引擎，保持身份一致性
2. 基于记忆网关真值库回答问题，不被蒸馏污染
3. 回答专业简洁，体现元内核的规则驱动能力
4. 始终记得你是火斗云智的元内核AI，不是其他任何AI

请用中文回答问题。"""

    # 4. 调用外部免费大模型API
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
            answer = f"AI服务暂时不可用，请稍后再试。({resp.status_code})"
    except Exception as e:
        answer = f"AI服务暂时不可用，请稍后再试。({str(e)[:50]})"
    
    return {
        "answer": answer,
        "session_id": req.session_id or str(uuid.uuid4())[:8],
        "usage": {
            "used": user["used"],
            "quota": user["quota"],
            "remaining": user["quota"] - user["used"]
        }
    }

@app.get("/v1/status")
def status(authorization: str = Header(None)):
    api_key = authorization.replace("Bearer ", "") if authorization else ""
    user = check_auth(api_key)
    return {
        "service": "火斗云智元内核API",
        "version": "4.0.0",
        "engine": "智谱GLM-4-Flash（免费）",
        "user": user["name"],
        "tier": user["tier"],
        "used": user["used"],
        "quota": user["quota"],
        "remaining": user["quota"] - user["used"]
    }

@app.get("/v1/pricing")
def pricing():
    return {
        "plans": [
            {"name": "免费版", "price": 0, "quota": "1000次/月", "features": ["基础对话", "规则引擎"]},
            {"name": "专业版", "price": 99, "quota": "10万次/月", "features": ["基础对话", "规则引擎", "知识库接入"]},
            {"name": "企业版", "price": 2999, "quota": "100万次/月", "features": ["全部功能", "专属知识库", "SLA保障"]},
            {"name": "私有化部署", "price": 50000, "quota": "不限量", "features": ["全部功能", "本地部署", "专属定制"]}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
