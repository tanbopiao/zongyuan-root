#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT Webhook事件驱动引擎 V1.0
- 13种事件类型
- HMAC-SHA256签名验证 (X-ZR-Signature)
- SQLite持久化
- 事件统计与查询API
- 确权：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""

import os
import sys
import json
import time
import hmac
import hashlib
import sqlite3
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

KERNEL_ROOT = "/opt/ZONGYUAN-ROOT"
WEBHOOK_DIR = os.path.join(KERNEL_ROOT, "engines", "webhook")
DB_PATH = os.path.join(WEBHOOK_DIR, "webhook_events.db")
SECRET = "DID-BR-000002-ZONGYUAN-ROOT-SECRET"
TIMESTAMP_WINDOW = 300  # 5分钟

# 13种事件类型
EVENT_TYPES = [
    "truth_update", "service_status", "approval_result", "deployment",
    "alert", "evolution", "node_report", "media_archive",
    "git_push", "cron_trigger", "manual_trigger", "system_health", "custom"
]

os.makedirs(WEBHOOK_DIR, exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        event_type TEXT,
        source TEXT,
        payload TEXT,
        signature TEXT,
        timestamp REAL,
        received_at REAL,
        status TEXT,
        processed_at REAL
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_type ON events(event_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_time ON events(received_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_status ON events(status)")
    conn.commit()
    conn.close()


def verify_signature(payload_str, timestamp, signature):
    """HMAC-SHA256签名验证"""
    if not signature:
        return False
    # 时间戳窗口检查
    try:
        if abs(time.time() - float(timestamp)) > TIMESTAMP_WINDOW:
            return False
    except:
        return False
    expected = hmac.new(
        SECRET.encode(),
        (timestamp + payload_str).encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def store_event(event_id, event_type, source, payload, signature, timestamp):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO events 
        (id, event_type, source, payload, signature, timestamp, received_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'received')""",
        (event_id, event_type, source, json.dumps(payload, ensure_ascii=False),
         signature, timestamp, time.time()))
    conn.commit()
    conn.close()


def get_events(limit=50, event_type=None, status=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    query = "SELECT * FROM events WHERE 1=1"
    params = []
    if event_type:
        query += " AND event_type=?"
        params.append(event_type)
    if status:
        query += " AND status=?"
        params.append(status)
    query += " ORDER BY received_at DESC LIMIT ?"
    params.append(limit)
    rows = c.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    total = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    by_type = c.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type ORDER BY 2 DESC").fetchall()
    by_status = c.execute("SELECT status, COUNT(*) FROM events GROUP BY status").fetchall()
    today = c.execute("SELECT COUNT(*) FROM events WHERE date(datetime(received_at, 'unixepoch', 'localtime')) = date('now', 'localtime')").fetchone()[0]
    conn.close()
    return {
        "total": total,
        "today": today,
        "by_type": dict(by_type),
        "by_status": dict(by_status),
        "event_types_supported": EVENT_TYPES
    }


class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/health":
            self._send_json({
                "status": "ok",
                "service": "webhook_event_engine",
                "version": "1.0.0",
                "event_types": len(EVENT_TYPES),
                "did": "DID-BR-000002",
                "trace": "Ω₀⊂⊙∞⊂Ω"
            })
        elif path == "/events":
            limit = int(params.get("limit", [50])[0])
            event_type = params.get("type", [None])[0]
            status = params.get("status", [None])[0]
            events = get_events(limit, event_type, status)
            self._send_json({"count": len(events), "events": events})
        elif path == "/stats":
            self._send_json(get_stats())
        elif path == "/dashboard":
            # 返回可视化页面
            dashboard_path = os.path.join(WEBHOOK_DIR, "dashboard.html")
            if os.path.exists(dashboard_path):
                with open(dashboard_path) as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content.encode())))
                self.end_headers()
                self.wfile.write(content.encode())
            else:
                self._send_json({"error": "dashboard_not_found"}, 404)
        else:
            self._send_json({"error": "not_found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length > 0 else "{}"

        if path == "/webhook":
            # 接收webhook事件
            signature = self.headers.get("X-ZR-Signature", "")
            timestamp = self.headers.get("X-ZR-Timestamp", str(time.time()))
            event_type = self.headers.get("X-ZR-Event-Type", "custom")
            source = self.headers.get("X-ZR-Source", "unknown")
            event_id = self.headers.get("X-ZR-Event-Id", str(uuid.uuid4()))

            # 签名验证（可选，无签名时标记为unverified）
            verified = verify_signature(body, timestamp, signature) if signature else False

            try:
                payload = json.loads(body)
            except:
                payload = {"raw": body}

            store_event(event_id, event_type, source, payload, signature, float(timestamp))

            self._send_json({
                "status": "accepted" if verified else "accepted_unverified",
                "event_id": event_id,
                "event_type": event_type,
                "verified": verified,
                "message": "事件已接收"
            })
        elif path == "/events/test":
            # 发送测试事件
            test_event = {
                "id": str(uuid.uuid4()),
                "event_type": "manual_trigger",
                "source": "dashboard_test",
                "payload": {"message": "测试事件", "time": datetime.now().isoformat()},
                "timestamp": time.time()
            }
            store_event(test_event["id"], test_event["event_type"], test_event["source"],
                       test_event["payload"], "", test_event["timestamp"])
            self._send_json({"status": "test_event_sent", "event": test_event})
        else:
            self._send_json({"error": "not_found"}, 404)


def main():
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8089
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    init_db()
    print(f"[Webhook Engine] V1.0 启动 | {host}:{port}")
    print(f"[Webhook Engine] 事件类型: {len(EVENT_TYPES)}种")
    print(f"[Webhook Engine] 签名: HMAC-SHA256 | 时间窗口: {TIMESTAMP_WINDOW}s")
    server = HTTPServer((host, port), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
