# ZONGYUAN-ROOT 云内核 API 接口协议

**协议版本：** V1.0
**发布日期：** 2026-09-06
**文档密级：** 内部使用
**内核ID：** ZONGYUAN-ROOT-AUTONOMOUS-KERNEL
**DID：** DID-BR-000002
**溯源标识：** Ω₀⊂⊙∞⊂Ω

---

## 目录

1. [协议概述](#1-协议概述)
2. [基础信息](#2-基础信息)
3. [认证方式](#3-认证方式)
4. [API端点清单](#4-api端点清单)
5. [内核身份标识API](#5-内核身份标识api)
6. [节点管理API](#6-节点管理api)
7. [同步API](#7-同步api)
8. [控制API](#8-控制api)
9. [协议注册中心API](#9-协议注册中心api)
10. [AI代理网关API](#10-ai代理网关api)
11. [数据模型定义](#11-数据模型定义)
12. [错误码定义](#12-错误码定义)
13. [调用示例](#13-调用示例)
14. [版本管理](#14-版本管理)

---

## 1. 协议概述

本协议定义了ZONGYUAN-ROOT云内核所有对外暴露的API接口规范，包括：

- **内核身份标识**：获取云内核唯一标识信息（IP/域名/端口/认证/服务状态）
- **节点管理**：节点注册、心跳、列表查询、详情查询
- **同步API**：双内核真值/协议/资产双向同步
- **控制API**：云内核向节点下发控制指令、节点上报执行结果
- **协议注册中心**：协议的注册、查询、更新、删除
- **AI代理网关**：多模型统一调用接口（OpenAI兼容）

所有API遵循RESTful设计规范，使用JSON作为数据交换格式。

---

## 2. 基础信息

| 项目 | 值 |
|------|-----|
| **基础域名** | `https://www.huodouai.com` |
| **公网IP** | `123.207.202.158` |
| **API版本** | `v1` |
| **数据格式** | `application/json; charset=utf-8` |
| **字符编码** | UTF-8 |
| **时间格式** | ISO 8601（`2026-09-06T09:00:00+08:00`） |
| **时区** | Asia/Shanghai (UTC+8) |

### 2.1 服务端口映射

| 服务 | 本地端口 | 外网路径 | 说明 |
|------|----------|----------|------|
| Nginx | 80/443 | - | 统一入口/SSL |
| Anchor API | 8006 | `/anchor/` | 同步/控制/真值管理 |
| 内核身份API | 8030 | `/api/v1/kernel/` | 身份标识/节点管理 |
| 协议注册中心 | 8024 | `/api/v1/protocols` | 协议注册管理 |
| AI代理网关 | 8021 | - | 多模型统一代理 |
| FRPS | 7100 | - | 内网穿透服务端 |

---

## 3. 认证方式

云内核API采用多种认证方式，不同端点使用不同认证：

### 3.1 X-API-Key 认证

**适用端点：** `/anchor/api/v1/sync/*`

**请求头：**
```
X-API-Key: 36f55bdd86407a1fc12f27240ed9736ac0c5cfb33e7b89ee9c9f7d8594e0c242
```

### 3.2 HTTP Basic Auth 认证

**适用端点：** `/anchor/*`（除sync外）、`/monitor/*`、`/gov-api/*`、`/system/state`

**请求头：**
```
Authorization: Basic em9uZ3l1YW46MTIzNDU2
```
（用户名：`zongyuan`，密码：`123456`）

### 3.3 无认证端点

以下端点无需认证即可访问：

- `GET /api/v1/kernel/identity` - 获取内核身份标识
- `GET /api/v1/kernel/nodes/list` - 节点列表查询
- `GET /api/v1/kernel/nodes/{node_id}` - 节点详情查询

### 3.4 FRP 认证

**适用场景：** 本地节点通过FRP内网穿透接入

**配置：**
```toml
serverAddr = "123.207.202.158"
serverPort = 7100
auth.token = "ZONGYUAN-FRP-20260903-SECRET-KEY-7f3a9b2c"
```

---

## 4. API端点清单

| 分组 | 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|------|
| **内核身份** | `/api/v1/kernel/identity` | GET | 无 | 获取内核身份标识 |
| **节点管理** | `/api/v1/kernel/nodes/register` | POST | 无 | 节点注册 |
| **节点管理** | `/api/v1/kernel/nodes/list` | GET | 无 | 节点列表 |
| **节点管理** | `/api/v1/kernel/nodes/heartbeat` | POST | 无 | 节点心跳 |
| **节点管理** | `/api/v1/kernel/nodes/{node_id}` | GET | 无 | 节点详情 |
| **同步** | `/anchor/api/v1/sync/handshake` | GET | X-API-Key | 握手 |
| **同步** | `/anchor/api/v1/sync/manifest` | GET | X-API-Key | 资产清单 |
| **同步** | `/anchor/api/v1/sync/pull` | POST | X-API-Key | 文件拉取 |
| **同步** | `/anchor/api/v1/sync/verify` | POST | X-API-Key | 一致性验证 |
| **同步** | `/anchor/api/v1/sync/truth-pull` | POST | X-API-Key | 真值拉取 |
| **同步** | `/anchor/api/v1/sync/truth-push` | POST | X-API-Key | 真值推送 |
| **控制** | `/anchor/api/v1/control/issue` | POST | Basic Auth | 下发指令 |
| **控制** | `/anchor/api/v1/control/commands` | GET | Basic Auth | 拉取指令 |
| **控制** | `/anchor/api/v1/control/result` | POST | Basic Auth | 上报结果 |
| **控制** | `/anchor/api/v1/control/heartbeat` | POST | Basic Auth | 心跳上报 |
| **控制** | `/anchor/api/v1/control/status` | GET | Basic Auth | 控制状态 |
| **协议中心** | `/api/v1/protocols` | GET | Basic Auth | 协议列表 |
| **协议中心** | `/api/v1/protocols/register` | POST | Basic Auth | 协议注册 |
| **协议中心** | `/api/v1/protocols/{id}` | GET | Basic Auth | 协议详情 |
| **协议中心** | `/api/v1/protocols/{id}` | PUT | Basic Auth | 协议更新 |
| **协议中心** | `/api/v1/protocols/{id}` | DELETE | Basic Auth | 协议删除 |
| **AI网关** | `/v1/chat/completions` | POST | API Key | 聊天补全 |
| **AI网关** | `/health` | GET | 无 | 健康检查 |

---

## 5. 内核身份标识API

### 5.1 获取内核身份标识

**端点：** `GET /api/v1/kernel/identity`

**认证：** 无

**描述：** 获取云内核的完整身份标识信息，包括内核ID、DID、网络信息、核心服务、API端点、认证方式、Web门户、内核状态等。

**响应示例：**
```json
{
  "protocol": "ZONGYUAN-ROOT-KERNEL-IDENTITY-PROTOCOL-V1.0",
  "kernel_id": "ZONGYUAN-ROOT-AUTONOMOUS-KERNEL",
  "kernel_name": "元极恒一超认知永恒自治内核",
  "did": "DID-BR-000002",
  "trace": "Ω₀⊂⊙∞⊂Ω",
  "version": "V1.7",
  "status": "ACTIVE",
  "network": {
    "public_ip": "123.207.202.158",
    "domain": "www.huodouai.com",
    "hostname": "VM-0-16-opencloudos",
    "os": "OpenCloudOS 9.6",
    "cloud_provider": "腾讯云",
    "region": "广州"
  },
  "core_services": {
    "anchor_api": {
      "name": "云内核Anchor服务",
      "local_port": 8006,
      "public_url": "https://www.huodouai.com/anchor",
      "description": "同步/控制/真值管理核心API",
      "status": "active"
    }
  },
  "api_endpoints": {
    "sync_api": {
      "base": "/anchor/api/v1/sync",
      "endpoints": {}
    }
  },
  "authentication": {
    "x_api_key": {
      "header": "X-API-Key",
      "key": "36f55bdd...",
      "applies_to": ["/anchor/api/v1/sync/"]
    }
  },
  "web_portals": {
    "hub_console": "https://www.huodouai.com/hub-console/",
    "gov_ai_v3": "https://www.huodouai.com/gov/",
    "workbench": "https://www.huodouai.com/workbench/"
  },
  "kernel_status": {
    "truth_version": "μ-1.0",
    "truth_count": 104,
    "protocol_count": 81,
    "services_active": 5,
    "services_total": 7,
    "memory_chain_seeds": 19
  },
  "hash": "d52b0563f9462dd4...",
  "accessed_at": "2026-09-06T09:00:00+08:00"
}
```

---

## 6. 节点管理API

### 6.1 节点注册

**端点：** `POST /api/v1/kernel/nodes/register`

**认证：** 无

**请求体：**
```json
{
  "node_id": "local-win-001",
  "node_type": "local_kernel",
  "node_name": "本地Windows内核-工作站",
  "public_key": "ssh-rsa AAAAB3NzaC1yc2E...",
  "capabilities": ["sync_agent", "frpc_tunnel", "aios_dashboard"]
}
```

**请求字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| node_id | string | 是 | 节点唯一ID |
| node_type | string | 是 | 节点类型：local_kernel/dev_workstation/edge_device/external_agent/backup_node |
| node_name | string | 是 | 节点名称 |
| public_key | string | 是 | 节点公钥（用于身份认证） |
| capabilities | array | 是 | 节点能力列表 |

**响应示例：**
```json
{
  "success": true,
  "message": "Node registered successfully",
  "node_id": "local-win-001",
  "registered_at": "2026-09-06T09:00:00+08:00",
  "heartbeat_interval": 300,
  "heartbeat_timeout": 900
}
```

### 6.2 节点列表

**端点：** `GET /api/v1/kernel/nodes/list`

**认证：** 无

**响应示例：**
```json
{
  "nodes": [
    {
      "node_id": "local-win-001",
      "node_type": "local_kernel",
      "node_name": "本地Windows内核-工作站",
      "public_key": "ssh-rsa AAAAB3NzaC1yc2E...",
      "capabilities": ["sync_agent", "frpc_tunnel"],
      "registered_at": "2026-09-06T09:00:00+08:00",
      "updated_at": "2026-09-06T09:05:00+08:00",
      "last_heartbeat": "2026-09-06T09:05:00+08:00",
      "online": true,
      "status": "active"
    }
  ],
  "total_count": 1,
  "updated_at": "2026-09-06T09:05:00+08:00"
}
```

### 6.3 节点心跳

**端点：** `POST /api/v1/kernel/nodes/heartbeat`

**认证：** 无

**请求体：**
```json
{
  "node_id": "local-win-001",
  "status_info": {
    "timestamp": "2026-09-06T09:05:00+08:00",
    "sync_agent": "running",
    "frpc_tunnel": "connected",
    "local_services": {
      "aios": "active",
      "dashboard": "active",
      "ollama": "active"
    }
  }
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "Heartbeat received",
  "node_id": "local-win-001",
  "server_time": "2026-09-06T09:05:00+08:00",
  "next_heartbeat_due": "2026-09-06T09:10:00+08:00"
}
```

### 6.4 节点详情

**端点：** `GET /api/v1/kernel/nodes/{node_id}`

**认证：** 无

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| node_id | string | 节点ID |

**响应示例：** 同节点列表中的单个节点对象

**错误响应（404）：**
```json
{
  "error": "Node not found",
  "node_id": "unknown-node"
}
```

---

## 7. 同步API

> **认证方式：** X-API-Key 请求头
> **基础路径：** `https://www.huodouai.com/anchor/api/v1/sync`

### 7.1 握手

**端点：** `GET /handshake`

**描述：** 建立同步连接，获取云内核状态信息。

**响应示例：**
```json
{
  "kernel_id": "ZONGYUAN-ROOT-AUTONOMOUS-KERNEL",
  "truth_version": "μ-1.0",
  "truth_count": 104,
  "protocol_count": 81,
  "services_active": 5,
  "services_total": 7,
  "memory_chain_seeds": 19,
  "server_time": "2026-09-06T09:00:00+08:00"
}
```

### 7.2 资产清单

**端点：** `GET /manifest`

**描述：** 获取所有协议和真值文件的SHA256哈希及Merkle根。

**响应示例：**
```json
{
  "manifest_version": "1.0",
  "generated_at": "2026-09-06T09:00:00+08:00",
  "merkle_root": "abc123...",
  "files": [
    {
      "path": "/protocols/protocol-001.json",
      "sha256": "def456...",
      "size": 1024
    }
  ],
  "total_files": 81
}
```

### 7.3 文件拉取

**端点：** `POST /pull`

**请求体：**
```json
{
  "file_path": "/protocols/protocol-001.json"
}
```

**响应示例：**
```json
{
  "success": true,
  "file_path": "/protocols/protocol-001.json",
  "content_base64": "eyJrZXkiOiAidmFsdWUifQ==",
  "sha256": "def456...",
  "size": 1024
}
```

### 7.4 一致性验证

**端点：** `POST /verify`

**请求体：**
```json
{
  "local_files": [
    {
      "path": "/protocols/protocol-001.json",
      "sha256": "def456..."
    }
  ]
}
```

**响应示例：**
```json
{
  "success": true,
  "match_count": 80,
  "mismatch_count": 1,
  "missing_count": 0,
  "mismatches": [
    {
      "path": "/protocols/protocol-002.json",
      "local_sha256": "aaa...",
      "remote_sha256": "bbb..."
    }
  ]
}
```

### 7.5 真值增量拉取

**端点：** `POST /truth-pull`

**请求体：**
```json
{
  "since_version": "μ-0.9",
  "truth_ids": ["TRUTH-001", "TRUTH-002"]
}
```

**响应示例：**
```json
{
  "success": true,
  "truth_version": "μ-1.0",
  "truth_count": 104,
  "truths": [
    {
      "truth_id": "TRUTH-001",
      "title": "三态秩序化智能最小完备闭包",
      "content": "...",
      "level": "L0_META",
      "confidence": 1.0,
      "timestamp": "2026-09-06T09:00:00+08:00"
    }
  ]
}
```

### 7.6 真值增量推送

**端点：** `POST /truth-push`

**请求体：**
```json
{
  "truths": [
    {
      "truth_id": "TRUTH-NEW-001",
      "title": "新真值标题",
      "content": "新真值内容",
      "level": "L2_STANDARD",
      "confidence": 0.9,
      "source": "local_kernel",
      "timestamp": "2026-09-06T09:00:00+08:00"
    }
  ]
}
```

**响应示例：**
```json
{
  "success": true,
  "received_count": 1,
  "new_count": 1,
  "duplicate_count": 0,
  "truth_count_after": 105
}
```

---

## 8. 控制API

> **认证方式：** HTTP Basic Auth（zongyuan/123456）
> **基础路径：** `https://www.huodouai.com/anchor/api/v1/control`

### 8.1 下发控制指令

**端点：** `POST /issue`

**请求体：**
```json
{
  "target_node": "local-win-001",
  "command_type": "config_update",
  "command": {
    "key": "value"
  },
  "priority": "high",
  "expires_at": "2026-09-06T10:00:00+08:00"
}
```

**指令类型：**

| 类型 | 说明 |
|------|------|
| config_update | 配置更新 |
| truth_push | 真值下发 |
| protocol_sync | 协议同步 |
| task_trigger | 任务触发 |
| remote_diagnose | 远程诊断 |
| self_update | 自更新 |
| backup | 备份触发 |
| restart | 重启服务 |

**响应示例：**
```json
{
  "success": true,
  "command_id": "CMD-20260906090000-abc123",
  "target_node": "local-win-001",
  "status": "pending",
  "issued_at": "2026-09-06T09:00:00+08:00"
}
```

### 8.2 拉取待执行指令

**端点：** `GET /commands?node_id={node_id}`

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| node_id | string | 是 | 节点ID |

**响应示例：**
```json
{
  "success": true,
  "node_id": "local-win-001",
  "pending_commands": [
    {
      "command_id": "CMD-20260906090000-abc123",
      "command_type": "config_update",
      "command": {"key": "value"},
      "priority": "high",
      "issued_at": "2026-09-06T09:00:00+08:00",
      "expires_at": "2026-09-06T10:00:00+08:00"
    }
  ],
  "count": 1
}
```

### 8.3 上报执行结果

**端点：** `POST /result`

**请求体：**
```json
{
  "command_id": "CMD-20260906090000-abc123",
  "node_id": "local-win-001",
  "status": "success",
  "result": {
    "message": "配置更新成功",
    "details": {}
  },
  "executed_at": "2026-09-06T09:01:00+08:00",
  "duration_ms": 5000
}
```

**响应示例：**
```json
{
  "success": true,
  "command_id": "CMD-20260906090000-abc123",
  "status": "completed",
  "received_at": "2026-09-06T09:01:05+08:00"
}
```

### 8.4 心跳上报

**端点：** `POST /heartbeat`

**请求体：**
```json
{
  "node_id": "local-win-001",
  "status": "online",
  "services": {
    "sync_agent": "running",
    "frpc": "connected"
  },
  "resources": {
    "cpu_percent": 15.2,
    "memory_percent": 68.5,
    "disk_percent": 45.3
  },
  "timestamp": "2026-09-06T09:00:00+08:00"
}
```

**响应示例：**
```json
{
  "success": true,
  "node_id": "local-win-001",
  "server_time": "2026-09-06T09:00:00+08:00",
  "next_heartbeat_due": "2026-09-06T09:00:30+08:00"
}
```

### 8.5 控制状态查询

**端点：** `GET /status`

**响应示例：**
```json
{
  "success": true,
  "total_commands": 100,
  "pending": 5,
  "executing": 2,
  "completed": 90,
  "failed": 3,
  "active_nodes": 1,
  "last_command_at": "2026-09-06T09:00:00+08:00"
}
```

---

## 9. 协议注册中心API

> **认证方式：** HTTP Basic Auth（zongyuan/123456）
> **基础路径：** `https://www.huodouai.com/api/v1/protocols`

### 9.1 协议列表

**端点：** `GET /`

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20 |
| category | string | 否 | 分类筛选 |
| status | string | 否 | 状态筛选 |

**响应示例：**
```json
{
  "success": true,
  "protocols": [
    {
      "protocol_id": "PROTO-001",
      "name": "双内核同步协议",
      "version": "V9.3",
      "category": "sync",
      "status": "active",
      "description": "本地内核与云内核双向真值同步协议",
      "created_at": "2026-09-06T09:00:00+08:00",
      "updated_at": "2026-09-06T09:00:00+08:00"
    }
  ],
  "total": 81,
  "page": 1,
  "page_size": 20
}
```

### 9.2 协议注册

**端点：** `POST /register`

**请求体：**
```json
{
  "protocol_id": "PROTO-NEW-001",
  "name": "新协议名称",
  "version": "V1.0",
  "category": "category_name",
  "description": "协议描述",
  "content": {
    "key": "value"
  },
  "metadata": {
    "author": "node_id",
    "tags": ["tag1", "tag2"]
  }
}
```

**响应示例：**
```json
{
  "success": true,
  "protocol_id": "PROTO-NEW-001",
  "status": "registered",
  "created_at": "2026-09-06T09:00:00+08:00"
}
```

### 9.3 协议详情

**端点：** `GET /{protocol_id}`

**响应示例：** 同协议注册时的完整内容

### 9.4 协议更新

**端点：** `PUT /{protocol_id}`

**请求体：** 同协议注册，支持部分更新

### 9.5 协议删除

**端点：** `DELETE /{protocol_id}`

**响应示例：**
```json
{
  "success": true,
  "protocol_id": "PROTO-001",
  "status": "deleted",
  "deleted_at": "2026-09-06T09:00:00+08:00"
}
```

---

## 10. AI代理网关API

> **基础路径：** `http://127.0.0.1:8021`（本地直连）
> **认证方式：** API Key（在aiproxy配置中）

### 10.1 聊天补全（OpenAI兼容）

**端点：** `POST /v1/chat/completions`

**请求体：**
```json
{
  "model": "doubao-pro",
  "messages": [
    {"role": "system", "content": "你是一个助手"},
    {"role": "user", "content": "你好"}
  ],
  "temperature": 0.7,
  "max_tokens": 1024,
  "stream": false
}
```

**支持模型：**

| 模型 | 说明 | 优先级 |
|------|------|--------|
| doubao-pro | 豆包专业版 | 1（主路） |
| hunyuan | 腾讯混元 | 2（备路） |
| ollama-local | 本地Ollama（qwen2.5:1.5b） | 3（兜底） |

**响应示例：**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1757200000,
  "model": "doubao-pro",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！有什么可以帮助你的？"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 15,
    "total_tokens": 35
  }
}
```

### 10.2 健康检查

**端点：** `GET /health`

**响应示例：**
```json
{
  "status": "healthy",
  "models": ["doubao-pro", "hunyuan", "ollama-local"],
  "failover": {
    "enabled": true,
    "primary": "doubao-pro",
    "fallback": ["hunyuan", "ollama-local"]
  },
  "uptime_seconds": 86400
}
```

---

## 11. 数据模型定义

### 11.1 内核身份对象

```json
{
  "kernel_id": "string",
  "kernel_name": "string",
  "did": "string",
  "trace": "string",
  "version": "string",
  "status": "ACTIVE|INACTIVE|MAINTENANCE",
  "network": {
    "public_ip": "string",
    "domain": "string",
    "hostname": "string",
    "os": "string",
    "cloud_provider": "string",
    "region": "string"
  }
}
```

### 11.2 节点对象

```json
{
  "node_id": "string",
  "node_type": "local_kernel|dev_workstation|edge_device|external_agent|backup_node",
  "node_name": "string",
  "public_key": "string",
  "capabilities": ["string"],
  "registered_at": "ISO8601",
  "updated_at": "ISO8601",
  "last_heartbeat": "ISO8601",
  "online": "boolean",
  "status": "active|inactive|maintenance"
}
```

### 11.3 真值对象

```json
{
  "truth_id": "string",
  "title": "string",
  "content": "string",
  "level": "L0_META|L1_AXIOM|L2_STANDARD|L2_RULE|L3_BUSINESS",
  "type": "string",
  "category": "string",
  "confidence": "float (0-1)",
  "source": "string",
  "sha256": "string",
  "timestamp": "ISO8601"
}
```

### 11.4 控制指令对象

```json
{
  "command_id": "string",
  "target_node": "string",
  "command_type": "string",
  "command": "object",
  "priority": "low|medium|high|critical",
  "status": "pending|executing|completed|failed|expired",
  "issued_at": "ISO8601",
  "expires_at": "ISO8601",
  "executed_at": "ISO8601",
  "result": "object"
}
```

---

## 12. 错误码定义

| HTTP状态码 | 错误码 | 说明 |
|------------|--------|------|
| 200 | SUCCESS | 请求成功 |
| 400 | BAD_REQUEST | 请求参数错误 |
| 401 | UNAUTHORIZED | 认证失败 |
| 403 | FORBIDDEN | 权限不足 |
| 404 | NOT_FOUND | 资源不存在 |
| 409 | CONFLICT | 资源冲突（如重复注册） |
| 429 | TOO_MANY_REQUESTS | 请求频率超限 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |
| 502 | BAD_GATEWAY | 网关错误（上游服务不可用） |
| 503 | SERVICE_UNAVAILABLE | 服务不可用 |

**错误响应格式：**
```json
{
  "error": "错误类型",
  "message": "错误描述",
  "code": "ERROR_CODE",
  "details": {},
  "timestamp": "2026-09-06T09:00:00+08:00"
}
```

---

## 13. 调用示例

### 13.1 获取内核身份（Python）

```python
import requests

response = requests.get("https://www.huodouai.com/api/v1/kernel/identity")
identity = response.json()
print(f"内核ID: {identity['kernel_id']}")
print(f"域名: {identity['network']['domain']}")
```

### 13.2 节点注册（Python）

```python
import requests

node_data = {
    "node_id": "my-node-001",
    "node_type": "dev_workstation",
    "node_name": "我的开发工作站",
    "public_key": "ssh-rsa AAAAB3NzaC1yc2E...",
    "capabilities": ["development", "testing"]
}

response = requests.post(
    "https://www.huodouai.com/api/v1/kernel/nodes/register",
    json=node_data
)
result = response.json()
print(f"注册结果: {result['message']}")
```

### 13.3 真值同步（Python）

```python
import requests

headers = {
    "X-API-Key": "36f55bdd86407a1fc12f27240ed9736ac0c5cfb33e7b89ee9c9f7d8594e0c242"
}

# 握手
response = requests.get(
    "https://www.huodouai.com/anchor/api/v1/sync/handshake",
    headers=headers
)
handshake = response.json()
print(f"云端真值数: {handshake['truth_count']}")

# 拉取真值
response = requests.post(
    "https://www.huodouai.com/anchor/api/v1/sync/truth-pull",
    headers=headers,
    json={"since_version": "μ-0.9"}
)
truths = response.json()
print(f"拉取真值数: {len(truths['truths'])}")
```

### 13.4 cURL 示例

```bash
# 获取内核身份
curl -s https://www.huodouai.com/api/v1/kernel/identity | jq .

# 节点列表
curl -s https://www.huodouai.com/api/v1/kernel/nodes/list | jq .

# 握手（需要X-API-Key）
curl -s -H "X-API-Key: 36f55bdd..." \
  https://www.huodouai.com/anchor/api/v1/sync/handshake | jq .

# 控制指令（需要Basic Auth）
curl -s -u zongyuan:123456 \
  https://www.huodouai.com/anchor/api/v1/control/status | jq .
```

---

## 14. 版本管理

### 14.1 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-09-06 | 初始版本，包含内核身份、节点管理、同步、控制、协议注册中心、AI代理网关6组API |

### 14.2 兼容性策略

- **主版本号变更**：不兼容的API变更，需要客户端升级
- **次版本号变更**：向后兼容的新增功能
- **修订号变更**：Bug修复和文档更新

### 14.3 弃用策略

- API端点弃用前至少提前30天通知
- 弃用的端点在通知期内继续可用，但返回 `Deprecation` 响应头
- 通知期结束后，端点返回 410 Gone

---

## 附录

### A. 相关文档

- 内核身份标识协议：`/opt/ZONGYUAN-ROOT/identity/kernel_identity.json`
- 双内核同步协议：V9.3
- 节点注册策略：300秒心跳间隔，900秒超时

### B. 联系方式

- 内核ID：ZONGYUAN-ROOT-AUTONOMOUS-KERNEL
- DID：DID-BR-000002
- 溯源标识：Ω₀⊂⊙∞⊂Ω

---

**文档结束**

Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜ZONGYUAN-ROOT V1.7
**云内核API接口协议 V1.0 · 6组API · 27个端点 · 全域锁档BLOWN_PERMANENT**
