#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智·政务AI中台 — 持久化审计服务 V1.0（标准库版，端口8202）
功能：接收审计事件写入 JSONL 文件（重启不清空），支持按时间/条数查询历史
零第三方依赖。本地仿真通过后云端部署。
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT
"""
import json
import os
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TRACE = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"
AUDIT_DIR = os.environ.get("GOV_AUDIT_DIR", "./audit")
AUDIT_FILE = os.path.join(AUDIT_DIR, "gov_audit.jsonl")
_LOCK = threading.Lock()


def ensure_dir():
    os.makedirs(AUDIT_DIR, exist_ok=True)


def append_record(rec):
    ensure_dir()
    with _LOCK:
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_records(limit=50, since=None):
    ensure_dir()
    if not os.path.exists(AUDIT_FILE):
        return []
    with _LOCK:
        with open(AUDIT_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    recs = []
    for ln in lines:
        try:
            r = json.loads(ln)
            if since and r.get("time", "") < since:
                continue
            recs.append(r)
        except Exception:
            continue
    return recs[-limit:]


class AuditHandler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            recs = read_records(limit=0)
            total = len(recs)
            self._send(200, {"status": "healthy", "service": "gov-audit", "version": "1.0.0",
                             "trace": TRACE, "did": DID, "audit_total": total})
        elif self.path.startswith("/audit"):
            limit = 50
            since = None
            q = self.path.split("?", 1)[-1]
            for pair in q.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    if k == "limit":
                        try:
                            limit = int(v)
                        except Exception:
                            pass
                    elif k == "since":
                        since = v
            recs = read_records(limit=limit, since=since)
            self._send(200, {"success": True, "count": len(recs), "records": recs,
                             "file": AUDIT_FILE})
        else:
            self._send(404, {"success": False, "error": "not found"})

    def do_POST(self):
        if self.path == "/audit":
            length = int(self.headers.get("Content-Length", 0))
            try:
                data = json.loads(self.rfile.read(length).decode() or "{}")
            except Exception:
                self._send(400, {"success": False, "error": "invalid json"})
                return
            data.setdefault("time", datetime.now().isoformat())
            data.setdefault("trace", TRACE)
            data.setdefault("did", DID)
            append_record(data)
            self._send(200, {"success": True, "stored": True, "count": len(read_records(limit=0))})
        else:
            self._send(404, {"success": False, "error": "not found"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    import os
    port = int(os.environ.get("GOV_AUDIT_PORT", "8202"))
    server = ThreadingHTTPServer(("0.0.0.0", port), AuditHandler)
    print(f"火斗云智·政务AI中台持久化审计 V1.0 启动于 :{port} | {TRACE} | {DID} | 存储:{AUDIT_FILE}")
    server.serve_forever()
