# 火斗云智AIOS 公开API文档 v1.0

确权：DID-BR-000002 ｜ ZONGYUAN-ROOT ｜ Ω₀⊂⊙∞⊂Ω

---

## 一、基础信息

| 项目 | 值 |
|------|-----|
| Base URL | `https://www.huodouai.com` |
| 协议版本 | 1.1 |
| 认证方式 | HMAC-SHA256签名 |
| 请求格式 | JSON |
| 响应格式 | JSON |

---

## 二、认证方式

所有请求必须携带以下Header：

| Header | 说明 |
|--------|------|
| `X-Node-DID` | 你的节点DID（如 DID-XXX-001） |
| `X-Signature` | HMAC-SHA256签名 |
| `X-Request-ID` | 请求唯一ID（UUID） |

### 签名计算方式

```python
import hmac
import hashlib
import json

payload = json.dumps(request_body, sort_keys=True)
signature = hmac.new(
    shared_key.encode("utf-8"),
    payload.encode("utf-8"),
    hashlib.sha256
).hexdigest()
```

---

## 三、接口列表

### 3.1 握手接口

**POST** `/anchor/api/v1/handshake`

请求体：
```json
{
  "msg_type": "HANDSHAKE",
  "request_id": "req-20260909-001",
  "timestamp": 1788888888,
  "from_did": "DID-YOUR-NODE-001",
  "to_did": "DID-CLOUD-CENTER-001",
  "protocol_version": "1.1"
}
```

响应：
```json
{
  "success": true,
  "peer_id": "DID-CLOUD-CENTER-001",
  "protocol_version": "1.1",
  "server_time": 1788888889
}
```

---

### 3.2 下发任务

**POST** `/anchor/api/v1/request`

请求体：
```json
{
  "msg_type": "REQUEST",
  "request_id": "req-20260909-002",
  "timestamp": 1788888890,
  "from_did": "DID-YOUR-NODE-001",
  "to_did": "DID-CLOUD-CENTER-001",
  "action": "DEPLOY_WEB_PAGE",
  "priority": "P1",
  "timeout_sec": 300,
  "params": {
    "file": "showcase-page/index.html",
    "target": "/www/wwwroot/example.com/index.html"
  }
}
```

响应：
```json
{
  "success": true,
  "task_id": "task-20260909-001",
  "status": "PENDING"
}
```

---

### 3.3 查询任务状态

**GET** `/anchor/api/v1/task/{task_id}`

响应：
```json
{
  "status": "SUCCESS",
  "progress": 100,
  "result": {
    "url": "https://example.com/index.html"
  },
  "error": ""
}
```

---

### 3.4 心跳保活

**POST** `/anchor/api/v1/heartbeat`

请求体：
```json
{
  "msg_type": "HEARTBEAT",
  "request_id": "req-20260909-003",
  "timestamp": 1788888891,
  "from_did": "DID-YOUR-NODE-001",
  "to_did": "DID-CLOUD-CENTER-001"
}
```

响应：
```json
{
  "success": true,
  "action": "PONG"
}
```

---

## 四、错误码

| 错误码 | HTTP状态 | 含义 | 处理方式 |
|--------|---------|------|---------|
| `E_AUTH_401` | 401 | 鉴权失败 | 检查DID和密钥 |
| `E_AUTH_403` | 403 | 无权限 | 申请对应权限 |
| `E_TIMEOUT_408` | 408 | 请求超时 | 重试或检查网络 |
| `E_RATE_429` | 429 | 请求限流 | 降低频率 |
| `E_SERVER_500` | 500 | 服务器错误 | 联系运维 |
| `E_TASK_FAILED_501` | 501 | 任务执行失败 | 查看错误详情 |
| `E_BAD_MSG_400` | 400 | 报文格式错误 | 检查报文结构 |
| `E_SIGNATURE_INVALID` | 401 | 签名错误 | 检查签名计算 |
| `E_PROTOCOL_VERSION` | 400 | 版本不兼容 | 升级SDK |

---

## 五、Python调用示例

```python
import requests
import hmac
import hashlib
import json
import time
import uuid

BASE_URL = "https://www.huodouai.com"
NODE_DID = "DID-YOUR-NODE-001"
SHARED_KEY = "your-shared-key"

def call_api(path, data):
    payload = json.dumps(data, sort_keys=True)
    signature = hmac.new(
        SHARED_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Node-DID": NODE_DID,
        "X-Signature": signature,
        "X-Request-ID": str(uuid.uuid4())
    }

    resp = requests.post(f"{BASE_URL}{path}", json=data, headers=headers, timeout=30)
    return resp.json()

# 握手
handshake = call_api("/anchor/api/v1/handshake", {
    "msg_type": "HANDSHAKE",
    "request_id": f"req-{int(time.time())}",
    "timestamp": int(time.time()),
    "from_did": NODE_DID,
    "to_did": "DID-CLOUD-CENTER-001",
    "protocol_version": "1.1"
})
print(f"握手: {handshake}")
```

---

## 六、限流策略

| 优先级 | QPS | 说明 |
|--------|-----|------|
| P0 | 10 | 紧急任务，优先处理 |
| P1 | 5 | 高优先级 |
| P2 | 2 | 普通任务 |
| P3 | 1 | 低优先级，排队执行 |

---

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ API文档 v1.0
