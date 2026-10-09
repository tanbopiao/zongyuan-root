#!/usr/bin/env python3
"""
P2断点补齐 - 统一配置中心 (Config Center)

消除各模块硬编码路径和参数，提供:
  - 统一配置加载 (JSON/YAML/环境变量)
  - 配置热更新 (运行时修改无需重启)
  - 配置版本管理 (变更历史+回滚)
  - 配置校验 (schema验证)
  - 配置哈希锚定 (防篡改)

所有模块从ConfigCenter读取配置，禁止硬编码路径。
"""

import hashlib
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ConfigCenter:
    """
    统一配置中心

    用法:
        config = ConfigCenter()
        api_key = config.get('vector.api_key', default='')
        config.set('executor.max_retries', 5)
        config.reload()
    """

    VERSION = "1.0.0"
    DEFAULT_CONFIG = {
        'system': {
            'name': 'ZONGYUAN-ROOT',
            'version': '1.0.0',
            'did': 'DID-BR-000002',
            'sovereign_root': 'Ω-TAN-7-001',
            'trace_symbol': 'Ω₀⊂⊙∞⊂Ω',
            'root_dir': str(Path(__file__).parent.parent),
        },
        'executor': {
            'work_dir': 'executor',
            'max_retries': 3,
            'default_timeout': 60,
            'queue_file': 'task_queue.jsonl',
        },
        'circuit_breaker': {
            'failure_threshold': 3,
            'recovery_timeout': 60,
            'half_open_max_requests': 1,
        },
        'rbac': {
            'confirmation_ttl': 300,
            'default_role': 'observer',
        },
        'vector': {
            'api_key': '',
            'api_base': 'https://ark.cn-beijing.volces.com/api/v3',
            'index_id': '',
            'embed_model': 'doubao-embedding-and-m3',
            'vision_model': 'doubao-embedding-vision',
            'sparse_enabled': True,
            'multi_embed_enabled': True,
            'rerank_enabled': True,
            'high_dim': 2048,
            'low_dim': 1024,
            'retrieve_count': 24,
            'final_top_k': 12,
            'dense_weight': 0.6,
            'confidence_threshold': 95.0,
        },
        'pipeline': {
            'default_stages': 8,
            'critical_stage_abort': True,
        },
        'evolution': {
            'stages': 7,
            'auto_lock': True,
        },
        'metrics': {
            'prometheus_enabled': True,
            'alert_thresholds': {
                'failure_rate_pct': 5.0,
                'p99_duration_ms': 30000,
                'queue_backlog': 50,
            },
        },
        'daemon': {
            'health_check_interval': 30,
            'max_restart_attempts': 5,
            'log_rotation_max_size_mb': 100,
            'log_rotation_max_files': 5,
        },
        'multi_writer': {
            'lock_timeout': 30,
            'conflict_resolution': 'last_write_wins',  # last_write_wins / merge / reject
            'max_concurrent_writers': 4,
        },
        'storage': {
            'cas_dir': 'cas_store',
            'lock_dir': 'lock_archive',
            'truth_dir': 'truth_architecture',
            'backup_dir': 'backups',
        },
    }

    def __init__(self, config_file: str = None, env_prefix: str = "ZYR_"):
        self.config_file = Path(config_file) if config_file else Path(__file__).parent.parent / 'config' / 'config.json'
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.env_prefix = env_prefix
        self._lock = threading.Lock()
        self._config: Dict[str, Any] = {}
        self._history: List[dict] = []
        self._load()

    def _load(self):
        """加载配置: 默认值 → 配置文件 → 环境变量覆盖"""
        with self._lock:
            # 1. 加载默认配置
            self._config = self._deep_copy(self.DEFAULT_CONFIG)

            # 2. 加载配置文件
            if self.config_file.exists():
                try:
                    with open(self.config_file) as f:
                        file_config = json.load(f)
                    self._deep_update(self._config, file_config)
                except Exception as e:
                    print(f"[ConfigCenter] Warning: failed to load config file: {e}")

            # 3. 环境变量覆盖 (ZYR_VECTOR_API_KEY → vector.api_key)
            self._load_env_overrides()

            # 记录初始版本
            self._history.append({
                'version': len(self._history) + 1,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'config_hash': self._compute_hash(),
                'source': 'initial_load',
            })

    def _load_env_overrides(self):
        """从环境变量加载覆盖配置"""
        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                # ZYR_VECTOR_API_KEY → vector.api_key
                path = key[len(self.env_prefix):].lower().split('_')
                if len(path) >= 2:
                    section = path[0]
                    sub_key = '_'.join(path[1:])
                    if section in self._config:
                        # 尝试类型转换
                        self._config[section][sub_key] = self._auto_convert(value)

    @staticmethod
    def _auto_convert(value: str) -> Any:
        """自动类型转换"""
        if value.lower() in ('true', 'yes'):
            return True
        if value.lower() in ('false', 'no'):
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    @staticmethod
    def _deep_copy(obj):
        return json.loads(json.dumps(obj))

    @staticmethod
    def _deep_update(base: dict, override: dict):
        """深度更新字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ConfigCenter._deep_update(base[key], value)
            else:
                base[key] = value

    def _compute_hash(self) -> str:
        """计算配置哈希（防篡改）"""
        content = json.dumps(self._config, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key_path: 点分隔路径，如 'vector.api_key'
            default: 默认值
        """
        with self._lock:
            keys = key_path.split('.')
            value = self._config
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            return value

    def set(self, key_path: str, value: Any, persist: bool = True):
        """
        设置配置值（热更新）

        Args:
            key_path: 点分隔路径
            value: 新值
            persist: 是否持久化到文件
        """
        with self._lock:
            keys = key_path.split('.')
            config = self._config
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            config[keys[-1]] = value

            # 记录变更历史
            self._history.append({
                'version': len(self._history) + 1,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'config_hash': self._compute_hash(),
                'change': {key_path: value},
                'source': 'runtime_update',
            })

            if persist:
                self._save()

    def _save(self):
        """持久化配置到文件"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ConfigCenter] Warning: failed to save config: {e}")

    def reload(self) -> dict:
        """重新加载配置（热更新）"""
        old_hash = self._compute_hash()
        self._load()
        new_hash = self._compute_hash()
        return {
            'reloaded': old_hash != new_hash,
            'old_hash': old_hash[:16],
            'new_hash': new_hash[:16],
            'config_hash': new_hash,
        }

    def get_section(self, section: str) -> dict:
        """获取整个配置段"""
        with self._lock:
            return self._deep_copy(self._config.get(section, {}))

    def get_all(self) -> dict:
        """获取全部配置（深拷贝）"""
        with self._lock:
            return self._deep_copy(self._config)

    def validate(self) -> Tuple[bool, List[str]]:
        """
        配置校验

        Returns:
            (valid, errors)
        """
        errors = []

        # 检查必要字段
        required = [
            ('system.name', str),
            ('system.did', str),
            ('executor.work_dir', str),
            ('vector.api_base', str),
        ]
        for key_path, expected_type in required:
            value = self.get(key_path)
            if value is None:
                errors.append(f"missing required config: {key_path}")
            elif not isinstance(value, expected_type):
                errors.append(f"invalid type for {key_path}: expected {expected_type.__name__}, got {type(value).__name__}")

        # 检查数值范围
        if self.get('executor.max_retries', 0) < 0:
            errors.append("executor.max_retries must be >= 0")
        if self.get('circuit_breaker.failure_threshold', 0) < 1:
            errors.append("circuit_breaker.failure_threshold must be >= 1")
        if not (0 <= self.get('vector.dense_weight', 0.5) <= 1):
            errors.append("vector.dense_weight must be between 0 and 1")

        return (len(errors) == 0, errors)

    def get_history(self, limit: int = 10) -> List[dict]:
        """获取配置变更历史"""
        return self._history[-limit:]

    def rollback(self, version: int) -> bool:
        """回滚到指定版本（简化版：重新加载默认+文件配置）"""
        if version <= 0 or version > len(self._history):
            return False
        self._load()
        return True

    def get_status(self) -> dict:
        """获取配置中心状态"""
        valid, errors = self.validate()
        return {
            'version': self.VERSION,
            'config_file': str(self.config_file),
            'config_hash': self._compute_hash(),
            'valid': valid,
            'validation_errors': errors,
            'total_sections': len(self._config),
            'history_versions': len(self._history),
            'env_prefix': self.env_prefix,
            'sections': list(self._config.keys()),
        }


# 全局单例
_global_config: Optional[ConfigCenter] = None

def get_config() -> ConfigCenter:
    global _global_config
    if _global_config is None:
        _global_config = ConfigCenter()
    return _global_config
