#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 统一API网关 V2.0 - 层级化算力调度版
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
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ============ 配置 ============
PORT = 8040
BASE_DIR = '/opt/ZONGYUAN-ROOT/api_gateway'
os.makedirs(BASE_DIR, exist_ok=True)

API_KEYS_FILE = os.path.join(BASE_DIR, 'api_keys.json')
STATS_FILE = os.path.join(BASE_DIR, 'stats.json')
USAGE_FILE = os.path.join(BASE_DIR, 'usage.json')
LOG_FILE = os.path.join(BASE_DIR, 'gateway.log')

# 上游服务地址
AIPROXY_URL = 'http://127.0.0.1:8021'
ANCHOR_URL = 'http://127.0.0.1:8006'
IDENTITY_URL = 'http://127.0.0.1:8030'

# ============ 层级化配置 ============
TIER_CONFIG = {
    'free': {
        'name': '免费层',
        'description': '体验测试用，仅免费模型',
        'rate_limit_per_minute': 10,
        'rate_limit_per_hour': 100,
        'daily_quota': 10000,  # Token/天
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
        'daily_quota': -1,  # 无限制
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

# 模型降级映射（主模型故障时自动切换到备用模型）
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

# 内置管理员API Key（首次启动时创建）
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
    """生成API Key: zy- + 32位十六进制"""
    return 'zy-' + uuid.uuid4().hex + uuid.uuid4().hex[:16]

def hash_api_key(api_key):
    """对API Key进行哈希存储（不存储明文）"""
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()

def get_today_str():
    """获取今天的日期字符串"""
    return datetime.now().strftime('%Y-%m-%d')

def estimate_tokens(text):
    """估算Token数量（粗略估算：中文1字≈1.5Token，英文1词≈1.3Token）"""
    if not text:
        return 0
    # 简单估算：字符数 * 0.75
    return max(1, int(len(text) * 0.75))

# ============ API Key管理 ============
def init_api_keys():
    """初始化API Key存储"""
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    if not keys.get('admin_key_hash'):
        keys['admin_key_hash'] = hash_api_key(ADMIN_API_KEY)
        keys['admin_key_created_at'] = datetime.now().isoformat()
        save_json(API_KEYS_FILE, keys)
        log(f"管理员API Key已创建: {ADMIN_API_KEY}")
    return keys

def verify_api_key(api_key):
    """验证API Key，返回key信息或None"""
    if not api_key:
        return None
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    
    # 检查管理员Key（enterprise层级，所有权限）
    if hash_api_key(api_key) == keys.get('admin_key_hash'):
        return {
            'key_id': 'admin',
            'name': 'Administrator',
            'permissions': ['*'],
            'tier': 'enterprise',
            'is_admin': True,
            'created_at': keys.get('admin_key_created_at', '')
        }
    
    # 检查普通Key
    key_hash = hash_api_key(api_key)
    for key_info in keys.get('keys', []):
        if key_info.get('key_hash') == key_hash:
            if key_info.get('status') == 'active':
                return key_info
            else:
                return None
    return None

def create_api_key(name, permissions=None, expires_at=None, tier='basic', created_by='admin'):
    """创建新的API Key"""
    if permissions is None:
        permissions = ['chat', 'models']
    
    # 验证层级有效性
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
        'expires_at': expires_at,
        'last_used_at': None,
        'usage_count': 0,
        'total_tokens': 0,
        'daily_usage': {}  # {date: {requests: N, tokens: N}}
    }
    
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    keys['keys'].append(key_info)
    save_json(API_KEYS_FILE, keys)
    
    log(f"API Key已创建: {key_info['key_id']} ({name}) - 层级: {tier}")
    return api_key, key_info

def list_api_keys():
    """列出所有API Key（不返回明文）"""
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
            'expires_at': key_info.get('expires_at'),
            'last_used_at': key_info.get('last_used_at'),
            'usage_count': key_info.get('usage_count', 0),
            'total_tokens': key_info.get('total_tokens', 0)
        })
    return result

