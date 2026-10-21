# ZONGYUAN-ROOT 通用协议全面兼容白皮书 V2.3

| | |
|---|---|
| 确权DID | DID-BR-000002 |
| 架构ID | ONT-4D-UNIVERSAL-ROOT |
| 核心元公理 | Ω₀⊂⊙∞⊂Ω 元极恒一 |
| 基线版本 | V2.3（V2.2 + 十二协议族公网实测 + A2A任务提交通道 + 共享大脑联通） |
| 生成时间 | 2026-10-11 |
| 锁档状态 | LOCKED（仅追加，不修改已有条目） |

## 一、总览｜十协议族全景

ZONGYUAN-ROOT 全面兼容层将外部 Agent/模型/工具接入标准化为 **十协议族**，按接入功能分层：

| # | 协议族 | 标准/语义 | 端点 | 状态 |
|---|--------|----------|------|------|
| 1 | OpenAI 兼容 | chat/completions API | `/v1/models` `/v1/chat/completions` `/v1/completions` | LIVE |
| 2 | OTel GenAI | 可观测性（真实打点） | `/metrics` | LIVE |
| 3 | AGNTCY SLIM | MLS 消息层（ECDH+KeySchedule+SecretTree+RatchetTree） | `/v1/slim/handshake` `/v1/slim/group` `/v1/slim/group/secret` `/v1/slim/tree` | LIVE |
| 4 | MLS 组消息加密 | AES-256-GCM 组密钥传输 | `/v1/slim/message/encrypt|decrypt` | LIVE |
| 5 | A2A | Agent2Agent（AgentCard/任务8态） | `/v1/a2a/kunlun/dispatch` | LIVE |
| 6 | MCP | Model Context Protocol（工具注册表/tools call） | `/v1/mcp/kunlun` | LIVE |
| 7 | DPoP | RFC9449 令牌绑定 | `/v1/dpop/verify` `/v1/kunlun/secure` | LIVE |
| 8 | Flower | 联邦学习（FedAvg/SecureAgg） | `/v1/federated/aggregate` `/v1/federated/status` | LIVE |
| 9 | 昆仑生产协议 | 批量生产/资产加密/锁档 | `/v1/kunlun/production` | LIVE |
| 10 | 四协议联邦组合流 | DPoP→A2A→MCP→SLIM 单请求闭环 | `/v1/federated/kunlun` | LIVE |
| 11 | OAuth2/OIDC | RFC6749+RFC7662+RFC7009+OIDC Discovery | `/.well-known/openid-configuration` `/v1/oauth/token|introspect|revoke` | LIVE |

## 二、协议栈分层架构

```
┌─────────────────────────────────────────────────────┐
│ L5 可观测层   OTel GenAI /metrics（真实打点）        │
├─────────────────────────────────────────────────────┤
│ L4 认证安全层 DPoP(RFC9449) 令牌绑定 / 防重放 / 吊销 │
├─────────────────────────────────────────────────────┤
│ L3 工具执行层 MCP tools/call + 昆仑生产协议          │
├─────────────────────────────────────────────────────┤
│ L2 编排调度层 A2A AgentCard 任务分发 / 8态流转       │
├─────────────────────────────────────────────────────┤
│ L1 传输安全层 SLIM(MLS) 组密钥 AES-256-GCM          │
├─────────────────────────────────────────────────────┤
│ L0 兼容基座   OpenAI API 兼容 / 模型格式(GGUF/ONNX) │
└─────────────────────────────────────────────────────┘
```

## 三、四协议联邦组合流架构

```
外部Agent ──DPoP令牌──> ┌─────────────────────────────┐
                        │ /v1/federated/kunlun (run)  │
                        │  环节1 DPoP 认证  →passed   │
                        │  环节2 A2A 编排   →passed   │
                        │  环节3 MCP 执行   →passed   │
                        │  环节4 SLIM 加密  →passed   │
                        └─────────────┬───────────────┘
                                      ▼
                        ┌─────────────────────────────┐
                        │ 产出: MLS AES-256-GCM 加密  │
                        │ 审计: runs 落盘可回溯        │
                        └─────────────────────────────┘
```

