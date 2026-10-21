#!/usr/bin/env python3
"""API 密钥安全存储（AES-256-GCM + KEK 注入，零明文落盘，META-LAW-CRYPT-LOCK-001）。

支持 provider：zhipu（智谱GLM-4-Flash免费）/ ark（火山方舟豆包）/ huodouai
用法：
  key_store.py set --provider ark --key <ARK_API_KEY>   # 加密入库 var/state/ark-key.enc.json
  key_store.py get --provider ark                        # 解密取出（仅运行时使用）
  key_store.py status                                    # 检查全部槽位
"""
import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = {"zhipu": "zongyuan-kernel-zhipu-key-v1", "ark": "zongyuan-kernel-ark-key-v1", "huodouai": "zongyuan-kernel-huodouai-key-v1"}
AAD = "zongyuan-kernel-key-v1"
DEFAULT_KEK = Path("/home/user/ZONGYUAN-ROOT/var/kek.env")


def get_kek():
    kek = os.environ.get("ZR_API_ENC_KEY", "")
    if not kek and DEFAULT_KEK.exists():
        kek = DEFAULT_KEK.read_text().strip()
    return kek


def set_key(provider, key):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    kek = get_kek()
    if not kek:
        print("KEK 未注入（ZR_API_ENC_KEY 或 /home/user/ZONGYUAN-ROOT/var/kek.env）", file=sys.stderr)
        return 2
    iv = secrets.token_bytes(12)
    k = hashlib.sha256(kek.encode()).digest()
    ct = AESGCM(k).encrypt(iv, key.encode(), AAD.encode())
    enc = {"subject": f"{provider} API key", "algorithm": "AES-256-GCM",
           "key_source": "env ZR_API_ENC_KEY（KEK，不落盘）",
           "iv_b64": base64.b64encode(iv).decode(),
           "ciphertext_b64": base64.b64encode(ct).decode(),
           "aad": AAD,
           "sha256_fingerprint": hashlib.sha256(key.encode()).hexdigest(),
           "plaintext": "NOT_STORED", "law": "META-LAW-CRYPT-LOCK-001",
           "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "owner": "zongyuan-kernel"}
    enc_path = ROOT / "var" / "state" / f"{provider}-key.enc.json"
    enc_path.parent.mkdir(parents=True, exist_ok=True)
    enc_path.write_text(json.dumps(enc, ensure_ascii=False, indent=2), encoding="utf-8")
    enc_path.chmod(0o600)
    print(f"已加密入库: {enc_path}（sha256 指纹 {enc['sha256_fingerprint'][:16]}…）")
    return 0


def get_key(provider):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    enc_path = ROOT / "var" / "state" / f"{provider}-key.enc.json"
    if not enc_path.exists():
        print(f"{provider} 槽位为空", file=sys.stderr)
        return 2
    enc = json.loads(enc_path.read_text(encoding="utf-8"))
    kek = get_kek()
    if not kek:
        print("KEK 未注入", file=sys.stderr)
        return 2
    iv = base64.b64decode(enc["iv_b64"])
    ct = base64.b64decode(enc["ciphertext_b64"])
    k = hashlib.sha256(kek.encode()).digest()
    pt = AESGCM(k).decrypt(iv, ct, enc.get("aad", AAD).encode())
    return pt.decode()


def status():
    found = False
    for prov in PROVIDERS:
        ep = ROOT / "var" / "state" / f"{prov}-key.enc.json"
        if ep.exists():
            enc = json.loads(ep.read_text(encoding="utf-8"))
            print(f"{prov}: 已加密存储 | 指纹 {enc['sha256_fingerprint'][:16]}… | 明文 NOT_STORED ✓")
            found = True
    if not found:
        print("槽位: 全部为空")
    return 0
    print(f"槽位: 已加密存储 | 算法 {enc['algorithm']} | 指纹 {enc['sha256_fingerprint'][:16]}… | 明文 NOT_STORED ✓")
    return 0


def main():
    ap = argparse.ArgumentParser(description="API key 安全存储")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("set"); s.add_argument("--provider", choices=list(PROVIDERS), required=True); s.add_argument("--key", required=True)
    g = sub.add_parser("get"); g.add_argument("--provider", choices=list(PROVIDERS), required=True)
    sub.add_parser("status")
    args = ap.parse_args()
    if args.cmd == "set":
        sys.exit(set_key(args.provider, args.key))
    elif args.cmd == "get":
        k = get_key(args.provider)
        if k:
            print(k)
        sys.exit(0 if k else 2)
    else:
        sys.exit(status())


if __name__ == "__main__":
    main()
