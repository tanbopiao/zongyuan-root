#!/usr/bin/env python3
"""gateway_server.py · 云端中枢元内核 · 真值网关 HTTP
端点：POST /api/report/truth（X-DID 单头认证，无尾部斜杠）
兼容：GET /api/status 状态页
启动：python3 gateway_server.py [--port 9001]
"""
import json, sys, os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from truth_store import append_truth, state, status_ok, DID, query_truth, ledger_snapshot, verify_merkle

PORT = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 9001
VALID_DIDS = {"DID-BR-000002"}


class GW(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/api/status":
            st = state()
            self._send(200, {
                "status": "ok" if status_ok() else "degraded",
                "service": "zhongshu-meta-core",
                "did": DID,
                "anchor": "Ω₀⊂⊙∞⊂Ω",
                "truth_count": st.get("ledger_lines", 0),
                "merkle_root": st.get("merkle_root", ""),
                "version": "V3.1",
            })
        elif p == "/api/truth":
            # 真值查询: ?key=前缀&limit=N
            from urllib.parse import parse_qs
            q = parse_qs(urlparse(self.path).query)
            rows = query_truth(q.get("key", [""])[0], int(q.get("limit", ["10"])[0]))
            self._send(200, {"ok": True, "count": len(rows), "results": rows})
        elif p == "/api/ledger":
            from urllib.parse import parse_qs
            q = parse_qs(urlparse(self.path).query)
            self._send(200, {"ok": True, **ledger_snapshot(int(q.get("limit", ["10"])[0]))})
        elif p == "/api/verify":
            self._send(200, {"ok": True, **verify_merkle()})
        elif p == "/api/verify-seed":
            from urllib.parse import parse_qs
            q = parse_qs(urlparse(self.path).query)
            self._send(200, {"ok": True, **verify_seed(q.get("doc", ["SEED_TRUTH_v5.1"])[0])})
        elif p == "/api/sub-l0":
            from urllib.parse import parse_qs
            q = parse_qs(urlparse(self.path).query)
            tenant = q.get("tenant", [""])[0]
            if tenant:
                self._send(200, {"ok": True, **sub_l0_get(tenant)})
            else:
                self._send(200, {"ok": True, "tenants": sub_l0_list()})
        else:
            self._send(404, {"error": "not_found", "message": f"未知端点: {p}"})

    def do_POST(self):
        p = urlparse(self.path).path
        if p == "/api/sub-l0":
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception as e:
                self._send(400, {"error": "bad_json", "message": str(e)[:120]}); return
            self._send(200, {"ok": True, **sub_l0_create(payload)})
            return
        if p != "/api/report/truth":
            self._send(404, {"error": "not_found", "message": f"未知端点: {p}"})
            return
        x_did = self.headers.get("X-DID", "")
        if x_did not in VALID_DIDS:
            self._send(401, {"error": "unauthorized", "message": "X-DID 未授权"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except Exception as e:
            self._send(400, {"error": "bad_json", "message": str(e)[:120]})
            return
        key = payload.get("key", f"truth-{int(__import__('time').time()*1000)}")
        value = payload.get("value", {})
        if not isinstance(value, dict):
            self._send(400, {"error": "value_must_be_object"})
            return
        try:
            res = append_truth(key, value, x_did)
            self._send(200, {
                "ok": True, "message": "真值写入成功",
                "key": key, "truth_count": res["truth_count"],
                "seq": res["seq"], "event_id": res["event_id"],
            })
        except Exception as e:
            self._send(500, {"error": "write_failed", "message": str(e)[:160]})



import time
DATA_DIR = "/www/wwwroot/huodouai.com/zhongshu/data"  # 云内核数据区(网关本机路径)

def verify_seed(doc="SEED_TRUTH_v5.1"):
    """种子 L0 公开校验: 重算 Merkle vs 存储根 (与种子根生成规则一致, 可复现)"""
    import hashlib as _h, os as _o
    p = _o.path.join(DATA_DIR, "seed-truth", f"{doc}.json")
    if not _o.path.exists(p):
        return {"error": "seed_doc_not_found", "doc": doc}
    d = json.load(open(p, encoding="utf-8"))
    order = {"本体层":0,"分层层":1,"工程层":2,"边界层":3,"公理层":4,"锚定层":5}
    ax = sorted(d["axioms"], key=lambda a: (order.get(a["layer"],9), a["id"]))
    root = "0000"
    for a in ax:
        ns = _h.sha256(f"{a['id']}|{a['layer']}|{a['text']}|mutable=false|{a['counterexample_lock']}".encode()).hexdigest()
        root = _h.sha256((root + ns).encode()).hexdigest()
    stored = d["merkle"]["root_sha256"]
    return {"doc": doc, "computed": root, "stored": stored, "consistent": root == stored,
            "axioms": len(ax), "version": d.get("version", "?"), "verified_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

def sub_l0_root(seed_root, tenant_id, extra_rules):
    """子 L0 派生规则(第8章): sub_root = sha256累积(seed_root + tenant_id + 排序extra_rules哈希)"""
    import hashlib as _h
    c = seed_root
    c = _h.sha256((c + f"|tenant:{tenant_id}").encode()).hexdigest()
    for r in sorted(extra_rules):
        c = _h.sha256((c + f"|rule:{r}").encode()).hexdigest()
    return c

def sub_l0_create(payload):
    import os as _o
    tenant = (payload.get("tenant_id") or "").strip()
    if not tenant or len(tenant) > 64:
        return {"error": "invalid_tenant", "message": "tenant_id 必填且<=64字符"}
    extra = [str(r) for r in (payload.get("extra_rules") or [])]
    seed_doc = payload.get("seed_doc", "SEED_TRUTH_v5.1")
    sv = verify_seed(seed_doc)
    if not sv.get("consistent"):
        return {"error": "seed_root_inconsistent", "message": "G-L0 根校验失败, 拒绝派生"}
    seed_root = sv["stored"]
    sub_root = sub_l0_root(seed_root, tenant, extra)
    d = {"tenant_id": tenant, "sub_l0_root": sub_root, "derived_from": seed_doc,
         "seed_root": seed_root, "extra_rules": extra, "inherited": "S1-S25+AΩ1-5/E1-4/M1-2(不可删改)",
         "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    ddir = _o.path.join(DATA_DIR, "sub-l0"); _o.makedirs(ddir, exist_ok=True)
    fp = _o.path.join(ddir, f"{tenant}.json")
    _o.makedirs(_o.path.join(DATA_DIR, "sub-l0"), exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=1)
    # 索引追加(append-only)
    with open(_o.path.join(DATA_DIR, "sub-l0", "index.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"tenant_id":tenant,"sub_l0_root":sub_root,"seed_root":seed_root,"at":d["created_at"]},ensure_ascii=False)+"\n")
    return d

def sub_l0_get(tenant):
    import os as _o
    fp = _o.path.join(DATA_DIR, "sub-l0", f"{tenant}.json")
    if not _o.path.exists(fp):
        return {"error": "tenant_not_found", "tenant": tenant}
    return json.load(open(fp, encoding="utf-8"))

def sub_l0_list():
    import os as _o
    idx = _o.path.join(DATA_DIR, "sub-l0", "index.jsonl")
    if not _o.path.exists(idx):
        return []
    return [json.loads(l) for l in open(idx, encoding="utf-8").read().strip().split("\n") if l.strip()]

if __name__ == "__main__":
    print(f"云端中枢元内核 · 真值网关启动 http://127.0.0.1:{PORT} (仅本机, nginx反代)")
    HTTPServer(("127.0.0.1", PORT), GW).serve_forever()

