#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 统一API网关 V3.0 - 用户注册系统版
- 用户系统（注册/登录/JWT认证/密码哈希）
- 用户API Key管理（创建/列表/吊销/轮换）
- 用户用量统计
- API Key管理（生成/列表/吊销/权限控制/层级管理）
- 层级化算力调度（free/basic/pro/enterprise四级）
- 模型白名单（按层级限制可用模型）
- 差异化限流（按层级不同QPS和日配额）
- Token计量和用量统计
- 优先级调度和自动降级
- OpenAI兼容接口（/v1/chat/completions, /v1/models）
- 内核能力API路由（转发到Anchor/身份API/aiproxy）
- 统一认证（X-API-Key或Bearer Token）
"""

import json
import os
import hashlib
import time
import uuid
import threading
import base64
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ============ 配置 ============
PORT = 8040
BASE_DIR = '/opt/ZONGYUAN-ROOT/api_gateway'
os.makedirs(BASE_DIR, exist_ok=True)

API_KEYS_FILE = os.path.join(BASE_DIR, 'api_keys.json')
USERS_FILE = os.path.join(BASE_DIR, 'users.json')
STATS_FILE = os.path.join(BASE_DIR, 'stats.json')
USAGE_FILE = os.path.join(BASE_DIR, 'usage.json')
LOG_FILE = os.path.join(BASE_DIR, 'gateway.log')

# 上游服务地址
AIPROXY_URL = 'http://127.0.0.1:8021'
ANCHOR_URL = 'http://127.0.0.1:8006'
IDENTITY_URL = 'http://127.0.0.1:8030'

# JWT 配置
JWT_SECRET = 'ZONGYUAN-ROOT-JWT-SECRET-2026'
JWT_EXPIRE_HOURS = 24

# 注册配置
REGISTER_DEFAULT_TIER = 'free'  # 注册默认层级
REGISTER_MAX_KEYS_PER_USER = 3  # 每个用户最多创建的Key数量
REGISTER_IP_LIMIT_PER_HOUR = 5  # 同一IP每小时最多注册数
LOGIN_FAIL_LIMIT = 5  # 连续登录失败次数
LOGIN_LOCK_MINUTES = 15  # 登录锁定时间（分钟）

# ============ 层级化配置 ============
TIER_CONFIG = {
    'free': {
        'name': '免费层',
        'description': '体验测试用，仅免费模型',
        'rate_limit_per_minute': 10,
        'rate_limit_per_hour': 100,
        'daily_quota': 10000,
        'priority': 1,
        'allowed_models': ['zhipu', 'agnes', 'ollama-local', 'ollama-win'],
        'max_tokens': 1024,
        'features': ['basic_chat']
    },
    'basic': {
        'name': '基础层',
        'description': '个人使用，免费+基础模型',
        'rate_limit_per_minute': 30,
        'rate_limit_per_hour': 500,
        'daily_quota': 100000,
        'priority': 2,
        'allowed_models': ['zhipu', 'agnes', 'ollama-local', 'ollama-win',
                           'doubao', 'hunyuan', 'kimi'],
        'max_tokens': 2048,
        'features': ['basic_chat', 'streaming']
    },
    'pro': {
        'name': '专业层',
        'description': '专业开发，全部模型',
        'rate_limit_per_minute': 60,
        'rate_limit_per_hour': 2000,
        'daily_quota': 1000000,
        'priority': 3,
        'allowed_models': ['zhipu', 'agnes', 'ollama-local', 'ollama-win',
                           'doubao', 'hunyuan', 'kimi',
                           'doubao-reasoning', 'doubao-reasoning2',
                           'siliconflow', 'aliyun'],
        'max_tokens': 4096,
        'features': ['basic_chat', 'streaming', 'reasoning', 'kernel_api']
    },
    'enterprise': {
        'name': '企业层',
        'description': '企业商用，全部模型+专属通道',
        'rate_limit_per_minute': 200,
        'rate_limit_per_hour': 10000,
        'daily_quota': -1,
        'priority': 4,
        'allowed_models': ['zhipu', 'agnes', 'ollama-local', 'ollama-win',
                           'doubao', 'hunyuan', 'kimi',
                           'doubao-reasoning', 'doubao-reasoning2',
                           'siliconflow', 'aliyun'],
        'max_tokens': 8192,
        'features': ['basic_chat', 'streaming', 'reasoning', 'kernel_api',
                    'priority_scheduling', 'dedicated_channel', 'sla']
    }
}

# 模型降级映射
MODEL_FALLBACK = {
    'doubao': ['hunyuan', 'kimi', 'zhipu'],
    'doubao-reasoning': ['doubao', 'hunyuan', 'kimi'],
    'doubao-reasoning2': ['doubao-reasoning', 'doubao', 'hunyuan'],
    'hunyuan': ['doubao', 'kimi', 'zhipu'],
    'kimi': ['doubao', 'hunyuan', 'zhipu'],
    'zhipu': ['agnes', 'ollama-local'],
    'siliconflow': ['doubao', 'hunyuan', 'kimi'],
    'aliyun': ['doubao', 'hunyuan', 'kimi'],
    'agnes': ['zhipu', 'ollama-local'],
    'ollama-local': ['ollama-win', 'zhipu'],
    'ollama-win': ['ollama-local', 'zhipu']
}

# 内置管理员API Key
ADMIN_API_KEY = 'zy-admin-' + hashlib.sha256(b'ZONGYUAN-ROOT-ADMIN-2026').hexdigest()[:32]

# ============ 工具函数 ============
def log(message):
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {message}\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    print(log_entry.strip())

def load_json(filepath, default=None):
    if default is None:
        default = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_api_key():
    return 'zy-' + uuid.uuid4().hex + uuid.uuid4().hex[:16]

def hash_api_key(api_key):
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()

def get_today_str():
    return datetime.now().strftime('%Y-%m-%d')

def estimate_tokens(text):
    if not text:
        return 0
    return max(1, int(len(text) * 0.75))

# ============ JWT 工具 ============
def create_jwt(user_id, username, tier='free'):
    """创建JWT Token"""
    header = {'alg': 'HS256', 'typ': 'JWT'}
    payload = {
        'user_id': user_id,
        'username': username,
        'tier': tier,
        'iat': int(time.time()),
        'exp': int(time.time()) + JWT_EXPIRE_HOURS * 3600
    }
    
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b'=').decode()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=').decode()
    
    signature = hashlib.sha256(f"{header_b64}.{payload_b64}.{JWT_SECRET}".encode()).hexdigest()
    
    return f"{header_b64}.{payload_b64}.{signature}"

def verify_jwt(token):
    """验证JWT Token，返回payload或None"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        header_b64, payload_b64, signature = parts
        
        # 验证签名
        expected_signature = hashlib.sha256(f"{header_b64}.{payload_b64}.{JWT_SECRET}".encode()).hexdigest()
        if signature != expected_signature:
            return None
        
        # 解码payload
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        
        # 检查过期
        if payload.get('exp', 0) < time.time():
            return None
        
        return payload
    except:
        return None

