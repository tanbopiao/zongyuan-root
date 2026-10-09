#!/usr/bin/env python3
"""通用健康端点模块 - 所有服务共用"""
import json, time, sys
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, "/opt/ZONGYUAN-ROOT")

class HealthHandler(BaseHTTPRequestHandler):
    service_name = "generic"
    service_version = "1.0"
    
    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ["/health", "/api/health"]:
            self._json({"status": "healthy", "service": self.service_name, "version": self.service_version, "uptime": int(time.time()-self.start_time)})
        elif path in ["/status", "/api/status"]:
            self._json(self._get_status())
        elif path == "/":
            self._json({"service": self.service_name, "version": self.service_version, "endpoints": ["/health", "/status"]})
        else:
            self._json({"error": "not_found", "path": path}, 404)
    
    def _get_status(self):
        return {"service": self.service_name, "version": self.service_version, "status": "running", "uptime": int(time.time()-self.start_time)}
    
    def log_message(self, format, *args): pass

def create_health_server(service_name, version, port, host="0.0.0.0"):
    handler = type(f"{service_name}Handler", (HealthHandler,), {
        "service_name": service_name,
        "service_version": version,
        "start_time": time.time()
    })
    return HTTPServer((host, port), handler)
