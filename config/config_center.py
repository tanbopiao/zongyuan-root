#!/usr/bin/env python3
"""
P2-6: 统一配置中心
集中管理所有配置，消除硬编码
"""
import json
from pathlib import Path
from typing import Any, Optional

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
CONFIG_DIR = ROOT / "config"

class ConfigCenter:
    """统一配置中心"""
    
    def __init__(self):
        self._configs = {}
        self._load_all()
    
    def _load_all(self):
        """加载所有配置文件"""
        if not CONFIG_DIR.exists():
            return
        for fp in CONFIG_DIR.glob("*.json"):
            try:
                with open(fp) as f:
                    self._configs[fp.stem] = json.load(f)
            except:
                pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置，支持点分隔路径
        例如: get("rag_config.mode")
        """
        parts = key.split(".")
        if len(parts) == 1:
            return self._configs.get(key, default)
        config = self._configs.get(parts[0], {})
        for part in parts[1:]:
            if isinstance(config, dict):
                config = config.get(part, default)
            else:
                return default
        return config
    
    def set(self, key: str, value: Any):
        """设置配置"""
        parts = key.split(".")
        if len(parts) == 1:
            self._configs[key] = value
        else:
            if parts[0] not in self._configs:
                self._configs[parts[0]] = {}
            config = self._configs[parts[0]]
            for part in parts[1:-1]:
                if part not in config:
                    config[part] = {}
                config = config[part]
            config[parts[-1]] = value
    
    def save(self, config_name: str):
        """保存指定配置到文件"""
        if config_name in self._configs:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_DIR / f"{config_name}.json", "w") as f:
                json.dump(self._configs[config_name], f, ensure_ascii=False, indent=2)
    
    def get_all(self) -> dict:
        """获取所有配置（脱敏）"""
        result = {}
        for k, v in self._configs.items():
            if isinstance(v, dict):
                result[k] = {
                    key: ("***" if any(s in key.lower() for s in ["key", "secret", "password", "token"]) else val)
                    for key, val in v.items()
                }
            else:
                result[k] = v
        return result

# 全局单例
_config_center = None

def get_config() -> ConfigCenter:
    global _config_center
    if _config_center is None:
        _config_center = ConfigCenter()
    return _config_center

if __name__ == "__main__":
    import sys
    cc = get_config()
    if len(sys.argv) > 1:
        if sys.argv[1] == "get" and len(sys.argv) > 2:
            print(json.dumps({sys.argv[2]: cc.get(sys.argv[2])}, ensure_ascii=False, indent=2))
        elif sys.argv[1] == "all":
            print(json.dumps(cc.get_all(), ensure_ascii=False, indent=2))
    else:
        print(f"已加载配置: {list(cc._configs.keys())}")
        print(json.dumps(cc.get_all(), ensure_ascii=False, indent=2))