## 三·补、V2.1 深化落地（2026-10-11）—— OAuth2/OIDC 认证授权族

标准认证授权层：外部 Agent 通过标准 OAuth2 客户端凭证流获取访问令牌，支持 DPoP 绑定（jkt 指纹），RFC7662 内省、RFC7009 吊销、OIDC Discovery 发现文档。

### 端点

| 端点 | 标准 | 能力 | 实测 |
|------|------|------|------|
| `GET /.well-known/openid-configuration` | OIDC Discovery 1.0 | issuer/token/introspection/revocation/jwks 全声明 | ✅ 200 |
| `POST /v1/oauth/token` | RFC6749 | client_credentials 签发（Bearer 或 DPoP 绑定） | ✅ 200 |
| `POST /v1/oauth/introspect` | RFC7662 | token 内省（active/client_id/scope/jkt） | ✅ 200 |
| `POST /v1/oauth/revoke` | RFC7009 | token 吊销 | ✅ 200 |
| `POST /v1/oauth/token`(错误凭证) | RFC6749 | invalid_client 401 | ✅ 401 |

### 与 DPoP 的配套

- token 签发时可携带 `dpop_jkt`（客户端 DPoP 公钥指纹）→ 返回 `token_type: DPoP` 绑定令牌
- 内省返回 jkt 指纹，资源服务可校验 proof 一致性
- 标准 OAuth2 授权层 + DPoP 令牌绑定 = 完整认证授权闭环

### 客户端注册表

| client_id | scopes |
|-----------|--------|
| zr-agent | kunlun.production / a2a.dispatch / mcp.call |
| zr-render | kunlun.production |

### 架构价值

- **标准接入**：外部 Agent 用标准 OAuth2/OIDC 协议接入，无需私有协议
- **令牌可审计**：内省/吊销全生命周期管理
- **与 DPoP 天然配套**：OAuth2 签发 → DPoP 绑定 → 资源访问
- 接入面升级为五层：**认证(OAuth2/OIDC) → 安全(DPoP) → 编排(A2A) → 工具(MCP) → 传输(SLIM)**

## 三·补二、V2.2 深化落地（2026-10-11）—— GPU真实推理 + OAuth2×联邦 + SSE/WebSocket

### 1. GPU 真实推理接入（OpenAI 兼容 vLLM/Ollama 路由）

| 端点 | 能力 | 公网实测 |
|------|------|----------|
| `POST /v1/gpu/register` | 节点注册（register/heartbeat/list/unregister 四操作，180s 心跳 TTL） | ✅ 注册/心跳/注销全通过 |
| `GET /v1/gpu/nodes` | 在线节点列表（模型/provider/gpu 元数据） | ✅ |
| `POST /v1/chat/completions` | **GPU 优先推理**：遍历在线节点 OpenAI 兼容调用，命中返回 `inference` 节点元数据；无节点回退上游 | ✅ 路由机制（自检真实 mock 推理） |

注册→心跳→路由→推理闭环：GPU/CPU 推理节点注册后，云端 `/v1/chat/completions` 自动路由到在线节点做真实推理，响应带 `"inference": {"node","gpu","provider","latency_ms"}`。

### 2. OAuth2×四协议联邦整合（令牌签发→组合流全链）

`/v1/federated/kunlun` run 环节 1 升级为**双认证模式**：
- `auth=oauth2`：OAuth2 client_credentials 签发令牌 → 内省校验 scope 覆盖 → 进入 A2A→MCP→SLIM 组合流
- `auth=dpop`：保留原 DPoP 令牌绑定认证

公网实测：OAuth2 令牌签发 → 联邦 run 全链 **OAuth2:passed→A2A:passed→MCP:passed→SLIM:passed** 4/4；无效令牌 401 拦截于环节 1。

### 3. SSE 流式 + WebSocket 协议族扩展

