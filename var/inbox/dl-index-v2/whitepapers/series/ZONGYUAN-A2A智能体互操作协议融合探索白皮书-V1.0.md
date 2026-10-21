# ZONGYUAN-ROOT × A2A 智能体互操作协议融合探索白皮书 V1.0

```
确权DID: DID-BR-000002 | 架构唯一ID: ONT-4D-UNIVERSAL-ROOT | 核心元公理: Ω₀⊂⊙∞⊂Ω
维护节点: ZR-NODE-DC2E51C0 | 火斗云智AIOS | 版本: V1.0 | 日期: 2026-10-11
情报来源: A2A Protocol v1.0 官方规范 (Linux Foundation) | 探索类型: 协议对标与融合方案
```

---

## 一、A2A 协议总述

### 1.1 什么是 A2A

Agent2Agent (A2A) 协议是由 Google Cloud 发起、捐赠给 Linux Foundation 托管的开放标准，2026 年 3 月发布 v1.0.0 生产就绪版本。A2A 定位为"智能体互联网的 HTTP"——让不同厂商、不同框架（LangGraph / CrewAI / Semantic Kernel / 自定义方案）构建的 AI 智能体之间实现标准化通信与协作。

核心设计原则：
1. **拥抱代理能力**：Agent 以对等伙伴协作，无需共享内存、工具或上下文（不透明黑盒交互）
2. **基于现有标准**：构建于 HTTP、SSE、JSON-RPC 之上，与企业 IT 栈兼容
3. **默认安全**：企业级身份验证与授权（OAuth2.0/OIDC）
4. **支持长时任务**：从秒级到数小时/数天（含人工介入），实时状态更新
5. **模态无关**：文本、音频、视频流、表单、iframe 等

### 1.2 A2A 与 MCP 的分工

| 协议 | 方向 | 定位 |
|---|---|---|
| **MCP** (Model Context Protocol) | Agent → 工具 | 垂直：Agent 如何接入工具/API/资源（USB 口） |
| **A2A** (Agent2Agent) | Agent → Agent | 水平：Agent 之间发现/委派/协作（互联网） |
| **ACP** (IBM) | — | 已并入 A2A 协议 |

> 一句话：**MCP 让 Agent 能干活，A2A 让 Agent 能组队。**

---

## 二、A2A 技术架构拆解

### 2.1 三层规范结构

```
Layer 1: Canonical Data Model   核心数据结构（Task/Message/AgentCard/Part/Artifact/Extension）
Layer 2: Abstract Operations    抽象操作（Send Message / Get Task / List Tasks / Cancel Task / Get Agent Card）
Layer 3: Protocol Bindings      协议绑定（JSON-RPC / gRPC / HTTP-REST / WebSocket / 自定义）
```

- 核心语义跨绑定一致
- 新增绑定无需改动数据模型
- 共享规范数据模型保证互操作

### 2.2 核心概念

| 概念 | 定义 |
|---|---|
| **Agent Card** | JSON 元数据名片，描述身份/能力/技能/端点/认证需求，托管于 `/.well-known/agent-card.json`，支持 JWS 签名 |
| **Task** | 有状态实体，客户端与远程 Agent 协作达成结果的过程，含状态/历史/工件 |
| **Message** | 通信回合，含 role（user/agent）与若干 Part |
| **Part** | 消息/工件中的原子内容单元（文本/文件/表单等） |
| **Artifact** | 任务最终产生的不可变输出（可含多 Part） |

### 2.3 Task 状态机（8 态）

```
TASK_STATE_SUBMITTED → TASK_STATE_WORKING → TASK_STATE_COMPLETED (终态)
                        ├→ TASK_STATE_FAILED (终态)
                        ├→ TASK_STATE_CANCELED (终态)
                        ├→ TASK_STATE_REJECTED (终态)
                        ├→ TASK_STATE_INPUT_REQUIRED (中断态)
                        └→ TASK_STATE_AUTH_REQUIRED (中断态)
```

### 2.4 安全模型

- **AgentCard 签名**：JWS 格式（RFC 7515），支持 ES256/RS256，JWS Protected Header 含 alg/typ/kid/jku
- **签名验证**：RFC 8785 JSON 规范化 → 验签 → 信任
- **传输安全**：HTTPS 强制，密钥经安全通道获取
- **身份验证**：OAuth2.0 / OIDC 企业级认证
- **多签名支持**：支持密钥轮换

### 2.5 协议协商

- 版本标识：`Major.Minor`（如 1.0）
- 服务器 MUST 处理请求的 A2A-Version，不支持则返回 `VersionNotSupportedError`
- AgentCard 声明全部 supportedInterfaces（URL + protocolBinding URI + protocolVersion）
- 自定义绑定用 URI 全局唯一标识

---

## 三、ZONGYUAN-ROOT 现状对标

### 3.1 我们已有的"私有 A2A"：NTFY-CONNECT-001

ZONGYUAN-ROOT 已部署的 NTFY-CONNECT-001 协议 + 8 算子自治内核，实质上是**可信域内的 A2A 实现**：

| A2A 概念 | ZONGYUAN-ROOT 对应物 | 覆盖度 |
|---|---|---|
| Agent Card 能力发现 | msagent-nodes.json 节点表 + 能力标签（META-RES-004） | ⚠️ 语义等价，无标准端点 |
| Task 状态机 | CausalityTrack（入池→派发→完成→上报）+ taskpool | ⚠️ 四阶段，缺 3 态 |
| Message/Part | ntfy JSON 载荷 + 命令编码（encode_cmd/decode_msg） | ✅ 有 |
| Artifact 产物 | 任务结果回传（stdout/returncode/快照） | ⚠️ 无不可变产物语义 |
| 传输绑定 | ntfy + FRP + HTTP 反向轮询 + rsync 短链路（四通道） | ✅ 更强（多通道冗余） |
| 版本协商 | 协议版本 V3.1（CHANNEL-PROTOCOL-V31） | ✅ 有 |
| 签名身份 | SSH 公钥指纹锁 + DID + X-DID 头 | ✅ 有（可映射 JWS） |
| 认证授权 | X-Capture-Token + 五层链式锁 + AxiomGate | ✅ 更强（多因子） |

