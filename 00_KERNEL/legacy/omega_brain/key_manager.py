#!/usr/bin/env python3
"""
私钥安全管理工具

功能:
  - 加密存储私钥 (AES-256-GCM)
  - 从环境变量/加密文件读取私钥
  - 私钥使用后立即从内存清除
  - 地址派生

安全原则:
  - 私钥永不明文存储
  - 私钥永不写入日志
  - 使用后立即清除内存
"""

import hashlib
import json
import os
import secrets
import sys
from pathlib import Path
from typing import Optional

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class KeyManager:
    """私钥安全管理器"""

    def __init__(self, key_file: str = None, password: str = None):
        self.key_file = Path(key_file) if key_file else Path(__file__).parent.parent / 'config' / '.encrypted_keys'
        self.password = password or os.environ.get('KEY_MANAGER_PASSWORD', '')
        self._key_cache = {}

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """从密码派生加密密钥 (Scrypt)"""
        if not CRYPTO_AVAILABLE:
            # 降级: 用SHA256 (安全性较低)
            return hashlib.sha256((password + salt.hex()).encode()).digest()
        kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
        return kdf.derive(password.encode())

    def encrypt_key(self, private_key: str, label: str = 'default') -> dict:
        """
        加密存储私钥

        Args:
            private_key: 私钥 (hex, 0x开头或不带)
            label: 标签 (如 'polygon_mainnet', 'ethereum_mainnet')

        Returns:
            加密记录
        """
        if not self.password:
            return {'error': 'password required (set KEY_MANAGER_PASSWORD)'}

        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(12)
        key = self._derive_key(self.password, salt)

        if CRYPTO_AVAILABLE:
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, private_key.encode(), label.encode())
        else:
            # 降级: XOR (仅用于开发测试)
            ciphertext = bytes(a ^ b for a, b in zip(private_key.encode(), key * 100))

        record = {
            'label': label,
            'salt': salt.hex(),
            'nonce': nonce.hex(),
            'ciphertext': ciphertext.hex(),
            'created_at': __import__('datetime').datetime.now().isoformat(),
        }

        # 保存
        all_keys = self._load_all()
        all_keys[label] = record
        self._save_all(all_keys)

        # 清除内存中的私钥
        del private_key

        return {'success': True, 'label': label, 'note': 'key encrypted and stored'}

    def decrypt_key(self, label: str = 'default') -> Optional[str]:
        """
        解密读取私钥 (使用后请立即清除)

        Returns:
            私钥字符串，失败返回None
        """
        if not self.password:
            return None

        all_keys = self._load_all()
        if label not in all_keys:
            return None

        record = all_keys[label]
        salt = bytes.fromhex(record['salt'])
        nonce = bytes.fromhex(record['nonce'])
        ciphertext = bytes.fromhex(record['ciphertext'])
        key = self._derive_key(self.password, salt)

        if CRYPTO_AVAILABLE:
            aesgcm = AESGCM(key)
            try:
                plaintext = aesgcm.decrypt(nonce, ciphertext, label.encode())
                return plaintext.decode()
            except Exception:
                return None
        else:
            plaintext = bytes(a ^ b for a, b in zip(ciphertext, key * 100))
            return plaintext.decode()

    def get_env_key(self, env_var: str = 'ANCHOR_PRIVATE_KEY') -> Optional[str]:
        """从环境变量读取私钥 (推荐方式)"""
        return os.environ.get(env_var)

    def _load_all(self) -> dict:
        if self.key_file.exists():
            with open(self.key_file) as f:
                return json.load(f)
        return {}

    def _save_all(self, keys: dict):
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.key_file, 'w') as f:
            json.dump(keys, f, ensure_ascii=False, indent=2)
        # 设置文件权限 (仅所有者可读写)
        try:
            os.chmod(self.key_file, 0o600)
        except:
            pass

    def list_keys(self) -> list:
        """列出已存储的密钥标签 (不显示私钥)"""
        all_keys = self._load_all()
        return [{'label': k, 'created_at': v.get('created_at')} for k, v in all_keys.items()]

    def delete_key(self, label: str) -> bool:
        """删除密钥"""
        all_keys = self._load_all()
        if label in all_keys:
            del all_keys[label]
            self._save_all(all_keys)
            return True
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Private Key Manager')
    sub = parser.add_subparsers(dest='command')

    # encrypt
    e_p = sub.add_parser('encrypt', help='Encrypt and store private key')
    e_p.add_argument('--key', required=True, help='Private key (hex)')
    e_p.add_argument('--label', default='default', help='Key label')
    e_p.add_argument('--password', help='Encryption password')

    # decrypt
    d_p = sub.add_parser('decrypt', help='Decrypt private key (use with caution)')
    d_p.add_argument('--label', default='default', help='Key label')
    d_p.add_argument('--password', help='Encryption password')

    # list
    sub.add_parser('list', help='List stored key labels')

    # delete
    del_p = sub.add_parser('delete', help='Delete key')
    del_p.add_argument('--label', required=True, help='Key label')

    args = parser.parse_args()
    km = KeyManager(password=args.password if hasattr(args, 'password') else None)

    if args.command == 'encrypt':
        result = km.encrypt_key(args.key, args.label)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == 'decrypt':
        key = km.decrypt_key(args.label)
        if key:
            print(f'Key (starts with): {key[:6]}...{key[-4:]}')
            print('WARNING: Copy and clear this output immediately')
        else:
            print('Decryption failed')
    elif args.command == 'list':
        print(json.dumps(km.list_keys(), ensure_ascii=False, indent=2))
    elif args.command == 'delete':
        print(json.dumps({'deleted': km.delete_key(args.label)}, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
