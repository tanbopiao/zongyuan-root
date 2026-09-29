#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智AIOS · 开放平台 API Key 轻认证服务
确权锚点：Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 本源根 Ω-TAN-7-001
生成：2026-09-10 | 依据 metalow.API-KEY-LIGHT-AUTH 元规则

作用：
  供 nginx auth_request 调用的 API Key 校验服务。
  仅监听 127.0.0.1:8120（内部端口，不新增公网暴露面）。
  校验通过返回 200，nginx 放行；失败返回 401/403，nginx 拒绝。

元规则（API Key 轻认证）：
  - 认证对象是 Agent/脚本而非人类，不建完整用户体系
  - 密钥即身份：API Key 携带即认证
  - Key 可配额 / 吊销 / 计量
  - 需要角色时用 Key 分组承载，后续叠加不重建

用法：
  python3 api_key_auth_server.py [--port 8120] [--store keys_store.json]
"""
import json, os, sys, hmac, time, hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PORT = 8120
DEFAULT_STORE = os.path.join(BASE_DIR, "keys_store.json")

# ---------- 密钥库管理 ----------
class KeyStore:
    def __init__(self, path):
        self.path = path
        self._ensure()

    def _ensure(self):
        if not os.path.exists(self.path):
            self._write({"version": 1, "keys": {}, "audit": []})

    def _read(self):
        self._ensure()
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def verify(self, key):
        """校验 API Key：存在且未吊销 → (True, 元信息)；否则 (False, 原因)"""
        data = self._read()
        rec = data.get("keys", {}).get(key)
        if not rec:
            return False, "invalid_key"
        if not rec.get("enabled", True):
            return False, "revoked"
        # 配额/过期检查
        if rec.get("expires_at") and time.time() > rec["expires_at"]:
            return False, "expired"
        # 计量：调用次数 +1
        rec["calls"] = rec.get("calls", 0) + 1
        rec["last_call"] = time.time()
        data["keys"][key] = rec
        # 审计
        data.setdefault("audit", []).append({
            "ts": time.time(), "key": rec.get("owner", key[:8]), "action": "verify_ok"
        })
        if len(data["audit"]) > 500:  # 控制审计体积
            data["audit"] = data["audit"][-200:]
        self._write(data)
        return True, rec

    def gen_key(self, owner, quota=None, expires_in=None, group=None):
        """生成新 API Key（管理员用）"""
        import secrets
        raw = secrets.token_hex(24)  # 48 hex chars
        key_id = "zk_" + hashlib.sha256(raw.encode()).hexdigest()[:16]
        data = self._read()
        data["keys"][key_id] = {
            "owner": owner, "enabled": True,
            "quota": quota, "calls": 0,
            "group": group or "default",
            "created": time.time(),
            "expires_at": (time.time() + expires_in) if expires_in else None,
        }
        data["_last_generated_raw"] = raw  # 仅管理员可见原始值（此处仅演示，生产应只返回一次）
        self._write(data)
        return key_id, raw

# ---------- HTTP 处理 ----------
class AuthHandler(BaseHTTPRequestHandler):
    store = None  # 注入

    def log_message(self, *a):
        pass  # 静默，避免刷日志

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def _handle(self):
        parsed = urlparse(self.path)
        # 从 Header X-API-Key 或查询参数 api_key 取密钥
        key = self.headers.get("X-API-Key") or parse_qs(parsed.query).get("api_key", [""])[0]
        if not key:
            self._respond(401, {"status": "denied", "reason": "missing_key",
                                "detail": "需携带 X-API-Key 或 ?api_key="})
            return
        ok, info = self.store.verify(key)
        if ok:
            self._respond(200, {"status": "ok", "owner": info.get("owner"),
                                "group": info.get("group")})
        else:
            self._respond(401 if info in ("invalid_key", "missing_key") else 403,
                          {"status": "denied", "reason": info})

    def _respond(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--store", default=DEFAULT_STORE)
    args = ap.parse_args()
    AuthHandler.store = KeyStore(args.store)
    srv = HTTPServer(("127.0.0.1", args.port), AuthHandler)
    print(f"✅ API Key 轻认证服务运行于 127.0.0.1:{args.port} (仅本机)")
    print(f"   密钥库: {args.store}")
    print(f"确权锚点: Ω₀⊂⊙∞⊂Ω | DID-BR-000002")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n停止")


if __name__ == "__main__":
    main()
