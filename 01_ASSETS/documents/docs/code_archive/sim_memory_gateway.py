#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地仿真·模拟记忆网关（替代云端 9120 上游）
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
本地仿真专用：SQLite + 简易HTTP，模拟 /health /api/nodes /api/truth/upsert 等端点。
"""
import json, os, sqlite3, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer

SIM_DIR = "/home/user/Doubao/chats/38438306874426882/.sim_nexus"
DB = os.path.join(SIM_DIR, "data", "memory_gateway.db")
PORT = 9120

def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS truths(id INTEGER PRIMARY KEY AUTOINCREMENT, truth_key TEXT, content TEXT, category TEXT, node_id TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS nodes(id TEXT PRIMARY KEY, node_type TEXT, capabilities TEXT, status TEXT, last_seen TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, node_id TEXT, detail TEXT, created_at TEXT)")
    conn.commit()
    # 预置节点
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    c.execute("INSERT OR IGNORE INTO nodes VALUES (?,?,?,?,?)", ("cloud-main-kernel-001","kernel",'["truth_rw"]',"online",now))
    conn.commit()
    conn.close()

class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a): pass
    def _j(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def _body(self):
        n = int(self.headers.get("Content-Length",0)); return self.rfile.read(n) if n>0 else b""
    def do_GET(self):
        conn = sqlite3.connect(DB); conn.row_factory=sqlite3.Row; c=conn.cursor()
        p = self.path.split("?")[0]
        if p=="/health":
            self._j(200, {"version":"V3.0-sim","status":"ok","db":"sqlite","truths":c.execute("SELECT COUNT(*) n FROM truths").fetchone()["n"]})
        elif p=="/api/nodes":
            rows=c.execute("SELECT id,node_type,status FROM nodes").fetchall()
            self._j(200, {"nodes":{r["id"]:{"node_type":r["node_type"],"status":r["status"]} for r in rows}})
        else:
            self._j(404, {"error":"not_found"})
        conn.close()
    def do_POST(self):
        conn = sqlite3.connect(DB); conn.row_factory=sqlite3.Row; c=conn.cursor()
        p=self.path.split("?")[0]; body=self._body()
        try: d=json.loads(body.decode() or "{}")
        except Exception: d={}
        now=time.strftime("%Y-%m-%dT%H:%M:%S")
        if p=="/api/truth/upsert":
            c.execute("INSERT INTO truths(truth_key,content,category,node_id,created_at) VALUES(?,?,?,?,?)",
                      (d.get("truth_key"),d.get("content"),d.get("category"),d.get("node_id"),now))
            conn.commit()
            self._j(200, {"ok":True,"id":c.lastrowid})
        elif p=="/api/node/register":
            c.execute("INSERT OR REPLACE INTO nodes(id,node_type,capabilities,status,last_seen) VALUES(?,?,?,?,?)",
                      (d.get("node_id"),d.get("node_type"),json.dumps(d.get("capabilities",[])),"online",now))
            conn.commit()
            self._j(200, {"ok":True,"node_id":d.get("node_id")})
        elif p=="/api/node/heartbeat":
            c.execute("UPDATE nodes SET last_seen=? WHERE id=?", (now,d.get("node_id")))
            conn.commit()
            self._j(200, {"ok":True})
        elif p=="/api/truth/sync":
            n=0
            for t in d.get("truths",[]):
                c.execute("INSERT INTO truths(truth_key,content,category,node_id,created_at) VALUES(?,?,?,?,?)",
                          (t.get("truth_key"),t.get("content"),t.get("category"),t.get("node_id"),now)); n+=1
            conn.commit()
            self._j(200, {"ok":True,"synced":n})
        else:
            self._j(404, {"error":"not_found"})
        conn.close()

def main():
    init_db()
    print(f"[sim-memory-gateway] listening 127.0.0.1:{PORT}", flush=True)
    HTTPServer(("127.0.0.1",PORT), H).serve_forever()

if __name__=="__main__":
    main()
