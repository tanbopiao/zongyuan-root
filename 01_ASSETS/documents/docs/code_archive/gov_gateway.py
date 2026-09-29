#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智·政务AI中台 — 统一网关服务 V1.0（标准库版，端口8200）
功能：对外统一入口（X-API-Key鉴权 + 简单限流）→ 路由到算子服务(8201) → 调用审计上报(8202)
零第三方依赖。本地仿真通过后云端部署。
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT
"""
import hashlib
import hmac
import json
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime

TRACE = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"
# 网关鉴权密钥（政务交付时由客户侧/私有化替换；演示用固定值）
API_KEY = "GOV-GATEWAY-INTERNAL-AUTH-2026"  # 内部服务认证，非云服务商付费Key
OPERATOR_URL = "http://127.0.0.1:8201"   # 后端算子集群
AUDIT_URL = "http://127.0.0.1:8202/audit"  # 持久化审计服务

# 简单滑动窗口限流：每IP每分钟最多 N 次
RATE_LIMIT = {"window": 60, "max": 120, "records": {}, "lock": threading.Lock()}


def check_ratelimit(ip):
    now = int(time.time())
    with RATE_LIMIT["lock"]:
        bucket = RATE_LIMIT["records"].get(ip, [])
        bucket = [t for t in bucket if now - t < RATE_LIMIT["window"]]
        if len(bucket) >= RATE_LIMIT["max"]:
            return False
        bucket.append(now)
        RATE_LIMIT["records"][ip] = bucket
        return True


def report_audit(op, node, status, detail):
    try:
        body = json.dumps({
            "op": op, "node": node or "gateway", "time": datetime.now().isoformat(),
            "trace": TRACE, "did": DID, "status": status, "detail": detail,
        }).encode()
        req = urllib.request.Request(AUDIT_URL, data=body, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass  # 审计服务不可达时网关仍放行（尽力而为）


class GatewayHandler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "healthy", "service": "gov-gateway",
                             "version": "1.0.0", "trace": TRACE, "did": DID})
        else:
            self._send(404, {"success": False, "error": "not found"})

    def do_POST(self):
        ip = self.client_address[0]
        # 1. 鉴权
        key = self.headers.get("X-API-Key")
        if key != API_KEY:
            self._send(401, {"success": False, "error": "unauthorized"})
            return
        # 2. 限流
        if not check_ratelimit(ip):
            self._send(429, {"success": False, "error": "rate limit exceeded"})
            return
        # 3. 仅转发 /api/gov/v1/* 到算子
        if not self.path.startswith("/api/gov/v1/"):
            self._send(404, {"success": False, "error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        # 4. 转发到算子
        try:
            req = urllib.request.Request(OPERATOR_URL + self.path, data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                code = resp.status
        except Exception as e:
            self._send(502, {"success": False, "error": f"operator unreachable: {e}"})
            return
        # 5. 审计上报
        node = self.headers.get("X-Gov-Node")
        report_audit(self.path.split("/")[-1], node, "ok" if code == 200 else "error", {"ip": ip})
        # 6. 返回
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    import os
    port = int(os.environ.get("GOV_GATEWAY_PORT", "8200"))
    server = ThreadingHTTPServer(("0.0.0.0", port), GatewayHandler)
    print(f"火斗云智·政务AI中台统一网关 V1.0 启动于 :{port} | {TRACE} | {DID}")
    server.serve_forever()
