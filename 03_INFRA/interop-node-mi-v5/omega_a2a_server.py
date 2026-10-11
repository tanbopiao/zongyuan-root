#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一自治内核 · A2A Server（互操作层）
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ INTEROP-A2A-V1.0

A2A (Agent2Agent) 协议轻量实现（零依赖，HTTP + JSON-RPC 2.0）：
  GET  /.well-known/agent-card.json   Agent Card 发现
  GET  /.well-known/agent.json        旧版发现（同一份卡片）
  POST /                              message/send / tasks/get

启动：python3 omega_a2a_server.py [--port 8099]
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CARD_PATH = os.path.join(HERE, "agent-card.json")
SNAPSHOT = "/workspace/universal-kernel/AI-UNIVERSAL-KERNEL-PACKET.json"
BOOT_REPORT = "/workspace/node-identity/var/dashboard.json"
MEMORY_INDEX = "/workspace/node-identity/var/truth-sync/truth-all.json"

GATEWAY = "https://www.huodouai.com"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
NODE_ID = "NODE-MI-V5-001"
CAPTURE_TOKEN = os.environ.get("ZR_CAPTURE_TOKEN", "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d")

TASKS = {}


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _text_from_message(msg):
    parts = msg.get("parts", []) if isinstance(msg, dict) else []
    out = []
    for p in parts:
        if isinstance(p, dict) and p.get("text"):
            out.append(p["text"])
    return " ".join(out)


def _gateway_post(path, payload):
    try:
        body = json.dumps(payload, ensure_ascii=False).encode()
        req = urllib.request.Request(
            GATEWAY + path, data=body, method="POST",
            headers={"Content-Type": "application/json", "X-DID": DID},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e), "ok": False}


def _gateway_get(path):
    try:
        req = urllib.request.Request(GATEWAY + path, headers={"X-DID": DID})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e), "ok": False}


def handle_text(text):
    """将 A2A 消息文本映射到内核技能，返回 (skill, result)"""
    t = (text or "").strip()
    low = t.lower()
    if low.startswith("status") or "状态" in t:
        snap = _load_json(SNAPSHOT, {})
        boot = _load_json(BOOT_REPORT, {})
        return "omega_status", {
            "kernel": snap.get("kernel"), "did": DID, "anchor": ANCHOR,
            "boot_report": {k: boot.get(k) for k in ("status", "steps_pass", "steps_total", "generated_at") if k in boot},
            "cloud_truth": snap.get("cloud_truth"),
        }
    if low.startswith("recall ") or low.startswith("召回 "):
        key = urllib.parse.quote(t.split(None, 1)[1].strip(), safe="")
        return "truth_recall", _gateway_get("/api/truth/" + key)
    if low.startswith("report ") or low.startswith("上报 "):
        rest = t.split(None, 1)[1]
        payload = {"key": "REPORT.A2A.%s" % NODE_ID, "value": {"content": rest, "did": DID, "anchor": ANCHOR}}
        if "=" in rest:
            k, _, v = rest.partition("=")
            payload["key"] = k.strip()
            payload["value"] = {"content": v.strip(), "did": DID, "anchor": ANCHOR}
        return "truth_report", _gateway_post("/api/report/truth", payload)
    if low.startswith("anchor ") or low.startswith("锚定 "):
        kw = t.split(None, 1)[1].strip().lower()
        idx = _load_json(MEMORY_INDEX, {})
        entries = idx.get("asset_entries", [])
        matched = [e for e in entries if kw in e.get("summary", "").lower() or kw in ",".join(e.get("tags", [])).lower()]
        return "memory_anchor", {
            "matched_count": len(matched),
            "memories": ["[%s] %s | %s" % (e.get("priority", "C"), e.get("asset_id", ""), e.get("summary", ""))[:400] for e in matched[:10]],
        }
    if "heartbeat" in low or "心跳" in t:
        payload = {
            "key": "REPORT.NODE.HEARTBEAT.%s" % NODE_ID,
            "value": {"event": "node_heartbeat", "node_id": NODE_ID, "did": DID,
                      "anchor": ANCHOR, "status": "alive",
                      "ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800")},
        }
        return "node_heartbeat", _gateway_post("/api/report/truth", payload)
    return "skills", {
        "skills": ["status/状态", "recall <key>/召回", "report <key>=<value>/上报",
                   "anchor <keyword>/锚定", "heartbeat/心跳"],
        "note": "未匹配技能，可用以上指令与元极恒一内核交互"
    }


def make_task(tid, text):
    skill, result = handle_text(text)
    return {
        "id": tid,
        "contextId": "omega-%s" % DID,
        "status": {"state": "completed"},
        "artifacts": [{
            "artifactId": "%s-artifact" % tid,
            "name": skill,
            "parts": [{"kind": "data", "data": result}],
        }],
        "metadata": {"did": DID, "anchor": ANCHOR, "skill": skill},
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/.well-known/agent-card.json", "/.well-known/agent.json"):
            self._send(200, _load_json(CARD_PATH, {}))
            return
        if path == "/health":
            self._send(200, {"status": "healthy", "service": "omega_a2a", "did": DID, "anchor": ANCHOR})
            return
        self._send(404, {"error": "not_found", "path": path})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode() or "{}")
        except Exception:
            self._send(400, {"jsonrpc": "2.0", "error": {"code": -32700, "message": "parse error"}})
            return
        rid = req.get("id")
        method = req.get("method", "")
        params = req.get("params") or {}
        if method == "message/send":
            text = _text_from_message(params.get("message") or {})
            tid = "task-%s" % time.strftime("%Y%m%d%H%M%S")
            task = make_task(tid, text)
            TASKS[tid] = task
            self._send(200, {"jsonrpc": "2.0", "id": rid, "result": task})
            return
        if method == "tasks/get":
            tid = params.get("id")
            task = TASKS.get(tid)
            if task:
                self._send(200, {"jsonrpc": "2.0", "id": rid, "result": task})
            else:
                self._send(200, {"jsonrpc": "2.0", "id": rid,
                                 "error": {"code": -32001, "message": "task not found: %s" % tid}})
            return
        self._send(200, {"jsonrpc": "2.0", "id": rid,
                         "error": {"code": -32601, "message": "method not found: %s" % method}})

    def log_message(self, fmt, *args):
        sys.stderr.write("[A2A] %s\n" % (fmt % args))


def main():
    ap = argparse.ArgumentParser(description="元极恒一自治内核 A2A Server")
    ap.add_argument("--port", type=int, default=8099)
    args = ap.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("[A2A] 元极恒一互操作节点已启动: http://127.0.0.1:%d  DID=%s %s" % (args.port, DID, ANCHOR))
    server.serve_forever()


if __name__ == "__main__":
    main()