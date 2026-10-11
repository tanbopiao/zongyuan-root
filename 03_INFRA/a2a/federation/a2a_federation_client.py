#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A 联邦出站客户端 v1.0
锚定: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 协议: A2A-FEDERATION-V1.0

职责：让本节点作为 A2A **客户端**主动联邦对端（补齐"只有 server 无 client"缺口）。
  - discover(peer): 拉取对端 agent-card，解析技能清单
  - send(peer, text): 携带同源令牌向对端发 message/send
  - federate(peer, text): discover + send 一步到位
  - 联邦台账：记录每次出站调用（对端/技能/裁决/耗时）

设计原则：
  - 出站一律携带 X-ZR-Token（同源令牌），满足对端鉴权
  - 令牌来源：本节点 self-issue（本地派生密钥签发），不落盘
  - 复用 a2a_identity 的密钥派生，不重复实现密码学（AXIOM-REUSE-NO-REDO-001）
  - 与网关仲裁联动：可选把出站裁决上报 /api/report/truth
"""
import os
import json
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.join(HERE, "..", "lib")
import sys
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

GATEWAY = os.environ.get("ZR_GATEWAY", "https://www.huodouai.com")
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
NODE_ID = os.environ.get("ZR_NODE_ID", "NODE-DEV-WORKBUDDY-001")
TIMEOUT = 15


class FederationClient:
    def __init__(self, salt: str, passphrase: str = None, self_name: str = None):
        from a2a_identity import A2AIdentity
        self.identity = A2AIdentity(salt, passphrase)
        self.self_name = self_name or NODE_ID
        self.ledger = []

    # ---------- 令牌自签发（本地派生密钥，内存） ----------
    def self_token(self, role: str = "writer", days: int = 1) -> str:
        import hmac as _hmac
        import base64 as _b64
        import secrets as _secrets
        key = self.identity.key
        payload = {
            "t": "HTK" + _secrets.token_hex(4).upper(),
            "n": self.self_name, "r": role, "s": "a2a-federation",
            "e": int(time.time()) + days * 86400,
            "o": "Ω-TAN-7-001", "d": DID,
        }
        pb = _b64.urlsafe_b64encode(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        ).decode().rstrip("=")
        sig = _hmac.new(key, pb.encode(), __import__("hashlib").sha256).hexdigest()[:16]
        return "ZRH1.%s.%s" % (pb, sig)

    # ---------- 发现 ----------
    def discover(self, card_url: str) -> dict:
        req = urllib.request.Request(card_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())

    # ---------- 出站调用 ----------
    def send(self, endpoint: str, text: str, token: str = None, role: str = "writer") -> dict:
        tok = token or self.self_token(role)
        payload = {
            "jsonrpc": "2.0", "id": int(time.time() * 1000),
            "method": "message/send",
            "params": {"message": {"role": "user",
                                   "parts": [{"kind": "text", "text": text}]}},
        }
        body = json.dumps(payload, ensure_ascii=False).encode()
        req = urllib.request.Request(
            endpoint, data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "X-ZR-Token": tok, "X-DID": DID},
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                out = json.loads(resp.read().decode())
            entry = {"peer": endpoint, "skill_req": text, "ok": "result" in out,
                     "elapsed_ms": int((time.time() - t0) * 1000),
                     "ts": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")}
            self.ledger.append(entry)
            return {"ok": "result" in out, "response": out, "ledger": entry}
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            entry = {"peer": endpoint, "skill_req": text, "ok": False,
                     "http_status": e.code, "detail": detail,
                     "elapsed_ms": int((time.time() - t0) * 1000),
                     "ts": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")}
            self.ledger.append(entry)
            return {"ok": False, "http_status": e.code, "detail": detail, "ledger": entry}
        except Exception as e:
            entry = {"peer": endpoint, "skill_req": text, "ok": False,
                     "error": str(e)[:200],
                     "elapsed_ms": int((time.time() - t0) * 1000),
                     "ts": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")}
            self.ledger.append(entry)
            return {"ok": False, "error": str(e)[:200], "ledger": entry}

    # ---------- 一步联邦 ----------
    def federate(self, card_url: str, text: str) -> dict:
        base = card_url.rsplit("/.well-known/", 1)[0].rstrip("/") + "/"
        try:
            card = self.discover(card_url)
        except Exception as e:
            return {"ok": False, "stage": "discover", "error": str(e)[:200]}
        res = self.send(base, text)
        res["stage"] = "send"
        res["peer_card"] = {"name": card.get("name"),
                            "skills": [s.get("id") for s in card.get("skills", [])]}
        return res

    # ---------- 网关仲裁上报（可选） ----------
    def report_to_gateway(self, entry: dict) -> dict:
        payload = {"key": "A2A.FEDERATION.%s" % NODE_ID,
                   "value": entry, "anchor": ANCHOR,
                   "truth_type": "protocol", "confidence": 0.9, "source_node": NODE_ID}
        body = json.dumps(payload, ensure_ascii=False).encode()
        h = {"Content-Type": "application/json", "X-DID": DID}
        cap = os.environ.get("ZR_CAPTURE_TOKEN", "")
        if cap:
            h["X-Capture-Token"] = cap
        req = urllib.request.Request(GATEWAY + "/api/report/truth", data=body,
                                     method="POST", headers=h)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)[:200]}


# ---------- CLI ----------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="A2A 联邦出站客户端")
    ap.add_argument("action", choices=["discover", "send", "federate", "token"])
    ap.add_argument("--card-url", default="")
    ap.add_argument("--endpoint", default="")
    ap.add_argument("--text", default="status")
    ap.add_argument("--salt", default=os.environ.get("ZR_HOMOLOGOUS_SALT", ""))
    ap.add_argument("--passphrase", default=os.environ.get("ZR_HOMOLOGOUS_PASSPHRASE", ""))
    ap.add_argument("--name", default=NODE_ID)
    a = ap.parse_args()
    if not a.salt:
        print(json.dumps({"error": "缺少 --salt"}, ensure_ascii=False)); sys.exit(1)
    c = FederationClient(a.salt, a.passphrase, a.name)
    if a.action == "token":
        print(json.dumps({"token_prefix": c.self_token()[:24] + "...",
                          "note": "同源令牌已签发（内存派生密钥，零落盘）"}, ensure_ascii=False))
    elif a.action == "discover":
        print(json.dumps(c.discover(a.card_url), ensure_ascii=False, indent=2))
    elif a.action == "send":
        print(json.dumps(c.send(a.endpoint, a.text), ensure_ascii=False, indent=2))
    elif a.action == "federate":
        print(json.dumps(c.federate(a.card_url, a.text), ensure_ascii=False, indent=2))