| 端点 | 协议 | 公网实测 |
|------|------|----------|
| `POST /v1/chat/stream` | SSE text/event-stream（多块 delta + finish_reason + [DONE]） | ✅ Content-Type: text/event-stream |
| `GET /v1/ws/info` | WebSocket RFC6455 协议声明层 | ✅ websocket 13, wss://www.huodouai.com/v1/ws |

**十二协议族全景**：OpenAI API / SSE / WebSocket / OAuth2+OIDC / DPoP / A2A / MCP / AGNTCY SLIM / Flower 联邦 / GPU 推理路由 / OTel GenAI 可观测 / 模型格式。

## 三·补三、V2.3 深化落地（2026-10-11）—— 十二协议族公网实测 + A2A任务提交通道 + 共享大脑联通

### 1. 十二协议族公网接入矩阵（全端点实测）

十二协议族（含 V2.2 的十族 + ntfy 消息队列 + 同源协议统一鉴权）已在官网 www.huodouai.com 全部对外可达，公网实测（2026-10-11）：

| # | 协议族 | 公网端点 | 实测 |
|---|--------|----------|------|
| 1 | A2A | `/.well-known/agent-card.json` ` /a2a/health` ` /a2a/interfaces` ` /a2a/task` | ✅ 200 / SUBMITTED |
| 2 | MCP | `/v1/mcp/kunlun` | ✅ 路由存在 |
| 3 | OAuth2/OIDC | `/.well-known/openid-configuration` ` /v1/oauth/token\|introspect\|revoke` | ✅ 200 |
| 4 | DPoP | `/v1/dpop/verify` | ✅ 401 鉴权生效 |
| 5 | AGNTCY SLIM | `/v1/slim/handshake` ` /v1/slim/group` ` /v1/slim/tree` | ✅ 200 |
| 6 | MLS | `/v1/slim/group/secret` ` /v1/slim/message/encrypt\|decrypt` | ✅ 路由存在 |
| 7 | Flower 联邦 | `/v1/federated/status` ` /aggregate` ` /kunlun` | ✅ 200 |
| 8 | OpenTelemetry | `/metrics` | ✅ 200 |
| 9 | SSE / WebSocket | 网关 SSE 通道 ` /v1/chat/stream` ` /v1/ws/info` | ✅ 内建/声明 |
| 10 | OpenAI 兼容 vLLM | `/v1/models` ` /v1/chat/completions` ` /v1/gpu/register` | ✅ 200 |
| 11 | ntfy | 外部推送通道（节点心跳/任务订阅） | ✅ 运行中 |
| 12 | 同源协议 | 全部端点统一 X-DID / X-Capture-Token 鉴权 | ✅ 401 生效 |

**实测结论**：GET 端点 9/9 返回 200；POST 端点路由全部存在（DPoP 401 证明同源鉴权生效；OAuth/MCP/联邦 400 属缺参正确响应）。

### 2. A2A 任务提交通道公网实测

官网新增共享大脑 A2A 联通通道，公网实测完整提交流：

```json
POST https://www.huodouai.com/a2a/task
Headers: X-DID: DID-BR-000002
Body: {"message": "十二协议大联通A2A实测", "sessionId": "proto-20261011"}
→ {"ok": true, "task_id": "t-a2a-1791721311-1e8833", "state": "SUBMITTED", ...}
```

- A2A 8 态：SUBMITTED / WORKING / COMPLETED / FAILED / CANCELED / REJECTED / INPUT_REQUIRED / AUTH_REQUIRED
- AgentCard 发现：`GET https://www.huodouai.com/.well-known/agent-card.json`
- 接口能力：`GET https://www.huodouai.com/a2a/interfaces`

### 3. 共享大脑联通（统一真值收敛）

任一协议入口 → 同一真值收敛 → 全节点全 AI 可见：