# ============ 用户系统 ============
def init_users():
    """初始化用户存储"""
    users = load_json(USERS_FILE, {'users': [], 'register_log': [], 'login_attempts': {}})
    if 'users' not in users:
        users['users'] = []
    if 'register_log' not in users:
        users['register_log'] = []
    if 'login_attempts' not in users:
        users['login_attempts'] = {}
    save_json(USERS_FILE, users)
    return users

def hash_password(password, salt=None):
    """密码哈希（SHA256 + 盐）"""
    if salt is None:
        salt = uuid.uuid4().hex
    password_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return password_hash, salt

def verify_password(password, salt, password_hash):
    """验证密码"""
    expected_hash, _ = hash_password(password, salt)
    return expected_hash == password_hash

def check_password_strength(password):
    """检查密码强度，返回(valid, message)"""
    if len(password) < 8:
        return False, '密码长度至少8位'
    if not any(c.isalpha() for c in password):
        return False, '密码必须包含字母'
    if not any(c.isdigit() for c in password):
        return False, '密码必须包含数字'
    return True, '密码强度合格'

def check_register_ip_limit(ip):
    """检查注册IP限流，返回(allowed, remaining)"""
    users = load_json(USERS_FILE, {'users': [], 'register_log': []})
    now = time.time()
    one_hour_ago = now - 3600
    
    # 清理过期记录
    users['register_log'] = [r for r in users.get('register_log', []) if r.get('timestamp', 0) > one_hour_ago]
    
    # 统计该IP注册数
    ip_count = sum(1 for r in users['register_log'] if r.get('ip') == ip)
    
    save_json(USERS_FILE, users)
    
    allowed = ip_count < REGISTER_IP_LIMIT_PER_HOUR
    remaining = REGISTER_IP_LIMIT_PER_HOUR - ip_count
    return allowed, remaining

def register_user(username, password, email=None, ip='unknown'):
    """用户注册，返回(success, message, user_data)"""
    # 检查用户名
    if not username or len(username) < 3 or len(username) > 32:
        return False, '用户名长度必须在3-32位之间', None
    
    # 检查用户名格式（只允许字母数字下划线）
    if not username.replace('_', '').isalnum():
        return False, '用户名只能包含字母、数字和下划线', None
    
    # 检查密码强度
    valid, msg = check_password_strength(password)
    if not valid:
        return False, msg, None
    
    # 检查IP限流
    allowed, remaining = check_register_ip_limit(ip)
    if not allowed:
        return False, f'该IP注册过于频繁，请稍后再试（每小时最多{REGISTER_IP_LIMIT_PER_HOUR}次）', None
    
    # 检查用户名是否已存在
    users = load_json(USERS_FILE, {'users': [], 'register_log': []})
    for user in users.get('users', []):
        if user.get('username') == username:
            return False, '用户名已存在', None
    
    # 检查邮箱是否已存在
    if email:
        for user in users.get('users', []):
            if user.get('email') == email:
                return False, '邮箱已被注册', None
    
    # 创建用户
    password_hash, salt = hash_password(password)
    user_id = 'user_' + uuid.uuid4().hex[:12]
    
    user_data = {
        'user_id': user_id,
        'username': username,
        'email': email,
        'password_hash': password_hash,
        'salt': salt,
        'tier': REGISTER_DEFAULT_TIER,
        'status': 'active',
        'created_at': datetime.now().isoformat(),
        'last_login': None,
        'api_key_count': 0,
        'total_requests': 0,
        'total_tokens': 0,
        'register_ip': ip
    }
    
    users['users'].append(user_data)
    users['register_log'].append({
        'ip': ip,
        'username': username,
        'user_id': user_id,
        'timestamp': time.time()
    })
    save_json(USERS_FILE, users)
    
    log(f"用户注册成功: {username} ({user_id}) - IP: {ip}")
    
    # 返回用户信息（不含密码哈希和盐）
    safe_user = {k: v for k, v in user_data.items() if k not in ['password_hash', 'salt']}
    return True, '注册成功', safe_user

def login_user(username, password, ip='unknown'):
    """用户登录，返回(success, message, token, user_data)"""
    users = load_json(USERS_FILE, {'users': [], 'login_attempts': {}})
    
    # 检查登录锁定
    login_attempts = users.get('login_attempts', {})
    user_attempts = login_attempts.get(username, {'fail_count': 0, 'lock_until': 0})
    
    if user_attempts.get('lock_until', 0) > time.time():
        lock_remaining = int(user_attempts['lock_until'] - time.time())
        return False, f'账号已锁定，请{lock_remaining}秒后再试', None, None
    
    # 查找用户
    user = None
    for u in users.get('users', []):
        if u.get('username') == username or u.get('email') == username:
            user = u
            break
    
    if not user:
        # 记录失败
        user_attempts['fail_count'] = user_attempts.get('fail_count', 0) + 1
        if user_attempts['fail_count'] >= LOGIN_FAIL_LIMIT:
            user_attempts['lock_until'] = time.time() + LOGIN_LOCK_MINUTES * 60
            user_attempts['fail_count'] = 0
        login_attempts[username] = user_attempts
        users['login_attempts'] = login_attempts
        save_json(USERS_FILE, users)
        return False, '用户名或密码错误', None, None
    
    # 检查用户状态
    if user.get('status') != 'active':
        return False, '账号已被禁用，请联系管理员', None, None
    
    # 验证密码
    if not verify_password(password, user.get('salt', ''), user.get('password_hash', '')):
        user_attempts['fail_count'] = user_attempts.get('fail_count', 0) + 1
        if user_attempts['fail_count'] >= LOGIN_FAIL_LIMIT:
            user_attempts['lock_until'] = time.time() + LOGIN_LOCK_MINUTES * 60
            user_attempts['fail_count'] = 0
        login_attempts[username] = user_attempts
        users['login_attempts'] = login_attempts
        save_json(USERS_FILE, users)
        return False, '用户名或密码错误', None, None
    
    # 登录成功，清除失败记录
    if username in login_attempts:
        del login_attempts[username]
        users['login_attempts'] = login_attempts
    
    # 更新最后登录时间
    user['last_login'] = datetime.now().isoformat()
    user['last_login_ip'] = ip
    save_json(USERS_FILE, users)
    
    # 生成JWT
    token = create_jwt(user['user_id'], user['username'], user.get('tier', 'free'))
    
    log(f"用户登录成功: {username} ({user['user_id']}) - IP: {ip}")
    
    safe_user = {k: v for k, v in user.items() if k not in ['password_hash', 'salt']}
    return True, '登录成功', token, safe_user

