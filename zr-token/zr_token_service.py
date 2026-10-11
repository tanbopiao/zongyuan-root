#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZR-TOKEN 体系专属外部访问令牌服务 v1.0
锚定: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 节点: NODE-DEV-DOUBAO-WORK-001

设计铁律（承 L19密钥治理回执 + 火斗云智JWT约定）:
  1. 代码零密钥字面量 —— 签名密钥从 .env 读取（gitignore）
  2. 台账只存哈希 —— 令牌明文永不入库/入公开面
  3. 令牌格式自描述 —— 前缀 ZR1 便于识别与审计
  4. HMAC-SHA256 签名 —— 防伪造，可离线校验
  5. 角色分级 —— 对齐既有 JWT roles 约定

令牌格式:
  ZR1.<base64url(payload)>.<hmac_sig12>
  payload = {"t":"<token_id>","d":"<did>","r":"<role>","e":<exp_epoch>,"s":"<scope>"}

用法:
  python3 zr_token_service.py issue  --name <名称> --role <角色> --scope <范围> [--days 365]
  python3 zr_token_service.py verify --token <令牌>
  python3 zr_token_service.py list
"""
import os, sys, json, hmac, hashlib, base64, time, secrets, argparse

CRED_FILE = "/root/.zr-credentials/zr_token_signing.env"
REGISTRY_HINT = "资料库台账 nGvD220L6C6rF96n7TMfA1"
PREFIX = "ZR1"
DID_DEFAULT = "DID-BR-000002"

# ============ 签名密钥（零字面量，从.env读取） ============
def load_signing_key():
    """签名密钥真值源：600权限文件。首次调用若无则生成。"""
    if not os.path.exists(CRED_FILE):
        os.makedirs(os.path.dirname(CRED_FILE), exist_ok=True)
        key = secrets.token_hex(32)
        with open(CRED_FILE, "w") as f:
            f.write("# ZR-TOKEN 签名密钥真值源 (600权限, 禁止入库/入网盘/入公开面)\n")
            f.write(f"ZR_TOKEN_SIGNING_KEY={key}\n")
        os.chmod(CRED_FILE, 0o600)
    key = None
    with open(CRED_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith("ZR_TOKEN_SIGNING_KEY="):
                key = line.split("=", 1)[1]
    if not key:
        raise RuntimeError("缺少签名密钥 ZR_TOKEN_SIGNING_KEY")
    return key

def b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

def sign(payload_b64: str, key: str) -> str:
    return hmac.new(key.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()[:12]

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def issue(name: str, role: str, scope: str, days: int, did: str = DID_DEFAULT) -> dict:
    key = load_signing_key()
    token_id = "TK" + secrets.token_hex(4).upper()
    exp = int(time.time()) + days * 86400
    payload = {"t": token_id, "d": did, "r": role, "e": exp, "s": scope}
    pb = b64e(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
    sig = sign(pb, key)
    token = f"{PREFIX}.{pb}.{sig}"
    return {
        "token": token,
        "token_id": token_id,
        "name": name,
        "role": role,
        "scope": scope,
        "did": did,
        "prefix": token[:8] + "...",
        "hash": sha256_hex(token),
        "issued_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "expires_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime(exp)),
    }

def verify(token: str) -> dict:
    key = load_signing_key()
    try:
        prefix, pb, sig = token.split(".")
    except ValueError:
        return {"valid": False, "reason": "格式非法"}
    if prefix != PREFIX:
        return {"valid": False, "reason": "前缀非ZR体系令牌"}
    if not hmac.compare_digest(sign(pb, key), sig):
        return {"valid": False, "reason": "签名不匹配(可能伪造)"}
    payload = json.loads(b64d(pb))
    if payload.get("e", 0) < time.time():
        return {"valid": False, "reason": "已过期", "payload": payload}
    return {"valid": True, "payload": payload}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["issue", "verify", "list"])
    ap.add_argument("--name", default="")
    ap.add_argument("--role", default="reader")
    ap.add_argument("--scope", default="public-read")
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--token", default="")
    args = ap.parse_args()
    if args.action == "issue":
        if not args.name:
            print(json.dumps({"error": "缺少 --name"}, ensure_ascii=False)); return
        r = issue(args.name, args.role, args.scope, args.days)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        print("\n★ 令牌明文仅此一次输出，请立即保存。台账只存哈希。", file=sys.stderr)
    elif args.action == "verify":
        print(json.dumps(verify(args.token), ensure_ascii=False, indent=2))
    elif args.action == "list":
        print(f"令牌台账: {REGISTRY_HINT}")
        print("签名密钥真值源:", CRED_FILE, "(600)" if os.path.exists(CRED_FILE) else "(未生成)")

if __name__ == "__main__":
    main()
