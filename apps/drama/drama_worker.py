#!/usr/bin/env python3
"""短剧生产Worker - 独立进程，资源隔离，不影响主架构"""
import json, time, os, sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler

WORKER_PORT = 8091
TASK_DB = "/opt/ZONGYUAN-ROOT/apps/drama/tasks.db"

class WorkerHandler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status":"healthy","service":"drama-worker","port":WORKER_PORT,"memory_limit":"512M"})
        elif self.path == "/tasks":
            conn = sqlite3.connect(TASK_DB)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tasks")
            self._send(200, {"total": cur.fetchone()[0]})
            conn.close()
        else:
            self._send(404, {"error":"not found"})
    def do_POST(self):
        length = int(self.headers.get("Content-Length",0))
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw)
        if self.path == "/task/submit":
            conn = sqlite3.connect(TASK_DB)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, topic TEXT, status TEXT, created_at TEXT)")
            cur.execute("INSERT INTO tasks (topic,status,created_at) VALUES (?,?,?)", (data.get("topic",""), "pending", time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            tid = cur.lastrowid
            conn.close()
            self._send(200, {"status":"submitted","task_id":tid,"message":"任务已提交到独立Worker"})
        else:
            self._send(404, {"error":"not found"})
    def log_message(self, *args): pass

if __name__ == "__main__":
    os.makedirs(os.path.dirname(TASK_DB), exist_ok=True)
    server = HTTPServer(("0.0.0.0", WORKER_PORT), WorkerHandler)
    print("Drama Worker running on port %d, memory limit 512M" % WORKER_PORT)
    server.serve_forever()
