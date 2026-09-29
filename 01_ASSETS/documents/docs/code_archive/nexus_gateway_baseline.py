#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 云枢 Nexus 网关 v1.0
免SSH HTTPS 直连层：TLS + 令牌HMAC签名 + 速率限制，转发至记忆网关 9120，
并开放真值列表/审计查询/远端锁档触发能力。
"""
import base64
import hashlib
import hmac
import http.client
import http.server
import json
import os
import re
import socket
import sqlite3
import ssl
import subprocess
import sys
import threading
import time
from collections import deque

BASE = "/opt/ZONGYUAN-ROOT/engine/nexus"
TOKEN_FILE = os.path.join(BASE, "nexus_token")
CERT_FILE = os.path.join(BASE, "nexus_cert.pem")
KEY_FILE = os.path.join(BASE, "nexus_key.pem")
UPSTREAM_HOST = "127.0.0.1"
UPSTREAM_PORT = 9120
DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
LOCK_SCRIPT = "/opt/ZONGYUAN-ROOT/engine/scripts/full_lock_archive.py"
PORT = 9443
TS_WINDOW = 300
RATE_LIMIT = 150          # 每分钟每IP
RATE_WINDOW = 60

TOKEN = ""
_ratelock = threading.Lock()
_hits = {}


def load_token():
    global TOKEN
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        TOKEN = f.read().strip()


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def verify_auth(headers, body_bytes: bytes, method: str, path: str) -> bool:
    tok = headers.get("X-ZY-Token", "")
    ts = headers.get("X-ZY-TS", "")
    sig = headers.get("X-ZY-SIG", "")
    if not tok or not ts or not sig:
        return False
    if not hmac.compare_digest(tok, TOKEN):
        return False
    try:
        if abs(time.time() - int(ts)) > TS_WINDOW:
            return False
    except Exception:
        return False
    body_sha = hashlib.sha256(body_bytes).hexdigest()
    expect = hmac.new(TOKEN.encode(), f"{ts}\n{method}\n{path}\n{body_sha}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expect, sig)


def rate_ok(ip: str) -> bool:
    now = time.time()
    with _ratelock:
        q = _hits.get(ip)
        if q is None:
            q = deque()
            _hits[ip] = q
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return False
        q.append(now)
    return True


def proxy_upstream(method: str, path: str, body: bytes):
    conn = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=10)
    headers = {"Content-Type": "application/json"}
    if body:
        headers["Content-Length"] = str(len(body))
    conn.request(method, path, body=body, headers=headers)
    resp = conn.getresponse()
    data = resp.read()
    status = resp.status
    conn.close()
    try:
        parsed = json.loads(data.decode("utf-8"))
    except Exception:
        parsed = {"raw": data.decode("utf-8", "replace")}
    return status, parsed


def list_table(table: str, limit: int):
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        row = cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if not row:
            return [], "table not found"
        sql = row["sql"] if "sql" in row.keys() else row[0]
        m = re.search(r"\((.*)\)", sql, re.S)
        cols = [c.strip().split(" ")[0].strip('"') for c in m.group(1).split(",") if c.strip()]
        rows = cur.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()
        out = [dict(r) for r in rows]
        return out, None
    finally:
        conn.close()


def run_lock():
    try:
        proc = subprocess.run(["python3", LOCK_SCRIPT], capture_output=True, text=True, timeout=180)
        out = proc.stdout.strip()
        last_json = None
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    last_json = json.loads(line)
                except Exception:
                    pass
        if last_json:
            return 0, last_json
        return proc.returncode, {"stdout_tail": out[-1200:], "stderr_tail": proc.stderr[-400:]}
    except subprocess.TimeoutExpired:
        return 1, {"error": "lock timeout(180s)"}
    except Exception as e:
        return 2, {"error": str(e)}


class NexusHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("[nexus] %s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), fmt % args))

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-ZY-Service", "zongyuan-nexus")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", 0))
        except Exception:
            length = 0
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def _route(self, method: str):
        path = self.path.split("?")[0]
        body = self._read_body()

        if not rate_ok(self.client_address[0]):
            self._send(429, {"ok": False, "error": "rate_limited"})
            return
        if not verify_auth(self.headers, body, method, path):
            self._send(401, {"ok": False, "error": "unauthorized"})
            return

        if path == "/v1/ping":
            self._send(200, {"ok": True, "data": {"service": "zongyuan-nexus", "time": time.strftime("%Y-%m-%dT%H:%M:%S%z")}})
            return

        if path == "/v1/health":
            st, data = proxy_upstream("GET", "/health", b"")
            self._send(st if st in (200, 503) else 502, {"ok": st == 200, "data": data, "upstream_status": st})
            return

        if path == "/v1/nodes" and method == "GET":
            st, data = proxy_upstream("GET", "/api/nodes", b"")
            self._send(st if st == 200 else 502, {"ok": st == 200, "data": data, "upstream_status": st})
            return

        if path == "/v1/node/register" and method == "POST":
            st, data = proxy_upstream("POST", "/api/node/register", body)
            self._send(st if st == 200 else 502, {"ok": st == 200, "data": data, "upstream_status": st})
            return

        if path == "/v1/node/heartbeat" and method == "POST":
            st, data = proxy_upstream("POST", "/api/node/heartbeat", body)
            self._send(st if st == 200 else 502, {"ok": st == 200, "data": data, "upstream_status": st})
            return

        if path == "/v1/truth/upsert" and method == "POST":
            st, data = proxy_upstream("POST", "/api/truth/upsert", body)
            self._send(st if st == 200 else 502, {"ok": st == 200, "data": data, "upstream_status": st})
            return

        if path == "/v1/truth/sync" and method == "POST":
            st, data = proxy_upstream("POST", "/api/truth/sync", body)
            self._send(st if st == 200 else 502, {"ok": st == 200, "data": data, "upstream_status": st})
            return

        if path == "/v1/truths" and method == "GET":
            limit = 20
            q = self.path.split("?", 1)
            if len(q) > 1:
                for kv in q[1].split("&"):
                    if kv.startswith("limit="):
                        try:
                            limit = min(int(kv.split("=")[1]), 200)
                        except Exception:
                            pass
            rows, err = list_table("truths", limit)
            if err:
                self._send(500, {"ok": False, "error": err})
            else:
                self._send(200, {"ok": True, "data": {"count": len(rows), "truths": rows}})
            return

        if path == "/v1/audit" and method == "GET":
            limit = 20
            q = self.path.split("?", 1)
            if len(q) > 1:
                for kv in q[1].split("&"):
                    if kv.startswith("limit="):
                        try:
                            limit = min(int(kv.split("=")[1]), 200)
                        except Exception:
                            pass
            rows, err = list_table("audit_logs", limit)
            if err:
                self._send(500, {"ok": False, "error": err})
            else:
                self._send(200, {"ok": True, "data": {"count": len(rows), "audit": rows}})
            return

        if path == "/v1/lock" and method == "POST":
            code, result = run_lock()
            self._send(200 if code == 0 else 500, {"ok": code == 0, "data": result})
            return

        self._send(404, {"ok": False, "error": "not_found", "path": path})

    def do_GET(self):
        try:
            self._route("GET")
        except Exception as e:
            try:
                self._send(500, {"ok": False, "error": str(e)})
            except Exception:
                pass

    def do_POST(self):
        try:
            self._route("POST")
        except Exception as e:
            try:
                self._send(500, {"ok": False, "error": str(e)})
            except Exception:
                pass


def main():
    load_token()
    if not TOKEN:
        print("nexus_token 缺失", file=sys.stderr)
        sys.exit(1)
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), NexusHandler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    print(f"[nexus] listening on 0.0.0.0:{PORT} (TLS)", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