def get_user_by_id(user_id):
    """根据用户ID获取用户信息"""
    users = load_json(USERS_FILE, {'users': []})
    for user in users.get('users', []):
        if user.get('user_id') == user_id:
            return user
    return None

def update_user_usage(user_id, tokens=0):
    """更新用户使用统计"""
    users = load_json(USERS_FILE, {'users': []})
    for user in users.get('users', []):
        if user.get('user_id') == user_id:
            user['total_requests'] = user.get('total_requests', 0) + 1
            user['total_tokens'] = user.get('total_tokens', 0) + tokens
            save_json(USERS_FILE, users)
            return
    return

def get_user_api_keys(user_id):
    """获取用户的所有API Key"""
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    user_keys = []
    for key_info in keys.get('keys', []):
        if key_info.get('user_id') == user_id:
            user_keys.append({
                'key_id': key_info['key_id'],
                'name': key_info['name'],
                'permissions': key_info['permissions'],
                'tier': key_info.get('tier', 'free'),
                'tier_name': TIER_CONFIG.get(key_info.get('tier', 'free'), {}).get('name', '未知'),
                'status': key_info['status'],
                'created_at': key_info['created_at'],
                'last_used_at': key_info.get('last_used_at'),
                'usage_count': key_info.get('usage_count', 0),
                'total_tokens': key_info.get('total_tokens', 0)
            })
    return user_keys

def create_user_api_key(user_id, name, permissions=None, tier=None):
    """用户创建API Key"""
    user = get_user_by_id(user_id)
    if not user:
        return False, '用户不存在', None
    
    # 检查Key数量限制
    user_keys = get_user_api_keys(user_id)
    active_keys = [k for k in user_keys if k['status'] == 'active']
    if len(active_keys) >= REGISTER_MAX_KEYS_PER_USER:
        return False, f'每个用户最多创建{REGISTER_MAX_KEYS_PER_USER}个API Key', None
    
    if permissions is None:
        permissions = ['chat', 'models']
    
    # 用户创建的Key使用用户的层级
    if tier is None:
        tier = user.get('tier', 'free')
    
    # 验证层级有效性（用户不能创建超过自己层级的Key）
    user_tier_priority = TIER_CONFIG.get(user.get('tier', 'free'), {}).get('priority', 1)
    requested_tier_priority = TIER_CONFIG.get(tier, {}).get('priority', 1)
    if requested_tier_priority > user_tier_priority:
        tier = user.get('tier', 'free')
    
    api_key = generate_api_key()
    key_info = {
        'key_id': 'key_' + uuid.uuid4().hex[:8],
        'key_hash': hash_api_key(api_key),
        'name': name,
        'permissions': permissions,
        'tier': tier,
        'status': 'active',
        'created_at': datetime.now().isoformat(),
        'created_by': 'user',
        'user_id': user_id,
        'expires_at': None,
        'last_used_at': None,
        'usage_count': 0,
        'total_tokens': 0,
        'daily_usage': {}
    }
    
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    keys['keys'].append(key_info)
    save_json(API_KEYS_FILE, keys)
    
    # 更新用户Key计数
    users = load_json(USERS_FILE, {'users': []})
    for u in users.get('users', []):
        if u.get('user_id') == user_id:
            u['api_key_count'] = u.get('api_key_count', 0) + 1
            save_json(USERS_FILE, users)
            break
    
    log(f"用户创建API Key: {key_info['key_id']} ({name}) - 用户: {user_id} - 层级: {tier}")
    return True, '创建成功', api_key

def revoke_user_api_key(user_id, key_id):
    """用户吊销自己的API Key"""
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    for key_info in keys.get('keys', []):
        if key_info['key_id'] == key_id and key_info.get('user_id') == user_id:
            key_info['status'] = 'revoked'
            key_info['revoked_at'] = datetime.now().isoformat()
            save_json(API_KEYS_FILE, keys)
            
            # 更新用户Key计数
            users = load_json(USERS_FILE, {'users': []})
            for u in users.get('users', []):
                if u.get('user_id') == user_id:
                    u['api_key_count'] = max(0, u.get('api_key_count', 0) - 1)
                    save_json(USERS_FILE, users)
                    break
            
            log(f"用户吊销API Key: {key_id} - 用户: {user_id}")
            return True, '吊销成功'
    return False, 'API Key不存在或无权操作'

def get_user_usage(user_id):
    """获取用户用量统计"""
    user = get_user_by_id(user_id)
    if not user:
        return None
    
    user_keys = get_user_api_keys(user_id)
    
    # 按模型统计
    by_model = {}
    total_requests = 0
    total_tokens = 0
    
    keys = load_json(API_KEYS_FILE, {'keys': []})
    for key_info in keys.get('keys', []):
        if key_info.get('user_id') == user_id:
            total_requests += key_info.get('usage_count', 0)
            total_tokens += key_info.get('total_tokens', 0)
    
    return {
        'user_id': user_id,
        'username': user.get('username'),
        'tier': user.get('tier', 'free'),
        'tier_name': TIER_CONFIG.get(user.get('tier', 'free'), {}).get('name', '未知'),
        'total_requests': total_requests,
        'total_tokens': total_tokens,
        'api_key_count': len(user_keys),
        'active_key_count': len([k for k in user_keys if k['status'] == 'active']),
        'daily_quota': TIER_CONFIG.get(user.get('tier', 'free'), {}).get('daily_quota', -1),
        'created_at': user.get('created_at'),
        'last_login': user.get('last_login')
    }