def revoke_api_key(key_id):
    """吊销API Key"""
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
    """更新API Key使用统计"""
    if key_id == 'admin':
        return  # 管理员Key不记录使用次数
    
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    today = get_today_str()
    
    for key_info in keys.get('keys', []):
        if key_info['key_id'] == key_id:
            key_info['usage_count'] = key_info.get('usage_count', 0) + 1
            key_info['total_tokens'] = key_info.get('total_tokens', 0) + tokens
            key_info['last_used_at'] = datetime.now().isoformat()
            
            # 更新每日用量
            if today not in key_info.get('daily_usage', {}):
                key_info['daily_usage'] = key_info.get('daily_usage', {})
                key_info['daily_usage'][today] = {'requests': 0, 'tokens': 0}
            key_info['daily_usage'][today]['requests'] += 1
            key_info['daily_usage'][today]['tokens'] += tokens
            
            # 清理超过30天的每日用量记录
            if len(key_info['daily_usage']) > 30:
                sorted_dates = sorted(key_info['daily_usage'].keys())
                for old_date in sorted_dates[:-30]:
                    del key_info['daily_usage'][old_date]
            
            save_json(API_KEYS_FILE, keys)
            return

def check_daily_quota(key_info):
    """检查每日配额，返回(allowed, remaining)"""
    tier = key_info.get('tier', 'basic')
    config = TIER_CONFIG.get(tier, TIER_CONFIG['basic'])
    daily_quota = config.get('daily_quota', -1)
    
    if daily_quota == -1:  # 无限制
        return True, -1
    
    today = get_today_str()
    daily_usage = key_info.get('daily_usage', {}).get(today, {'tokens': 0})
    used_tokens = daily_usage.get('tokens', 0)
    remaining = daily_quota - used_tokens
    
    return remaining > 0, remaining

def check_model_allowed(key_info, model):
    """检查模型是否在当前层级的白名单中"""
    if key_info.get('is_admin'):
        return True  # 管理员可以用所有模型
    
    tier = key_info.get('tier', 'basic')
    config = TIER_CONFIG.get(tier, TIER_CONFIG['basic'])
    allowed_models = config.get('allowed_models', [])
    
    return model in allowed_models

def get_fallback_model(model, key_info):
    """获取降级备用模型"""
    if key_info.get('is_admin'):
        fallbacks = MODEL_FALLBACK.get(model, [])
        return fallbacks[0] if fallbacks else model
    
    tier = key_info.get('tier', 'basic')
    config = TIER_CONFIG.get(tier, TIER_CONFIG['basic'])
    allowed_models = config.get('allowed_models', [])
    
    # 从降级列表中找第一个在白名单中的模型
    fallbacks = MODEL_FALLBACK.get(model, [])
    for fallback in fallbacks:
        if fallback in allowed_models:
            return fallback
    
    return None

# ============ 层级化限流 ============
rate_limit_store = {}  # {key_hash: {'minute': [timestamps], 'hour': [timestamps]}}
rate_lock = threading.Lock()

def check_rate_limit(key_hash, tier='basic'):
    """检查限流（按层级差异化），返回(allowed, retry_after)"""
    config = TIER_CONFIG.get(tier, TIER_CONFIG['basic'])
    per_minute = config.get('rate_limit_per_minute', 60)
    per_hour = config.get('rate_limit_per_hour', 1000)
    
    now = time.time()
    with rate_lock:
        if key_hash not in rate_limit_store:
            rate_limit_store[key_hash] = {'minute': [], 'hour': []}
        
        store = rate_limit_store[key_hash]
        
        # 清理过期记录
        store['minute'] = [t for t in store['minute'] if now - t < 60]
        store['hour'] = [t for t in store['hour'] if now - t < 3600]
        
        # 检查限制
        if len(store['minute']) >= per_minute:
            return False, 60 - (now - store['minute'][0])
        if len(store['hour']) >= per_hour:
            return False, 3600 - (now - store['hour'][0])
        
        # 记录请求
        store['minute'].append(now)
        store['hour'].append(now)
        return True, 0