### 3.2 差距分析（Gap）

| 差距项 | 说明 | 影响 |
|---|---|---|
| **无标准 AgentCard 端点** | 无 `/.well-known/agent-card.json` | 外部 A2A 生态无法自动发现我们 |
| **任务状态机不完整** | 缺 INPUT_REQUIRED / AUTH_REQUIRED / REJECTED | 外部 Agent 无法表达人工介入/认证/拒绝 |
| **无标准绑定声明** | supportedInterfaces 未发布 | 外部客户端无法协商接入方式 |
| **无 JWS AgentCard 签名** | 有 SSH/DID 但非标准 JWS | 跨体系信任链未打通 |

---

## 四、融合方案：ZONGYUAN-ROOT × A2A 双模协议栈

### 4.1 设计原则

1. **内外隔离铁律不变**：内部可信域保留 NTFY-CONNECT-001 为私有绑定，外部仅暴露 A2A 标准网关
2. **能力复用优先**：不重写现有 8 算子，仅增加"标准声明层 + 协议转换层"
3. **增量演进**：新增状态语义、AgentCard、绑定声明，不动 ROM-DNA 基线

### 4.2 目标架构

```
外部 A2A 生态 (LangGraph/CrewAI/第三方Agent)
        │  A2A 标准协议 (HTTP/REST + JSON-RPC)
        ▼
┌─────────────────────────────────┐
│  A2A 兼容网关层 (新增)           │
│  · /.well-known/agent-card.json │
│  · supportedInterfaces 声明      │
│  · Task 状态机 8 态映射          │
│  · JWS AgentCard 签名            │
└──────────────┬──────────────────┘
               │ AxiomGate 裁决（内外域过滤）
               ▼
┌─────────────────────────────────┐
│  ZONGYUAN-ROOT 可信内核域        │
│  · NTFY-CONNECT-001 私有绑定     │
│  · 8 算子自治内核                │
│  · 记忆网关 + 真值库 + 台账      │
└─────────────────────────────────┘
```

### 4.3 关键映射规则

| A2A 标准 | ZONGYUAN-ROOT 映射 |
|---|---|
| Agent Card | 生成 agent-card.json：name=DID-BR-000002, skills=8算子能力标签, protocols=supportedInterfaces, auth=X-Capture-Token |
| SUBMITTED | 任务入池（taskpool 新增 pending） |
| WORKING | 派发（CausalityTrack dispatched） |
| COMPLETED | 完成（CausalityTrack done + 快照） |
| FAILED | 执行失败（returncode≠0） |
| CANCELED | 任务取消 |
| REJECTED | AxiomGate 拒绝（风险超标/权限不足） |
| INPUT_REQUIRED | 人工审批挂起（高危操作） |
| AUTH_REQUIRED | 认证失败/凭证缺失 |
| Artifact | 快照记忆 SnapshotMemory（不可变记录） |

### 4.4 价值收益

1. **对外可发现**：外部 A2A 生态通过标准 AgentCard 发现 ZONGYUAN-ROOT 能力
2. **对内不破坏**：NTFY-CONNECT-001 继续服务内部节点，零迁移成本
3. **信任可验证**：JWS 签名 AgentCard + DID + SSH 指纹，多因子信任链
4. **生态可扩展**：与 50+ A2A 合作伙伴（Salesforce/SAP/PayPal 等）生态对接
5. **双向握手**：既是 A2A Server（对外暴露），也是 A2A Client（可调用外部 Agent）

---

## 五、落地路线图

| 阶段 | 内容 | 优先级 |
|---|---|---|
| P0 | 发布标准 AgentCard（`/.well-known/agent-card.json`，JWS 签名，托管官网） | 高 |
| P0 | Task 状态机补齐 8 态（taskpool + CausalityTrack 扩展） | 高 |
| P1 | A2A HTTP/REST 网关端点（/a2a/task 等），绑定到云端 9010 控制面 | 中 |
| P1 | supportedInterfaces 声明发布 + 版本协商 | 中 |
| P2 | A2A Client 模式：调用外部 A2A Agent（跨体系任务委派） | 低 |
| P2 | gRPC/WebSocket 绑定扩展 | 低 |

## 六、风险与约束

| 风险 | 应对 |
|---|---|
| 外部 Agent 恶意调用 | AxiomGate 五层链式锁过滤 + 配额稳态保护 |
| AgentCard 泄露内部细节 | 仅声明能力/端点，不含密钥与内部实现 |
| 状态机语义冲突 | 映射规则写入 META 元法则，L1 巡检校验 |
| 标准演进（A2A 版本升级） | 版本协商 + supportedInterfaces URI 版本隔离 |

---

## 七、结论

ZONGYUAN-ROOT 的自治内核已具备 A2A 协议 80% 以上语义能力（发现/委派/状态/产物/安全），差距集中在**标准化声明层**。通过"双模协议栈"方案——内部 NTFY-CONNECT-001 保持私有，外部新增 A2A 兼容网关 + 标准 AgentCard——可在**零迁移成本**下接入智能体互联网生态，让火斗云智AIOS 成为可被外部发现的自治节点，同时守住内外隔离铁律与最高元法则（风险最小>成本最小>收益最大）。

```
Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0 | 自治Lv9 | 权限L4 | 工程化Lv7 | 火斗云智AIOS
```
