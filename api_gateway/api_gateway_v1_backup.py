#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 统一API网关 V1.0
- API Key管理（生成/列表/吊销/权限控制）
- OpenAI兼容接口（/v1/chat/completions, /v1/models）
- 内核能力API路由（转发到Anchor/身份API/aiproxy）
- 调用统计和限流
- 统一认证（X-API-Key或Bearer Token）
"""

import json
import os
import hashlib
import time
import uuid
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ============ 配置 ============
PORT = 8040
BASE_DIR = '/opt/ZONGYUAN-ROOT/api_gateway'
os.makedirs(BASE_DIR, exist_ok=True)

API_KEYS_FILE = os.path.join(BASE_DIR, 'api_keys.json')
STATS_FILE = os.path.join(BASE_DIR, 'stats.json')
LOG_FILE = os.path.join(BASE_DIR, 'gateway.log')

# 上游服务地址
AIPROXY_URL = 'http://127.0.0.1:8021'
ANCHOR_URL = 'http://127.0.0.1:8006'
IDENTITY_URL = 'http://127.0.0.1:8030'

# 限流配置
RATE_LIMIT_PER_MINUTE = 60  # 每个API Key每分钟最多60次请求
RATE_LIMIT_PER_HOUR = 1000  # 每个API Key每小时最多1000次请求

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
    
    # 检查管理员Key
    if hash_api_key(api_key) == keys.get('admin_key_hash'):
        return {
            'key_id': 'admin',
            'name': 'Administrator',
            'permissions': ['*'],
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

def create_api_key(name, permissions=None, expires_at=None, created_by='admin'):
    """创建新的API Key"""
    if permissions is None:
        permissions = ['chat', 'models']
    
    api_key = generate_api_key()
    key_info = {
        'key_id': 'key_' + uuid.uuid4().hex[:8],
        'key_hash': hash_api_key(api_key),
        'name': name,
        'permissions': permissions,
        'status': 'active',
        'created_at': datetime.now().isoformat(),
        'created_by': created_by,
        'expires_at': expires_at,
        'last_used_at': None,
        'usage_count': 0
    }
    
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    keys['keys'].append(key_info)
    save_json(API_KEYS_FILE, keys)
    
    log(f"API Key已创建: {key_info['key_id']} ({name})")
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
            'status': key_info['status'],
            'created_at': key_info['created_at'],
            'expires_at': key_info.get('expires_at'),
            'last_used_at': key_info.get('last_used_at'),
            'usage_count': key_info.get('usage_count', 0)
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

def update_api_key_usage(key_id):
    """更新API Key使用统计"""
    keys = load_json(API_KEYS_FILE, {'keys': [], 'admin_key_hash': ''})
    for key_info in keys.get('keys', []):
        if key_info['key_id'] == key_id:
            key_info['usage_count'] = key_info.get('usage_count', 0) + 1
            key_info['last_used_at'] = datetime.now().isoformat()
            save_json(API_KEYS_FILE, keys)
            return
    # 管理员Key不记录使用次数

# ============ 限流 ============
rate_limit_store = {}  # {key_hash: {'minute': [timestamps], 'hour': [timestamps]}}
rate_lock = threading.Lock()

def check_rate_limit(key_hash):
    """检查限流，返回(allowed, retry_after)"""
    now = time.time()
    with rate_lock:
        if key_hash not in rate_limit_store:
            rate_limit_store[key_hash] = {'minute': [], 'hour': []}
        
        store = rate_limit_store[key_hash]
        
        # 清理过期记录
        store['minute'] = [t for t in store['minute'] if now - t < 60]
        store['hour'] = [t for t in store['hour'] if now - t < 3600]
        
        # 检查限制
        if len(store['minute']) >= RATE_LIMIT_PER_MINUTE:
            return False, 60 - (now - store['minute'][0])
        if len(store['hour']) >= RATE_LIMIT_PER_HOUR:
            return False, 3600 - (now - store['hour'][0])
        
        # 记录请求
        store['minute'].append(now)
        store['hour'].append(now)
        return True, 0

# ============ 上游请求转发 ============
def forward_request(url, method='GET', headers=None, body=None, timeout=30):
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
        # 支持 X-API-Key 头
        api_key = self.headers.get('X-API-Key')
        if api_key:
            return api_key
        
        # 支持 Authorization: Bearer <key>
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
        
        # 限流检查
        key_hash = hash_api_key(api_key)
        allowed, retry_after = check_rate_limit(key_hash)
        if not allowed:
            self.send_json_response({
                'error': 'Too Many Requests',
                'message': f'Rate limit exceeded. Retry after {int(retry_after)} seconds.',
                'retry_after': int(retry_after)
            }, 429, {'Retry-After': str(int(retry_after))})
            return None
        
        # 更新使用统计
        update_api_key_usage(key_info.get('key_id', 'admin'))
        
        return key_info
    
    def read_body(self):
        """读取请求体"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                return json.loads(body)
            except:
                return body
        return {}
    
    def log_message(self, format, *args):
        log(f"{self.client_address[0]} - {format % args}")
    
    # ============ GET请求 ============
    def do_GET(self):
        log(f"GET {self.path}")
        
        # 健康检查（不需要认证）
        if self.path == '/health' or self.path == '/v1/health':
            self.send_json_response({
                'status': 'healthy',
                'service': 'zongyuan-api-gateway',
                'version': 'V1.0',
                'did': 'DID-BR-000002',
                'trace': 'Ω₀⊂⊙∞⊂Ω',
                'upstream_services': {
                    'aiproxy': AIPROXY_URL,
                    'anchor': ANCHOR_URL,
                    'identity': IDENTITY_URL
                }
            })
            return
        
        # OpenAI兼容：模型列表
        if self.path == '/v1/models':
            key_info = self.authenticate(['models'])
            if not key_info:
                return
            
            # 从aiproxy获取模型列表
            status, body, headers = forward_request(f'{AIPROXY_URL}/models')
            if status == 200:
                try:
                    aiproxy_data = json.loads(body)
                    models = aiproxy_data.get('models', [])
                    # 转换为OpenAI格式
                    openai_models = {
                        'object': 'list',
                        'data': [
                            {
                                'id': model,
                                'object': 'model',
                                'created': 1700000000,
                                'owned_by': 'zongyuan-root'
                            }
                            for model in models
                        ]
                    }
                    self.send_json_response(openai_models)
                    return
                except:
                    pass
            
            # 如果aiproxy不可用，返回默认模型列表
            self.send_json_response({
                'object': 'list',
                'data': [
                    {'id': 'doubao', 'object': 'model', 'created': 1700000000, 'owned_by': 'zongyuan-root'},
                    {'id': 'hunyuan', 'object': 'model', 'created': 1700000000, 'owned_by': 'zongyuan-root'},
                    {'id': 'zhipu', 'object': 'model', 'created': 1700000000, 'owned_by': 'zongyuan-root'},
                    {'id': 'ollama-local', 'object': 'model', 'created': 1700000000, 'owned_by': 'zongyuan-root'}
                ]
            })
            return
        
        # 管理员：API Key列表
        if self.path == '/v1/admin/api-keys':
            key_info = self.authenticate(['admin'])
            if not key_info:
                return
            self.send_json_response({'api_keys': list_api_keys()})
            return
        
        # 内核状态
        if self.path == '/v1/kernel/status':
            key_info = self.authenticate(['kernel'])
            if not key_info:
                return
            # 转发到Anchor API
            status, body, headers = forward_request(f'{ANCHOR_URL}/api/v1/sync/handshake')
            self.send_json_response(json.loads(body) if status == 200 else {'error': 'Failed to get kernel status'}, status)
            return
        
        # 内核身份
        if self.path == '/v1/kernel/identity':
            key_info = self.authenticate(['kernel'])
            if not key_info:
                return
            status, body, headers = forward_request(f'{IDENTITY_URL}/api/v1/kernel/identity')
            self.send_json_response(json.loads(body) if status == 200 else {'error': 'Failed to get identity'}, status)
            return
        
        # 节点列表
        if self.path == '/v1/kernel/nodes/list':
            key_info = self.authenticate(['kernel'])
            if not key_info:
                return
            status, body, headers = forward_request(f'{IDENTITY_URL}/api/v1/kernel/nodes/list')
            self.send_json_response(json.loads(body) if status == 200 else {'error': 'Failed to get nodes'}, status)
            return
        
        # 使用统计
        if self.path == '/v1/usage':
            key_info = self.authenticate(['usage'])
            if not key_info:
                return
            status, body, headers = forward_request(f'{AIPROXY_URL}/usage')
            self.send_json_response(json.loads(body) if status == 200 else {'error': 'Failed to get usage'}, status)
            return
        
        self.send_json_response({'error': 'Not Found', 'path': self.path}, 404)
    
    # ============ POST请求 ============
    def do_POST(self):
        log(f"POST {self.path}")
        body = self.read_body()
        
        # OpenAI兼容：聊天补全
        if self.path == '/v1/chat/completions':
            key_info = self.authenticate(['chat'])
            if not key_info:
                return
            
            # 转换为aiproxy格式并转发
            model = body.get('model', 'doubao')
            messages = body.get('messages', [])
            stream = body.get('stream', False)
            
            # 转发到aiproxy的/chat端点
            aiproxy_body = {
                'model': model,
                'messages': messages,
                'stream': stream
            }
            
            status, resp_body, headers = forward_request(
                f'{AIPROXY_URL}/chat',
                method='POST',
                body=aiproxy_body,
                timeout=60
            )
            
            if status == 200:
                try:
                    aiproxy_resp = json.loads(resp_body)
                    # 转换为OpenAI格式
                    openai_resp = {
                        'id': 'chatcmpl-' + uuid.uuid4().hex[:24],
                        'object': 'chat.completion',
                        'created': int(time.time()),
                        'model': model,
                        'choices': [
                            {
                                'index': 0,
                                'message': {
                                    'role': 'assistant',
                                    'content': aiproxy_resp.get('response', aiproxy_resp.get('content', aiproxy_resp.get('message', '')))
                                },
                                'finish_reason': 'stop'
                            }
                        ],
                        'usage': aiproxy_resp.get('usage', {
                            'prompt_tokens': 0,
                            'completion_tokens': 0,
                            'total_tokens': 0
                        })
                    }
                    self.send_json_response(openai_resp)
                    return
                except Exception as e:
                    log(f"转换aiproxy响应失败: {e}, 原始响应: {resp_body[:200]}")
                    # 如果转换失败，直接返回原始响应
                    self.send_json_response(json.loads(resp_body) if resp_body else {'error': 'Empty response'}, status)
                    return
            
            self.send_json_response({'error': 'Upstream service error', 'status': status, 'response': resp_body[:500]}, status)
            return
        
        # 管理员：创建API Key
        if self.path == '/v1/admin/api-keys':
            key_info = self.authenticate(['admin'])
            if not key_info:
                return
            
            name = body.get('name', 'Unnamed Key')
            permissions = body.get('permissions', ['chat', 'models'])
            expires_at = body.get('expires_at')
            
            api_key, key_info_created = create_api_key(name, permissions, expires_at)
            self.send_json_response({
                'api_key': api_key,
                'key_id': key_info_created['key_id'],
                'name': name,
                'permissions': permissions,
                'created_at': key_info_created['created_at'],
                'message': '请保存好此API Key，之后无法再次查看'
            }, 201)
            return
        
        # 内核：推送真值
        if self.path == '/v1/kernel/truth/push':
            key_info = self.authenticate(['kernel'])
            if not key_info:
                return
            status, body, headers = forward_request(f'{ANCHOR_URL}/api/v1/sync/truth-push', method='POST', body=body)
            self.send_json_response(json.loads(body) if body else {'error': 'Empty response'}, status)
            return
        
        # 内核：拉取真值
        if self.path == '/v1/kernel/truth/pull':
            key_info = self.authenticate(['kernel'])
            if not key_info:
                return
            status, body, headers = forward_request(f'{ANCHOR_URL}/api/v1/sync/truth-pull', method='POST', body=body)
            self.send_json_response(json.loads(body) if body else {'error': 'Empty response'}, status)
            return
        
        # 内核：节点心跳
        if self.path == '/v1/kernel/nodes/heartbeat':
            key_info = self.authenticate(['kernel'])
            if not key_info:
                return
            status, body, headers = forward_request(f'{IDENTITY_URL}/api/v1/kernel/nodes/heartbeat', method='POST', body=body)
            self.send_json_response(json.loads(body) if body else {'error': 'Empty response'}, status)
            return
        
        # 内核：节点注册
        if self.path == '/v1/kernel/nodes/register':
            key_info = self.authenticate(['kernel'])
            if not key_info:
                return
            status, body, headers = forward_request(f'{IDENTITY_URL}/api/v1/kernel/nodes/register', method='POST', body=body)
            self.send_json_response(json.loads(body) if body else {'error': 'Empty response'}, status)
            return
        
        self.send_json_response({'error': 'Not Found', 'path': self.path}, 404)
    
    # ============ DELETE请求 ============
    def do_DELETE(self):
        log(f"DELETE {self.path}")
        
        # 管理员：吊销API Key
        if self.path.startswith('/v1/admin/api-keys/'):
            key_info = self.authenticate(['admin'])
            if not key_info:
                return
            
            key_id = self.path.split('/')[-1]
            if revoke_api_key(key_id):
                self.send_json_response({'status': 'revoked', 'key_id': key_id})
            else:
                self.send_json_response({'error': 'API Key not found'}, 404)
            return
        
        self.send_json_response({'error': 'Not Found', 'path': self.path}, 404)

# ============ 主函数 ============
def main():
    init_api_keys()
    
    server = HTTPServer(('0.0.0.0', PORT), GatewayHandler)
    log(f"=" * 60)
    log(f"ZONGYUAN-ROOT 统一API网关 V1.0 启动")
    log(f"端口: {PORT}")
    log(f"管理员API Key: {ADMIN_API_KEY}")
    log(f"上游服务:")
    log(f"  - aiproxy: {AIPROXY_URL}")
    log(f"  - anchor: {ANCHOR_URL}")
    log(f"  - identity: {IDENTITY_URL}")
    log(f"OpenAI兼容端点:")
    log(f"  - GET /v1/models")
    log(f"  - POST /v1/chat/completions")
    log(f"  - GET /v1/health")
    log(f"认证方式: X-API-Key 头 或 Authorization: Bearer <key>")
    log(f"=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("API网关已停止")
        server.shutdown()

if __name__ == '__main__':
    main()