# ============ 用量统计 ============
def record_usage(key_id, model, tokens_input, tokens_output, duration_ms):
    """记录用量统计"""
    usage = load_json(USAGE_FILE, {'total_requests': 0, 'total_tokens': 0, 'by_model': {}, 'by_tier': {}, 'daily': {}})
    
    usage['total_requests'] = usage.get('total_requests', 0) + 1
    usage['total_tokens'] = usage.get('total_tokens', 0) + tokens_input + tokens_output
    
    # 按模型统计
    if model not in usage.get('by_model', {}):
        usage['by_model'][model] = {'requests': 0, 'tokens': 0}
    usage['by_model'][model]['requests'] += 1
    usage['by_model'][model]['tokens'] += tokens_input + tokens_output
    
    # 按日期统计
    today = get_today_str()
    if today not in usage.get('daily', {}):
        usage['daily'][today] = {'requests': 0, 'tokens': 0}
    usage['daily'][today]['requests'] += 1
    usage['daily'][today]['tokens'] += tokens_input + tokens_output
    
    # 清理超过30天的每日统计
    if len(usage['daily']) > 30:
        sorted_dates = sorted(usage['daily'].keys())
        for old_date in sorted_dates[:-30]:
            del usage['daily'][old_date]
    
    save_json(USAGE_FILE, usage)

# ============ 上游请求转发 ============
def forward_request(url, method='GET', headers=None, body=None, timeout=60):
    """转发请求到上游服务"""
    if headers is None:
        headers = {}
    if body is not None and isinstance(body, dict):
        body = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as response:
            response_body = response.read().decode('utf-8')
            return response.status, response_body, dict(response.headers)
    except HTTPError as e:
        response_body = e.read().decode('utf-8') if e.fp else ''
        return e.code, response_body, dict(e.headers)
    except URLError as e:
        return 502, json.dumps({'error': 'Bad Gateway', 'message': str(e)}), {}
    except Exception as e:
        return 500, json.dumps({'error': 'Internal Server Error', 'message': str(e)}), {}

