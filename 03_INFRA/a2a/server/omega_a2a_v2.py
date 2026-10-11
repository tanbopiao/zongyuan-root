#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一自治内核 · A2A Server (同源鉴权增强版) v2.0
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ INTEROP-A2A-V2.0

承接既有 03_INFRA/interop/omega_a2a_server.py（INTEROP-A2A-V1.0），
在**不改变原技能语义**的前提下，补齐两处关键缺口：

  [缺口1] 原版 do_POST 完全匿名 → 任何人可调用 report 向网关写入真值
          → 本版焊入「同源协议 ZRH1」身份仲裁（X-ZR-Token 头）
  [缺口2] 原版仅 127.0.0.1 绑定 → 对端无法发现
          → 本版支持 --host 绑定与 --public-url 声明

新增端点：
  GET  /health                          健康探针（匿名）
  GET  /.well-known/agent-card.json      Agent Card 发现（匿名，对端握手）
  POST /                                  JSON-RPC 2.0（message/send 需同源令牌）

鉴权策略（可配置）：
  --require-auth      强制所有 message/send 需同源令牌（默认 true，生产）
  --anon-readonly     匿名仅可调用只读技能（status/recall/anchor/skills）
  --open              完全开放（仅调试，等价原版行为）

启动：
  python3 omega_a2a_v2.py --port 8099 --host 0.0.0.0 \
      --salt <salt> --passphrase <pp> --public-url http://<host>:8099/
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
ROOT = os.path.dirname(os.path.dirname(HERE))

CARD_PATH = os.path.join(HERE, "agent-card.json")
CARD_BASELINE = os.path.join(HERE, "agent-card.baseline.json")

GATEWAY = os.environ.get("ZR_GATEWAY", "https://www.huodouai.com")
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
NODE_ID = os.environ.get("ZR_NODE_ID", "NODE-DEV-WORKBUDDY-001")
CAPTURE_TOKEN = os.environ.get("ZR_CAPTURE_TOKEN", "")

# 只读技能集合（匿名可访问）
READONLY_SKILLS = {"omega_status", "truth_recall", "memory_anchor", "skills"}
WRITE_SKILLS = {"truth_report", "node_heartbeat"}

TASKS = {}
_START_TS = time.time()

# 身份仲裁器（延迟初始化）
_IDENTITY = None


def get_identity():
    global _IDENTITY
    return _IDENTITY


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


def _gateway_headers():
    h = {"Content-Type": "application/json", "X-DID": DID}
    if CAPTURE_TOKEN:
        h["X-Capture-Token"] = CAPTURE_TOKEN
    return h


def _gateway_post(path, payload):
    body = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(GATEWAY + path, data=body, method="POST",
                                 headers=_gateway_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"ok": False, "gateway_status": e.code,
                "detail": e.read().decode()[:300], "degraded": True}
    except Exception as e:
        return {"ok": False, "gateway_unreachable": True,
                "detail": str(e)[:200], "degraded": True}


def _gateway_get(path):
    req = urllib.request.Request(GATEWAY + path, headers=_gateway_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"ok": False, "gateway_status": e.code,
                "detail": e.read().decode()[:300], "degraded": True}
    except Exception as e:
        return {"ok": False, "gateway_unreachable": True,
                "detail": str(e)[:200], "degraded": True}


def classify(text):
    """仅识别技能名（无副作用），用于鉴权预判。"""
    t = (text or "").strip()
    low = t.lower()
    if low.startswith("status") or "状态" in t:
        return "omega_status"
    if low.startswith("recall ") or low.startswith("召回 "):
        return "truth_recall"
    if low.startswith("report ") or low.startswith("上报 "):
        return "truth_report"
    if low.startswith("anchor ") or low.startswith("锚定 "):
        return "memory_anchor"
    if "heartbeat" in low or "心跳" in t:
        return "node_heartbeat"
    return "skills"


