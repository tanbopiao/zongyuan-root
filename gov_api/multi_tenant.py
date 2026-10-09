#!/usr/bin/env python3
"""
多租户SaaS管理模块
功能：租户创建、配置管理、数据隔离、租户统计
确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import hashlib
import datetime
import uuid

DATA_DIR = '/opt/ZONGYUAN-ROOT/gov_api/data/tenants'
os.makedirs(DATA_DIR, exist_ok=True)

def _load_json(filename, default=None):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}

def _save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def create_tenant(name, domain, plan='standard', config=None):
    """创建租户"""
    tenants = _load_json('tenants.json', {})
    
    tenant_id = 'TENANT-' + uuid.uuid4().hex[:8].upper()
    api_key = 'zk-' + hashlib.sha256(f'{tenant_id}{name}{datetime.datetime.now()}'.encode()).hexdigest()[:32]
    
    tenant = {
        'tenant_id': tenant_id,
        'name': name,
        'domain': domain,
        'plan': plan,  # trial/standard/professional/enterprise
        'status': 'active',
        'api_key': api_key,
        'config': config or {
            'max_users': 10 if plan == 'trial' else 50 if plan == 'standard' else 200 if plan == 'professional' else 9999,
            'max_storage_gb': 1 if plan == 'trial' else 10 if plan == 'standard' else 50 if plan == 'professional' else 500,
            'ai_calls_per_day': 100 if plan == 'trial' else 1000 if plan == 'standard' else 5000 if plan == 'professional' else 50000,
            'custom_domain': plan in ('professional', 'enterprise'),
            'data_export': plan != 'trial',
            'priority_support': plan in ('professional', 'enterprise')
        },
        'created_at': datetime.datetime.now().isoformat(),
        'expires_at': (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat() if plan == 'trial' else None,
        'usage': {
            'users': 0,
            'ai_calls_today': 0,
            'storage_mb': 0,
            'last_reset': datetime.datetime.now().strftime('%Y-%m-%d')
        }
    }
    
    tenants[tenant_id] = tenant
    _save_json('tenants.json', tenants)
    
    # 创建租户专属数据目录
    tenant_data_dir = os.path.join(DATA_DIR, tenant_id)
    os.makedirs(tenant_data_dir, exist_ok=True)
    
    return {
        'success': True,
        'tenant_id': tenant_id,
        'api_key': api_key,
        'name': name,
        'plan': plan,
        'config': tenant['config']
    }

def get_tenant(tenant_id):
    """获取租户信息"""
    tenants = _load_json('tenants.json', {})
    if tenant_id in tenants:
        tenant = tenants[tenant_id].copy()
        tenant.pop('api_key', None)  # 不返回API密钥
        return tenant
    return {'error': '租户不存在', 'code': 404}

def verify_api_key(api_key):
    """验证API密钥，返回租户ID"""
    tenants = _load_json('tenants.json', {})
    for tid, tenant in tenants.items():
        if tenant.get('api_key') == api_key:
            if tenant['status'] != 'active':
                return None, '租户已停用'
            return tid, None
    return None, 'API密钥无效'

def update_tenant_config(tenant_id, config_updates):
    """更新租户配置"""
    tenants = _load_json('tenants.json', {})
    if tenant_id not in tenants:
        return {'error': '租户不存在', 'code': 404}
    
    tenants[tenant_id]['config'].update(config_updates)
    tenants[tenant_id]['updated_at'] = datetime.datetime.now().isoformat()
    _save_json('tenants.json', tenants)
    
    return {'success': True, 'tenant_id': tenant_id, 'config': tenants[tenant_id]['config']}

def record_usage(tenant_id, usage_type, amount=1):
    """记录租户使用量"""
    tenants = _load_json('tenants.json', {})
    if tenant_id not in tenants:
        return False
    
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    if tenants[tenant_id]['usage'].get('last_reset') != today:
        tenants[tenant_id]['usage']['ai_calls_today'] = 0
        tenants[tenant_id]['usage']['last_reset'] = today
    
    if usage_type == 'ai_call':
        tenants[tenant_id]['usage']['ai_calls_today'] += amount
    elif usage_type == 'user':
        tenants[tenant_id]['usage']['users'] += amount
    elif usage_type == 'storage':
        tenants[tenant_id]['usage']['storage_mb'] += amount
    
    _save_json('tenants.json', tenants)
    return True

def check_quota(tenant_id, usage_type):
    """检查租户配额"""
    tenants = _load_json('tenants.json', {})
    if tenant_id not in tenants:
        return False, '租户不存在'
    
    tenant = tenants[tenant_id]
    config = tenant['config']
    usage = tenant['usage']
    
    if usage_type == 'ai_call':
        if usage['ai_calls_today'] >= config['ai_calls_per_day']:
            return False, '今日AI调用配额已用完'
    elif usage_type == 'user':
        if usage['users'] >= config['max_users']:
            return False, '用户数已达上限'
    
    return True, None

def list_tenants(limit=50):
    """列出所有租户"""
    tenants = _load_json('tenants.json', {})
    result = []
    for tid, tenant in tenants.items():
        t = tenant.copy()
        t.pop('api_key', None)
        result.append(t)
    result.sort(key=lambda x: x['created_at'], reverse=True)
    return {'tenants': result[:limit], 'total': len(result)}

def get_stats():
    """获取多租户统计"""
    tenants = _load_json('tenants.json', {})
    plans = {}
    total_ai_calls = 0
    total_users = 0
    
    for tenant in tenants.values():
        plan = tenant.get('plan', 'unknown')
        plans[plan] = plans.get(plan, 0) + 1
        total_ai_calls += tenant.get('usage', {}).get('ai_calls_today', 0)
        total_users += tenant.get('usage', {}).get('users', 0)
    
    return {
        'total_tenants': len(tenants),
        'active_tenants': len([t for t in tenants.values() if t['status'] == 'active']),
        'plans': plans,
        'total_ai_calls_today': total_ai_calls,
        'total_users': total_users
    }

# 初始化默认租户
if not os.path.exists(os.path.join(DATA_DIR, 'tenants.json')):
    create_tenant('默认租户', 'huodouai.com', 'enterprise', {'max_users': 9999, 'custom_domain': True})
    print('多租户系统初始化完成，默认租户已创建')
