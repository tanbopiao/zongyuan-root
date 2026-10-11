#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZR-TOKEN 校验网关 v1.0 —— 外部访问入口
外部请求携带 ZR1 令牌，网关校验签名+有效期+角色，通过则放行。

用法:
  python3 zr_token_gateway.py serve --port 8788        # 启动校验服务
  curl -H "X-ZR-Token: <令牌>" http://localhost:8788/verify
"""
import json, sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from zr_token_service import verify

def check(token, required_role=None):
    r = verify(token)
    if not r.get("valid"):
        return {"allow": False, "reason": r.get("reason")}, 401
    role = r["payload"].get("r")
    if required_role and required_role != "reader":
        hierarchy = {"reader": 0, "writer": 1, "admin": 2}
        if hierarchy.get(role, -1) < hierarchy.get(required_role, 99):
            return {"allow": False, "reason": "角色权限不足", "role": role}, 403
    return {"allow": True, "payload": r["payload"]}, 200

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["serve", "check"])
    ap.add_argument("--port", type=int, default=8788)
    ap.add_argument("--token", default="")
    ap.add_argument("--role", default="")
    args = ap.parse_args()
    if args.action == "check":
        res, code = check(args.token, args.role or None)
        print(json.dumps(res, ensure_ascii=False, indent=2)); return
    # serve
    from http.server import BaseHTTPRequestHandler, HTTPServer
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/verify"):
                tok = self.headers.get("X-ZR-Token", "")
                res, code = check(tok)
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(res, ensure_ascii=False).encode())
            else:
                self.send_response(404); self.end_headers()
        def log_message(self, *a): pass
    print(f"ZR-TOKEN 网关监听 :{args.port} (Ctrl-C 停)", file=sys.stderr)
    HTTPServer(("127.0.0.1", args.port), H).serve_forever()

if __name__ == "__main__":
    main()
