#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU大脑统一反向代理
把7B大脑(7861)和0.5B模型(7862)统一到8080端口
路径区分：/7b/* -> 7861, /05b/* -> 7862, /* -> 7861(默认)
"""
import requests
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="ZONGYUAN-ROOT GPU Brain Proxy", version="1.0")

UPSTREAM_7B = "http://127.0.0.1:7861"
UPSTREAM_05B = "http://127.0.0.1:7862"

async def proxy_request(upstream: str, path: str, request: Request):
    """反向代理请求"""
    url = f"{upstream}{path}"
    try:
        if request.method == "GET":
            resp = requests.get(url, params=request.query_params, timeout=120)
        elif request.method == "POST":
            body = await request.body()
            resp = requests.post(url, params=request.query_params, data=body, 
                                headers={"Content-Type": request.headers.get("content-type", "application/json")}, 
                                timeout=120)
        else:
            return JSONResponse({"error": f"Method {request.method} not supported"}, status_code=405)
        
        return Response(content=resp.content, status_code=resp.status_code, 
                       media_type=resp.headers.get("content-type", "application/json"))
    except requests.exceptions.Timeout:
        return JSONResponse({"error": "upstream timeout"}, status_code=504)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)

@app.get("/")
async def root():
    return {
        "service": "ZONGYUAN-ROOT GPU Brain Proxy",
        "version": "1.0",
        "endpoints": {
            "7b_brain": "/7b/* -> Qwen2.5-7B-Instruct (port 7861)",
            "05b_model": "/05b/* -> zongyuan-0.5B (port 7862)",
            "default": "/* -> 7B brain"
        }
    }

@app.get("/7b/{path:path}")
async def proxy_7b_get(path: str, request: Request):
    return await proxy_request(UPSTREAM_7B, f"/{path}", request)

@app.post("/7b/{path:path}")
async def proxy_7b_post(path: str, request: Request):
    return await proxy_request(UPSTREAM_7B, f"/{path}", request)

@app.get("/05b/{path:path}")
async def proxy_05b_get(path: str, request: Request):
    return await proxy_request(UPSTREAM_05B, f"/{path}", request)

@app.post("/05b/{path:path}")
async def proxy_05b_post(path: str, request: Request):
    return await proxy_request(UPSTREAM_05B, f"/{path}", request)

# 默认路径走7B
@app.get("/{path:path}")
async def proxy_default_get(path: str, request: Request):
    return await proxy_request(UPSTREAM_7B, f"/{path}", request)

@app.post("/{path:path}")
async def proxy_default_post(path: str, request: Request):
    return await proxy_request(UPSTREAM_7B, f"/{path}", request)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