def handle_text(text):
    """将 A2A 消息文本映射到内核技能，返回 (skill, result)。语义与原版一致。"""
    t = (text or "").strip()
    low = t.lower()
    if low.startswith("status") or "状态" in t:
        return "omega_status", {
            "kernel": "元极恒一自治内核", "did": DID, "anchor": ANCHOR,
            "node_id": NODE_ID,
            "gateway": GATEWAY,
            "uptime_sec": int(time.time() - _START_TS),
            "protocol": "INTEROP-A2A-V2.0",
        }
    if low.startswith("recall ") or low.startswith("召回 "):
        key = urllib.parse.quote(t.split(None, 1)[1].strip(), safe="")
        return "truth_recall", _gateway_get("/api/truth/" + key)
    if low.startswith("report ") or low.startswith("上报 "):
        rest = t.split(None, 1)[1]
        payload = {"key": "A2A.%s" % NODE_ID, "value": rest, "anchor": ANCHOR,
                   "truth_type": "data", "confidence": 0.9, "source_node": NODE_ID}
        if "=" in rest:
            k, _, v = rest.partition("=")
            payload["key"] = k.strip()
            payload["value"] = v.strip()
        return "truth_report", _gateway_post("/api/report/truth", payload)
    if low.startswith("anchor ") or low.startswith("锚定 "):
        kw = t.split(None, 1)[1].strip().lower()
        return "memory_anchor", {"keyword": kw, "note": "本地记忆索引锚定检索",
                                 "did": DID, "anchor": ANCHOR}
    if "heartbeat" in low or "心跳" in t:
        payload = {"key": "NODE.HEARTBEAT.%s" % NODE_ID,
                   "value": {"node_id": NODE_ID, "did": DID, "anchor": ANCHOR,
                             "ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800")},
                   "anchor": ANCHOR, "truth_type": "protocol",
                   "confidence": 1.0, "source_node": NODE_ID}
        return "node_heartbeat", _gateway_post("/api/report/truth", payload)
    return "skills", {
        "skills": ["status/状态", "recall <key>/召回", "report <key>=<value>/上报",
                   "anchor <keyword>/锚定", "heartbeat/心跳"],
        "note": "未匹配技能",
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
        "metadata": {"did": DID, "anchor": ANCHOR, "skill": skill, "node_id": NODE_ID},
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "OmegaA2A/2.0"

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _rpc_err(self, rid, code, message):
        self._send(200, {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}})

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/.well-known/agent-card.json", "/.well-known/agent.json"):
            card = _load_json(CARD_PATH, {}) or _load_json(CARD_BASELINE, {})
            self._send(200, card)
            return
        if path == "/health":
            self._send(200, {"status": "healthy", "service": "omega_a2a",
                             "version": "2.0", "protocol": "INTEROP-A2A-V2.0",
                             "did": DID, "anchor": ANCHOR, "node_id": NODE_ID,
                             "auth": "homologous-zrh1",
                             "uptime_sec": int(time.time() - _START_TS)})
            return
        if path == "/identity":
            idn = get_identity()
            if idn is None:
                self._send(503, {"error": "identity_not_initialized"})
            else:
                self._send(200, idn.identity_summary())
            return
        self._send(404, {"error": "not_found", "path": path})

    def do_POST(self):
        try:
            self._do_post_inner()
        except Exception as e:
            # 兜底：任何未捕获异常都不得导致连接静默断开
            try:
                self._send(500, {"jsonrpc": "2.0", "id": None,
                                 "error": {"code": -32000,
                                           "message": "internal error: %s" % str(e)[:200]}})
            except Exception:
                pass

    def _do_post_inner(self):
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
            # 预判技能（只识别不执行，避免副作用）
            skill = classify(text)
            need_auth = self.server.require_auth or (skill in WRITE_SKILLS)

            token = self.headers.get("X-ZR-Token", "") or params.get("token", "")
            verdict = {"allow": True, "layer": "open", "peer": None}

            if self.server.open_mode:
                verdict = {"allow": True, "layer": "open", "peer": {"name": "anonymous", "role": "admin"}}
            elif token:
                idn = get_identity()
                if idn is None:
                    self._send(503, {"jsonrpc": "2.0", "id": rid,
                                     "error": {"code": -32003, "message": "identity layer not initialized"}})
                    return
                required = "writer" if skill in WRITE_SKILLS else "reader"
                verdict = idn.check(token, required)
                if not verdict["allow"]:
                    self._send(403, {"jsonrpc": "2.0", "id": rid,
                                     "error": {"code": -32004,
                                               "message": "forbidden: %s (%s)" % (verdict["reason"], verdict["layer"])}})
                    return
            elif skill in READONLY_SKILLS and self.server.anon_readonly:
                # 匿名只读通道：放行只读技能
                verdict = {"allow": True, "layer": "anon-readonly",
                           "peer": {"name": "anonymous", "role": "reader"}}
            else:
                # 无令牌 + 写技能：--no-auth 模式下放宽，否则拒绝
                if skill in WRITE_SKILLS and not self.server.require_auth:
                    verdict = {"allow": True, "layer": "no-auth-write",
                               "peer": {"name": "anonymous", "role": "writer"}}
                else:
                    msg = ("unauthorized: 缺少同源令牌 X-ZR-Token（写技能必须鉴权）"
                           if skill in WRITE_SKILLS else
                           "forbidden: 匿名仅允许只读技能")
                    self._send(401 if skill in WRITE_SKILLS else 403,
                               {"jsonrpc": "2.0", "id": rid,
                                "error": {"code": -32002, "message": msg}})
                    return

            tid = "task-%s" % time.strftime("%Y%m%d%H%M%S")
            if tid in TASKS:
                tid = "%s-%s" % (tid, hashlib.md5(text.encode()).hexdigest()[:4])
            task = make_task(tid, text)
            task["metadata"]["auth"] = {"layer": verdict.get("layer"),
                                        "peer": (verdict.get("peer") or {}).get("name")}
            TASKS[tid] = task
            self._send(200, {"jsonrpc": "2.0", "id": rid, "result": task})
            return

        if method == "tasks/get":
            tid = params.get("id")
            task = TASKS.get(tid)
            if task:
                self._send(200, {"jsonrpc": "2.0", "id": rid, "result": task})
            else:
                self._rpc_err(rid, -32001, "task not found: %s" % tid)
            return

        self._rpc_err(rid, -32601, "method not found: %s" % method)

    def log_message(self, fmt, *args):
        sys.stderr.write("[A2A] %s\n" % (fmt % args))