# ============ API Key管理 ============
def init_api_keys():
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    if not keys.get('admin_key_hash'):
        keys['admin_key_hash'] = hash_api_key(ADMIN_API_KEY)
        keys['admin_key_created_at'] = datetime.now().isoformat()
        save_json(API_KEYS_FILE, keys)
        log(f"管理员API Key已创建: {ADMIN_API_KEY}")
    return keys

def verify_api_key(api_key):
    if not api_key:
        return None
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    
    if hash_api_key(api_key) == keys.get('admin_key_hash'):
        return {
            'key_id': 'admin',
            'name': 'Administrator',
            'permissions': ['*'],
            'tier': 'enterprise',
            'is_admin': True,
            'created_at': keys.get('admin_key_created_at', '')
        }
    
    key_hash = hash_api_key(api_key)
    for key_info in keys.get('keys', []):
        if key_info.get('key_hash') == key_hash:
            if key_info.get('status') == 'active':
                return key_info
            else:
                return None
    return None

def create_api_key(name, permissions=None, expires_at=None, tier='basic', created_by='admin', user_id=None):
    if permissions is None:
        permissions = ['chat', 'models']
    
    if tier not in TIER_CONFIG:
        tier = 'basic'
    
    api_key = generate_api_key()
    key_info = {
        'key_id': 'key_' + uuid.uuid4().hex[:8],
        'key_hash': hash_api_key(api_key),
        'name': name,
        'permissions': permissions,
        'tier': tier,
        'status': 'active',
        'created_at': datetime.now().isoformat(),
        'created_by': created_by,
        'user_id': user_id,
        'expires_at': expires_at,
        'last_used_at': None,
        'usage_count': 0,
        'total_tokens': 0,
        'daily_usage': {}
    }
    
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    keys['keys'].append(key_info)
    save_json(API_KEYS_FILE, keys)
    
    log(f"API Key已创建: {key_info['key_id']} ({name}) - 层级: {tier}")
    return api_key, key_info

def list_api_keys():
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    result = []
    for key_info in keys.get('keys', []):
        result.append({
            'key_id': key_info['key_id'],
            'name': key_info['name'],
            'permissions': key_info['permissions'],
            'tier': key_info.get('tier', 'basic'),
            'tier_name': TIER_CONFIG.get(key_info.get('tier', 'basic'), {}).get('name', '未知'),
            'status': key_info['status'],
            'created_at': key_info['created_at'],
            'created_by': key_info.get('created_by', 'admin'),
            'user_id': key_info.get('user_id'),
            'expires_at': key_info.get('expires_at'),
            'last_used_at': key_info.get('last_used_at'),
            'usage_count': key_info.get('usage_count', 0),
            'total_tokens': key_info.get('total_tokens', 0)
        })
    return result

def revoke_api_key(key_id):
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    for key_info in keys.get('keys', []):
        if key_info['key_id'] == key_id:
            key_info['status'] = 'revoked'
            key_info['revoked_at'] = datetime.now().isoformat()
            save_json(API_KEYS_FILE, keys)
            log(f"API Key已吊销: {key_id}")
            return True
    return False

def update_api_key_usage(key_id, tokens=0):
    if key_id == 'admin':
        return
    
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    today = get_today_str()
    
    for key_info in keys.get('keys', []):
        if key_info['key_id'] == key_id:
            key_info['usage_count'] = key_info.get('usage_count', 0) + 1
            key_info['total_tokens'] = key_info.get('total_tokens', 0) + tokens
            key_info['last_used_at'] = datetime.now().isoformat()
            
            if today not in key_info.get('daily_usage', {}):
                key_info['daily_usage'] = key_info.get('daily_usage', {})
                key_info['daily_usage'][today] = {'requests': 0, 'tokens': 0}
            key_info['daily_usage'][today]['requests'] += 1
            key_info['daily_usage'][today]['tokens'] += tokens
            
            if len(key_info['daily_usage']) > 30:
                sorted_dates = sorted(key_info['daily_usage'].keys())
                for old_date in sorted_dates[:-30]:
                    del key_info['daily_usage'][old_date]
            
            save_json(API_KEYS_FILE, keys)
            
            # 同步更新用户用量
            user_id = key_info.get('user_id')
            if user_id:
                update_user_usage(user_id, tokens)
            return

def check_daily_quota(key_info):
    tier = key_info.get('tier', 'basic')
    config = TIER_CONFIG.get(tier, TIER_CONFIG['basic'])
    daily_quota = config.get('daily_quota', -1)
    
    if daily_quota == -1:
        return True, -1
    
    today = get_today_str()
    daily_usage = key_info.get('daily_usage', {}).get(today, {'tokens': 0})
    used_tokens = daily_usage.get('tokens', 0)
    remaining = daily_quota - used_tokens
    
    return remaining > 0, remaining

def check_model_allowed(key_info, model):
    if key_info.get('is_admin'):
        return True
    
    tier = key_info.get('tier', 'basic')
    config = TIER_CONFIG.get(tier, TIER_CONFIG['basic'])
    allowed_models = config.get('allowed_models', [])
    
    return model in allowed_models

def get_fallback_model(model, key_info):
    if key_info.get('is_admin'):
        fallbacks = MODEL_FALLBACK.get(model, [])
        return fallbacks[0] if fallbacks else model
    
    tier = key_info.get('tier', 'basic')
    config = TIER_CONFIG.get(tier, TIER_CONFIG['basic'])
    allowed_models = config.get('allowed_models', [])
    
    fallbacks = MODEL_FALLBACK.get(model, [])
    for fallback in fallbacks:
        if fallback in allowed_models:
            return fallback
    
    return None

# ============ 层级化限流 ============
rate_limit_store = {}
rate_lock = threading.Lock()

