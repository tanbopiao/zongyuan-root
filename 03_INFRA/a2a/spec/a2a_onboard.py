#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A 接入向导 v1.0 （SPEC-A2A-ONBOARD-V1.0 配套）
锚定: Ω₀⊂⊙∞⊂Ω | DID-BR-000002

任何体系内节点运行本脚本，即可完成 A2A 接入自检 + 对端登记。
零依赖（仅用标准库），拷贝即可用。

用法:
  python3 a2a_onboard.py check   --endpoint http://127.0.0.1:8099 --salt <salt> --passphrase <pp>
  python3 a2a_onboard.py card    --endpoint http://127.0.0.1:8099
  python3 a2a_onboard.py register --peer-id <ID> --peer-card <url>
  python3 a2a_onboard.py guide
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request

ONTOLOGY_ROOT = "Ω-TAN-7-001"
DID_ROOT = "DID-BR-000002"
DERIVE_LABEL = "ZR-HOMOLOGOUS-v1"
ITERATIONS = 600000
ANCHOR = "Ω₀⊂⊙∞⊂Ω"

READONLY = {"omega_status", "truth_recall", "memory_anchor", "skills"}


# ---------- 密钥派生（与体系同源，算法字节级对齐 homologous_keyderive.py） ----------
def derive_key(passphrase: str, salt: str, length: int = 32) -> bytes:
    # 同源 salt = 派生标签 || 本体根 || 资产根 || 公开salt  （注意：双竖线分隔，须与体系一致）
    seed = ("%s||%s||%s||%s" % (DERIVE_LABEL, ONTOLOGY_ROOT, DID_ROOT, salt)).encode()
    return hashlib.pbkdf2_hmac("sha512", passphrase.encode("utf-8"), seed, ITERATIONS, dklen=length)


def make_token(key: bytes, role: str, name: str, hours: int = 1) -> str:
    payload = {
        "t": "HTK" + secrets.token_hex(4).upper(), "n": name, "r": role,
        "s": "a2a-onboard", "e": int(time.time()) + hours * 3600,
        "o": ONTOLOGY_ROOT, "d": DID_ROOT,
    }
    pb = base64.urlsafe_b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    sig = hmac.new(key, pb.encode(), hashlib.sha256).hexdigest()[:16]
    return "ZRH1.%s.%s" % (pb, sig)


# ---------- HTTP ----------
def _req(url, method="GET", body=None, headers=None, timeout=10):
    h = headers or {}
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    if data:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)[:200]}


def rpc(endpoint, text, token=None):
    payload = {"jsonrpc": "2.0", "id": int(time.time() * 1000), "method": "message/send",
               "params": {"message": {"role": "user",
                                      "parts": [{"kind": "text", "text": text}]}}}
    h = {"X-ZR-Token": token} if token else {}
    return _req(endpoint.rstrip("/") + "/", "POST", payload, h)


# ---------- 命令 ----------
def cmd_card(endpoint):
    print("▌Agent Card 发现")
    code, card = _req(endpoint.rstrip("/") + "/.well-known/agent-card.json")
    print("  HTTP %s" % code)
    if code == 200:
        for k in ("name", "version", "url"):
            print("  %-14s %s" % (k + ":", card.get(k)))
        md = card.get("metadata", {})
        print("  %-14s %s" % ("node_id:", md.get("node_id")))
        print("  %-14s %s" % ("did:", md.get("did")))
        print("  %-14s %s" % ("anchor:", md.get("anchor")))
        sk = [s.get("id") for s in card.get("skills", [])]
        print("  %-14s %s" % ("skills:", ", ".join(sk)))
        need = {"omega_status", "truth_recall", "memory_anchor", "truth_report", "node_heartbeat"}
        miss = need - set(sk)
        print("  五技能齐备: %s" % ("✔ 是" if not miss else "✘ 缺 %s" % miss))
    return code == 200


