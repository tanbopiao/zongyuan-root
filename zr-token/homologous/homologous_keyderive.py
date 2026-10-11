#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同源协议 · 派生式密钥引擎 v1.0
锚定: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 本体根: Ω-TAN-7-001

设计目标（B方案）:
  根密钥永不落盘、永不外传 —— 从「口令 + 同源双标识 + 公开salt」派生
  任何新沙箱输入同一口令 → 重建出完全相同的密钥 → 零外存、沙箱无关

同源双标识（承《元极恒一·同源协议终版唯一真值》，2026-09-10锁档）:
  本体根标识: Ω-TAN-7-001
  资产身份标识: DID-BR-000002

派生算法（标准密码学，无自创）:
  key = PBKDF2-HMAC-SHA512( passphrase,
                            salt = ZR-HOMOLOGOUS-v1 || Ω-TAN-7-001 || DID-BR-000002 || PUBLIC_SALT,
                            iterations = 600000, dklen = 32 )

  说明: 双标识拼入 salt 使密钥「天然同源」——异源节点即使知道口令，
        因缺少体系双标识也无法派生出同一密钥。

用法:
  python3 homologous_keyderive.py derive --salt <hex>              # 交互式输口令
  python3 homologous_keyderive.py derive --salt <hex> --passphrase <口令>
  python3 homologous_keyderive.py new-salt                         # 生成新salt
  python3 homologous_keyderive.py fingerprint --salt <hex> --passphrase <口令>
"""
import os, sys, json, argparse, hashlib, secrets, getpass

# ============ 同源双标识（锁档常量，不可更改） ============
ONTOLOGY_ROOT = "Ω-TAN-7-001"      # 本体根标识
DID_ROOT      = "DID-BR-000002"    # 资产身份标识
ANCHOR        = "Ω₀⊂⊙∞⊂Ω"         # 确权锚点
DERIVE_LABEL  = "ZR-HOMOLOGOUS-v1"
ITERATIONS    = 600000
DKLEN         = 32

def build_salt(public_salt_hex: str) -> bytes:
    """同源salt = 派生标签 || 本体根 || 资产根 || 公开salt"""
    base = f"{DERIVE_LABEL}||{ONTOLOGY_ROOT}||{DID_ROOT}||{public_salt_hex}".encode()
    return base

def derive_key(passphrase: str, public_salt_hex: str) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha512",
        passphrase.encode("utf-8"),
        build_salt(public_salt_hex),
        ITERATIONS,
        dklen=DKLEN,
    )

def new_salt() -> str:
    return secrets.token_hex(16)

def fingerprint(key: bytes) -> str:
    """密钥指纹（可公开，用于校验，不泄露密钥）"""
    return hashlib.sha256(key).hexdigest()

def homologous_id(key: bytes) -> str:
    """同源ID：密钥 + 双标识 的单向指纹，用于确权"""
    h = hashlib.sha256(key + ONTOLOGY_ROOT.encode() + DID_ROOT.encode()).hexdigest()
    return "ZR-HID-" + h[:16].upper()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["derive", "new-salt", "fingerprint"])
    ap.add_argument("--salt", default="")
    ap.add_argument("--passphrase", default="")
    ap.add_argument("--show-key", action="store_true")
    args = ap.parse_args()

    if args.action == "new-salt":
        print(json.dumps({"public_salt": new_salt()}, ensure_ascii=False)); return

    if not args.salt:
        print(json.dumps({"error": "缺少 --salt（公开salt，存资料库）"}, ensure_ascii=False)); return

    pp = args.passphrase
    if not pp:
        pp = getpass.getpass("请输入同源口令: ")
    if not pp:
        print(json.dumps({"error": "口令为空"}, ensure_ascii=False)); return

    key = derive_key(pp, args.salt)
    result = {
        "homologous_id": homologous_id(key),
        "key_fingerprint": fingerprint(key),
        "ontology_root": ONTOLOGY_ROOT,
        "did_root": DID_ROOT,
        "anchor": ANCHOR,
        "iterations": ITERATIONS,
        "salt_used": args.salt,
    }
    if args.show_key:
        result["key_hex"] = key.hex()  # 仅供本地调试，禁止入库
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
