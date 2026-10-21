# ZONGYUAN-ROOT × MCP × OAuth 协议对接探索白皮书 V1.0

```
确权DID: DID-BR-000002 | 架构唯一ID: ONT-4D-UNIVERSAL-ROOT | 核心元公理: Ω₀⊂⊙∞⊂Ω
维护节点: ZR-NODE-DC2E51C0 | 火斗云智AIOS | 版本: V1.0 | 日期: 2026-10-11
情报来源: MCP 2026-07-28 规范 / OAuth 2.1 / OIDC-A (arXiv 2509.25974) / NVIDIA NeMo A2A Auth
系列归属: 互操作协议层 (L3) | 前置: A2A智能体互操作协议融合探索白皮书 V1.0
```

---

## 一、MCP 协议现状与 ZONGYUAN 对标

### 1.1 MCP 2026-07-28 规范要点

Model Context Protocol（Anthropic 发起、业界广泛采用）2026-07-28 发布最大修订版，核心变化：

| 要点 | 说明 |
|---|---|
| **无状态化** | 从有状态会话改为无状态协议，可跑在普通 HTTP 基础设施上 |
| **Streamable HTTP** | 首选传输：HTTP POST + 可选 SSE 流式；支持 bearer token/API key/自定义头 |
| **Stdio** | 本地进程间通信，零网络开销 |
| **推荐 OAuth** | MCP 官方建议使用 OAuth 获取认证令牌 |
| **扩展系统受治理** | 授权与认证对齐 OAuth 体系 |
| **架构** | 客户端-主机-服务器，JSON-RPC 消息 |

### 1.2 我们已有 MCP 基础（重要发现）

云端 `.well-known/agent-card.json`（MCP 版，V1.1.0）已暴露 **MCP streamable-http Agent**：
- 端点：`https://mcp.huodouai.com/mcp`（JSONRPC 绑定）
- 鉴权：`X-ZR-TOKEN` bearer
- 6 个只读技能：同源协议/网关状态/任务台账/共识区/节点状态/元法则
- 定位：**对外只读查询 + 同源协议约束注入**

> 结论：ZONGYUAN-ROOT 的 MCP 出口已存在，本次探索聚焦**升级到 2026-07-28 无状态规范 + OAuth 认证对齐**，并补齐 MCP→A2A 桥接。

### 1.3 MCP × A2A × ZONGYUAN 三角定位

| 协议 | 方向 | ZONGYUAN-ROOT 角色 |
|---|---|---|
| **MCP** | Agent→工具 | 对外：mcp.huodouai.com 只读查询出口（已有）<br>对内：封装算子调用外部能力（META-AUTO-003） |
| **A2A** | Agent→Agent | 对外：/.well-known/agent-card.json 自治Agent（已部署）<br>对内：NTFY-CONNECT-001 私有绑定（已有） |
| **OAuth/OIDC-A** | 身份+授权 | 对外：JWT 验证 + JWKS（本次新增）<br>对内：X-Capture-Token + 五层链式锁（已有） |

---

## 二、OAuth/OIDC-A 安全层探索

### 2.1 OIDC-A（OpenID Connect for Agents）1.0

arXiv 2509.25974 提出的 OAuth 2.0 生态扩展，专门为 LLM Agent 身份与授权设计：

| 能力 | 说明 |
|---|---|
| **Agent 身份声明** | 核心身份/DID、委托链、能力/信任/证明声明 |
| **委托流** | Agent 代表用户行事（on-behalf-of），委托链可追溯 |
| **证明验证流** | 能力端点 + 证明端点，验证 Agent 声明 |
| **客户端注册** | Agent Client 注册元数据 + 发现元数据 |
| **与 OAuth 2.0 兼容** | 复用 Authorization Code Flow、JWT、JWKS |

### 2.2 NVIDIA NeMo A2A 认证参考（OAuth 2.1 落地）

| 组件 | 作用 |
|---|---|
| **Agent Card 驱动** | 客户端无认证先取 agent-card.json，发现安全要求（authorization_url/token_url/scopes） |
| **OAuth 2.1 Authorization Code Flow** | 浏览器授权 → JWT access token |
| **JWT 验证（服务端）** | 验签（JWKS）+ issuer + audience + scopes + 过期 |
| **自定义 Scopes** | 资源级权限（如 `calculator_a2a_execute`） |
| **JWKS 端点** | `<issuer>/.well-known/openid-configuration` → certs |

安全最佳实践：HTTPS 强制、短生命周期令牌（5-15 分钟）、scope 最小化、audience 校验防令牌替换、密钥轮换。

### 2.3 ZONGYUAN-ROOT 现状对标