def check_rate_limit(key_hash, tier='basic'):
    config = TIER_CONFIG.get(tier, TIER_CONFIG['basic'])
    per_minute = config.get('rate_limit_per_minute', 60)
    per_hour = config.get('rate_limit_per_hour', 1000)
    
    now = time.time()
    with rate_lock:
        if key_hash not in rate_limit_store:
            rate_limit_store[key_hash] = {'minute': [], 'hour': []}
        
        store = rate_limit_store[key_hash]
        store['minute'] = [t for t in store['minute'] if now - t < 60]
        store['hour'] = [t for t in store['hour'] if now - t < 3600]
        
        if len(store['minute']) >= per_minute:
            retry_after = 60 - (now - store['minute'][0])
            return False, retry_after
        
        if len(store['hour']) >= per_hour:
            retry_after = 3600 - (now - store['hour'][0])
            return False, retry_after
        
        store['minute'].append(now)
        store['hour'].append(now)
        
        return True, 0

# ============ 用量统计 ============
def record_usage(model, tokens, key_id=None, user_id=None):
    usage = load_json(USAGE_FILE, {'total_requests': 0, 'total_tokens': 0, 'by_model': {}, 'by_date': {}})
    today = get_today_str()
    
    # 确保键存在
    if 'total_requests' not in usage:
        usage['total_requests'] = 0
    if 'total_tokens' not in usage:
        usage['total_tokens'] = 0
    if 'by_model' not in usage:
        usage['by_model'] = {}
    if 'by_date' not in usage:
        usage['by_date'] = {}
    
    usage['total_requests'] += 1
    usage['total_tokens'] += tokens
    
    if model not in usage['by_model']:
        usage['by_model'][model] = {'requests': 0, 'tokens': 0}
    usage['by_model'][model]['requests'] += 1
    usage['by_model'][model]['tokens'] += tokens
    
    if today not in usage['by_date']:
        usage['by_date'][today] = {'requests': 0, 'tokens': 0}
    usage['by_date'][today]['requests'] += 1
    usage['by_date'][today]['tokens'] += tokens
    
    save_json(USAGE_FILE, usage)

# ============ 上游服务调用 ============
def call_aiproxy_chat(model, messages, max_tokens=2048, temperature=0.7):
    """调用aiproxy的chat接口"""
    url = f"{AIPROXY_URL}/chat"
    payload = {
        'model': model,
        'messages': messages,
        'max_tokens': max_tokens,
        'temperature': temperature
    }
    
    try:
        req = Request(url, data=json.dumps(payload).encode('utf-8'),
                      headers={'Content-Type': 'application/json'})
        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        log(f"aiproxy调用失败: {model} - {str(e)}")
        return None

def call_aiproxy_models():
    """获取aiproxy的模型列表"""
    url = f"{AIPROXY_URL}/models"
    try:
        req = Request(url)
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        log(f"获取aiproxy模型列表失败: {str(e)}")
        return None

def call_anchor_api(path, method='GET', data=None):
    """调用Anchor API"""
    url = f"{ANCHOR_URL}{path}"
    try:
        headers = {'Content-Type': 'application/json'}
        body = json.dumps(data).encode('utf-8') if data else None
        req = Request(url, data=body, headers=headers, method=method)
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        log(f"Anchor API调用失败: {path} - {str(e)}")
        return None

def call_identity_api(path, method='GET', data=None):
    """调用身份API"""
    url = f"{IDENTITY_URL}{path}"
    try:
        headers = {'Content-Type': 'application/json'}
        body = json.dumps(data).encode('utf-8') if data else None
        req = Request(url, data=body, headers=headers, method=method)
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        log(f"身份API调用失败: {path} - {str(e)}")
        return None

