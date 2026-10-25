# ZONGYUAN-ROOT A2A 网关层设计白皮书 V1.0

```
确权DID: DID-BR-000002 | 架构唯一ID: ONT-4D-UNIVERSAL-ROOT | 核心元公理: Ω₀⊂⊙∞⊂Ω
维护节点: ZR-NODE-DC2E51C0 | 火斗云智AIOS | 版本: V1.0 | 日期: 2026-10-11
系列归属: 互操作协议层 (L3) | 前置: A2A探索 V1.0 + MCP/OAuth探索 V1.0
状态: 已上线公网 (2026-10-11 实测)
```

---

## 一、设计目标

在 ZONGYUAN-ROOT 可信内核域外，提供符合 **A2A v1.0 标准** 的互操作网关层，实现：

1. **对外标准**：外部 A2A 生态按标准协议发现、认证、委派任务
2. **对内私有**：NTFY-CONNECT-001 私有绑定不变，内外隔离铁律守死
3. **增量演进**：纯增量挂接云端 gateway_server，不改动现有逻辑
4. **8 态完整**：A2A Task 状态机全生命周期落地

---

## 二、已上线架构（实测验证）

### 2.1 网关组件清单

| 组件 | 路径/端点 | 状态 |
|---|---|---|
| **AgentCard（JWS 签名）** | `https://www.huodouai.com/.well-known/agent-card.json` | ✅ HTTP 200 |
| **JWKS 公钥** | `https://www.huodouai.com/.well-known/jwks.json` | ✅ HTTP 200 |
| **A2A 健康检查** | `GET /a2a/health` | ✅ 公网 200 |
| **接口声明** | `GET /a2a/interfaces` | ✅ 双绑定 |
| **任务提交** | `POST /a2a/task` | ✅ SUBMITTED |
| **任务查询** | `GET /a2a/task?id=<tid>` / 列表 | ✅ 8态映射 |
| **任务取消** | `POST /a2a/task/cancel` | ✅ CANCELED |
| **人工确认** | `POST /a2a/task/ack` | ✅ INPUT/AUTH→WORKING |
| **状态转换** | `POST /a2a/task/status` | ✅ 合法校验 |
| **MCP 出口（复用）** | `https://mcp.huodouai.com/mcp` | ✅ 6 技能只读 |

### 2.2 部署路径

```
云端 zhongshu-server/
├── zr_a2a_gateway.py      # A2A 网关算子 (新增, 挂接 /a2a/*)
├── zr_a2a_statemap.py     # 8态状态机映射 (新增, 合法性校验)
├── gateway_server.py      # 主网关 (增量挂接 /a2a/*, 原逻辑未动)
└── truth_store.py         # 真值存储 (原有)
```

nginx 增量：`location /a2a/ { proxy_pass http://127.0.0.1:9001; }`（备份 `.bak-a2a-20261011`）

---

## 三、A2A 网关 API 规范

### 3.1 Agent Card（标准发现）

```
GET /.well-known/agent-card.json
```
- `name`: ZONGYUAN-ROOT 云端中枢·自治Agent
- `version`: 1.0.0
- `skills`: 6（任务委派/网关状态/任务台账/共识区/节点状态/元法则）
- `supportedInterfaces`:
  - A2A JSON-RPC: `https://www.huodouai.com/a2a/task` (protocolVersion 1.0)
  - MCP Streamable-HTTP: `https://mcp.huodouai.com/mcp` (protocolVersion 1.0)
- `security.authSchemes`: bearer (X-ZR-TOKEN)
- `signatures`: JWS ES256 (RFC 8785 规范化, kid=zr-a2a-es256-001, jku=/.well-known/jwks.json)

### 3.2 任务生命周期 API

