#!/usr/bin/env python3
# ZONGYUAN-ROOT OpenAI 标准协议网关（:9120/v1）
# 聚合上游：云端 doubao / 魔塔 / deapi / Agnes / 润道 / 千帆
# 密钥零明文：var/secrets/api_keys.env（600）启动时读取；上游配置 var/gateway/upstreams.json（600）
# 鉴权：X-API-Key == var/gateway/gateway.key
# 端点：GET /v1/models · POST /v1/chat/completions（含 SSE 流式透传）· GET /healthz
import os, json, re, asyncio
from pathlib import Path
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

ROOT = Path('/home/user/ZONGYUAN-ROOT')
UPSTREAMS = json.load(open(ROOT/'var/gateway/upstreams.json', encoding='utf-8'))['upstreams']
GATEWAY_KEY = (ROOT/'var/gateway/gateway.key').read_text().strip()
if GATEWAY_KEY.startswith('GATEWAY_KEY='):
    GATEWAY_KEY = GATEWAY_KEY.split('=',1)[1].strip()

# 加载密钥环境（600 文件，进程内存，不写日志）
for line in (ROOT/'var/secrets/api_keys.env').read_text().splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())

app = FastAPI(title="ZONGYUAN-ROOT OpenAI Gateway", version="1.0.0")

def check_auth(request: Request):
    key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if key != GATEWAY_KEY:
        raise HTTPException(status_code=401, detail="invalid gateway api key")

def resolve_upstream(model: str):
    for name, u in UPSTREAMS.items():
        if model in u['models'] or model == name or model.startswith(name + '/'):
            return name, u
    # 默认路由：云中枢 doubao
    return 'huodouai-cloud', UPSTREAMS['huodouai-cloud']

@app.get("/healthz")
async def healthz():
    alive = []
    async with httpx.AsyncClient(timeout=5) as c:
        for name, u in UPSTREAMS.items():
            if u['status'] != 'ONLINE':
                alive.append({"upstream": name, "status": u['status']})
                continue
            try:
                r = await c.get(u['base_url'] + '/models',
                                headers={"Authorization": "Bearer " + os.environ.get(u['key_env'], '')})
                alive.append({"upstream": name, "status": "ok" if r.status_code < 500 else f"http_{r.status_code}"})
            except Exception as e:
                alive.append({"upstream": name, "status": "down"})
    return {"gateway": "ok", "upstreams": alive}

@app.get("/v1/models")
async def list_models(request: Request):
    check_auth(request)
    models = []
    for name, u in UPSTREAMS.items():
        for m in u['models']:
            models.append({"id": m, "object": "model", "owned_by": name, "status": u['status']})
    return {"object": "list", "data": models}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    check_auth(request)
    body = await request.json()
    model = body.get('model', 'doubao')
    name, u = resolve_upstream(model)
    if u['status'] != 'ONLINE' or not os.environ.get(u['key_env']):
        raise HTTPException(status_code=503, detail=f"upstream {name} 未就绪（{u['status']}）")
    headers = {"Authorization": "Bearer " + os.environ[u['key_env']], "Content-Type": "application/json"}
    upstream_url = u['base_url'] + '/chat/completions'
    stream = body.get('stream', False)
    async with httpx.AsyncClient(timeout=120) as c:
        if stream:
            req = c.build_request("POST", upstream_url, headers=headers, json=body)
            upstream_resp = await c.send(req, stream=True)
            if upstream_resp.status_code >= 400:
                return JSONResponse(status_code=upstream_resp.status_code, content={"error": {"message": "upstream error", "detail": upstream_resp.status_code}})
            async def sse():
                async for chunk in upstream_resp.aiter_bytes():
                    yield chunk
            return StreamingResponse(sse(), media_type="text/event-stream")
        r = await c.post(upstream_url, headers=headers, json=body)
        if r.status_code >= 400:
            return JSONResponse(status_code=r.status_code, content={"error": {"message": f"upstream {name} error", "detail": r.text[:300]}})
        return JSONResponse(content=r.json())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9120, log_level="warning")