def cmd_check(endpoint, salt, passphrase):
    print("═" * 68)
    print("A2A 接入自检（SPEC-A2A-ONBOARD-V1.0 §7 十项）")
    print("═" * 68)
    key = derive_key(passphrase, salt)
    reader = make_token(key, "reader", "onboard-reader")
    writer = make_token(key, "writer", "onboard-writer")
    bogus = "ZRH1.eyJ0IjoiSEsifQ.deadbeefdeadbeef"

    cases = [
        ("1  卡片发现(匿名)",        None,    "GETCARD", 200),
        ("2  健康探针(匿名)",        None,    "__HEALTH", 200),
        ("3  匿名只读 status",       None,    "status", 200),
        ("4  匿名写 report",         None,    "report ONBOARD.TEST=1", 401),
        ("5  reader 只读 status",    reader,  "status", 200),
        ("6  reader 越权写",         reader,  "report ONBOARD.TEST=1", 403),
        ("7  伪造签名令牌",          bogus,   "status", 403),
        ("8  writer 写 report",      writer,  "report ONBOARD.TEST=1", 200),
        ("9  异源前缀令牌",          "ZRX1.abc.def", "status", 403),
        ("10 残缺令牌",              "garbage", "status", 403),
    ]
    base = endpoint.rstrip("/")
    passed = failed = 0
    for name, tok, text, expect in cases:
        if text == "GETCARD":
            code, _ = _req(base + "/.well-known/agent-card.json")
        elif text == "__HEALTH":
            code, _ = _req(base + "/health")
        else:
            code, _ = rpc(base, text, tok)
        ok = code == expect
        passed += ok
        failed += (not ok)
        print("%s | %-22s | HTTP %-4s (期望 %s)" % ("✔ PASS" if ok else "✘ FAIL", name, code, expect))
    print("-" * 68)
    print("PASS=%d  FAIL=%d  TOTAL=%d  →  %s" % (
        passed, failed, len(cases), "接入合格 ✔" if failed == 0 else "未通过，请排查 ✘"))
    print("═" * 68)
    return failed == 0


def cmd_register(peer_id, peer_card, trust):
    import subprocess
    reg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", "a2a_registry.py")
    if not os.path.exists(reg):
        print("[!] 未找到注册表工具，请手工登记到 peer-registry.json")
        print(json.dumps({"node_id": peer_id, "card_url": peer_card, "trust": trust},
                         ensure_ascii=False, indent=2))
        return
    out = subprocess.run([sys.executable, reg, "add", "--node-id", peer_id,
                          "--card-url", peer_card, "--trust", trust],
                         capture_output=True, text=True)
    print(out.stdout or out.stderr)


def cmd_guide():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║  元极恒一 · A2A 接入三步走                                       ║
╚══════════════════════════════════════════════════════════════════╝

【第 1 步】自检你的服务端
  python3 a2a_onboard.py check --endpoint http://<你的IP>:8099 \\
      --salt <salt> --passphrase <口令>
  期望：PASS=10 FAIL=0

【第 2 步】确认 Agent Card
  python3 a2a_onboard.py card --endpoint http://<你的IP>:8099
  期望：五技能齐备 ✔（omega_status/truth_recall/memory_anchor/truth_report/node_heartbeat）

【第 3 步】与对端互登
  python3 a2a_onboard.py register --peer-id <对端ID> \\
      --peer-card http://<对端IP>:8099/.well-known/agent-card.json

【最小调用示例】
  # 发现
  curl http://<对端>:8099/.well-known/agent-card.json

  # 调用（需令牌）
  curl -X POST http://<对端>:8099/ \\
    -H "Content-Type: application/json" \\
    -H "X-ZR-Token: ZRH1.<payload>.<sig>" \\
    -d '{"jsonrpc":"2.0","id":1,"method":"message/send",
         "params":{"message":{"role":"user",
                  "parts":[{"kind":"text","text":"status"}]}}}'

【安全红线】
  · 口令零入库  · 令牌不落盘  · 仅体系内  · 不得自行直连  · 不得静默失败

【网关读法勘误】（务必遵守）
  读：GET  /api/truth?key=<key>     ← 正确
  误：GET  /api/truth/<key>         → 恒 404（体系内多处误报的根因）
  写：POST /api/report/truth        + 合法 JSON body（空 body → 404）

规范全文：SPEC-A2A-ONBOARD-V1.0.md
""")


def main():
    ap = argparse.ArgumentParser(description="A2A 接入向导 (SPEC-A2A-ONBOARD-V1.0)")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("check", "card"):
        p = sub.add_parser(name)
        p.add_argument("--endpoint", default="http://127.0.0.1:8099")
        if name == "check":
            p.add_argument("--salt", default=os.environ.get("ZR_HOMOLOGOUS_SALT", ""))
            p.add_argument("--passphrase", default=os.environ.get("ZR_HOMOLOGOUS_PASSPHRASE", ""))
    p = sub.add_parser("register")
    p.add_argument("--peer-id", required=True)
    p.add_argument("--peer-card", required=True)
    p.add_argument("--trust", default="unverified")
    sub.add_parser("guide")
    a = ap.parse_args()

    if a.cmd == "card":
        cmd_card(a.endpoint)
    elif a.cmd == "check":
        if not a.salt or not a.passphrase:
            print(json.dumps({"error": "缺少 --salt 或 --passphrase"}, ensure_ascii=False))
            sys.exit(1)
        ok = cmd_check(a.endpoint, a.salt, a.passphrase)
        sys.exit(0 if ok else 1)
    elif a.cmd == "register":
        cmd_register(a.peer_id, a.peer_card, a.trust)
    else:
        cmd_guide()


if __name__ == "__main__":
    main()