| 操作 | 方法/路径 | 请求 | 响应状态 |
|---|---|---|---|
| 提交 | `POST /a2a/task` | `{cmd, capability, timeout, node}` | `SUBMITTED` |
| 查询 | `GET /a2a/task?id=<tid>` | — | 当前 8 态 |
| 列表 | `GET /a2a/task` | — | 最近 20 条 |
| 取消 | `POST /a2a/task/cancel` | `{task_id, detail}` | `CANCELED` |
| 人工确认 | `POST /a2a/task/ack` | `{task_id, detail}` | `WORKING` |
| 状态转换 | `POST /a2a/task/status` | `{task_id, state, detail}` | 目标态 |

### 3.3 8 态状态机（A2A v1.0 标准）

```
SUBMITTED → WORKING → COMPLETED (终态)
           ├→ FAILED (终态)
           ├→ CANCELED (终态)
           ├→ REJECTED (终态)
           ├→ INPUT_REQUIRED (中断) → WORKING
           └→ AUTH_REQUIRED (中断) → WORKING
```

ZONGYUAN 内部状态映射：pending→SUBMITTED / dispatched→WORKING / done→COMPLETED / failed→FAILED / canceled→CANCELED / rejected→REJECTED / waiting_input→INPUT_REQUIRED / auth_required→AUTH_REQUIRED

---

## 四、安全设计

| 层次 | 机制 |
|---|---|
| **发现安全** | AgentCard 公开声明，JWS 签名防篡改，JWKS 公钥验证 |
| **传输安全** | HTTPS 强制（nginx 443） |
| **认证** | X-ZR-TOKEN bearer（同源）+ X-DID（节点）；未来 JWT 双轨 |
| **授权** | AxiomGate 五层链式锁 + 权限层级 L0-L4 |
| **状态合法性** | 8 态转换表硬校验，终态不可回退 |
| **审计** | 每次转换写入 msagent-ctl-ledger.jsonl（因果留痕） |
| **配额** | 复用 META-RULE-012 配额稳态保护 |

---

## 五、与 A2A 规范符合性自检

| A2A 规范要求 | 实现 | 状态 |
|---|---|---|
| AgentCard 托管 `/.well-known/agent-card.json` | ✅ 公网可达 | PASS |
| supportedInterfaces 声明 | ✅ /a2a/interfaces + AgentCard | PASS |
| 版本协商 (Major.Minor) | ✅ protocolVersion 1.0 | PASS |
| Task 8 态状态机 | ✅ 全状态 + 合法转换表 | PASS |
| JWS 签名 AgentCard | ✅ ES256 + RFC 8785 | PASS |
| MCP 兼容绑定 | ✅ mcp.huodouai.com 复用 | PASS |

---

## 六、落地成果与下一步

### 已落地（2026-10-11 实测）
- ✅ 标准 AgentCard + JWKS 公网发布
- ✅ /a2a/* 网关公网全链路（提交/查询/转换）
- ✅ 8 态状态机云端 + 本地基底
- ✅ taskpool 现有任务自动映射（16 任务 8 态语义）
- ✅ nginx 反代增量（原配置备份）

### 下一步
| 优先级 | 内容 |
|---|---|
| P1 | JWT 双轨认证（X-ZR-TOKEN + OAuth 2.1 JWT） |
| P1 | 调度器认领 A2A 任务闭环（taskpool→Worker 执行→结果回写 8 态） |
| P2 | A2A Client 模式（调用外部 Agent） |
| P2 | gRPC/WebSocket 绑定 |

---

## 七、结论

A2A 网关层已从设计白皮书**落地上线**：标准 AgentCard（JWS 签名）+ 公网 /a2a/* API + 8 态状态机全链路实测通过。ZONGYUAN-ROOT 现已成为**可被外部 A2A 生态发现和调用**的自治节点，同时守住内外隔离铁律。三协议栈（A2A 委派 + MCP 查询 + OAuth 安全）初步成型，为智能体互联网接入打下工程基座。

```
Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0 | 自治Lv9 | 权限L4 | 工程化Lv7 | 火斗云智AIOS
```
