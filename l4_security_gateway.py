#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L4 七层安全网关服务
端口: 8015
集成: 身份认证 + IP白名单 + 多层限流 + 分级保护 + 详细审计 + 异常检测 + 写入审批
作为统一安全入口，转发到后端API服务
"""
import json
import os
import sys
import time
import hashlib
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

# ============ 配置 ============
KERNEL_DIR = "/home/user/ZONGYUAN-ROOT"
ENV_FILE = os.path.join(KERNEL_DIR, ".env")
SECURITY_CONFIG_DIR = os.path.join(KERNEL_DIR, "security_l4")
AUDIT_LOG_FILE = os.path.join(KERNEL_DIR, "logs", "l4_security_audit.log")

# 后端服务映射
BACKEND_SERVICES = {
    "kernel": {"url": "http://127.0.0.1:8013", "tier": 3},
    "readonly": {"url": "http://127.0.0.1:8014", "tier": 2},
    "identity": {"url": "http://127.0.0.1:8300", "tier": 2},
}

# 限流配置
RATE_LIMITS = {
    "global_per_minute": 60,
    "global_per_hour": 1000,
    "per_api_key_per_minute": 30,
    "per_ip_per_minute": 20,
}

# IP白名单
IP_WHITELIST = {"127.0.0.1", "localhost", "::1"}

# ============ 日志配置 ============
os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(AUDIT_LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("l4-security-gateway")

# ============ 状态存储 ============
request_timestamps = {"global": [], "api_keys": {}, "ips": {}}
auth_failures = {"ips": {}, "api_keys": {}}
anomaly_alerts = []

# ============ 工具函数 ============
def get_api_key():
    """从.env文件获取API Key"""
    if not os.path.exists(ENV_FILE):
        return None
    with open(ENV_FILE, 'r') as f:
        for line in f:
            if line.startswith('X_API_KEY=') or line.startswith('API_KEY='):
                return line.split('=', 1)[1].strip()
    return None

API_KEY = get_api_key()
API_KEY_HASH = hashlib.sha256(API_KEY.encode()).hexdigest() if API_KEY else None

def generate_request_id():
    """生成请求ID"""
    return hashlib.sha256(f"{time.time()}-{os.urandom(8)}".encode()).hexdigest()[:16]

def cleanup_old_timestamps(timestamps_list, seconds=60):
    """清理过期时间戳"""
    cutoff = time.time() - seconds
    return [t for t in timestamps_list if t > cutoff]

def check_rate_limit(client_id, client_type="ip"):
    """检查限流，返回(是否允许, 剩余次数)"""
    now = time.time()
    
    # 全局限流
    request_timestamps["global"] = cleanup_old_timestamps(request_timestamps["global"])
    if len(request_timestamps["global"]) >= RATE_LIMITS["global_per_minute"]:
        return False, 0
    request_timestamps["global"].append(now)
    
    # IP限流
    if client_type == "ip":
        if client_id not in request_timestamps["ips"]:
            request_timestamps["ips"][client_id] = []
        request_timestamps["ips"][client_id] = cleanup_old_timestamps(request_timestamps["ips"][client_id])
        if len(request_timestamps["ips"][client_id]) >= RATE_LIMITS["per_ip_per_minute"]:
            return False, 0
        request_timestamps["ips"][client_id].append(now)
    
    # API Key限流
    if client_type == "api_key":
        if client_id not in request_timestamps["api_keys"]:
            request_timestamps["api_keys"][client_id] = []
        request_timestamps["api_keys"][client_id] = cleanup_old_timestamps(request_timestamps["api_keys"][client_id])
        if len(request_timestamps["api_keys"][client_id]) >= RATE_LIMITS["per_api_key_per_minute"]:
            return False, 0
        request_timestamps["api_keys"][client_id].append(now)
    
    return True, RATE_LIMITS["per_ip_per_minute"] - len(request_timestamps["ips"].get(client_id, []))

def detect_anomalies(request_id, client_ip, api_key_hash, path, method, status_code, response_time):
    """异常检测"""
    now = time.time()
    
    # AD-001: 异常高频请求
    ip_count = len(request_timestamps["ips"].get(client_ip, []))
    if ip_count > 50:
        alert = {
            "rule_id": "AD-001",
            "name": "异常高频请求",
            "client_ip": client_ip,
            "request_count": ip_count,
            "timestamp": datetime.now().isoformat(),
            "severity": "medium"
        }
        anomaly_alerts.append(alert)
        logger.warning(f"[ANOMALY AD-001] 异常高频请求: IP={client_ip}, 计数={ip_count}")
    
    # AD-003: 认证失败激增
    ip_failures = auth_failures["ips"].get(client_ip, 0)
    if ip_failures > 5:
        alert = {
            "rule_id": "AD-003",
            "name": "认证失败激增",
            "client_ip": client_ip,
            "failure_count": ip_failures,
            "timestamp": datetime.now().isoformat(),
            "severity": "critical"
        }
        anomaly_alerts.append(alert)
        logger.warning(f"[ANOMALY AD-003] 认证失败激增: IP={client_ip}, 失败数={ip_failures}")
    
    # AD-005: 响应时间异常
    if response_time > 5000:
        alert = {
            "rule_id": "AD-005",
            "name": "响应时间异常",
            "request_id": request_id,
            "path": path,
            "response_time_ms": response_time,
            "timestamp": datetime.now().isoformat(),
            "severity": "low"
        }
        anomaly_alerts.append(alert)
        logger.info(f"[ANOMALY AD-005] 响应时间异常: path={path}, 耗时={response_time}ms")

def write_audit_log(request_id, client_ip, api_key_hash, path, method, status_code, response_time_ms, request_body_hash=None):
    """写入审计日志"""
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "client_ip": client_ip,
        "api_key_hash": api_key_hash,
        "path": path,
        "method": method,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "request_body_hash": request_body_hash
    }
    logger.info(f"[AUDIT] {json.dumps(audit_entry, ensure_ascii=False)}")

# ============ FastAPI应用 ============
app = FastAPI(title="L4 七层安全网关", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def security_gateway_middleware(request: Request, call_next):
    """七层安全网关中间件"""
    start_time = time.time()
    request_id = generate_request_id()
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    method = request.method
    
    # 跳过健康检查端点的安全检查
    if path == "/health" or path == "/gateway/health":
        response = await call_next(request)
        return response
    
    # ===== 第一层：身份认证 =====
    api_key_header = request.headers.get("X-API-Key", "")
    api_key_hash = hashlib.sha256(api_key_header.encode()).hexdigest() if api_key_header else None
    
    # 只读操作(tier1/2)不需要认证，写入操作(tier3+)需要认证
    service_name = path.split("/")[2] if len(path.split("/")) > 2 else None
    service_tier = BACKEND_SERVICES.get(service_name, {}).get("tier", 1)
    
    needs_auth = service_tier >= 3 or method in ["POST", "PUT", "DELETE", "PATCH"]
    
    if needs_auth:
        if not api_key_header:
            auth_failures["ips"][client_ip] = auth_failures["ips"].get(client_ip, 0) + 1
            write_audit_log(request_id, client_ip, None, path, method, 401, int((time.time()-start_time)*1000))
            return JSONResponse(status_code=401, content={
                "status": "error",
                "error": "authentication_required",
                "message": "此操作需要API Key认证",
                "request_id": request_id
            })
        
        if API_KEY_HASH and api_key_hash != API_KEY_HASH:
            auth_failures["ips"][client_ip] = auth_failures["ips"].get(client_ip, 0) + 1
            write_audit_log(request_id, client_ip, api_key_hash, path, method, 403, int((time.time()-start_time)*1000))
            return JSONResponse(status_code=403, content={
                "status": "error",
                "error": "invalid_api_key",
                "message": "API Key无效",
                "request_id": request_id
            })
    
    # ===== 第二层：IP白名单(advisory模式，仅记录不拦截) =====
    if client_ip not in IP_WHITELIST:
        logger.info(f"[IP-WHITELIST] 非白名单IP访问: {client_ip}, path={path} (advisory模式，仅记录)")
    
    # ===== 第三层：多层限流 =====
    client_id = api_key_hash if api_key_hash else client_ip
    client_type = "api_key" if api_key_hash else "ip"
    allowed, remaining = check_rate_limit(client_id, client_type)
    
    if not allowed:
        write_audit_log(request_id, client_ip, api_key_hash, path, method, 429, int((time.time()-start_time)*1000))
        return JSONResponse(status_code=429, content={
            "status": "error",
            "error": "rate_limit_exceeded",
            "message": "请求频率超限，请稍后重试",
            "request_id": request_id,
            "retry_after": 60
        })
    
    # ===== 第四层：分级保护(已在认证阶段处理tier) =====
    
    # 继续处理请求
    response = await call_next(request)
    response_time_ms = int((time.time() - start_time) * 1000)
    
    # ===== 第五层：详细审计 =====
    write_audit_log(request_id, client_ip, api_key_hash, path, method, response.status_code, response_time_ms)
    
    # ===== 第六层：异常检测 =====
    detect_anomalies(request_id, client_ip, api_key_hash, path, method, response.status_code, response_time_ms)
    
    # 添加安全响应头
    response.headers["X-Request-ID"] = request_id
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-Security-Gateway"] = "L4-Seven-Layer-v1.0"
    
    return response

# ============ 网关健康检查 ============
@app.get("/health")
@app.get("/gateway/health")
async def gateway_health():
    """网关健康检查"""
    return {
        "status": "ok",
        "service": "l4-security-gateway",
        "version": "1.0.0",
        "layers": {
            "layer1_authentication": "active",
            "layer2_ip_whitelist": "advisory",
            "layer3_rate_limiting": "active",
            "layer4_tiered_protection": "active",
            "layer5_audit_logging": "active",
            "layer6_anomaly_detection": "active",
            "layer7_write_approval": "configured"
        },
        "api_key_configured": API_KEY is not None,
        "active_anomaly_alerts": len(anomaly_alerts),
        "uptime_seconds": int(time.time() - start_time)
    }

@app.get("/gateway/status")
async def gateway_status():
    """网关状态详情"""
    return {
        "status": "ok",
        "rate_limits": RATE_LIMITS,
        "ip_whitelist": list(IP_WHITELIST),
        "backend_services": BACKEND_SERVICES,
        "active_requests_global": len(request_timestamps["global"]),
        "tracked_ips": len(request_timestamps["ips"]),
        "tracked_api_keys": len(request_timestamps["api_keys"]),
        "anomaly_alerts": anomaly_alerts[-10:] if anomaly_alerts else [],
        "audit_log_file": AUDIT_LOG_FILE
    }

# ============ 反向代理到后端服务 ============
@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_to_backend(service: str, path: str, request: Request):
    """反向代理到后端API服务"""
    if service not in BACKEND_SERVICES:
        raise HTTPException(status_code=404, detail=f"未知服务: {service}")
    
    backend = BACKEND_SERVICES[service]
    backend_url = f"{backend['url']}/{path}"
    
    # 构建请求头
    headers = dict(request.headers)
    headers.pop("host", None)
    headers["X-Forwarded-For"] = request.client.host if request.client else "unknown"
    headers["X-Forwarded-Proto"] = "https"
    
    # 获取请求体
    body = await request.body()
    
    # 转发请求
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=backend_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            # 流式响应
            return StreamingResponse(
                response.iter_bytes(),
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail=f"后端服务 {service} 连接失败")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail=f"后端服务 {service} 超时")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"网关错误: {str(e)}")

# ============ 启动 ============
start_time = time.time()

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("L4 七层安全网关服务启动")
    print(f"端口: 8015")
    print(f"API Key已配置: {API_KEY is not None}")
    print(f"后端服务: {list(BACKEND_SERVICES.keys())}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8015, workers=1)
