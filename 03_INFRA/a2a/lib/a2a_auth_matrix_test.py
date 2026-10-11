#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A2A 鉴权矩阵验收测试（Python 版，消除 shell 引用歧义）。"""
import sys
import json
import hmac
import time
import base64
import hashlib
import secrets
import urllib.request
import urllib.error

sys.path.insert(0, "/workspace/a2a/lib")
from a2a_identity import A2AIdentity

SALT = "ZR-HOMOLOGOUS-SALT-2026-OMEGA"
PP = "YuanJiHengYi-2026"
ENDPOINT = "http://127.0.0.1:8099/"
idn = A2AIdentity(SALT, PP)


def make_token(role, name):
    p = {"t": "HTK" + secrets.token_hex(4).upper(), "n": name, "r": role, "s": role,
         "e": int(time.time()) + 3600, "o": "Ω-TAN-7-001", "d": "DID-BR-000002"}
    pb = base64.urlsafe_b64encode(
        json.dumps(p, ensure_ascii=False, separators=(",", ":")).encode()).decode().rstrip("=")
    sig = hmac.new(idn.key, pb.encode(), hashlib.sha256).hexdigest()[:16]
    return "ZRH1.%s.%s" % (pb, sig)


def call(text, token=None):
    payload = {"jsonrpc": "2.0", "id": int(time.time() * 1000), "method": "message/send",
               "params": {"message": {"role": "user", "parts": [{"kind": "text", "text": text}]}}}
    body = json.dumps(payload, ensure_ascii=False).encode()
    h = {"Content-Type": "application/json"}
    if token:
        h["X-ZR-Token"] = token
    req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers=h)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def verdict_of(resp):
    r = resp.get("result", {})
    a = r.get("metadata", {}).get("auth", {})
    return "layer=%s peer=%s" % (a.get("layer"), a.get("peer"))


def err_of(resp):
    return resp.get("error", {}).get("message", "")


reader = make_token("reader", "peer-reader")
writer = make_token("writer", "peer-writer")
admin = make_token("admin", "peer-admin")

cases = [
    ("A 匿名只读 status",          "status",         None,   200, "anon-readonly"),
    ("B 匿名写 report",            "report HACK=1",  None,   401, None),
    ("C reader 只读 status",       "status",         reader, 200, "ok"),
    ("D reader 越权写 report",     "report X.Y=1",   reader, 403, None),
    ("E 伪造签名令牌",             "status",         "ZRH1.eyJ0IjoiSEsifQ.deadbeefdeadbeef", 403, None),
    ("F writer 写 report",         "report A2A.DEMO.OK=1", writer, 200, "ok"),
    ("G writer 只读 status",       "status",         writer, 200, "ok"),
    ("H 异源前缀令牌",             "status",         "ZRX1.abc.def", 403, None),
    ("I 格式残缺令牌",             "status",         "garbage",      403, None),
    ("J admin 写 report",          "report A2A.ADMIN.OK=1", admin, 200, "ok"),
]

print("=" * 78)
print("A2A 同源鉴权矩阵验收")
print("=" * 78)
passed = failed = 0
for name, text, tok, exp_code, exp_layer in cases:
    code, resp = call(text, tok)
    layer = (resp.get("result", {}).get("metadata", {}).get("auth", {}) or {}).get("layer")
    ok = (code == exp_code) and (exp_layer is None or layer == exp_layer)
    mark = "✔ PASS" if ok else "✘ FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    detail = verdict_of(resp) if code == 200 else err_of(resp)[:60]
    print("%s | %-22s | HTTP %-3s (期望 %s) | %s" % (mark, name, code, exp_code, detail))
print("-" * 78)
print("PASS=%d  FAIL=%d  TOTAL=%d" % (passed, failed, len(cases)))
print("=" * 78)
sys.exit(0 if failed == 0 else 1)
