#!/usr/bin/env python3
"""
P1-7: 安全配置管理器
敏感配置加密存储，API Key等不明文保存
"""
import json
import hashlib
import base64
from pathlib import Path
from cryptography.fernet import Fernet

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
SECRETS_FILE = ROOT / "config" / "secrets.enc"
KEY_FILE = ROOT / "config" / ".master_key"

def get_or_create_key() -> bytes:
    """获取或创建主密钥"""
    if KEY_FILE.exists():
        with open(KEY_FILE, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    try:
        KEY_FILE.chmod(0o600)
    except:
        pass
    return key

def encrypt_secret(value: str) -> str:
    """加密敏感值"""
    f = Fernet(get_or_create_key())
    return f.encrypt(value.encode()).decode()

def decrypt_secret(encrypted: str) -> str:
    """解密敏感值"""
    f = Fernet(get_or_create_key())
    return f.decrypt(encrypted.encode()).decode()

def save_secrets(secrets: dict):
    """保存加密后的配置"""
    encrypted = {k: encrypt_secret(v) for k, v in secrets.items() if v}
    SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SECRETS_FILE, "w") as f:
        json.dump(encrypted, f, ensure_ascii=False, indent=2)
    try:
        SECRETS_FILE.chmod(0o600)
    except:
        pass

def load_secrets() -> dict:
    """加载解密后的配置"""
    if not SECRETS_FILE.exists():
        return {}
    with open(SECRETS_FILE) as f:
        encrypted = json.load(f)
    return {k: decrypt_secret(v) for k, v in encrypted.items()}

def get_secret(key: str, default: str = "") -> str:
    """获取单个密钥"""
    secrets = load_secrets()
    return secrets.get(key, default)

def set_secret(key: str, value: str):
    """设置单个密钥"""
    secrets = load_secrets()
    secrets[key] = value
    save_secrets(secrets)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "init":
            get_or_create_key()
            print("安全配置管理器已初始化")
        elif sys.argv[1] == "set" and len(sys.argv) > 3:
            set_secret(sys.argv[2], sys.argv[3])
            print(f"已设置: {sys.argv[2]}")
        elif sys.argv[1] == "get" and len(sys.argv) > 2:
            val = get_secret(sys.argv[2])
            print(f"{sys.argv[2]}: {'***已配置***' if val else '(未设置)'}")
        elif sys.argv[1] == "list":
            secrets = load_secrets()
            print(json.dumps({k: "***" for k in secrets}, ensure_ascii=False, indent=2))
    else:
        print("用法: python3 secure_config.py [init|set|get|list]")