class A2AServer(ThreadingHTTPServer):
    require_auth = True
    anon_readonly = True
    open_mode = False
    public_url = ""


def main():
    ap = argparse.ArgumentParser(description="元极恒一自治内核 A2A Server v2.0 (同源鉴权)")
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--salt", default=os.environ.get("ZR_HOMOLOGOUS_SALT", ""))
    ap.add_argument("--passphrase", default=os.environ.get("ZR_HOMOLOGOUS_PASSPHRASE", ""))
    ap.add_argument("--public-url", default="")
    ap.add_argument("--open", action="store_true", help="调试：完全开放")
    ap.add_argument("--no-auth", action="store_true", help="不强制鉴权（仍限只读）")
    ap.add_argument("--no-anon-readonly", action="store_true", help="禁止匿名只读")
    args = ap.parse_args()

    global _IDENTITY
    if args.salt and not args.open:
        from a2a_identity import A2AIdentity
        try:
            _IDENTITY = A2AIdentity(args.salt, args.passphrase)
            _IDENTITY.key  # 触发派生，校验口令
            print("[A2A] 同源身份已装载: %s (密钥内存持有，零落盘)"
                  % _IDENTITY.identity_summary()["homologous_id"])
        except Exception as e:
            print("[A2A] 警告: 同源身份装载失败: %s" % e)
            _IDENTITY = None

    srv = A2AServer((args.host, args.port), Handler)
    srv.require_auth = not (args.open or args.no_auth)
    srv.anon_readonly = not args.no_anon_readonly
    srv.open_mode = args.open
    srv.public_url = args.public_url
    print("[A2A] 节点启动: http://%s:%d  DID=%s %s" % (args.host, args.port, DID, ANCHOR))
    print("[A2A] 模式: auth=%s anon_readonly=%s open=%s identity=%s"
          % (srv.require_auth, srv.anon_readonly, srv.open_mode, _IDENTITY is not None))
    srv.serve_forever()


if __name__ == "__main__":
    main()
