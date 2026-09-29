#!/usr/bin/env python3
"""
安全中间件模块
功能：API速率限制 + 输入校验 + 密码加密
确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import time
import hashlib
import re
import os
import json
from collections import defaultdict

# 速率限制配置
RATE_LIMIT = {
    'default': {'max_requests': 60, 'window': 60},      # 默认：60次/分钟
    'chat': {'max_requests': 20, 'window': 60},          # 聊天：20次/分钟
    'login': {'max_requests': 5, 'window': 300},         # 登录：5次/5分钟
    'api': {'max_requests': 100, 'window': 60},          # 通用API：100次/分钟
}

# 内存中的请求记录（生产环境应使用Redis）
request_log = defaultdict(list)

def get_client_ip(handler):
    """获取客户端IP"""
    return handler.headers.get('X-Forwarded-For', handler.client_address[0]).split(',')[0].strip()

def check_rate_limit(handler, endpoint_type='default'):
    """检查速率限制，返回(allowed, retry_after)"""
    ip = get_client_ip(handler)
    config = RATE_LIMIT.get(endpoint_type, RATE_LIMIT['default'])
    
    now = time.time()
    window_start = now - config['window']
    
    # 清理过期记录
    request_log[ip] = [t for t in request_log[ip] if t > window_start]
    
    # 检查是否超限
    if len(request_log[ip]) >= config['max_requests']:
        oldest = request_log[ip][0]
        retry_after = int(config['window'] - (now - oldest)) + 1
        return False, retry_after
    
    # 记录本次请求
    request_log[ip].append(now)
    return True, 0

def sanitize_input(value, max_length=1000):
    """输入清洗：防XSS/注入"""
    if not isinstance(value, str):
        return str(value)[:max_length]
    
    # 移除潜在危险字符
    value = value[:max_length]
    
    # 防XSS：转义HTML特殊字符
    value = value.replace('<', '&lt;').replace('>', '&gt;')
    value = value.replace('"', '&quot;').replace("'", '&#x27;')
    
    # 防注入：移除SQL注释和命令分隔符
    value = re.sub(r'--.*$', '', value, flags=re.MULTILINE)
    value = value.replace(';', '；').replace('|', '｜')
    
    # 移除控制字符
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
    
    return value

def validate_email(email):
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone):
    """验证手机号格式（中国大陆）"""
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))

def validate_username(username):
    """验证用户名：3-20位字母数字下划线"""
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return bool(re.match(pattern, username))

def hash_password(password, salt=None):
    """密码哈希（PBKDF2）"""
    if salt is None:
        salt = os.urandom(16).hex()
    
    # PBKDF2 with SHA256, 100000 iterations
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 100000)
    return {
        'hash': dk.hex(),
        'salt': salt,
        'iterations': 100000,
        'algorithm': 'PBKDF2-SHA256'
    }

def verify_password(password, stored_hash, salt):
    """验证密码"""
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 100000)
    return dk.hex() == stored_hash

def get_security_headers():
    """获取安全响应头"""
    return {
        'X-Frame-Options': 'SAMEORIGIN',
        'X-Content-Type-Options': 'nosniff',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Strict-Transport-Security': 'max-age=31536000',
        'Content-Security-Policy': "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: data: blob:",
        'X-Permitted-Cross-Domain-Policies': 'none',
        'X-DNS-Prefetch-Control': 'off',
    }

def log_security_event(event_type, ip, details):
    """记录安全事件"""
    log_entry = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'event_type': event_type,
        'ip': ip,
        'details': details
    }
    
    log_dir = '/opt/ZONGYUAN-ROOT/gov_api/data/security'
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'security_events.jsonl')
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    return log_entry

# 初始化
print('安全中间件模块加载完成')
print(f'速率限制配置: {len(RATE_LIMIT)}类端点')
print(f'密码加密: PBKDF2-SHA256, 100000 iterations')