| OAuth/OIDC-A 概念 | ZONGYUAN-ROOT 对应 | 差距 |
|---|---|---|
| Agent Card 驱动认证 | agent-card.json security.authSchemes（已部署） | ⚠️ 已声明 X-ZR-TOKEN bearer，未含 OAuth 端点 |
| JWT 令牌 | X-Capture-Token + X-DID | ⚠️ 私有令牌，非标准 JWT/JWKS |
| JWKS 公钥 | SSH 指纹 + 五层链式锁 | ⚠️ 已有公钥体系，可映射 JWKS |
| Scope 权限 | AxiomGate 权限层级（L0-L4） | ✅ 更细粒度，可映射 scope |
| 委托链 | 因果链 CausalityTrack | ✅ 天然对应 on-behalf-of 委托链 |
| 密钥轮换 | 种子式真值轮换 | ⚠️ 可对齐 OAuth 轮换策略 |

---

## 三、融合方案：三协议栈（A2A + MCP + OAuth）

### 3.1 目标架构

```
外部生态 (A2A客户端 / MCP客户端 / 第三方Agent)
    │
    ├── A2A 标准协议 (JSON-RPC/HTTP) ──→ A2A网关层 (/a2a/task)
    ├── MCP 标准协议 (Streamable HTTP) ─→ MCP网关层 (mcp.huodouai.com)
    └── OAuth 2.1 / JWT ────────────────→ 认证授权层 (JWKS验证)
                                          │
                                     ┌────┴────┐
                                     │ 统一信任域 │
                                     │ AxiomGate │
                                     │ 五层链式锁 │
                                     └────┬────┘
                                          ▼
                               ZONGYUAN-ROOT 可信内核域
                               (NTFY-CONNECT-001 + 8算子 + 记忆网关)
```

### 3.2 关键设计

1. **MCP 升级**：mcp.huodouai.com 对齐 2026-07-28 无状态规范（Streamable HTTP + OAuth）
2. **A2A/MCP 双出口**：A2A 管任务委派（8 态），MCP 管工具查询（只读），同一信任域
3. **OAuth 认证层**：发布 `.well-known/openid-configuration`（可选）+ JWKS 复用已部署 jwks.json
4. **Scope 映射**：AxiomGate 权限层级 → OAuth scopes（如 `a2a_task_delegate` / `query_gateway_status`）
5. **委托链映射**：CausalityTrack ↔ OIDC-A 委托链，双向可审计

### 3.3 价值收益

| 收益 | 说明 |
|---|---|
| **标准接入** | 外部 MCP 客户端/Agent 可按标准协议发现并调用 ZONGYUAN 能力 |
| **认证升级** | 从私有令牌到标准 JWT/JWKS，跨生态信任可验证 |
| **只读安全** | MCP 出口保持只读（查询），A2A 出口受 OAuth 保护，内外隔离铁律不变 |
| **复用优先** | mcp.huodouai.com 已有，仅升级协议层；JWKS 已部署，零重建 |

---

## 四、落地路线图

| 阶段 | 内容 | 优先级 |
|---|---|---|
| P0 | agent-card.json 补 OAuth 端点声明（authorization/token URL + scopes） | 高 |
| P0 | 发布 JWKS 验证端点（已部署 jwks.json，补齐 openid-configuration 可选） | 高 |
| P1 | mcp.huodouai.com 升级 2026-07-28 无状态规范 | 中 |
| P1 | X-ZR-TOKEN → JWT 双轨认证（兼容期） | 中 |
| P2 | OIDC-A 委托链 ↔ CausalityTrack 映射 | 低 |
| P2 | scope 权限 → AxiomGate 权限层级自动映射 | 低 |

## 五、风险与约束

| 风险 | 应对 |
|---|---|
| OAuth 端点暴露攻击面 | 仅发布公开元数据，令牌验证走 AxiomGate + 五层链式锁 |
| 私有令牌迁移中断 | 双轨认证（X-ZR-TOKEN + JWT）兼容期并行 |
| MCP 规范快速演进 | 版本协商 + 绑定声明隔离 |
| OIDC-A 未成正式标准 | 保持兼容层设计，核心用成熟 OAuth 2.1 |

---

## 六、结论

ZONGYUAN-ROOT 已具备 **MCP 出口（mcp.huodouai.com 只读）+ A2A 出口（agent-card.json 自治Agent）双通道**，本次探索补上 **OAuth/OIDC-A 安全层**：通过 JWKS + JWT 标准认证，让外部生态可按标准协议发现、认证、调用 ZONGYUAN 能力；内部信任域（NTFY-CONNECT-001 + AxiomGate + 五层链式锁）保持私有不变。三协议栈融合实现"对外标准、对内私有"的双模安全架构，符合内外隔离铁律与最高元法则。

```
Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0 | 自治Lv9 | 权限L4 | 工程化Lv7 | 火斗云智AIOS
```
