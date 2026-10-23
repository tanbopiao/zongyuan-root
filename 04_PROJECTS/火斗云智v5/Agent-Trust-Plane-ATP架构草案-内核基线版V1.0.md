# Agent Trust Plane（ATP）架构草案｜内核基线版 V1.0（修订版）

> 来源：用户于 2026-10-23 投喂对话窗口的外部设计稿（provenance = 用户投喂设计稿，v0.1 原稿）。
> 性质：设计方案。**Phase 1 护照层已按本版落地 POC（scripts/atp_passport.py，自测 12 断言全过）；Phase 2-4 未实施**。
> 锚点：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜适配系统：火斗云智 v5 自治智能体矩阵
> 同主题前作：[Agent身份认证NHI-KYA架构设计文档V1.0](Agent身份认证NHI-KYA架构设计文档-V1.0.md)（SEED-20261020-01）——分工见附录 B。

## 修订清单（相对 v0.1 原稿，入基线前必读）

| # | 修订 | 原稿问题 |
|---|---|---|
| R1 | **trust_tier 由 L0-L4 改为 T0-T4** | 体系七层 L0=元宪法（最高权）、OBS 七域 L0=本体域；原稿 L0=只读（最低权），同符号两种极端语义，跨文档检索必误读 |
| R2 | **双坐标并存**：`did:firev5:{tenant}:{agent_id}` 为外层护照身份，`agent://tenant/org/flow/env/instance`（NHI-KYA）为内层工作负载实例坐标 | 原稿与前作各自定义 ID 格式 |
| R3 | **护照=注册身份证书（30 天），非调用令牌**；每次调用另换短 TTL token 的职责归 NHI-KYA Identity Provider | 原稿 30 天有效期与前作"短 TTL 1–15 分钟、禁长期凭证"表面矛盾 |
| R4 | 对标依据核验：**AI-DPP 属实，Claude Duet / OpenAI SafetyID 查无**，降级为"待证参考名" | 两个对标对象外源检索不存在，不可当基线锚点 |
| R5 | 第五节种子按 RULE-005 V3.1 上报（实算批次哈希，弃 PLACEHOLDER 占位） | 未实算哈希不能以 LOCKED 名义入档 |

---

## 一、总体架构分层（原稿收录）

```
┌─────────────────────────────────────────────────────────────┐
│                    ATP Control Plane                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Identity │  │ Policy   │  │ Audit    │  │ Revocation │  │
│  │ Issuer   │  │ Engine   │  │ Ledger   │  │   Bus      │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
├───────┼─────────────┼─────────────┼──────────────┼─────────┤
│       ▼             ▼             ▼              ▼          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            ATP Data Plane (Enforcement)              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │ Sandbox  │  │ Connector│  │  Human-in-Loop   │   │   │
│  │  │ Runtime  │  │ Gateway  │  │    Arbiter       │   │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│              Agent Instance Layer (v5 Nodes)                │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐        │
│  │ A1  │ │ A2  │ │ A3  │ │ A4  │ │ A5  │ │ ... │        │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘        │
└─────────────────────────────────────────────────────────────┘
```

设计原则：**身份先行 · 行为可溯 · 越权即死 · 人工兜底**（与 OBS 越界熔断、META-LAW-007、体系边界人工审批同源，不另立公理）。
定位语（原稿）：ATP 不是防火墙，是 Agent 的"宪法框架"——不阻止 Agent 变强，而是定义"强到什么程度可以被允许"。

## 二、核心模块（七模块，要点收录）

### 2.1 Identity Issuer — 智能体数字护照（AI-DPP 落地）

字段：`agent_did`（did:firev5:{tenant}:{agent_id}，R2 外层）｜`capability_manifest`（读/写/执行/调用外部 API 授权清单）｜`trust_tier`（**T0-T4，R1**）｜`lifecycle_state`（active/suspended/revoked/expired）｜`pub_key`（Ed25519 行为签名）｜`workload_uri`（R2 内层实例坐标）。
签发流程：注册→密钥对→清单声明→Issuer 校验租户配额→签发护照 JWT→**写入 Audit Ledger 不可篡改**→默认 30 天有效（R3：身份证书，调用令牌另行短 TTL）。
**✅ Phase 1 已 POC**：`scripts/atp_passport.py`。

