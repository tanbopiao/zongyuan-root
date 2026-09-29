#!/usr/bin/env python3
"""
记忆闭环自动化·阶段1 本地侧 Nexus 客户端 SDK（免SSH双向通道）
ZONGYUAN-ROOT / 火斗云智AIOS | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

通道：本地 → Nexus HTTPS :9443 →(转发) 记忆网关 9120
鉴权：TLS(自签证书) + X-ZY-Token + X-ZY-TS + X-ZY-SIG (HMAC-SHA256)
遵守 AAB 双隔离公理：仅经 Nexus 真值通道，其余隔离；本地仿真产物未人工审核不自动上云。

【令牌安全约定】nexus_token 为机密，通过环境变量 ZY_NEXUS_TOKEN 注入，
脚本不落盘、不打印、不写入日志。证书为公钥，可随脚本分发。
"""
import os, sys, json, time, hmac, hashlib, ssl, http.client, urllib.parse

# 云端 Nexus 网关
NEXUS_HOST = os.environ.get("ZY_NEXUS_HOST", "123.207.202.158")
NEXUS_PORT = int(os.environ.get("ZY_NEXUS_PORT", "9443"))
# 证书文件（公钥，非机密）
CERT_FILE = os.environ.get("ZY_NEXUS_CERT", "/home/user/Doubao/chats/38438306874426882/nexus_cert.pem")
TS_WINDOW = 300  # 与云端一致

def _load_token():
    """从环境变量读取令牌，绝不落盘/打印"""
    tok = os.environ.get("ZY_NEXUS_TOKEN", "").strip()
    if not tok:
        # 兼容受控文件（权限600），仅本地读取
        tokfile = os.environ.get("ZY_NEXUS_TOKEN_FILE", "")
        if tokfile and os.path.isfile(tokfile):
            tok = open(tokfile, "r", encoding="utf-8").read().strip()
    if not tok:
        raise RuntimeError("缺少令牌：请设置环境变量 ZY_NEXUS_TOKEN（或受控文件 ZY_NEXUS_TOKEN_FILE）")
    return tok

def _ctx():
    return ssl.create_default_context(cafile=CERT_FILE)

def _sign(token, ts, method, path, body):
    body_sha = hashlib.sha256(body).hexdigest()
    msg = f"{ts}\n{method}\n{path}\n{body_sha}".encode("utf-8")
    return hmac.new(token.encode(), msg, hashlib.sha256).hexdigest()

def request(method, path, body=None, params=None, timeout=15):
    token = _load_token()
    # 节点级令牌：若设置 ZY_NEXUS_NODE，自动带 X-ZY-Node-Id 头（v2 多令牌鉴权）
    node = os.environ.get("ZY_NEXUS_NODE", "").strip()
    # 签名路径必须与网关一致（不含 query），query 仅附加到 URL
    sign_path = path
    if params:
        path = path + "?" + urllib.parse.urlencode(params)
    body_bytes = body.encode("utf-8") if body is not None else b""
    ts = str(int(time.time()))
    sig = _sign(token, ts, method, sign_path, body_bytes)
    conn = http.client.HTTPSConnection(NEXUS_HOST, NEXUS_PORT, timeout=timeout, context=_ctx())
    headers = {
        "Content-Type": "application/json",
        "X-ZY-Token": token,
        "X-ZY-TS": ts,
        "X-ZY-SIG": sig,
    }
    if node:
        headers["X-ZY-Node-Id"] = node
    if body_bytes:
        headers["Content-Length"] = str(len(body_bytes))
    conn.request(method, path, body=body_bytes, headers=headers)
    resp = conn.getresponse()
    data = resp.read().decode("utf-8", "replace")
    conn.close()
    try:
        return resp.status, json.loads(data)
    except Exception:
        return resp.status, {"raw": data}

def ping():
    return request("GET", "/v1/ping")

def health():
    return request("GET", "/v1/health")

def nodes():
    return request("GET", "/v1/nodes")

def register(node_id, node_type="local_dev", capabilities=None):
    cap = capabilities or ["truth_rw"]
    body = json.dumps({"node_id": node_id, "node_type": node_type, "capabilities": cap})
    return request("POST", "/v1/node/register", body=body)

def heartbeat(node_id):
    body = json.dumps({"node_id": node_id})
    return request("POST", "/v1/node/heartbeat", body=body)

def truths(params=None):
    return request("GET", "/v1/truths", params=params)

def truth_upsert(truth_key, content, category="kernel_truth", node_id="LOCAL"):
    body = json.dumps({
        "truth_key": truth_key, "content": content,
        "category": category, "node_id": node_id
    })
    return request("POST", "/v1/truth/upsert", body=body)

def truth_sync(truths_list):
    body = json.dumps({"truths": truths_list})
    return request("POST", "/v1/truth/sync", body=body)

def audit(params=None):
    return request("GET", "/v1/audit", params=params)

def lock(asset_id, asset_hash):
    body = json.dumps({"asset_id": asset_id, "asset_hash": asset_hash})
    return request("POST", "/v1/lock", body=body)


if __name__ == "__main__":
    # 自检模式：只读 ping + health + nodes，验证通道与令牌
    st, d = ping()
    print(f"[ping]  status={st} data={d}")
    if st != 200:
        print("通道异常：请检查令牌/证书/网络。退出。")
        sys.exit(1)
    st, h = health()
    print(f"[health] status={st} data={h}")
    st, n = nodes()
    print(f"[nodes] status={st} count={n.get('data',{}).get('count') if isinstance(n,dict) else n}")
