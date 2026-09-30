#!/usr/bin/env python3
"""ZONGYUAN-ROOT 云端 Webhook 接收器
接收 Gitee push 事件，触发自动部署
确权: DID-BR-000002
"""
import json
import subprocess
import hmac
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler

SECRET = "zongyuan-root-2026"  # 与Gitee Webhook密钥一致
REPO_DIR = "/var/www/huodouai-website"

class DeployHandler(BaseHTTPRequestHandler):
    def verify_signature(self, body, signature_header):
        """验证 Gitee Webhook 签名"""
        if not signature_header:
            return False
        expected = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header.split("=")[-1])

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # 验证签名
        signature = self.headers.get("X-Gitee-Token", "")
        if not self.verify_signature(body, signature):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"forbidden")
            return

        # 解析事件
        try:
            event = json.loads(body)
            ref = event.get("ref", "")
            if "web-deploy" not in ref:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"skip: not deploy branch")
                return
        except:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"bad request")
            return

        # 触发部署
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"deploy triggered")

        # 异步执行部署脚本
        subprocess.Popen(["/bin/bash", f"{REPO_DIR}/deploy.sh"])
        print(f"[webhook] 部署已触发: {ref}")

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9120), DeployHandler)
    print("[webhook] 监听 0.0.0.0:9120 ...")
    server.serve_forever()
