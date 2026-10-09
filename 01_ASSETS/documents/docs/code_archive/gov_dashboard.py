#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智·政务AI中台 — 大屏数据服务 V1.0（标准库版，端口8203）
功能：聚合算子(8201)/网关(8200)/审计(8202)实时数据，输出大屏JSON
零第三方依赖。本地仿真通过后云端部署。
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT
"""
import json
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TRACE = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"
OPERATOR_URL = "http://127.0.0.1:8201"
GATEWAY_URL = "http://127.0.0.1:8200"
AUDIT_URL = "http://127.0.0.1:8202"


def fetch(url, timeout=3):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def build_summary():
    op_health = fetch(OPERATOR_URL + "/health")
    gw_health = fetch(GATEWAY_URL + "/health")
    audit_health = fetch(AUDIT_URL + "/health")
    audit_records = fetch(AUDIT_URL + "/audit?limit=200") or {}

    records = audit_records.get("records", [])
    today = datetime.now().strftime("%Y-%m-%d")
    today_calls = [r for r in records if r.get("time", "").startswith(today)]

    op_dist = {}
    status_dist = {"ok": 0, "error": 0}
    for r in records:
        op = r.get("op", "unknown")
        op_dist[op] = op_dist.get(op, 0) + 1
        status_dist[r.get("status", "unknown")] = status_dist.get(r.get("status", "unknown"), 0) + 1

    total_calls = len(records)
    pass_rate = round(status_dist.get("ok", 0) / total_calls * 100, 1) if total_calls else 0.0

    return {
        "timestamp": datetime.now().isoformat(),
        "trace": TRACE,
        "did": DID,
        "kpi": {
            "operator_status": op_health.get("status", "unknown") if op_health else "down",
            "gateway_status": gw_health.get("status", "unknown") if gw_health else "down",
            "audit_status": audit_health.get("status", "unknown") if audit_health else "down",
            "total_audit": audit_health.get("audit_total", 0) if audit_health else 0,
            "today_calls": len(today_calls),
            "pass_rate": pass_rate,
        },
        "operator_distribution": op_dist,
        "status_distribution": status_dist,
        "recent_calls": records[-10:][::-1],
        "services": [
            {"name": "政务算子集群", "port": 8201, "status": op_health.get("status", "down") if op_health else "down"},
            {"name": "政务统一网关", "port": 8200, "status": gw_health.get("status", "down") if gw_health else "down"},
            {"name": "持久化审计", "port": 8202, "status": audit_health.get("status", "down") if audit_health else "down"},
            {"name": "大屏数据服务", "port": 8203, "status": "healthy"},
        ],
    }


class DashboardHandler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "healthy", "service": "gov-dashboard",
                             "version": "1.0.0", "trace": TRACE, "did": DID})
        elif self.path.startswith("/api/dashboard/summary") or self.path.startswith("/gov/api/dashboard/summary"):
            self._send(200, build_summary())
        else:
            self._send(404, {"success": False, "error": "not found"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    import os
    port = int(os.environ.get("GOV_DASHBOARD_PORT", "8203"))
    server = ThreadingHTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"火斗云智·政务AI中台大屏数据服务 V1.0 启动于 :{port} | {TRACE} | {DID}")
    server.serve_forever()
