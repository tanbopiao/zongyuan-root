# 火斗云智同源协议 Python SDK 开发文档 v1.0

确权：DID-BR-000002 ｜ ZONGYUAN-ROOT ｜ Ω₀⊂⊙∞⊂Ω

---

## 一、SDK概述

### 定位
火斗云智同源协议Python SDK，封装了多节点通信、资产校验、水印读取等核心能力，让开发者3行代码即可接入火斗云智中枢智能体网络。

### 设计原则
- **极简**：3行代码完成握手，10行代码完成任务下发
- **安全**：HMAC-SHA256签名，全程加密
- **幂等**：所有任务自动去重，不重复执行
- **可观测**：全链路日志，方便调试

---

## 二、安装

```bash
pip install huodouai-sdk
```

或从源码安装：
```bash
git clone https://gitee.com/huodou-cloud-intelligence-aios/ZONGYUAN-ROOT.git
cd ZONGYUAN-ROOT/sdk
pip install -e .
```

---

## 三、快速开始

### 3.1 3行代码完成握手

```python
from huodouai import HomoClient

# 1. 初始化客户端
client = HomoClient(
    node_did="DID-YOUR-NODE-001",
    shared_key="your-shared-key-here"
)

# 2. 发起握手
response = client.handshake()

# 3. 打印结果
print(f"握手成功！中枢节点ID: {response.peer_id}")
```

### 3.2 下发任务

```python
from huodouai import HomoClient

client = HomoClient(
    node_did="DID-YOUR-NODE-001",
    shared_key="your-shared-key-here"
)

# 下发部署任务
result = client.send_task(
    action="DEPLOY_WEB_PAGE",
    params={
        "file": "showcase-page/index.html",
        "target": "/www/wwwroot/example.com/index.html"
    }
)

print(f"任务已提交，任务ID: {result.task_id}")
print(f"状态: {result.status}")
```

---

## 四、核心API

### 4.1 HomoClient 初始化

```python
HomoClient(
    node_did: str,           # 你的节点DID
    shared_key: str,         # 共享密钥
    base_url: str = None,    # 中枢地址，默认 https://www.huodouai.com
    timeout: int = 30,       # 请求超时（秒）
    retry: int = 3           # 重试次数
)
```

### 4.2 握手

```python
client.handshake() -> HandshakeResponse
```

返回字段：
- `success`: bool — 握手是否成功
- `peer_id`: str — 中枢节点ID
- `protocol_version`: str — 协议版本
- `server_time`: int — 中枢服务器时间戳

### 4.3 下发任务

```python
client.send_task(
    action: str,            # 动作类型
    params: dict = None,    # 任务参数
    priority: str = "P2",   # 优先级 P0/P1/P2
    timeout_sec: int = 300  # 超时时间
) -> TaskResponse
```

返回字段：
- `task_id`: str — 任务唯一ID
- `status`: str — 任务状态 PENDING/RUNNING/SUCCESS/FAILED
- `request_id`: str — 请求ID

### 4.4 查询任务状态

```python
client.get_task_status(task_id: str) -> TaskStatus
```

返回字段：
- `status`: str — 任务状态
- `progress`: int — 进度（0-100）
- `result`: dict — 任务结果（完成后）
- `error`: str — 错误信息（失败后）

### 4.5 资产校验

```python
from huodouai import AssetVerifier

verifier = AssetVerifier()

# 校验文件SHA256
result = verifier.verify_file("path/to/asset.zip")
print(f"哈希: {result.sha256}")
print(f"完整性: {'✓ 通过' if result.valid else '✗ 失败'}")

# 读取溯源水印
watermark = verifier.read_watermark("path/to/asset.zip")
print(f"订单ID: {watermark.order_id}")
print(f"购买用户: {watermark.user_did}")
```

---

## 五、报文结构

### 5.1 请求报文

```json
{
  "msg_type": "REQUEST",
  "request_id": "req-20260909-001",
  "timestamp": 1788888888,
  "from_did": "DID-YOUR-NODE-001",
  "to_did": "DID-CLOUD-CENTER-001",
  "action": "DEPLOY_WEB_PAGE",
  "priority": "P1",
  "params": { ... },
  "signature": "hmac-sha256-signature"
}
```

### 5.2 响应报文

```json
{
  "msg_type": "RESPONSE",
  "request_id": "req-20260909-001",
  "timestamp": 1788888889,
  "from_did": "DID-CLOUD-CENTER-001",
  "to_did": "DID-YOUR-NODE-001",
  "status": "SUCCESS",
  "data": { ... },
  "signature": "hmac-sha256-signature"
}
```

---

## 六、错误码

| 错误码 | 含义 | 处理方式 |
|--------|------|---------|
| E_AUTH_401 | 鉴权失败 | 检查DID和密钥 |
| E_AUTH_403 | 无权限 | 申请对应权限 |
| E_TIMEOUT_408 | 请求超时 | 重试或检查网络 |
| E_RATE_429 | 请求限流 | 降低频率 |
| E_SERVER_500 | 服务器错误 | 联系运维 |
| E_TASK_FAILED_501 | 任务执行失败 | 查看错误详情 |

---

## 七、完整示例：自动部署脚本

```python
#!/usr/bin/env python3
"""
一键部署示例：从Git拉取代码并部署到Web目录
"""
from huodouai import HomoClient

client = HomoClient(
    node_did="DID-BR-000002",
    shared_key="your-shared-key"
)

# 1. 握手
hs = client.handshake()
print(f"✓ 握手成功: {hs.peer_id}")

# 2. 下发部署任务
task = client.send_task(
    action="DEPLOY_STATIC_PAGE",
    params={
        "repo": "ZONGYUAN-ROOT",
        "branch": "main",
        "file": "showcase-page/diff.html",
        "target": "/www/wwwroot/huodouai.com/diff.html"
    },
    priority="P0"
)
print(f"✓ 任务已提交: {task.task_id}")

# 3. 轮询等待完成
import time
while True:
    status = client.get_task_status(task.task_id)
    print(f"  进度: {status.progress}% - {status.status}")
    if status.status in ["SUCCESS", "FAILED"]:
        break
    time.sleep(5)

# 4. 输出结果
if status.status == "SUCCESS":
    print(f"✓ 部署完成！访问: {status.result['url']}")
else:
    print(f"✗ 部署失败: {status.error}")
```

---

## 八、最佳实践

1. **重试机制**：网络不稳定时，SDK自动重试3次，无需手动处理
2. **幂等设计**：每个请求带唯一request_id，中枢自动去重
3. **日志开启**：`client.set_log_level("DEBUG")` 可查看详细通信日志
4. **错误处理**：捕获 `HomoError` 异常，根据错误码做对应处理
5. **批量任务**：支持批量下发多个任务，自动限流

---

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ SDK文档 v1.0