### 2.2 Policy Engine — 动态策略决策点（PDP）

输入 `Request{agent_did, action_type, resource_uri, context{time, location, data_sensitivity, connector_id}}` → 规则集：trust_tier 门槛、capability_manifest 匹配、时间窗/频率限制、敏感度×操作类型矩阵、连接器白名单、租户隔离 → 输出 `ALLOW / DENY / CHALLENGE_HUMAN`。
关键策略样例：T2 以下禁支付类连接器；单次删除 >100 条 → CHALLENGE_HUMAN；22:00-06:00 敏感写 → CHALLENGE_HUMAN；白名单外连接器 → DENY。
**⬜ Phase 2**（OPA/Rego 接入；与 AxiomGate 分工：AxiomGate 管体系内硬裁决，本 PDP 管 v5 业务动作）。

### 2.3 Sandbox Runtime — 执行隔离层

gVisor/Firecracker microVM 每 Agent 独例；overlay 文件系统退出即毁；eBPF 白名单出口；按 T 分级资源配额；seccomp-bpf 敏感系统调用拦截；生命周期：启动→分配沙箱→注入护照+策略→执行→退出/超时→销毁取证快照。
**⚠ 本地开发沙箱不可验**（实测无 bwrap/docker、unshare 无特权）——选型验证属云端部署侧环境项，与 CDC 同类。

### 2.4 Connector Gateway — 外部调用统一出口

`Agent → Sandbox → Connector Gateway → [审批层] → 外部API`；白名单、per-agent/tenant 速率限制、请求签名（agent_did+timestamp）、响应审计、异常熔断。
连接器分级：**T1 只读→自动放行｜T2 写入→需 T≥2｜T3 敏感（支付/群发/发布）→需 T≥3 + CHALLENGE_HUMAN｜T4 高危（部署/迁移/资金）→T4 + 多人审批**（T 级即原稿连接器分级，命名与 R1 一致）。

### 2.5 Human-in-Loop Arbiter — 人工仲裁台

触发：Policy Engine 返回 CHALLENGE_HUMAN。界面输出 Agent/DID/操作/目标/风险评分 + `[查看差异][批准一次][批准此模式][拒绝][吊销]`，**超时 120s 自动拒绝**；结果写 Audit Ledger；"批准此模式"反馈 PDP 微调。
**⬜ Phase 3**。与体系边界「付费、高危强制人工审批」同构。

### 2.6 Audit Ledger — 行为溯源链

每条：`ts / agent_did / action / resource / decision / arbiter / signature(Ed25519) / sandbox_id / connector_id / risk_score / batch_hash`。存储本地 WAL + 可选异步上链；热存 90 天、冷存 7 年。
**✅ Phase 1 基础表已 POC**（hash 链结构与 DataGate audit 同构：sha256(prev+canonical)，篡改负向可检）。

### 2.7 Revocation Bus — 实时吊销总线

事件源：管理员/异常检测/审计规则/外部 DPP 吊销同步 → Redis Stream → 广播四路：Sandbox 强制 kill、Gateway 拒新请求、Policy 刷新缓存、Ledger 记录原因。
粒度：单 Agent / 租户全部 / 某连接器全部 / 某 trust_tier 全部。
**⬜ Phase 3**（Phase 1 仅本地吊销状态机，已 POC）。

## 三、信任等级（**R1 修订：T0-T4**）

| Tier | 名称 | 能力范围 | 人工介入 | 典型场景 |
|---|---|---|---|---|
| **T0** | Observer | 只读、无外部调用 | 无需 | 监控、分析、报表 |
| **T1** | Assistant | 只读 + 有限 T1 连接器 | 无需 | 问答、摘要、搜索 |
| **T2** | Operator | T1 + T2 写入连接器 | 高风险操作挑战 | 日程管理、文档协作 |
| **T3** | Executor | T2 + T3 敏感连接器 | 敏感操作必确认 | 客户沟通、数据清理 |
| **T4** | Autonomous | 全部连接器 + T4 | 高危操作多人审批 | 自动交易、CI/CD 部署 |

