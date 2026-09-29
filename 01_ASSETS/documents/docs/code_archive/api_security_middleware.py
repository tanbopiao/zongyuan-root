#!/usr/bin/env python3
"""API安全认证中间件 V1.0 - 记忆网关安全加固"""
import os,time,hashlib,json
from functools import wraps
from collections import defaultdict

# 从环境变量读取API Key（生产环境）
API_KEYS=set(os.environ.get("GATEWAY_API_KEYS","").split(",")) if os.environ.get("GATEWAY_API_KEYS") else set()
RATE_LIMIT=defaultdict(list)
MAX_PER_MINUTE=60

def require_auth(f):
    @wraps(f)
    def decorated(request,*args,**kwargs):
        # 1. API Key认证
        api_key=request.headers.get("X-API-Key","")
        if API_KEYS and api_key not in API_KEYS:
            return json.dumps({"error":"unauthorized","code":401}),401,{"Content-Type":"application/json"}
        # 2. 限流
        client_ip=request.remote_addr if hasattr(request,'remote_addr') else "unknown"
        now=time.time()
        RATE_LIMIT[client_ip]=[t for t in RATE_LIMIT[client_ip] if now-t<60]
        if len(RATE_LIMIT[client_ip])>=MAX_PER_MINUTE:
            return json.dumps({"error":"rate_limited","code":429}),429,{"Content-Type":"application/json"}
        RATE_LIMIT[client_ip].append(now)
        return f(request,*args,**kwargs)
    return decorated

def mask_sensitive(data):
    """敏感数据脱敏"""
    if isinstance(data,dict):
        return {k:mask_sensitive(v) if k not in ['phone','ip','open_id'] else _mask(k,v) for k,v in data.items()}
    if isinstance(data,list):return [mask_sensitive(i) for i in data]
    return data

def _mask(field,value):
    if not isinstance(value,str):return value
    if field=='phone' and len(value)==11:return value[:3]+"****"+value[7:]
    if field=='ip':parts=value.split('.');return '.'.join(parts[:2]+['**','**']) if len(parts)==4 else value
    if field=='open_id':return value[:8]+"****"
    return value

if __name__=="__main__":
    print("API安全认证中间件 V1.0 就绪")
    print(f"已配置API Key: {len(API_KEYS)}个")
    print(f"限流: {MAX_PER_MINUTE}次/分钟")
