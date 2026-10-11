#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同源协议 · 实现层 v1.0 (派生密钥版)
锚定: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 本体根: Ω-TAN-7-001

承《元极恒一·同源协议【终版唯一真值】》(2026-09-10锁档):
  - 双标识绑定: Ω-TAN-7-001 + DID-BR-000002
  - 双层校验: 调度层 + Worker层
  - 不满足同源 → 拒绝/隔离/不入库

本实现层补全「密钥根」—— 用派生密钥作为同源信任根的密码学载体:
  1. 同源身份: 派生密钥 → 同源ID(ZR-HID)
  2. 同源令牌: 用派生密钥HMAC签发的ZR1令牌
  3. 双层校验: 令牌签名校验 + 双标识校验
  4. 零外存: 密钥从口令派生，永不落盘

用法:
  python3 homologous_protocol.py init --salt <salt>            # 初始化(交互输口令)
  python3 homologous_protocol.py issue --salt <salt> --name X  # 签发同源令牌
  python3 homologous_protocol.py verify --salt <salt> --token T
"""
import os, sys, json, argparse, hmac, hashlib, base64, time, secrets, getpass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from homologous_keyderive import derive_key, fingerprint, homologous_id, ONTOLOGY_ROOT, DID_ROOT, ANCHOR

# 会话级密钥缓存（仅内存，进程结束即消失）
_SESSION_KEY = {"key": None}

def load_key(salt: str, passphrase: str = None):
    """载入同源密钥（内存，零落盘）"""
    if _SESSION_KEY["key"] is not None:
        return _SESSION_KEY["key"]
    pp = passphrase or getpass.getpass("请输入同源口令: ")
    key = derive_key(pp, salt)
    _SESSION_KEY["key"] = key
    return key

def b64e(d): return base64.urlsafe_b64encode(d).decode().rstrip("=")
def b64d(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

def issue_homologous_token(key: bytes, name: str, role: str, scope: str, days: int) -> dict:
    """同源令牌：用派生密钥HMAC签名，payload含双标识"""
    token_id = "HTK" + secrets.token_hex(4).upper()
    exp = int(time.time()) + days * 86400
    payload = {
        "t": token_id, "n": name, "r": role, "s": scope, "e": exp,
        "o": ONTOLOGY_ROOT, "d": DID_ROOT,          # 双标识绑定
    }
    pb = b64e(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
    sig = hmac.new(key, pb.encode(), hashlib.sha256).hexdigest()[:16]
    return {
        "token": f"ZRH1.{pb}.{sig}",
        "token_id": token_id, "name": name, "role": role, "scope": scope,
        "homologous_id": homologous_id(key),
        "issued_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "expires_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime(exp)),
        "sign_alg": "HMAC-SHA256(derived_key)",
    }

def verify_homologous_token(key: bytes, token: str) -> dict:
    """双层校验：签名 + 双标识"""
    try:
        prefix, pb, sig = token.split(".")
    except ValueError:
        return {"valid": False, "layer": "format", "reason": "格式非法"}
    if prefix != "ZRH1":
        return {"valid": False, "layer": "format", "reason": "前缀非同源令牌"}
    # 第一层：签名校验
    exp_sig = hmac.new(key, pb.encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(exp_sig, sig):
        return {"valid": False, "layer": "signature", "reason": "签名不匹配(异源或伪造)"}
    payload = json.loads(b64d(pb))
    # 第二层：双标识校验
    if payload.get("o") != ONTOLOGY_ROOT or payload.get("d") != DID_ROOT:
        return {"valid": False, "layer": "identity", "reason": "双标识不匹配(异源)"}
    if payload.get("e", 0) < time.time():
        return {"valid": False, "layer": "expiry", "reason": "已过期"}
    return {"valid": True, "layer": "both", "payload": payload}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["init", "issue", "verify"])
    ap.add_argument("--salt", default="")
    ap.add_argument("--passphrase", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--role", default="reader")
    ap.add_argument("--scope", default="portal-read")
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--token", default="")
    args = ap.parse_args()
    if not args.salt:
        print(json.dumps({"error": "缺少 --salt"}, ensure_ascii=False)); return
    key = load_key(args.salt, args.passphrase)
    if args.action == "init":
        print(json.dumps({
            "homologous_id": homologous_id(key),
            "key_fingerprint": fingerprint(key),
            "ontology_root": ONTOLOGY_ROOT, "did_root": DID_ROOT, "anchor": ANCHOR,
            "key_persisted": False, "note": "密钥仅在内存，零落盘"
        }, ensure_ascii=False, indent=2))
    elif args.action == "issue":
        print(json.dumps(issue_homologous_token(key, args.name or "未命名", args.role, args.scope, args.days), ensure_ascii=False, indent=2))
    elif args.action == "verify":
        print(json.dumps(verify_homologous_token(key, args.token), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
