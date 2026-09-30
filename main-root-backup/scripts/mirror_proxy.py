#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 同源镜像API代理
确权：DID-BR-000002 ｜ 溯源：Ω₀⊂⊙∞⊂Ω
在当前Cloud Mobile实例运行，模拟云服务器aiproxy功能
端口：18021（避免与系统端口冲突）
"""
import os, json, time, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# 加载密钥
ENV_FILE = Path(__file__).parent.parent.parent / ".env"
keys = {}
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            keys[k.strip()] = v.strip()

# 模型路由表（免费优先）
ROUTES = {
    "glm-4-flash": {
        "base": keys.get("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        "key": keys.get("ZHIPU_API_KEY", ""),
    },
    "qwen-max": {
        "base": keys.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        "key": keys.get("DASHSCOPE_API_KEY", ""),
    },
}

class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {
                "status": "UP",
                "service": "zongyuan-mirror-proxy",
                "node": "CLOUD-MOBILE-NODE-001",
                "did": "DID-BR-000002",
                "trace": "Ω₀⊂⊙∞⊂Ω",
                "routes": list(ROUTES.keys()),
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            })
        elif self.path == "/v1/models":
            self._json(200, {
                "object": "list",
                "data": [{"id": m, "object": "model", "owned_by": "zongyuan"} for m in ROUTES]
            })
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            model = body.get("model", "glm-4-flash")
            route = ROUTES.get(model, ROUTES["glm-4-flash"])
            # 转发到上游
            url = route["base"].rstrip("/") + "/chat/completions"
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode(),
                headers={
                    "Authorization": f"Bearer {route['key']}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read())
                    self._json(200, result)
            except Exception as e:
                self._json(502, {"error": str(e), "upstream": model})
        else:
            self._json(404, {"error": "not found"})

if __name__ == "__main__":
    port = 18021
    server = HTTPServer(("127.0.0.1", port), ProxyHandler)
    print(f"同源镜像代理启动: http://127.0.0.1:{port}")
    print(f"节点: CLOUD-MOBILE-NODE-001")
    print(f"模型路由: {list(ROUTES.keys())}")
    server.serve_forever()