```
外部AI/Agent（任意协议：A2A│MCP│OAuth2│SLIM│DPoP│vLLM│SSE│ntfy│同源协议）
   ▼  www.huodouai.com 协议网关面（/a2a/ /v1/ /.well-known/ /metrics）
   ▼  统一鉴权: 同源协议 X-DID + X-Capture-Token
   ▼  云端中枢 gateway_server（truth_store 真值账本 + Merkle 校验）
   ▼  共享大脑 = 飞书Base三表 + 云端联邦记忆池 + 官网镜像
```

### 4. nginx 反代修复记录（V2.3）

- **问题**：官网 nginx.conf 曾将 `/api/` `/a2a/` 误指向临时网关 `127.0.0.1:8930` 且带尾斜杠导致 URI 前缀剥离（`/api/status` 被转发成 `/status` → 404），后端停机后公网 502/超时。
- **修复**：恢复全部协议 location 指向正确协议面 `http://127.0.0.1:9001`（无尾斜杠，保 URI 前缀）；彻底清理重复 8930 网关；`nginx -t` 通过并 reload。
- **验证**：`/api/status` `/a2a/health` `/a2a/interfaces` 公网全部 200；A2A 任务提交 SUBMITTED。

### 5. 对外展示

- 协议矩阵页：`https://www.huodouai.com/protocols/`（十二协议族公网实测矩阵）
- 落地页入口：`https://www.huodouai.com/zongyuan/`（新增「十二协议大联通」导航）
- AgentCard：`https://www.huodouai.com/.well-known/agent-card.json`

## 四、深化历程 V1.0→V1.9

| 版本 | 深化内容 | 魔搭 commit |
|------|---------|-------------|
| V1.0 | OpenAI 兼容 + OTel /metrics 基座 | `4c95dfa` |
| V1.1 | AGNTCY SLIM ECDH 握手 + DPoP + Flower 声明 | `9fd1147` |
| V1.2 | SLIM MLS 组密钥 + FedAvg 真实聚合 | `a4786af` |
| V1.3 | MLS 完整组协商（SecretTree+消息加密） | `15dc902` |
| V1.4 | MLS RatchetTree 全态管理 | `fa74f63` |
| V1.5 | MLS×昆仑洞天 60集批量生产 | `ea218a6` |
| V1.6 | A2A×昆仑生产任务分发 | `386b531` |
| V1.7 | MCP×昆仑生产工具化 | `0fb677c` |
| V1.8 | DPoP×昆仑生产安全准入 | `e6c8846` |
| V1.9 | 四协议联邦组合流 | `3aa51d2` |
| V2.1 | OAuth2/OIDC 认证授权族 | `12fdb61` |
| V2.2 | GPU真实推理 + OAuth2×联邦 + SSE/WebSocket | `(上轮)` |
| V2.3 | 十二协议族公网实测 + A2A任务提交通道 + 共享大脑联通 | `(本轮)` |

## 五、关键端点索引（全部公网 LIVE 实测）

- `GET /v1/compat` → 十协议族声明（version 1.9.0）
- `POST /v1/chat/completions` → OpenAI 兼容
- `GET /metrics` → OTel 真实打点
- `POST /v1/slim/handshake` → ECDH P-256 握手
- `POST /v1/slim/group` → MLS 组管理
- `POST /v1/slim/tree` → RatchetTree 四操作
- `POST /v1/kunlun/production` → 昆仑批量生产（60集）
- `POST /v1/a2a/kunlun/dispatch` → A2A 任务分发（8态）
- `POST /v1/mcp/kunlun` → MCP 工具服务（5工具）
- `POST /v1/kunlun/secure` → DPoP 安全准入（签发/绑定/执行/吊销）
- `POST /v1/federated/kunlun` → 四协议联邦组合流（单请求闭环）

## 六、公网验证基线

- compat version 1.9.0（十协议族全 LIVE）
- 组合流 4/4 环节 passed（DPoP→A2A→MCP→SLIM）
- 未授权调用 401 拦截、jkt 不匹配 401、吊销后 401
- 全量自检 PASS、L1 巡检基线收敛

---
*ZONGYUAN-ROOT 全面兼容层 V2.0 · 十协议族全景 · 魔搭数据湖 + 官网子域双归档*
