#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nexus 多令牌鉴权逻辑本地仿真测试（不连云端，纯算法验证）"""
import hashlib, hmac, json, os, sys, time, tempfile, importlib.util, secrets

# 加载 v2 网关模块（不执行 main）
spec = importlib.util.spec_from_file_location(
    "nexus_v2",
    "/home/user/Doubao/chats/38438306874426882/nexus_gateway_v2_multitoken.py",
)
nv2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nv2)

# 模拟令牌白名单
LEGACY = "legacy_shared_secret_test"
NODES = {
    "LOCAL-DEV-001": secrets.token_urlsafe(48),
    "LOCAL-DEV-002": secrets.token_urlsafe(48),
}
nv2.LEGACY_TOKEN = LEGACY
nv2.NODE_TOKENS = NODES

def sign(token, ts, method, path, body):
    body_sha = hashlib.sha256(body).hexdigest()
    msg = f"{ts}\n{method}\n{path}\n{body_sha}".encode()
    return hmac.new(token.encode(), msg, hashlib.sha256).hexdigest()

def mkheaders(token, method, path, body, node=None, ts=None):
    ts = ts or str(int(time.time()))
    sig = sign(token, ts, method, path, body)
    h = {"X-ZY-Token": token, "X-ZY-TS": ts, "X-ZY-SIG": sig}
    if node:
        h["X-ZY-Node-Id"] = node
    return h

passed = 0
def check(name, cond):
    global passed
    print(("✅ " if cond else "❌ ") + name)
    if cond: passed += 1

# 1. 多令牌主路径：LOCAL-DEV-001 用自己的 token，带 node 头 → 通过
h = mkheaders(NODES["LOCAL-DEV-001"], "POST", "/v1/truth/upsert", b'{"x":1}', node="LOCAL-DEV-001")
check("多令牌: 正确节点+正确token → 通过", nv2.verify_auth(h, b'{"x":1}', "POST", "/v1/truth/upsert"))

# 2. 用错误节点 token → 拒绝
h = mkheaders(NODES["LOCAL-DEV-002"], "POST", "/v1/truth/upsert", b'{"x":1}', node="LOCAL-DEV-001")
check("多令牌: 节点不匹配(token错) → 拒绝", not nv2.verify_auth(h, b'{"x":1}', "POST", "/v1/truth/upsert"))

# 3. 未知节点 id → 拒绝
h = mkheaders(LEGACY, "GET", "/v1/ping", b"", node="UNKNOWN-NODE")
check("多令牌: 未知节点id → 拒绝", not nv2.verify_auth(h, b"", "GET", "/v1/ping"))

# 4. 无 node 头 → 回退 legacy 单令牌 → 通过
h = mkheaders(LEGACY, "GET", "/v1/ping", b"")
check("legacy兼容: 无node头+legacy token → 通过", nv2.verify_auth(h, b"", "GET", "/v1/ping"))

# 5. 无 node 头 + 错误 legacy token → 拒绝
h = mkheaders("wrong", "GET", "/v1/ping", b"")
check("legacy兼容: 无node头+错误token → 拒绝", not nv2.verify_auth(h, b"", "GET", "/v1/ping"))

# 6. 防重放：过期时间戳 → 拒绝
h = mkheaders(NODES["LOCAL-DEV-001"], "GET", "/v1/ping", b"", node="LOCAL-DEV-001", ts=str(int(time.time())-400))
check("防重放: 过期ts(>300s) → 拒绝", not nv2.verify_auth(h, b"", "GET", "/v1/ping"))

# 7. body篡改 → 签名不匹配 → 拒绝
h = mkheaders(NODES["LOCAL-DEV-001"], "POST", "/v1/truth/upsert", b'{"x":1}', node="LOCAL-DEV-001")
check("防篡改: body被改 → 拒绝", not nv2.verify_auth(h, b'{"x":2}', "POST", "/v1/truth/upsert"))

# 8. 缺少必要头 → 拒绝
check("缺头: 无X-ZY-Token → 拒绝", not nv2.verify_auth({"X-ZY-TS":"1","X-ZY-SIG":"x"}, b"", "GET", "/v1/ping"))

print(f"\n本地仿真测试通过 {passed}/8")
sys.exit(0 if passed == 8 else 1)
