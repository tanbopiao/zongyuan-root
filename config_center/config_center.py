#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 统一配置中心 P1-1
集中管理所有服务配置，一处修改全网生效
"""

import os
import json
import yaml
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# 配置中心根目录
CONFIG_ROOT = Path("/opt/zongyuan/config")
CONFIG_ROOT.mkdir(parents=True, exist_ok=True)

# 全局配置文件
GLOBAL_CONFIG_FILE = CONFIG_ROOT / "global_config.yaml"

# 配置变更审计日志
AUDIT_LOG_FILE = CONFIG_ROOT / "config_audit.json"

# 配置版本历史
VERSION_HISTORY_FILE = CONFIG_ROOT / "config_versions.json"


class ConfigCenter:
    """统一配置中心"""
    
    def __init__(self):
        self.config = self._load_config()
        self._ensure_defaults()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载全局配置"""
        if GLOBAL_CONFIG_FILE.exists():
            with open(GLOBAL_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _save_config(self):
        """保存全局配置"""
        with open(GLOBAL_CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        # 计算配置哈希
        config_hash = hashlib.sha256(
            json.dumps(self.config, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()[:16]
        
        # 记录版本
        self._record_version(config_hash)
    
    def _ensure_defaults(self):
        """确保默认配置存在"""
        defaults = {
            'meta': {
                'version': '1.0.0',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'description': 'ZONGYUAN-ROOT统一配置中心'
            },
            'services': {
                'aios': {
                    'host': '127.0.0.1',
                    'port': 8765,
                    'path': '/opt/aios',
                    'log': '/var/log/aios/backend.log',
                    'status': 'active'
                },
                'omega_brain': {
                    'host': '127.0.0.1',
                    'port': 8000,
                    'path': '/opt/ZONGYUAN-ROOT/omega_brain',
                    'status': 'active'
                },
                'loip': {
                    'host': '127.0.0.1',
                    'port': 8001,
                    'path': '/opt/ZONGYUAN-ROOT/loip',
                    'status': 'active'
                },
                'anchor': {
                    'host': '127.0.0.1',
                    'port': 8006,
                    'path': '/opt/ZONGYUAN-ROOT/anchor',
                    'status': 'active'
                },
                'gov_platform': {
                    'host': '127.0.0.1',
                    'port': 8010,
                    'path': '/opt/gov-ai-platform',
                    'status': 'active'
                },
                'nginx': {
                    'host': '0.0.0.0',
                    'http_port': 80,
                    'https_port': 443,
                    'config': '/www/server/panel/vhost/nginx/huodouai.com.conf',
                    'status': 'active'
                },
                'mysql': {
                    'host': '127.0.0.1',
                    'port': 3306,
                    'status': 'active'
                },
                'redis': {
                    'host': '127.0.0.1',
                    'port': 6379,
                    'status': 'active'
                },
                'frp_server': {
                    'host': '0.0.0.0',
                    'port': 7100,
                    'status': 'active'
                },
                'bt_panel': {
                    'host': '0.0.0.0',
                    'port': 8888,
                    'path': '/www/server/panel',
                    'status': 'active'
                }
            },
            'domains': {
                'primary': 'huodouai.com',
                'www': 'www.huodouai.com',
                'ssl_expiry': '2026-11-02'
            },
            'paths': {
                'aios': '/opt/aios',
                'zongyuan_root': '/opt/ZONGYUAN-ROOT',
                'web_root': '/www/wwwroot/huodouai.com',
                'workbench': '/www/wwwroot/huodouai.com/workbench',
                'gov_platform': '/www/wwwroot/huodouai.com/gov',
                'logs': '/var/log',
                'config': '/opt/zongyuan/config'
            },
            'security': {
                'env_file_permission': '600',
                'internal_ports': [8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010, 8011, 8021, 8765, 3306, 6379],
                'public_ports': [22, 80, 443, 7100, 8888],
                'rate_limit': {
                    'api': '10r/s',
                    'general': '30r/s'
                }
            },
            'monitoring': {
                'check_interval': '*/5 * * * *',
                'cpu_threshold': 80,
                'memory_threshold': 90,
                'disk_threshold': 85,
                'log_retention_days': 7
            }
        }
        
        # 合并默认配置（不覆盖已有配置）
        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value
        
        self.config['meta']['updated_at'] = datetime.now().isoformat()
    
    def _record_version(self, config_hash: str):
        """记录配置版本"""
        versions = []
        if VERSION_HISTORY_FILE.exists():
            with open(VERSION_HISTORY_FILE, 'r', encoding='utf-8') as f:
                versions = json.load(f)
        
        versions.append({
            'hash': config_hash,
            'timestamp': datetime.now().isoformat(),
            'changes': 'config updated'
        })
        
        # 只保留最近50个版本
        versions = versions[-50:]
        
        with open(VERSION_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(versions, f, ensure_ascii=False, indent=2)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """获取配置（支持点分隔路径，如 'services.aios.port'）"""
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path: str, value: Any, reason: str = ""):
        """设置配置"""
        keys = key_path.split('.')
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
        
        self.config['meta']['updated_at'] = datetime.now().isoformat()
        self._save_config()
        
        # 记录审计日志
        self._audit_log('SET', key_path, value, reason)
    
    def _audit_log(self, action: str, key: str, value: Any, reason: str):
        """记录审计日志"""
        logs = []
        if AUDIT_LOG_FILE.exists():
            with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        
        logs.append({
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'key': key,
            'value': str(value)[:200],
            'reason': reason
        })
        
        # 只保留最近1000条
        logs = logs[-1000:]
        
        with open(AUDIT_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    
    def get_service(self, name: str) -> Optional[Dict]:
        """获取服务配置"""
        return self.config.get('services', {}).get(name)
    
    def list_services(self) -> Dict[str, Dict]:
        """列出所有服务"""
        return self.config.get('services', {})
    
    def get_port(self, service_name: str) -> Optional[int]:
        """获取服务端口"""
        service = self.get_service(service_name)
        return service.get('port') if service else None
    
    def export_env(self, service_name: str) -> str:
        """导出服务的环境变量格式"""
        service = self.get_service(service_name)
        if not service:
            return ""
        
        lines = [f"# {service_name} 服务配置"]
        for key, value in service.items():
            if isinstance(value, (str, int, float, bool)):
                env_key = f"{service_name.upper()}_{key.upper()}"
                lines.append(f"{env_key}={value}")
        return "\n".join(lines)
    
    def status_summary(self) -> Dict:
        """配置状态摘要"""
        return {
            'config_version': self.config.get('meta', {}).get('version'),
            'updated_at': self.config.get('meta', {}).get('updated_at'),
            'services_count': len(self.config.get('services', {})),
            'active_services': sum(1 for s in self.config.get('services', {}).values() if s.get('status') == 'active'),
            'domains': self.config.get('domains', {}),
            'security_ports': {
                'public': self.config.get('security', {}).get('public_ports', []),
                'internal': self.config.get('security', {}).get('internal_ports', [])
            }
        }


def main():
    """命令行入口"""
    import sys
    
    center = ConfigCenter()
    
    if len(sys.argv) < 2:
        # 默认显示状态摘要
        print("=" * 60)
        print("ZONGYUAN-ROOT 统一配置中心")
        print("=" * 60)
        summary = center.status_summary()
        print(f"配置版本: {summary['config_version']}")
        print(f"更新时间: {summary['updated_at']}")
        print(f"服务总数: {summary['services_count']} (活跃: {summary['active_services']})")
        print(f"主域名: {summary['domains'].get('primary')}")
        print(f"SSL到期: {summary['domains'].get('ssl_expiry')}")
        print(f"公网端口: {', '.join(map(str, summary['security_ports']['public']))}")
        print(f"内部端口: {len(summary['security_ports']['internal'])}个 (仅本地访问)")
        print()
        print("服务列表:")
        for name, service in center.list_services().items():
            status_icon = "✅" if service.get('status') == 'active' else "❌"
            port = service.get('port', service.get('http_port', 'N/A'))
            print(f"  {status_icon} {name}: 127.0.0.1:{port}")
        print()
        print("使用方法:")
        print("  python3 config_center.py get <key>     # 获取配置")
        print("  python3 config_center.py set <key> <value>  # 设置配置")
        print("  python3 config_center.py services      # 列出服务")
        print("  python3 config_center.py export <service>  # 导出环境变量")
        return
    
    command = sys.argv[1]
    
    if command == 'get' and len(sys.argv) >= 3:
        key = sys.argv[2]
        value = center.get(key)
        print(f"{key} = {json.dumps(value, ensure_ascii=False, indent=2) if isinstance(value, (dict, list)) else value}")
    
    elif command == 'set' and len(sys.argv) >= 4:
        key = sys.argv[2]
        value = sys.argv[3]
        reason = sys.argv[4] if len(sys.argv) >= 5 else ""
        center.set(key, value, reason)
        print(f"✅ 已设置 {key} = {value}")
    
    elif command == 'services':
        for name, service in center.list_services().items():
            print(f"{name}: {json.dumps(service, ensure_ascii=False)}")
    
    elif command == 'export' and len(sys.argv) >= 3:
        service = sys.argv[2]
        print(center.export_env(service))
    
    else:
        print(f"未知命令: {command}")


if __name__ == '__main__':
    main()
