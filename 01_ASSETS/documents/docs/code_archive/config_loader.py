#!/usr/bin/env python3
"""
元极恒一｜统一配置加载器
支持从meta_rules.json加载配置，支持热加载（文件变更自动重新加载）
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_DIR = Path(__file__).parent.parent / "config"
META_RULES_PATH = CONFIG_DIR / "meta_rules.json"
ENV_PATH = CONFIG_DIR / "env.json"


class ConfigLoader:
    """统一配置加载器，支持热加载"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._meta_rules: Dict[str, Any] = {}
        self._env: Dict[str, Any] = {}
        self._meta_mtime: float = 0
        self._env_mtime: float = 0
        self._reload_count = 0
        self._load_all()

    def _load_all(self):
        """加载所有配置文件"""
        self._load_meta_rules()
        self._load_env()

    def _load_meta_rules(self):
        """加载元规则配置"""
        if not META_RULES_PATH.exists():
            self._meta_rules = {}
            return
        try:
            with open(META_RULES_PATH, "r", encoding="utf-8") as f:
                self._meta_rules = json.load(f)
            self._meta_mtime = os.path.getmtime(META_RULES_PATH)
        except Exception as e:
            print(f"[ConfigLoader] 加载meta_rules.json失败: {e}")
            self._meta_rules = {}

    def _load_env(self):
        """加载环境配置"""
        if not ENV_PATH.exists():
            self._env = {}
            return
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                self._env = json.load(f)
            self._env_mtime = os.path.getmtime(ENV_PATH)
        except Exception as e:
            print(f"[ConfigLoader] 加载env.json失败: {e}")
            self._env = {}

    def _check_reload(self):
        """检查配置文件是否变更，变更则热加载"""
        try:
            if META_RULES_PATH.exists():
                current_mtime = os.path.getmtime(META_RULES_PATH)
                if current_mtime > self._meta_mtime:
                    print(f"[ConfigLoader] meta_rules.json变更，热加载中...")
                    self._load_meta_rules()
                    self._reload_count += 1
                    print(f"[ConfigLoader] 热加载完成（第{self._reload_count}次）")
            if ENV_PATH.exists():
                current_mtime = os.path.getmtime(ENV_PATH)
                if current_mtime > self._env_mtime:
                    self._load_env()
        except Exception:
            pass

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值，支持点分路径
        例如: get("master.loop_interval") -> 15
        """
        self._check_reload()
        keys = key_path.split(".")
        value = self._meta_rules
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """获取整个配置段"""
        self._check_reload()
        return self._meta_rules.get(section, {})

    def get_env(self, key: str, default: Any = None) -> Any:
        """获取环境配置"""
        self._check_reload()
        return self._env.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """获取全部元规则配置"""
        self._check_reload()
        return self._meta_rules.copy()

    def reload(self):
        """强制重新加载所有配置"""
        self._load_all()
        self._reload_count += 1

    @property
    def reload_count(self) -> int:
        return self._reload_count

    @property
    def meta_rules_version(self) -> str:
        return self._meta_rules.get("meta_rules_version", "unknown")


# 全局单例
config = ConfigLoader()


def get_config() -> ConfigLoader:
    """获取全局配置加载器"""
    return config


if __name__ == "__main__":
    # 测试
    print("=== 配置加载器测试 ===")
    print(f"元规则版本: {config.meta_rules_version}")
    print(f"主中枢循环间隔: {config.get('master.loop_interval')}")
    print(f"仪表盘端口: {config.get('dashboard.port')}")
    print(f"网关URL: {config.get('gateway.base_url')}")
    print(f"热加载次数: {config.reload_count}")
    print("=== 测试完成 ===")
