#!/usr/bin/env python3
"""SNN感知层：事件过滤器，异常才调Ark"""
import json, time, hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 已知事件指纹库（Merkle树叶子）
known = {}
# 简单规则：哪些pattern直接放过
RULES = {
    "heartbeat": {"action": "log", "ark_needed": False},
    "health_check": {"action": "log", "ark_needed": False},
    "deploy.success": {"action": "log", "ark_needed": False},
    "gpu.done": {"action": "notify", "ark_needed": True},
    "error": {"action": "alert", "ark_needed": True},
}

HOST, PORT = "127.0.0.1", 18082

class H(BaseHTTPRequestHandler):
    def _j(self,c,o):
        b=json.dumps(o,ensure_ascii=False).encode()
        self.send_response(c);self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):
        if self.path=="/health":
            self._j(200,{"ok":True,"service":"snn-gate","known_signals":len(known)})
        else: self._j(404,{"ok":False})
    def do_POST(self):
        n=int(self.headers.get("Content-Length",0))
        try: p=json.loads(self.rfile.read(n) or "{}")
        except: p={}
        event = p.get("event","unknown")
        # 指纹
        fp = hashlib.sha256(event.encode()).hexdigest()[:16]
        # 匹配规则
        rule = RULES.get(event, {"action":"unknown","ark_needed":True})
        known[fp] = {"event":event,"ts":int(time.time()),"action":rule["action"]}
        self._j(200,{
            "ok":True,
            "event":event,
            "fingerprint":fp,
            "action":rule["action"],
            "ark_needed":rule["ark_needed"],
            "note":"已过SNN门控"
        })
    def log_message(self,*a): pass

if __name__=="__main__":
    print("SNN gate :%d" % PORT)
    ThreadingHTTPServer((HOST,PORT),H).serve_forever()
