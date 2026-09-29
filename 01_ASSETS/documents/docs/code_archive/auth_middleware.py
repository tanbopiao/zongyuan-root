#!/usr/bin/env python3
"""
ZONGYUAN-ROOT API鉴权中间件 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
功能：Token验证 + 速率限制 + IP白名单 + 审计日志
"""
import time, hashlib, json, os, threading
from collections import defaultdict
from functools import wraps

# 配置
AUTH_CONFIG = {
    "token_header": "X-Capture-Token",
    "token_env": "ZR_API_TOKEN",
    "rate_limit_per_min": 60,
    "rate_limit_burst": 10,
    "ip_whitelist_enabled": False,
    "ip_whitelist": ["127.0.0.1", "::1"],
    "audit_log_path": "/var/log/zr_api_audit.log",
    "token_rotation_days": 90,
}

# 内存状态
_request_log = defaultdict(list)
_lock = threading.Lock()
_valid_tokens = set()

def load_tokens():
    """从环境变量和配置文件加载有效Token"""
    global _valid_tokens
    _valid_tokens.clear()
    env_token = os.environ.get(AUTH_CONFIG["token_env"], "")
    if env_token:
        _valid_tokens.add(env_token)
    token_file = os.environ.get("ZR_TOKEN_FILE", "/etc/zr/tokens.json")
    if os.path.exists(token_file):
        try:
            with open(token_file) as f:
                data = json.load(f)
                for t in data.get("tokens", []):
                    if t.get("active", True):
                        _valid_tokens.add(t["token"])
        except: pass
    return len(_valid_tokens)

def verify_token(token):
    """验证Token有效性"""
    if not token:
        return False, "missing_token"
    if not _valid_tokens:
        load_tokens()
    if token in _valid_tokens:
        return True, "valid"
    # 支持哈希匹配（Token以哈希形式存储）
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    if token_hash in _valid_tokens:
        return True, "valid_hashed"
    return False, "invalid_token"

def check_rate_limit(client_ip):
    """检查速率限制（令牌桶算法）"""
    now = time.time()
    with _lock:
        requests = _request_log[client_ip]
        # 清理1分钟前的记录
        _request_log[client_ip] = [t for t in requests if now - t < 60]
        current = len(_request_log[client_ip])
        if current >= AUTH_CONFIG["rate_limit_per_min"]:
            return False, f"rate_limit_exceeded ({current}/min)"
        _request_log[client_ip].append(now)
    return True, f"ok ({current+1}/min)"

def check_ip_whitelist(client_ip):
    """检查IP白名单"""
    if not AUTH_CONFIG["ip_whitelist_enabled"]:
        return True, "whitelist_disabled"
    if client_ip in AUTH_CONFIG["ip_whitelist"]:
        return True, "whitelisted"
    return False, f"ip_not_whitelisted ({client_ip})"

def audit_log(client_ip, path, method, status, reason=""):
    """审计日志"""
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ip": client_ip, "path": path, "method": method,
        "status": status, "reason": reason
    }
    try:
        with open(AUTH_CONFIG["audit_log_path"], "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except: pass

def require_auth(f):
    """装饰器：要求鉴权的API端点"""
    @wraps(f)
    def decorated(request, *args, **kwargs):
        client_ip = request.client.host if hasattr(request, 'client') else "unknown"
        path = request.url.path if hasattr(request, 'url') else "unknown"
        method = request.method if hasattr(request, 'method') else "UNKNOWN"
        
        # 1. IP白名单
        ip_ok, ip_msg = check_ip_whitelist(client_ip)
        if not ip_ok:
            audit_log(client_ip, path, method, "denied", ip_msg)
            return {"error": "access_denied", "reason": ip_msg}, 403
        
        # 2. Token验证
        token = request.headers.get(AUTH_CONFIG["token_header"], "")
        token_ok, token_msg = verify_token(token)
        if not token_ok:
            audit_log(client_ip, path, method, "denied", token_msg)
            return {"error": "unauthorized", "reason": token_msg}, 401
        
        # 3. 速率限制
        rl_ok, rl_msg = check_rate_limit(client_ip)
        if not rl_ok:
            audit_log(client_ip, path, method, "denied", rl_msg)
            return {"error": "too_many_requests", "reason": rl_msg}, 429
        
        audit_log(client_ip, path, method, "allowed")
        return f(request, *args, **kwargs)
    return decorated

# 纯函数版本（不依赖框架）
def verify_request(headers, client_ip, path, method="POST"):
    """纯函数鉴权验证，返回(allowed, status_code, reason)"""
    ip_ok, ip_msg = check_ip_whitelist(client_ip)
    if not ip_ok:
        audit_log(client_ip, path, method, "denied", ip_msg)
        return False, 403, ip_msg
    token = headers.get(AUTH_CONFIG["token_header"], "")
    token_ok, token_msg = verify_token(token)
    if not token_ok:
        audit_log(client_ip, path, method, "denied", token_msg)
        return False, 401, token_msg
    rl_ok, rl_msg = check_rate_limit(client_ip)
    if not rl_ok:
        audit_log(client_ip, path, method, "denied", rl_msg)
        return False, 429, rl_msg
    audit_log(client_ip, path, method, "allowed")
    return True, 200, "ok"

if __name__ == "__main__":
    load_tokens()
    print(f"ZR API鉴权中间件 V1.0")
    print(f"已加载Token: {len(_valid_tokens)}个")
    print(f"速率限制: {AUTH_CONFIG['rate_limit_per_min']}/分钟")
    print(f"IP白名单: {'启用' if AUTH_CONFIG['ip_whitelist_enabled'] else '禁用'}")
    print(f"DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
