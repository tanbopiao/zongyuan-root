#!/usr/bin/env python3
"""
API网关与Key管理体系
API Key生成、管理、鉴权、计量、限流
"""
import os
import json
import hashlib
import secrets
import time
from datetime import datetime, timedelta

API_DIR = '/opt/ZONGYUAN-ROOT/api_gateway'
KEYS_FILE = os.path.join(API_DIR, 'api_keys.json')
USAGE_FILE = os.path.join(API_DIR, 'usage_log.json')

class APIKeyManager:
    """API Key管理器"""
    
    def __init__(self):
        os.makedirs(API_DIR, exist_ok=True)
        self.keys = self._load_keys()
        self.usage = self._load_usage()
    
    def _load_keys(self):
        """加载API Keys"""
        if os.path.exists(KEYS_FILE):
            with open(KEYS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_keys(self):
        """保存API Keys"""
        with open(KEYS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.keys, f, ensure_ascii=False, indent=2)
    
    def _load_usage(self):
        """加载使用日志"""
        if os.path.exists(USAGE_FILE):
            with open(USAGE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_usage(self):
        """保存使用日志"""
        with open(USAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.usage, f, ensure_ascii=False, indent=2)
    
    def generate_key(self, name, scope='read', rate_limit=100, expires_days=365):
        """生成新的API Key"""
        api_key = 'zy-' + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        key_info = {
            'name': name,
            'key_hash': key_hash,
            'scope': scope,  # read/write/admin
            'rate_limit': rate_limit,  # 每分钟请求数
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=expires_days)).isoformat(),
            'status': 'active',
            'usage_count': 0,
            'last_used': None
        }
        
        self.keys[key_hash] = key_info
        self._save_keys()
        
        return {
            'api_key': api_key,
            'key_hash': key_hash,
            'name': name,
            'scope': scope,
            'rate_limit': rate_limit,
            'expires_at': key_info['expires_at']
        }
    
    def validate_key(self, api_key, required_scope='read'):
        """验证API Key"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        if key_hash not in self.keys:
            return {'valid': False, 'error': '无效的API Key'}
        
        key_info = self.keys[key_hash]
        
        # 检查状态
        if key_info['status'] != 'active':
            return {'valid': False, 'error': f'API Key已{key_info["status"]}'}
        
        # 检查过期
        expires_at = datetime.fromisoformat(key_info['expires_at'])
        if datetime.now() > expires_at:
            return {'valid': False, 'error': 'API Key已过期'}
        
        # 检查权限范围
        scope_levels = {'read': 1, 'write': 2, 'admin': 3}
        if scope_levels.get(key_info['scope'], 0) < scope_levels.get(required_scope, 0):
            return {'valid': False, 'error': f'权限不足，需要{required_scope}权限'}
        
        # 检查限流
        now = datetime.now()
        minute_key = now.strftime('%Y-%m-%d %H:%M')
        if minute_key not in self.usage:
            self.usage[minute_key] = {}
        if key_hash not in self.usage[minute_key]:
            self.usage[minute_key][key_hash] = 0
        
        if self.usage[minute_key][key_hash] >= key_info['rate_limit']:
            return {'valid': False, 'error': '超过限流阈值'}
        
        # 更新使用记录
        self.usage[minute_key][key_hash] += 1
        key_info['usage_count'] += 1
        key_info['last_used'] = now.isoformat()
        self._save_keys()
        self._save_usage()
        
        return {
            'valid': True,
            'name': key_info['name'],
            'scope': key_info['scope'],
            'usage_count': key_info['usage_count']
        }
    
    def revoke_key(self, api_key):
        """吊销API Key"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if key_hash in self.keys:
            self.keys[key_hash]['status'] = 'revoked'
            self._save_keys()
            return {'success': True, 'message': 'API Key已吊销'}
        return {'success': False, 'error': 'API Key不存在'}
    
    def list_keys(self):
        """列出所有API Keys（不显示完整Key）"""
        return [
            {
                'name': info['name'],
                'key_hash': key_hash[:16] + '...',
                'scope': info['scope'],
                'status': info['status'],
                'usage_count': info['usage_count'],
                'created_at': info['created_at'],
                'expires_at': info['expires_at']
            }
            for key_hash, info in self.keys.items()
        ]
    
    def get_stats(self):
        """获取API网关统计"""
        total_keys = len(self.keys)
        active_keys = sum(1 for k in self.keys.values() if k['status'] == 'active')
        total_usage = sum(k['usage_count'] for k in self.keys.values())
        
        return {
            'total_keys': total_keys,
            'active_keys': active_keys,
            'revoked_keys': total_keys - active_keys,
            'total_usage': total_usage,
            'api_gateway_status': 'active'
        }


def main():
    """主函数 - 初始化API网关"""
    print("=" * 60)
    print("API网关与Key管理体系 - 初始化")
    print("=" * 60)
    
    manager = APIKeyManager()
    
    # 生成默认管理Key
    print("\n【1. 生成默认管理Key】")
    admin_key = manager.generate_key(
        name='default-admin',
        scope='admin',
        rate_limit=1000,
        expires_days=365
    )
    print(f"  ✅ 管理Key已生成: {admin_key['api_key'][:20]}...")
    print(f"  ⚠️  请妥善保存此Key，仅显示一次")
    
    # 生成只读Key
    print("\n【2. 生成只读Key】")
    read_key = manager.generate_key(
        name='default-readonly',
        scope='read',
        rate_limit=100,
        expires_days=365
    )
    print(f"  ✅ 只读Key已生成: {read_key['api_key'][:20]}...")
    
    # 验证Key
    print("\n【3. 验证Key有效性】")
    result = manager.validate_key(admin_key['api_key'], 'admin')
    print(f"  ✅ 管理Key验证: {'通过' if result['valid'] else '失败'}")
    
    result = manager.validate_key(read_key['api_key'], 'read')
    print(f"  ✅ 只读Key验证: {'通过' if result['valid'] else '失败'}")
    
    # 统计
    print("\n【4. API网关统计】")
    stats = manager.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("✅ API网关与Key管理体系初始化完成！")
    print("=" * 60)
    
    return manager

if __name__ == '__main__':
    main()
