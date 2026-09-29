#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地端到端仿真·Nexus v2 多令牌网关全链路验证
本地起：模拟记忆网关9120 + Nexus v2网关9443(TLS)
验证：用本地节点令牌(LOCAL-DEV-001) 带 X-ZY-Node-Id 打通真实 TLS 服务。
"""
import hashlib, hmac, http.client, json, ssl, time

HOST = "127.0.0.1"; PORT = 9443
CERT = "/home/user/Doubao/chats/38438306874426882/.sim_nexus/engine/nexus/nexus_cert.pem"
NODE = "LOCAL-DEV-001"
NODE_TOKEN = "sim_node_token_LOCALDEV001"
LEGACY = "legacy_sim_token_0001"

ctx = ssl.create_default_context(cafile=CERT)

def sign(token, ts, method, path, body):
    body_sha = hashlib.sha256(body).hexdigest()
    return hmac.new(token.encode(), f"{ts}\n{method}\n{path}\n{body_sha}".encode(), hashlib.sha256).hexdigest()

def req(method, path, body=None, token=None, node=None):
    body = body if body is not None else ""
    body_bytes = body.encode() if body else b""
    ts = str(int(time.time()))
    sig = sign(token, ts, method, path, body_bytes)
    conn = http.client.HTTPSConnection(HOST, PORT, timeout=10, context=ctx)
    h = {"Content-Type":"application/json","X-ZY-Token":token,"X-ZY-TS":ts,"X-ZY-SIG":sig}
    if node: h["X-ZY-Node-Id"]=node
    conn.request(method, path, body=body_bytes if body_bytes else None, headers=h)
    r = conn.getresponse(); data = r.read().decode()
    conn.close()
    try: return r.status, json.loads(data)
    except: return r.status, {"raw":data}

passed=0
def check(n, c): 
    global passed; print(("✅" if c else "❌")+n); 
    if c: passed+=1

print("═══ 端到端仿真 1: 多令牌主路径 (LOCAL-DEV-001 节点令牌) ═══")
st,d = req("GET","/v1/ping",token=NODE_TOKEN,node=NODE)
check("ping → 200 & v2.0-multitoken", st==200 and d.get("data",{}).get("version")=="2.0-multitoken")

st,d = req("GET","/v1/health",token=NODE_TOKEN,node=NODE)
check("health → 上游9120打通", st==200 and d.get("data",{}).get("status")=="ok")

st,d = req("GET","/v1/nodes",token=NODE_TOKEN,node=NODE)
check("nodes → 列表返回", st==200 and "cloud-main-kernel-001" in json.dumps(d))

print("═══ 端到端仿真 2: 真值写入 (LOCAL-DEV-001 upsert) ═══")
body=json.dumps({"truth_key":"KD-SIM-TRUTH-001","content":"Nexus v2多令牌端到端仿真验证真值","category":"kernel_truth","node_id":NODE})
st,d = req("POST","/v1/truth/upsert",body=body,token=NODE_TOKEN,node=NODE)
check("truth/upsert → 写入成功", st==200 and d.get("ok") is True)

print("═══ 端到端仿真 3: 多令牌安全校验 ═══")
st,d = req("GET","/v1/ping",token="WRONG_TOKEN",node=NODE)
check("错误token → 401拒绝", st==401)

st,d = req("GET","/v1/ping",token=NODE_TOKEN,node="UNKNOWN-NODE")
check("未知节点 → 401拒绝", st==401)

print("═══ 端到端仿真 4: legacy 兼容 (无node头, legacy令牌) ═══")
st,d = req("GET","/v1/ping",token=LEGACY,node=None)
check("legacy无node头 → 200通过", st==200)

print("═══ 端到端仿真 5: 节点令牌管理端点 (root) ═══")
# 需 root 节点令牌才能访问 /v1/tokens，当前白名单无root，预期403/401
st,d = req("GET","/v1/tokens",token=NODE_TOKEN,node=NODE)
check("非root访问 /v1/tokens → 被拒(非root)", st!=200)

print(f"\n═══ 端到端仿真通过 {passed}/9 ═══")
