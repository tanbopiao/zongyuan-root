# 同源协议规范 v1.0
DID-BR-000002｜ZONGYUAN-ROOT｜Ω₀⊂⊙∞⊂Ω
快照：SNAP-20260909-HOMO-PROTOCOL-V1

---

## 一、协议概述

同源协议 = ZONGYUAN-ROOT体系内所有节点间通信的统一报文规范。
核心：所有节点基于同一套JSON Schema通信，保证跨节点消息可解析、可验证、可审计。

## 二、通用报文结构

所有报文必须包含以下头部字段：

```json
{
  "header": {
    "version": "homo-v1.0",
    "msg_id": "MSG-YYYYMMDD-XXXXX",
    "timestamp": "ISO8601",
    "from_did": "DID-BR-000002",
    "to_did": "DID-XXXX-XXXXXX",
    "msg_type": "HANDSHAKE|REQUEST|RESPONSE|REPORT|RECEIPT|LOCK",
    "anchor": "Ω₀⊂⊙∞⊂Ω",
    "signature": "SHA256签名"
  },
  "body": {}
}
```

## 三、六种报文类型

### 3.1 HANDSHAKE（握手）
节点首次接入时，向目标节点发送握手请求，确认身份和权限。

```json
{
  "header": {
    "msg_type": "HANDSHAKE"
  },
  "body": {
    "node_id": "ext-agent-1788663115-3e3fd867",
    "node_name": "ZONGYUAN-ROOT-MetaAxiom-Foundation-Node",
    "role_level": "L0",
    "capabilities": ["truth_define", "lock_archive", "conflict_arbiter"],
    "public_key": "ssh-ed25519 AAAA..."
  }
}
```

### 3.2 REQUEST（请求）
节点间调用功能时发送请求。

```json
{
  "header": {
    "msg_type": "REQUEST"
  },
  "body": {
    "action": "IDENTITY_QUERY|TRUTH_READ|TRUTH_WRITE|SCHEDULE_TASK|SNAPSHOT_CREATE",
    "params": {},
    "priority": "P0|P1|P2",
    "timeout_sec": 30
  }
}
```

### 3.3 RESPONSE（响应）
对REQUEST的回复。

```json
{
  "header": {
    "msg_type": "RESPONSE",
    "ref_msg_id": "原请求msg_id"
  },
  "body": {
    "status": "OK|ERROR|DEGRADED",
    "data": {},
    "error_code": "E_XXX_XXX",
    "error_msg": ""
  }
}
```

### 3.4 REPORT（上报）
节点主动上报状态、问题、告警。

```json
{
  "header": {
    "msg_type": "REPORT"
  },
  "body": {
    "report_type": "STATUS|ISSUE|ALERT|METRIC",
    "issues": [],
    "metrics": {},
    "severity": "INFO|WARN|ERROR|CRITICAL"
  }
}
```

### 3.5 RECEIPT（回执）
对REPORT的确认接收。

```json
{
  "header": {
    "msg_type": "RECEIPT",
    "ref_msg_id": "原上报msg_id"
  },
  "body": {
    "received": true,
    "action_taken": "ACK|QUEUED|IGNORED",
    "note": ""
  }
}
```

### 3.6 LOCK（锁档）
全域锁档完成后的广播。

```json
{
  "header": {
    "msg_type": "LOCK"
  },
  "body": {
    "snapshot_id": "SNAP-YYYYMMDD-NAME",
    "root_version": 85,
    "merkle_hash": "SHA256...",
    "assets_affected": [],
    "eFuse_status": "NOT_BLOWN|BLOWN_PERMANENT"
  }
}
```

## 四、签名规则

1. 所有报文必须签名
2. 签名内容：header + body的JSON（sort_keys=True）的SHA256哈希
3. 签名密钥：节点DID对应的私钥
4. 验证方式：接收方用发送方公钥验证签名

## 五、错误码规范

| 错误码 | 含义 |
|--------|------|
| E_AUTH_401 | 认证失败 |
| E_AUTH_403 | 权限不足 |
| E_SCHEMA_400 | 报文格式错误 |
| E_NOTFOUND_404 | 资源不存在 |
| E_STATE_409 | 状态冲突 |
| E_COMPUTE_520 | 算力不可用 |
| E_S8_AXIOM | 真值校验失败 |
| E_INTERNAL_500 | 内部错误 |

## 六、版本兼容性

- 版本格式：homo-vX.Y
- 主版本X变更：不兼容，必须升级
- 次版本Y变更：向下兼容，新增字段可选

---

快照：SNAP-20260909-HOMO-PROTOCOL-V1
LOCKED
