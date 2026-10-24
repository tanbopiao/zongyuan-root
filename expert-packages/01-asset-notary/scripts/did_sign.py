#!/usr/bin/env python3
"""DID 确权签名/验签 v1.0 —— Ed25519（依赖 cryptography）"""
import sys, argparse
from pathlib import Path

def load_key(path: str) -> bytes:
    data = Path(path).read_bytes()
    if b'-----BEGIN' in data:
        from cryptography.hazmat.primitives import serialization
        if b'PRIVATE' in data:
            return serialization.load_pem_private_key(data, password=None)
        return serialization.load_pem_public_key(data)
    return data  # 裸字节密钥

def main():
    ap = argparse.ArgumentParser(description='DID 确权签名/验签')
    ap.add_argument('--action', choices=['sign', 'verify'], required=True)
    ap.add_argument('--key', required=True, help='Ed25519 私钥(sign) 或 公钥(verify)')
    ap.add_argument('--message', required=True, help='待签名消息（如 Merkle 根）')
    ap.add_argument('--sig', default='', help='签名输出/输入文件路径')
    args = ap.parse_args()

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature

    msg = args.message.encode()

    if args.action == 'sign':
        key = load_key(args.key)
        if isinstance(key, bytes):
            key = Ed25519PrivateKey.from_private_bytes(key)
        sig = key.sign(msg)
        out = Path(args.sig) if args.sig else Path('credential.sig')
        out.write_bytes(sig)
        print(f'[DID] 签名完成: {out} ({len(sig)}B)')
    else:
        key = load_key(args.key)
        if isinstance(key, bytes):
            key = Ed25519PublicKey.from_public_bytes(key)
        sig = Path(args.sig).read_bytes()
        try:
            key.verify(sig, msg)
            print('[DID] 验签通过: True')
        except InvalidSignature:
            print('[DID] 验签失败: False')
            sys.exit(1)

if __name__ == '__main__':
    main()
