#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
节点身份重新注册器 v1.0（按当前环境配置）
锚定: Ω₀⊂⊙∞⊂Ω | 本体根 Ω-TAN-7-001 | DID-BR-000002

设计：
  - public_salt 由「随机熵 + 当前环境指纹」共同生成 → 身份与所在沙箱强绑定
  - 派生算法完全复用既有 homologous_keyderive.py（不重造）
  - 口令不落盘明文（写入 600 权限 env 文件）
  - 输出：新 homologous_id / key_fingerprint（旧身份仅降级对照，不覆盖）
"""
import os, sys, json, hashlib, secrets, datetime

sys.path.insert(0, "/workspace/zr-token/homologous")
from homologous_keyderive import (
    derive_key, build_salt, fingerprint, homologous_id,
    ONTOLOGY_ROOT, DID_ROOT, ANCHOR, ITERATIONS
)

ENV_FP = "8d51ac289f027d601a90925b88345aa42e607988b7733b95a5f7ffc73147186b"
ENV_FP_SHORT = ENV_FP[:16].upper()
CONTAINER = "c47dc3ed06fe"

def new_env_bound_salt() -> str:
    """环境绑定盐：随机 16B hex，前 8 位由环境指纹派生校验，确保可追溯绑定关系"""
    rnd = secrets.token_hex(16)                       # 32 hex
    # 环境绑定标识：取环境指纹前 8 位转小写，拼入随机盐尾部（可公开，不含秘密）
    bound = f"{rnd}{ENV_FP_SHORT.lower()[:8]}"
    return bound

def new_passphrase() -> str:
    """生成本地强口令（32 字节 URL-safe），仅写入 600 权限文件"""
    return secrets.token_urlsafe(24)

def main():
    pub_salt = new_env_bound_salt()
    pp = new_passphrase()

    key = derive_key(pp, pub_salt)
    hid = homologous_id(key)
    fp  = fingerprint(key)

    out = {
        "registration_version": "2.0",
        "node_id": "NODE-DEV-WORKBUDDY-001",
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "anchor": ANCHOR,
        "ontology_root": ONTOLOGY_ROOT,
        "did_root": DID_ROOT,
        "public_salt": pub_salt,
        "homologous_id": hid,
        "key_fingerprint": fp,
        "key_persisted": False,
        "env_binding": {
            "container_id": CONTAINER,
            "env_fingerprint": ENV_FP,
            "env_fingerprint_short": ENV_FP_SHORT,
            "salt_bound_tail": ENV_FP_SHORT.lower()[:8],
        },
        "prev_identity": {
            "homologous_id": "ZR-HID-85F2DE2652C109F2",
            "key_fingerprint": "64f7dcc374cf63e13dd481b6ceb0bebc1636f67a55a01c8aeafeaa576e74446e",
            "status": "superseded-by-env-rebuild",
            "note": "旧身份(未落盐)在沙箱重建后不可复原；本记录仅为对照，不覆盖、不删除",
        },
        "algorithm": {
            "kdf": "PBKDF2-HMAC-SHA512",
            "iterations": ITERATIONS,
            "dklen": 32,
            "salt_construction": "ZR-HOMOLOGOUS-v1||Ω-TAN-7-001||DID-BR-000002||public_salt",
        },
    }

    # 1) 公开部分（可入库）：不含口令
    pub = {k: v for k, v in out.items() if k != "passphrase"}
    pub_path = "/workspace/zr-token/identity-v2/identity-registration.json"
    with open(pub_path, "w") as f:
        json.dump(pub, f, ensure_ascii=False, indent=2)

    # 2) 口令部分（600 权限，禁止入库）
    priv_path = "/root/.zr-credentials/homologous_v2.env"
    with open(priv_path, "w") as f:
        f.write("# ZR 同源身份 v2 凭证（600权限，禁止入库/入网盘/入公开面）\n")
        f.write(f"ZR_HOMOLOGOUS_SALT={pub_salt}\n")
        f.write(f"ZR_HOMOLOGOUS_PASSPHRASE={pp}\n")
        f.write(f"ZR_NODE_ID=NODE-DEV-WORKBUDDY-001\n")
        f.write(f"ZR_HOMOLOGOUS_ID={hid}\n")
    os.chmod(priv_path, 0o600)

    print(json.dumps({
        "ok": True,
        "public_salt": pub_salt,
        "homologous_id": hid,
        "key_fingerprint": fp,
        "identity_file": pub_path,
        "credential_file": priv_path + " (600)",
        "env_binding": ENV_FP_SHORT,
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
