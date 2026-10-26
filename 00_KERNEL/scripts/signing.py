#!/usr/bin/env python3
"""
中枢签名模块 signing.py
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω

契约来源: AGENTS.md RULE-005 V3.1 + 2026-10-26 实测打通
算法:
  secret  = PBKDF2-HMAC-SHA256(passphrase, salt=b"yuanji-signing-salt", iters=100000, dklen=32)
  msg     = "METHOD|PATH|{unix_ts}|{sha256(request_body).hex()}"  (空body时 sha256(b'').hexdigest())
  X-Signature    = HMAC-SHA256(secret, msg).hexdigest()
  X-Signature-Timestamp = unix秒 (±300s 窗口)

兼容通道 (待废弃): X-DID + X-Capture-Token (auto_truth_report.py 当前在用)
"""
import hashlib, hmac, time, os

SIGN_SALT = b"yuanji-signing-salt"
SION_ITERS = 100000
SION_DKLEN = 32

# 三路 passphrase 候选 (按优先级): 内核 vault → 持久层副本 → 环境变量
_PASSPHRASE_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "..", "kernel_vault", ".yuanji_signing.key"),
    os.path.join(os.path.dirname(__file__), "..", "shared_brain", "zongyuan-yuanji", "var", ".yuanji_signing_passphrase"),
]


def load_passphrase():
    """从候选路径取 passphrase; 找不到返回 None (调用方应回退到兼容 token 通道)"""
    for p in _PASSPHRASE_CANDIDATES:
        try:
            if os.path.exists(p) and os.path.getsize(p) > 0:
                data = open(p, "rb").read().strip()
                if data:
                    return data
        except Exception:
            continue
    env = os.environ.get("ZR_SIGN_PASSPHRASE")
    if env:
        return env.encode()
    return None


def derive_secret(passphrase):
    """PBKDF2 派生 32B HMAC secret"""
    return hashlib.pbkdf2_hmac("sha256", passphrase, SIGN_SALT, SION_ITERS, dklen=SION_DKLEN)


def build_signature(method, path, body=b"", passphrase=None):
    """
    生成签名头字典。
    method: "POST"/"GET"
    path:   "/api/report/truth"
    body:   请求体 bytes (GET 传 b"" 即可)
    passphrase: 可预传, 否则自动探测
    返回: {"X-Signature": hex, "X-Signature-Timestamp": str(unix)}  或 {} (passphrase 缺失)
    """
    pp = passphrase or load_passphrase()
    if not pp:
        return {}
    secret = derive_secret(pp)
    ts = str(int(time.time()))
    body_hash = hashlib.sha256(body).hexdigest()
    msg = f"{method.upper()}|{path}|{ts}|{body_hash}"
    sig = hmac.new(secret, msg.encode("utf-8"), hashlib.sha256).hexdigest()
    return {"X-Signature": sig, "X-Signature-Timestamp": ts}


def signed_headers(did, method, path, body=b"", token=None, prefer_sig=True):
    """
    完整请求头 (含 X-DID)。
    prefer_sig=True → 优先签名三头; 缺失 passphrase 时自动降级为 X-Capture-Token
    prefer_sig=False → 只用 token 兼容通道
    """
    headers = {"Content-Type": "application/json", "X-DID": did}
    sig = build_signature(method, path, body) if prefer_sig else {}
    if sig and prefer_sig:
        headers.update(sig)
    elif token:
        headers["X-Capture-Token"] = token
    return headers