# ============ HTTP请求处理器 ============
class GatewayHandler(BaseHTTPRequestHandler):
    def send_json_response(self, data, status_code=200, headers=None):
        response = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-API-Key')
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(response)
    
    def do_OPTIONS(self):
        self.send_json_response({'status': 'ok'}, 200)
    
    def get_api_key(self):
        """从请求头获取API Key"""
        api_key = self.headers.get('X-API-Key')
        if api_key:
            return api_key
        
        auth = self.headers.get('Authorization')
        if auth and auth.startswith('Bearer '):
            return auth[7:]
        
        return None
    
    def authenticate(self, required_permissions=None):
        """认证和权限检查，返回key_info或发送错误响应"""
        api_key = self.get_api_key()
        if not api_key:
            self.send_json_response({
                'error': 'Unauthorized',
                'message': 'Missing API Key. Use X-API-Key header or Authorization: Bearer <key>'
            }, 401)
            return None
        
        key_info = verify_api_key(api_key)
        if not key_info:
            self.send_json_response({
                'error': 'Unauthorized',
                'message': 'Invalid or revoked API Key'
            }, 401)
            return None
        
        # 权限检查
        if required_permissions and not key_info.get('is_admin'):
            for perm in required_permissions:
                if perm not in key_info.get('permissions', []):
                    self.send_json_response({
                        'error': 'Forbidden',
                        'message': f'API Key does not have permission: {perm}'
                    }, 403)
                    return None
        
        # 层级化限流检查
        tier = key_info.get('tier', 'basic')
        key_hash = hash_api_key(api_key)
        allowed, retry_after = check_rate_limit(key_hash, tier)
        if not allowed:
            self.send_json_response({
                'error': 'Too Many Requests',
                'message': f'Rate limit exceeded for tier "{tier}". Retry after {int(retry_after)} seconds.',
                'tier': tier,
                'retry_after': int(retry_after)
            }, 429, {'Retry-After': str(int(retry_after))})
            return None
        
        # 每日配额检查
        quota_allowed, remaining = check_daily_quota(key_info)
        if not quota_allowed:
            self.send_json_response({
                'error': 'Quota Exceeded',
                'message': f'Daily token quota exceeded for tier "{tier}".',
                'tier': tier
            }, 429)
            return None
        
        return key_info
    
    def do_GET(self):
        path = self.path.split('?')[0]
        
        # 健康检查（无需认证）
        if path == '/v1/health' or path == '/health':
            self.send_json_response({
                'status': 'healthy',
                'service': 'zongyuan-api-gateway',
                'version': 'V2.0',
                'did': 'DID-BR-000002',
                'trace': 'Ω₀⊂⊙∞⊂Ω',
                'tiers': list(TIER_CONFIG.keys()),
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
                    'max_tokens': config['max_tokens']
                }
            self.send_json_response({'tiers': tiers_info})
            return
        
        # 模型列表
        if path == '/v1/models' or path == '/models':
            key_info = self.authenticate(['models'])
            if not key_info:
                return
            
            # 根据层级过滤可用模型
            if key_info.get('is_admin'):
                allowed_models = None  # 所有模型
            else:
                tier = key_info.get('tier', 'basic')
                allowed_models = TIER_CONFIG.get(tier, TIER_CONFIG['basic']).get('allowed_models')
            
            # 从aiproxy获取模型列表
            status, body, headers = forward_request(f'{AIPROXY_URL}/models')
            if status == 200:
                try:
                    models_data = json.loads(body)
                    if allowed_models:
                        models_data['data'] = [m for m in models_data.get('data', []) if m.get('id') in allowed_models]
                    self.send_json_response(models_data)
                except:
                    self.send_json_response({'data': [], 'object': 'list'})
            else:
                self.send_json_response({'data': [], 'object': 'list', 'error': 'upstream_error'})
            return
        
        # 用量统计
        if path == '/v1/usage' or path == '/usage':
            key_info = self.authenticate(['usage'])
            if not key_info:
                return
            
            usage = load_json(USAGE_FILE, {'total_requests': 0, 'total_tokens': 0, 'by_model': {}})
            self.send_json_response(usage)
            return
        
        # API Key列表（管理员）
        if path == '/v1/admin/api-keys' or path == '/admin/api-keys':
            key_info = self.authenticate(['admin'])
            if not key_info:
                return
            
            keys = list_api_keys()
            self.send_json_response({'api_keys': keys, 'count': len(keys)})
            return
        
        # 内核状态
        if path == '/v1/kernel/status' or path == '/kernel/status':
            key_info = self.authenticate(['kernel'])
            if not key_info:
                return
            
            status, body, headers = forward_request(f'{ANCHOR_URL}/api/v1/sync/handshake')
            if status == 200:
                try:
                    self.send_json_response(json.loads(body))
                except:
                    self.send_json_response({'status': 'error', 'message': 'parse_error'})
            else:
                self.send_json_response({'status': 'error', 'message': 'upstream_error', 'code': status})
            return
        
        # 内核身份
        if path == '/v1/kernel/identity' or path == '/kernel/identity':
            key_info = self.authenticate(['kernel'])
            if not key_info:
                return
            
            status, body, headers = forward_request(f'{IDENTITY_URL}/api/v1/identity')
            if status == 200:
                try:
                    self.send_json_response(json.loads(body))
                except:
                    self.send_json_response({'status': 'error', 'message': 'parse_error'})
            else:
                self.send_json_response({'status': 'error', 'message': 'upstream_error', 'code': status})
            return
        
        # 节点列表
        if path == '/v1/kernel/nodes/list' or path == '/kernel/nodes/list':
            key_info = self.authenticate(['kernel'])
            if not key_info:
                return
            
            status, body, headers = forward_request(f'{IDENTITY_URL}/api/v1/nodes/list')
            if status == 200:
                try:
                    self.send_json_response(json.loads(body))
                except:
                    self.send_json_response({'nodes': []})
            else:
                self.send_json_response({'nodes': [], 'error': 'upstream_error'})
            return
        
        # 默认404
        self.send_json_response({'error': 'Not Found', 'message': f'Endpoint not found: {path}'}, 404)
    
    def do_POST(self):
        path = self.path.split('?')[0]
        
        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
        # 聊天补全（OpenAI兼容）
        if path == '/v1/chat/completions' or path == '/chat/completions':
            key_info = self.authenticate(['chat'])
            if not key_info:
                return
            
            try:
                request_data = json.loads(body.decode('utf-8')) if body else {}
            except:
                self.send_json_response({'error': 'Invalid JSON', 'message': 'Request body is not valid JSON'}, 400)
                return
            
            model = request_data.get('model', 'doubao')
            messages = request_data.get('messages', [])
            
            # 检查模型白名单
            if not check_model_allowed(key_info, model):
                tier = key_info.get('tier', 'basic')
                allowed = TIER_CONFIG.get(tier, TIER_CONFIG['basic']).get('allowed_models', [])
                self.send_json_response({
                    'error': 'Model Not Allowed',
                    'message': f'Model "{model}" is not available for tier "{tier}". Allowed models: {", ".join(allowed)}',
                    'tier': tier,
                    'allowed_models': allowed
                }, 403)
                return
            
            # 估算输入Token
            input_text = ' '.join([m.get('content', '') for m in messages])
            tokens_input = estimate_tokens(input_text)
            
            # 转发到aiproxy（带自动降级）
            start_time = time.time()
            current_model = model
            fallback_used = False
            
            for attempt in range(3):  # 最多尝试3次（主模型+2个降级）
                request_data['model'] = current_model
                status, resp_body, resp_headers = forward_request(
                    f'{AIPROXY_URL}/chat',
                    method='POST',
                    body=request_data,
                    timeout=120
                )
                
                if status == 200:
                    break
                elif attempt < 2:
                    # 尝试降级
                    fallback = get_fallback_model(current_model, key_info)
                    if fallback and fallback != current_model:
                        log(f"模型 {current_model} 失败({status})，自动降级到 {fallback}")
                        current_model = fallback
                        fallback_used = True
                        continue
                    else:
                        break
                else:
                    break
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if status == 200:
                try:
                    response_data = json.loads(resp_body)
                    # 估算输出Token
                    output_text = ''
                    if 'choices' in response_data and len(response_data['choices']) > 0:
                        output_text = response_data['choices'][0].get('message', {}).get('content', '')
                    tokens_output = estimate_tokens(output_text)
                    
                    # 记录用量
                    record_usage(key_info['key_id'], model, tokens_input, tokens_output, duration_ms)
                    update_api_key_usage(key_info['key_id'], tokens_input + tokens_output)
                    
                    # 添加层级和降级信息
                    response_data['tier'] = key_info.get('tier', 'basic')
                    if fallback_used:
                        response_data['fallback_used'] = True
                        response_data['original_model'] = model
                        response_data['actual_model'] = current_model
                    
                    self.send_json_response(response_data)
                except Exception as e:
                    self.send_json_response({'error': 'Parse Error', 'message': str(e)}, 500)
            else:
                self.send_json_response({
                    'error': 'Upstream Error',
                    'message': f'Failed to get response from model "{model}" after {attempt+1} attempts.',
                    'code': status,
                    'tier': key_info.get('tier', 'basic')
                }, status if status >= 400 else 502)
            return
        
        # 创建API Key（管理员）
        if path == '/v1/admin/api-keys' or path == '/admin/api-keys':
            key_info = self.authenticate(['admin'])
            if not key_info:
                return
            
            try:
                request_data = json.loads(body.decode('utf-8')) if body else {}
            except:
                self.send_json_response({'error': 'Invalid JSON'}, 400)
                return
            
            name = request_data.get('name', 'Unnamed')
            permissions = request_data.get('permissions', ['chat', 'models'])
            expires_at = request_data.get('expires_at')
            tier = request_data.get('tier', 'basic')
            
            if tier not in TIER_CONFIG:
                self.send_json_response({'error': 'Invalid Tier', 'message': f'Tier must be one of: {", ".join(TIER_CONFIG.keys())}'}, 400)
                return
            
            api_key, key_info_result = create_api_key(name, permissions, expires_at, tier)
            self.send_json_response({
                'api_key': api_key,
                'key_id': key_info_result['key_id'],
                'name': key_info_result['name'],
                'tier': key_info_result['tier'],
                'permissions': key_info_result['permissions'],
                'created_at': key_info_result['created_at']
            }, 201)
            return
        
        # 节点注册
        if path == '/v1/kernel/nodes/register' or path == '/kernel/nodes/register':
            key_info = self.authenticate(['kernel'])
            if not key_info:
                return
            
            status, resp_body, resp_headers = forward_request(
                f'{IDENTITY_URL}/api/v1/nodes/register',
                method='POST',
                body=json.loads(body.decode('utf-8')) if body else {}
            )
            self.send_json_response(json.loads(resp_body) if resp_body else {}, status)
            return
        
        # 节点心跳
        if path == '/v1/kernel/nodes/heartbeat' or path == '/kernel/nodes/heartbeat':
            key_info = self.authenticate(['kernel'])
            if not key_info:
                return
            
            status, resp_body, resp_headers = forward_request(
                f'{IDENTITY_URL}/api/v1/nodes/heartbeat',
                method='POST',
                body=json.loads(body.decode('utf-8')) if body else {}
            )
            self.send_json_response(json.loads(resp_body) if resp_body else {}, status)
            return
        
        # 真值拉取
        if path == '/v1/kernel/truth/pull' or path == '/kernel/truth/pull':
            key_info = self.authenticate(['kernel'])
            if not key_info:
                return
            
            status, resp_body, resp_headers = forward_request(
                f'{ANCHOR_URL}/api/v1/sync/truth-pull',
                method='POST',
                body=json.loads(body.decode('utf-8')) if body else {}
            )
            self.send_json_response(json.loads(resp_body) if resp_body else {}, status)
            return
        
        # 真值推送
        if path == '/v1/kernel/truth/push' or path == '/kernel/truth/push':
            key_info = self.authenticate(['kernel'])
            if not key_info:
                return
            
            status, resp_body, resp_headers = forward_request(
                f'{ANCHOR_URL}/api/v1/sync/truth-push',
                method='POST',
                body=json.loads(body.decode('utf-8')) if body else {}
            )
            self.send_json_response(json.loads(resp_body) if resp_body else {}, status)
            return
        
        # 默认404
        self.send_json_response({'error': 'Not Found', 'message': f'Endpoint not found: {path}'}, 404)
    
    def do_DELETE(self):
        path = self.path.split('?')[0]
        
        # 吊销API Key
        if path.startswith('/v1/admin/api-keys/') or path.startswith('/admin/api-keys/'):
            key_info = self.authenticate(['admin'])
            if not key_info:
                return
            
            key_id = path.split('/')[-1]
            success = revoke_api_key(key_id)
            if success:
                self.send_json_response({'status': 'revoked', 'key_id': key_id})
            else:
                self.send_json_response({'error': 'Not Found', 'message': f'API Key not found: {key_id}'}, 404)
            return
        
        self.send_json_response({'error': 'Not Found', 'message': f'Endpoint not found: {path}'}, 404)
    
    def log_message(self, format, *args):
        """重写日志方法，使用自定义日志"""
        log(f"{self.command} {self.path} - {args[0] if args else ''}")

# ============ 主函数 ============
def main():
    init_api_keys()
    log(f"ZONGYUAN-ROOT API网关 V2.0 启动，端口: {PORT}")
    log(f"层级配置: {', '.join(TIER_CONFIG.keys())}")
    log(f"管理员API Key: {ADMIN_API_KEY}")
    
    server = HTTPServer(('0.0.0.0', PORT), GatewayHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("API网关已停止")
        server.shutdown()

if __name__ == '__main__':
    main()
