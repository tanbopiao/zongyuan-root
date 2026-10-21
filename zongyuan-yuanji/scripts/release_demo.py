#!/usr/bin/env python3
# SiphonIris 发布演练演示服务（多实例/多版本，真实可观测）
import json, time, random, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1])
VERSION = sys.argv[2] if len(sys.argv) > 2 else "v1"
START = time.time()

class H(BaseHTTPRequestHandler):
    def _j(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if self.path == "/health":
            self._j({"ok": True, "version": VERSION, "instance": PORT, "uptime": round(time.time()-START,1)})
        elif self.path == "/metrics":
            # 模拟虹彩折射率观测：延迟ms + 错误率%
            lat = round(random.uniform(20, 120), 1)
            err = round(random.uniform(0, 1.5), 2)
            self._j({"version": VERSION, "instance": PORT, "latency_ms": lat, "error_rate_pct": err,
                     "cpu_pct": round(random.uniform(10, 60), 1), "mem_pct": round(random.uniform(20, 70), 1)})
        elif self.path == "/":
            self._j({"service": "siphoniris-demo", "version": VERSION, "pact": "G0-G3"})
        else:
            self._j({"ok": False})
    def log_message(self, *a):
        pass

if __name__ == "__main__":
    print("release_demo instance=%s version=%s port=%s" % (PORT, VERSION, PORT), flush=True)
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