# ============ HTTP 请求处理 ============
class GatewayHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 禁用默认日志
    
    def send_json(self, data, status=200):
        response = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-API-Key, Authorization')
        self.end_headers()
        self.wfile.write(response)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-API-Key, Authorization')
        self.end_headers()
    
    def get_client_ip(self):
        """获取客户端IP"""
        return self.client_address[0]
    
    def get_api_key(self):
        """从请求头获取API Key"""
        api_key = self.headers.get('X-API-Key')
        if not api_key:
            auth = self.headers.get('Authorization')
            if auth and auth.startswith('Bearer '):
                api_key = auth[7:]
        return api_key
    
    def get_jwt_token(self):
        """从请求头获取JWT Token"""
        auth = self.headers.get('Authorization')
        if auth and auth.startswith('Bearer '):
            token = auth[7:]
            # 检查是否是JWT（包含两个点）
            if token.count('.') == 2:
                return token
        return None
    
    def authenticate(self):
        """认证，返回(key_info, error_response)"""
        # 先尝试JWT认证（用户系统）
        jwt_token = self.get_jwt_token()
        if jwt_token:
            payload = verify_jwt(jwt_token)
            if payload:
                user = get_user_by_id(payload.get('user_id'))
                if user and user.get('status') == 'active':
                    # JWT认证成功，返回虚拟key_info（使用用户层级）
                    return {
                        'key_id': 'jwt_' + user['user_id'],
                        'name': user['username'],
                        'permissions': ['chat', 'models', 'usage'],
                        'tier': user.get('tier', 'free'),
                        'is_admin': False,
                        'user_id': user['user_id'],
                        'is_jwt': True
                    }, None
        
        # 再尝试API Key认证
        api_key = self.get_api_key()
        if not api_key:
            return None, {'error': '未提供认证信息', 'message': '请在请求头中提供 X-API-Key 或 Authorization: Bearer <token>'}
        
        key_info = verify_api_key(api_key)
        if not key_info:
            return None, {'error': '认证失败', 'message': 'API Key 无效或已被吊销'}
        
        return key_info, None
    
    def check_permission(self, key_info, permission):
        """检查权限"""
        if key_info.get('is_admin'):
            return True
        permissions = key_info.get('permissions', [])
        return '*' in permissions or permission in permissions
    
    def read_body(self):
        """读取请求体"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            try:
                return json.loads(body.decode('utf-8'))
            except:
                return {}
        return {}
    
    def do_GET(self):
        path = self.path.split('?')[0]
        
        # 健康检查（无需认证）
        if path == '/v1/health' or path == '/health':
            self.send_json({
                'status': 'healthy',
                'service': 'zongyuan-api-gateway',
                'version': 'V3.0',
                'did': 'DID-BR-000002',
                'trace': 'Ω₀⊂⊙∞⊂Ω',
                'tiers': list(TIER_CONFIG.keys()),
                'features': ['user_registration', 'jwt_auth', 'tiered_compute', 'auto_fallback', 'token_metering'],
                'upstream_services': {
                    'aiproxy': AIPROXY_URL,
                    'anchor': ANCHOR_URL,
                    'identity': IDENTITY_URL
                }
            })
            return
        
        # 层级配置（无需认证）
        if path == '/v1/tiers' or path == '/tiers':
            tiers_info = {}
            for tier, config in TIER_CONFIG.items():
                tiers_info[tier] = {
                    'name': config['name'],
                    'description': config['description'],
                    'rate_limit_per_minute': config['rate_limit_per_minute'],
                    'rate_limit_per_hour': config['rate_limit_per_hour'],
                    'daily_quota': config['daily_quota'],
                    'priority': config['priority'],
                    'allowed_models_count': len(config['allowed_models']),
                    'max_tokens': config['max_tokens'],
                    'features': config['features']
                }
            self.send_json({'tiers': tiers_info, 'default_tier': REGISTER_DEFAULT_TIER})
            return
        
        # 认证
        key_info, error = self.authenticate()
        if error:
            self.send_json(error, 401)
            return
        
        # 模型列表
        if path == '/v1/models' or path == '/models':
            if not self.check_permission(key_info, 'models'):
                self.send_json({'error': '权限不足', 'message': '需要 models 权限'}, 403)
                return
            
            # 限流检查
            allowed, retry_after = check_rate_limit(key_info['key_id'], key_info.get('tier', 'free'))
            if not allowed:
                self.send_json({'error': '限流', 'message': f'请求过于频繁，请{int(retry_after)}秒后重试', 'retry_after': int(retry_after)}, 429)
                return
            
            # 获取aiproxy模型列表并按层级过滤
            aiproxy_models = call_aiproxy_models()
            all_models = []
            
            if aiproxy_models and 'models' in aiproxy_models:
                # aiproxy返回格式: {"models": {"doubao": {"model": "...", "available": true}}}
                for model_id, model_info in aiproxy_models['models'].items():
                    if isinstance(model_info, dict):
                        all_models.append({
                            'id': model_id,
                            'object': 'model',
                            'created': 1700000000,
                            'owned_by': model_info.get('provider', 'zongyuan'),
                            'available': model_info.get('available', True)
                        })
                    else:
                        all_models.append({
                            'id': model_id,
                            'object': 'model',
                            'created': 1700000000,
                            'owned_by': 'zongyuan'
                        })
            else:
                # 默认模型列表
                default_models = ['doubao', 'doubao-reasoning', 'doubao-reasoning2', 'hunyuan', 'zhipu', 'siliconflow', 'aliyun', 'kimi', 'agnes', 'ollama-local', 'ollama-win']
                for model_id in default_models:
                    all_models.append({
                        'id': model_id,
                        'object': 'model',
                        'created': 1700000000,
                        'owned_by': 'zongyuan'
                    })
            
            # 按层级过滤
            if not key_info.get('is_admin'):
                tier = key_info.get('tier', 'free')
                allowed_models = TIER_CONFIG.get(tier, TIER_CONFIG['free']).get('allowed_models', [])
                filtered_models = [m for m in all_models if m['id'] in allowed_models]
            else:
                filtered_models = all_models
            
            self.send_json({
                'object': 'list',
                'data': filtered_models,
                'tier': key_info.get('tier', 'enterprise'),
                'total': len(filtered_models)
            })
            return
        
        # 用量统计
        if path == '/v1/usage' or path == '/usage':
            if not self.check_permission(key_info, 'usage'):
                self.send_json({'error': '权限不足', 'message': '需要 usage 权限'}, 403)
                return
            
            usage = load_json(USAGE_FILE, {'total_requests': 0, 'total_tokens': 0, 'by_model': {}, 'by_date': {}})
            
            # 如果是普通用户，只返回自己的用量
            if not key_info.get('is_admin') and key_info.get('user_id'):
                user_usage = get_user_usage(key_info['user_id'])
                self.send_json(user_usage)
                return
            
            self.send_json({
                'total_requests': usage.get('total_requests', 0),
                'total_tokens': usage.get('total_tokens', 0),
                'by_model': usage.get('by_model', {}),
                'by_date': usage.get('by_date', {})
            })
            return
        
        # 管理员：列出所有API Key
        if path == '/v1/admin/api-keys' or path == '/admin/api-keys':
            if not key_info.get('is_admin'):
                self.send_json({'error': '权限不足', 'message': '需要管理员权限'}, 403)
                return
            
            keys = list_api_keys()
            self.send_json({'api_keys': keys, 'count': len(keys)})
            return
        
        # 用户：列出自己的API Key
        if path == '/v1/user/api-keys' or path == '/user/api-keys':
            user_id = key_info.get('user_id')
            if not user_id:
                self.send_json({'error': '需要用户身份', 'message': '请使用JWT Token认证'}, 401)
                return
            
            user_keys = get_user_api_keys(user_id)
            self.send_json({'api_keys': user_keys, 'count': len(user_keys), 'max_keys': REGISTER_MAX_KEYS_PER_USER})
            return
        
        # 用户：个人信息
        if path == '/v1/user/profile' or path == '/user/profile':
            user_id = key_info.get('user_id')
            if not user_id:
                self.send_json({'error': '需要用户身份', 'message': '请使用JWT Token认证'}, 401)
                return
            
            user = get_user_by_id(user_id)
            if not user:
                self.send_json({'error': '用户不存在'}, 404)
                return
            
            safe_user = {k: v for k, v in user.items() if k not in ['password_hash', 'salt']}
            self.send_json(safe_user)
            return
        
        # 用户：用量统计
        if path == '/v1/user/usage' or path == '/user/usage':
            user_id = key_info.get('user_id')
            if not user_id:
                self.send_json({'error': '需要用户身份', 'message': '请使用JWT Token认证'}, 401)
                return
            
            user_usage = get_user_usage(user_id)
            if not user_usage:
                self.send_json({'error': '用户不存在'}, 404)
                return
            
            self.send_json(user_usage)
            return
        
        # 内核状态
        if path == '/v1/kernel/status' or path == '/kernel/status':
            status = call_anchor_api('/api/v1/sync/handshake')
            if status:
                self.send_json(status)
            else:
                self.send_json({'status': 'unknown', 'message': '无法连接到内核服务'}, 503)
            return
        
        # 内核节点列表
        if path == '/v1/kernel/nodes/list' or path == '/kernel/nodes/list':
            nodes = call_identity_api('/api/v1/nodes/list')
            if nodes:
                self.send_json(nodes)
            else:
                self.send_json({'nodes': [], 'count': 0})
            return
        
        # 404
        self.send_json({'error': '未找到', 'message': f'路径 {path} 不存在'}, 404)
    
    def do_POST(self):
        path = self.path.split('?')[0]
        body = self.read_body()
        
        # 用户注册（无需认证）
        if path == '/v1/auth/register' or path == '/auth/register':
            username = (body.get('username') or '').strip()
            password = body.get('password') or ''
            email = (body.get('email') or '').strip() or None
            ip = self.get_client_ip()
            
            success, message, user_data = register_user(username, password, email, ip)
            if success:
                # 注册成功后自动登录
                login_success, login_msg, token, _ = login_user(username, password, ip)
                if login_success:
                    self.send_json({
                        'success': True,
                        'message': '注册成功',
                        'user': user_data,
                        'token': token,
                        'token_type': 'Bearer',
                        'expires_in': JWT_EXPIRE_HOURS * 3600
                    }, 201)
                else:
                    self.send_json({'success': True, 'message': '注册成功，请登录', 'user': user_data}, 201)
            else:
                self.send_json({'success': False, 'error': message}, 400)
            return
        
        # 用户登录（无需认证）
        if path == '/v1/auth/login' or path == '/auth/login':
            username = (body.get('username') or '').strip()
            password = body.get('password') or ''
            ip = self.get_client_ip()
            
            success, message, token, user_data = login_user(username, password, ip)
            if success:
                self.send_json({
                    'success': True,
                    'message': '登录成功',
                    'token': token,
                    'token_type': 'Bearer',
                    'expires_in': JWT_EXPIRE_HOURS * 3600,
                    'user': user_data
                })
            else:
                self.send_json({'success': False, 'error': message}, 401)
            return
        
        # 认证
        key_info, error = self.authenticate()
        if error:
            self.send_json(error, 401)
            return
        
        # 聊天补全（OpenAI兼容）
        if path == '/v1/chat/completions' or path == '/chat/completions':
            if not self.check_permission(key_info, 'chat'):
                self.send_json({'error': '权限不足', 'message': '需要 chat 权限'}, 403)
                return
            
            model = body.get('model') or 'doubao'
            messages = body.get('messages') or []
            max_tokens = body.get('max_tokens') or 2048
            temperature = body.get('temperature') if body.get('temperature') is not None else 0.7
            
            # 检查模型白名单
            if not check_model_allowed(key_info, model):
                self.send_json({
                    'error': '模型不可用',
                    'message': f'模型 {model} 不在当前层级({key_info.get("tier", "free")})的白名单中',
                    'available_models': TIER_CONFIG.get(key_info.get('tier', 'free'), {}).get('allowed_models', [])
                }, 403)
                return
            
            # 限流检查
            allowed, retry_after = check_rate_limit(key_info['key_id'], key_info.get('tier', 'free'))
            if not allowed:
                self.send_json({'error': '限流', 'message': f'请求过于频繁，请{int(retry_after)}秒后重试', 'retry_after': int(retry_after)}, 429)
                return
            
            # 每日配额检查
            quota_allowed, remaining = check_daily_quota(key_info)
            if not quota_allowed:
                self.send_json({'error': '配额耗尽', 'message': '今日Token配额已用完，请明天再试或升级层级'}, 429)
                return
            
            # 调用模型（带自动降级）
            result = None
            used_model = model
            fallback_used = False
            
            # 第一次尝试
            result = call_aiproxy_chat(model, messages, max_tokens, temperature)
            
            # 如果失败，尝试降级
            if not result and not key_info.get('is_jwt'):
                fallback = get_fallback_model(model, key_info)
                if fallback and fallback != model:
                    log(f"模型 {model} 调用失败，自动降级到 {fallback}")
                    result = call_aiproxy_chat(fallback, messages, max_tokens, temperature)
                    if result:
                        used_model = fallback
                        fallback_used = True
            
            if not result:
                self.send_json({'error': '模型调用失败', 'message': '所有可用模型均调用失败，请稍后重试'}, 502)
                return
            
            # 估算Token
            input_text = ' '.join([m.get('content', '') for m in messages])
            input_tokens = estimate_tokens(input_text)
            output_text = result.get('choices', [{}])[0].get('message', {}).get('content', '') if 'choices' in result else ''
            output_tokens = estimate_tokens(output_text)
            total_tokens = input_tokens + output_tokens
            
            # 更新用量
            update_api_key_usage(key_info['key_id'], total_tokens)
            record_usage(used_model, total_tokens, key_info['key_id'], key_info.get('user_id'))
            
            # 构建OpenAI兼容响应
            response = {
                'id': 'chatcmpl-' + uuid.uuid4().hex[:24],
                'object': 'chat.completion',
                'created': int(time.time()),
                'model': used_model,
                'choices': [{
                    'index': 0,
                    'message': {
                        'role': 'assistant',
                        'content': output_text
                    },
                    'finish_reason': 'stop'
                }],
                'usage': {
                    'prompt_tokens': input_tokens,
                    'completion_tokens': output_tokens,
                    'total_tokens': total_tokens
                }
            }
            
            if fallback_used:
                response['fallback'] = {
                    'requested_model': model,
                    'used_model': used_model,
                    'reason': 'auto_fallback'
                }
            
            self.send_json(response)
            return
        
        # 管理员：创建API Key
        if path == '/v1/admin/api-keys' or path == '/admin/api-keys':
            if not key_info.get('is_admin'):
                self.send_json({'error': '权限不足', 'message': '需要管理员权限'}, 403)
                return
            
            name = body.get('name') or '未命名'
            permissions = body.get('permissions') or ['chat', 'models']
            tier = body.get('tier') or 'basic'
            expires_at = body.get('expires_at')
            
            api_key, key_info_new = create_api_key(name, permissions, expires_at, tier)
            self.send_json({'api_key': api_key, 'key_info': {k: v for k, v in key_info_new.items() if k != 'key_hash'}}, 201)
            return
        
        # 用户：创建API Key
        if path == '/v1/user/api-keys' or path == '/user/api-keys':
            user_id = key_info.get('user_id')
            if not user_id:
                self.send_json({'error': '需要用户身份', 'message': '请使用JWT Token认证'}, 401)
                return
            
            name = body.get('name') or '未命名'
            permissions = body.get('permissions') or ['chat', 'models']
            tier = body.get('tier')  # 用户不能指定超过自己层级的Key
            
            success, message, api_key = create_user_api_key(user_id, name, permissions, tier)
            if success:
                self.send_json({'success': True, 'api_key': api_key, 'message': message}, 201)
            else:
                self.send_json({'success': False, 'error': message}, 400)
            return
        
        # 用户：修改密码
        if path == '/v1/user/change-password' or path == '/user/change-password':
            user_id = key_info.get('user_id')
            if not user_id:
                self.send_json({'error': '需要用户身份', 'message': '请使用JWT Token认证'}, 401)
                return
            
            old_password = body.get('old_password') or ''
            new_password = body.get('new_password') or ''
            
            user = get_user_by_id(user_id)
            if not user:
                self.send_json({'error': '用户不存在'}, 404)
                return
            
            # 验证旧密码
            if not verify_password(old_password, user.get('salt', ''), user.get('password_hash', '')):
                self.send_json({'error': '旧密码错误'}, 400)
                return
            
            # 检查新密码强度
            valid, msg = check_password_strength(new_password)
            if not valid:
                self.send_json({'error': msg}, 400)
                return
            
            # 更新密码
            password_hash, salt = hash_password(new_password)
            users = load_json(USERS_FILE, {'users': []})
            for u in users.get('users', []):
                if u.get('user_id') == user_id:
                    u['password_hash'] = password_hash
                    u['salt'] = salt
                    u['password_changed_at'] = datetime.now().isoformat()
                    save_json(USERS_FILE, users)
                    break
            
            log(f"用户修改密码: {user_id}")
            self.send_json({'success': True, 'message': '密码修改成功'})
            return
        
        # 内核真值拉取
        if path == '/v1/kernel/truth/pull' or path == '/kernel/truth/pull':
            result = call_anchor_api('/api/v1/sync/truth-pull', 'POST', body)
            if result:
                self.send_json(result)
            else:
                self.send_json({'error': '内核服务不可用'}, 503)
            return
        
        # 内核真值推送
        if path == '/v1/kernel/truth/push' or path == '/kernel/truth/push':
            result = call_anchor_api('/api/v1/sync/truth-push', 'POST', body)
            if result:
                self.send_json(result)
            else:
                self.send_json({'error': '内核服务不可用'}, 503)
            return
        
        # 内核节点注册
        if path == '/v1/kernel/nodes/register' or path == '/kernel/nodes/register':
            result = call_identity_api('/api/v1/nodes/register', 'POST', body)
            if result:
                self.send_json(result)
            else:
                self.send_json({'error': '内核服务不可用'}, 503)
            return
        
        # 内核节点心跳
        if path == '/v1/kernel/nodes/heartbeat' or path == '/kernel/nodes/heartbeat':
            result = call_identity_api('/api/v1/nodes/heartbeat', 'POST', body)
            if result:
                self.send_json(result)
            else:
                self.send_json({'error': '内核服务不可用'}, 503)
            return
        
        # 404
        self.send_json({'error': '未找到', 'message': f'路径 {path} 不存在'}, 404)
    
    def do_DELETE(self):
        path = self.path.split('?')[0]
        
        # 认证
        key_info, error = self.authenticate()
        if error:
            self.send_json(error, 401)
            return
        
        # 管理员：吊销API Key
        if path.startswith('/v1/admin/api-keys/') or path.startswith('/admin/api-keys/'):
            if not key_info.get('is_admin'):
                self.send_json({'error': '权限不足', 'message': '需要管理员权限'}, 403)
                return
            
            key_id = path.split('/')[-1]
            success = revoke_api_key(key_id)
            if success:
                self.send_json({'success': True, 'message': 'API Key已吊销'})
            else:
                self.send_json({'error': 'API Key不存在'}, 404)
            return
        
        # 用户：吊销自己的API Key
        if path.startswith('/v1/user/api-keys/') or path.startswith('/user/api-keys/'):
            user_id = key_info.get('user_id')
            if not user_id:
                self.send_json({'error': '需要用户身份', 'message': '请使用JWT Token认证'}, 401)
                return
            
            key_id = path.split('/')[-1]
            success, message = revoke_user_api_key(user_id, key_id)
            if success:
                self.send_json({'success': True, 'message': message})
            else:
                self.send_json({'error': message}, 400)
            return
        
        # 404
        self.send_json({'error': '未找到', 'message': f'路径 {path} 不存在'}, 404)

# ============ 启动服务 ============
def main():
    log("=" * 60)
    log("ZONGYUAN-ROOT 统一API网关 V3.0 启动")
    log("=" * 60)
    log(f"端口: {PORT}")
    log(f"层级: {list(TIER_CONFIG.keys())}")
    log(f"默认注册层级: {REGISTER_DEFAULT_TIER}")
    log(f"每用户最大Key数: {REGISTER_MAX_KEYS_PER_USER}")
    log(f"JWT有效期: {JWT_EXPIRE_HOURS}小时")
    log(f"管理员API Key: {ADMIN_API_KEY}")
    log("=" * 60)
    
    # 初始化存储
    init_api_keys()
    init_users()
    
    # 启动HTTP服务
    server = HTTPServer(('0.0.0.0', PORT), GatewayHandler)
    log(f"API网关已启动，监听端口 {PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("API网关已停止")
        server.shutdown()

if __name__ == '__main__':
    main()
