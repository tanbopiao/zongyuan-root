#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 云枢 Nexus 网关 v2.0 · 多令牌/节点级鉴权增强版（本地仿真产物）
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

相对 v1.0 的增强：
  1. 令牌白名单模型：nexus_tokens.json { node_id: token } 替代单一 nexus_token
  2. verify_auth 按节点令牌校验：请求头 X-ZY-Node-Id 指定节点，用该节点 token 验 HMAC
  3. 向后兼容：未带 node 头时回退到 legacy 单令牌（nexus_token）校验
  4. 提供节点级令牌签发/吊销管理能力（配合 nexus_token_admin.py）
  5. 端到端不变：TLS + 转发记忆网关 9120 + 速率限制

安全约束：令牌文件 0600；本版本为本地仿真，未经人工审核不上云。
"""
import base64
import hashlib
import hmac
import http.client
import http.server
import json
import os
import re
import secrets
import socket
import sqlite3
import ssl
import subprocess
import sys
import threading
import time
from collections import deque

# ---------- 路径常量 ----------
BASE = "/opt/ZONGYUAN-ROOT/engine/nexus"          # 云端部署路径（本地仿真可改）
TOKEN_FILE = os.path.join(BASE, "nexus_token")     # legacy 单令牌（兼容）
TOKENS_JSON = os.path.join(BASE, "nexus_tokens.json")  # 多令牌白名单 {node_id: token}
CERT_FILE = os.path.join(BASE, "nexus_cert.pem")
KEY_FILE = os.path.join(BASE, "nexus_key.pem")
UPSTREAM_HOST = "127.0.0.1"
UPSTREAM_PORT = 9120
DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
LOCK_SCRIPT = "/opt/ZONGYUAN-ROOT/engine/scripts/full_lock_archive.py"
PORT = 9443
TS_WINDOW = 300
RATE_LIMIT = 150
RATE_WINDOW = 60

# ---------- 运行态 ----------
LEGACY_TOKEN = ""          # v1 单令牌（向后兼容）
NODE_TOKENS = {}           # {node_id: token} 多令牌白名单
_ratelock = threading.Lock()
_hits = {}


def load_legacy_token():
    """加载 v1 单令牌（若存在，向后兼容）"""
    global LEGACY_TOKEN
    if os.path.isfile(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                LEGACY_TOKEN = f.read().strip()
        except Exception:
            LEGACY_TOKEN = ""


def load_node_tokens():
    """加载多令牌白名单 {node_id: token}"""
    global NODE_TOKENS
    NODE_TOKENS = {}
    if os.path.isfile(TOKENS_JSON):
        try:
            with open(TOKENS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            NODE_TOKENS = data.get("nodes", data)
        except Exception:
            NODE_TOKENS = {}


def save_node_tokens():
    """持久化多令牌白名单（0600）"""
    tmp = TOKENS_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"nodes": NODE_TOKENS, "updated_at": int(time.time())}, f, ensure_ascii=False, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, TOKENS_JSON)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def verify_auth(headers, body_bytes: bytes, method: str, path: str) -> bool:
    """多令牌/节点级鉴权：
       - 带 X-ZY-Node-Id：用该节点 token 验 HMAC（主路径）
       - 不带：回退 legacy 单令牌（向后兼容 v1）
    """
    tok = headers.get("X-ZY-Token", "")
    ts = headers.get("X-ZY-TS", "")
    sig = headers.get("X-ZY-SIG", "")
    node = headers.get("X-ZY-Node-Id", "")
    if not tok or not ts or not sig:
        return False

    # 选择校验密钥
    secret = None
    if node:
        val = NODE_TOKENS.get(node, "")
        if not val:
            return False  # 节点不存在或已吊销
        # 兼容两种白名单格式：字符串 token 或 {token:...} 对象
        secret = val if isinstance(val, str) else val.get("token", "")
        if not secret:
            return False
    else:
        secret = LEGACY_TOKEN
        if not secret:
            return False

    if not hmac.compare_digest(tok, secret):
        return False
    try:
        if abs(time.time() - int(ts)) > TS_WINDOW:
            return False
    except Exception:
        return False
    body_sha = hashlib.sha256(body_bytes).hexdigest()
    expect = hmac.new(secret.encode(), f"{ts}\n{method}\n{path}\n{body_sha}".encode(), hashlib.sha256).hexdigest()
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

        # ---- 节点级令牌管理端点（仅限 root 节点，防滥用）----
        node = self.headers.get("X-ZY-Node-Id", "")
        if node == "root" and path == "/v1/tokens" and method == "GET":
            # 脱敏：不返回明文 token，只返回 node_id + 哈希
            masked = {}
            for k, v in NODE_TOKENS.items():
                tok = v if isinstance(v, str) else v.get("token", "")
                masked[k] = {"token_hash": sha256_hex(tok)[:16]} if tok else None
            self._send(200, {"ok": True, "data": {"nodes": masked, "count": len(masked)}})
            return

        if path == "/v1/ping":
            self._send(200, {"ok": True, "data": {"service": "zongyuan-nexus", "version": "2.0-multitoken", "time": time.strftime("%Y-%m-%dT%H:%M:%S%z")}})
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
    load_legacy_token()
    load_node_tokens()
    if not LEGACY_TOKEN and not NODE_TOKENS:
        print("[nexus] 无任何令牌（legacy 或节点令牌）", file=sys.stderr)
        sys.exit(1)
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), NexusHandler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    print(f"[nexus] v2.0 listening on 0.0.0.0:{PORT} (TLS, multi-token)", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