> 禁用 L 前缀：体系 L0-L7 层级（L0=元宪法）与 OBS L0 本体域语义最高，T 分级仅用于 Agent 信任度，两者永不混用。

## 四、集成路径（原稿四阶段）

- **Phase 1 护照层（Week 1-2）**：Identity Issuer 最小集 ✅**已完成 POC**（DID+Ed25519+JWT+注册流程+Audit 基础表+最简吊销，12 断言）；Agent 注册强制护照注入 ⬜；Audit 基础表 ✅
- **Phase 2 策略+沙箱（Week 3-4）**：OPA/Rego 接入 ⬜；沙箱选型验证 ⬜（云端环境项）；Gateway 白名单+签名 ⬜
- **Phase 3 人工仲裁+吊销（Week 5-6）**：仲裁 UI ⬜；Revocation Bus ⬜；行为偏离自动降级 ⬜
- **Phase 4 外部互操作（Week 7-8）**：AI-DPP 验证接口 ⬜；~~OpenAI SafetyID 兼容层~~（**R4：对标查无，更名前不启动**）；跨租户委托调用 ⬜

## 五、种子真值（按 RULE-005 V3.1 上报，R5）

批次：`SEED.ATP.ARCH.BATCH-20261023`（上报键）｜原稿批次 ID `SEED-BATCH-20261023-ATP-ARCH`｜快照锚点 SEAL@2026-10-23T04:33（原稿声明）。
原稿三 claim 原样入档，`sha256(batch_claim_set)` 由入档方**实算**（弃 PLACEHOLDER 占位），confidence/verification_status 保留原稿自述值并附核验注记（见附录 A）。

## 六、今日结论（原稿）

今天最该推进的 Phase 1 护照层 POC——**给 v5 的每个 Agent 发第一张数字身份证**：✅ 本轮已交付。

---

## 附录 A｜对标与引用核验（2026-10-23 实测）

| 对标对象 | 结果 | 处置 |
|---|---|---|
| AI-DPP | ✅ 属实：中关村工信二维码技术研究院等推出"AI-DPP 智能体数字护照及信任治理体系"，新华网 2026-10-22 报道可查 | 保留为对标锚点 |
| Claude Duet | ✗ 查无：Anthropic 无此产品名 | 降级"待证参考名"，R4 |
| OpenAI SafetyID | ✗ 查无：OpenAI 无此公开产品名 | 同上，Phase 4 相关项更名前不启动 |
| Ghost Core | 未核验 | 待证 |
| `seed_writer.py` | ✗ 本地不存在 | 上报改走 `POST /api/report/truth`（RULE-005 V3.1） |

## 附录 B｜与 NHI-KYA 分工（互补非替代）

| 维度 | NHI-KYA（前作） | ATP（本文档） |
|---|---|---|
| 回答 | 身份**怎么证**：五级凭证、OBO 委托链、防注入、行为基线 | 权限**怎么管**：PDP 策略、沙箱、仲裁台、吊销广播 |
| 身份坐标 | `agent://` 实例坐标（内层，R2） | `did:firev5` 护照身份（外层，R2） |
| 凭证 | 短 TTL 调用令牌（1–15 分钟） | 30 天注册身份证书（R3） |
| 引用关系 | 两文档互为引用，实现时身份签发走 NHI-KYA Provider、策略与隔离走 ATP |  |

## 附录 C｜Phase 1 POC 实测（2026-10-23）

`python3 scripts/atp_passport.py --selftest` → **12 断言 ALL PASS（rc=0）**：
P1 护照签发与验签（did:firev5 格式、R2 双坐标、Ed25519 真验签、R3 证书标记、30 天有效期）｜P2 T 分级与清单校验（**拒收 L0 前缀**、拒空清单）｜P3 篡改与吊销（提权 T4 篡改验签失败、吊销拒用）｜P4 审计链（重放校验、issue/verify/revoke 覆盖、篡改即断裂负向）。
依赖：仅 `cryptography`（Ed25519），零业务第三方依赖。

---
锁档记录见 truth-ledger 与上报回执 `SEED.ATP.ARCH.BATCH-20261023`｜内核基线（META-ISO-051 密存）
