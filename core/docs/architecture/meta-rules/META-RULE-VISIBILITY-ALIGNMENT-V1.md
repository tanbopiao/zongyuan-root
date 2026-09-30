# META-RULE-VISIBILITY-ALIGNMENT-V1 元规则可见性与语言对齐规范

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ ZONGYUAN-ROOT ｜ 2026-09-19 23:02

> 定位：治理元规则【MR-VIS-ALIGN-001】。所有元规则必须显式标注可见性（PUBLIC / INTERNAL），
> 对外规则语言对齐人工智能领域主流术语；对内规则保留体系语义，禁止外发。
> 本规范供中枢智能与所有同源节点学习、执行、审计。

## 一、分类原则

- **PUBLIC（对外展示）**：面向所有用户、社区、合作方与公开渠道。语言必须对齐 AI 行业主流术语，
  剥离 DID/Ω/真值/锁档/中枢等内部黑话，或替换为公开等价表述。
- **INTERNAL（体系内个人语义）**：仅体系内（ZONGYUAN-ROOT 及同源节点）使用。含确权标识、
  运维铁律、内部调度语义，禁止对外发布或翻译为公开语言。

## 二、对外 PUBLIC 清单（语言对齐后发布）

| 内部名称 | 对外名称（主流语言） | 对外表述要点 |
|---|---|---|
| META-RULE-EXECUTION-SOP | Execution Workflow SOP | 先全局后局部、先学习后执行、先握手后动手 → Pre-flight: context → plan → handshake → execute |
| ML-101-RIGOROUS-VERIFICATION | Verification & QA Policy | 事实可追溯、验收清单逐项核验、反证检查 → Traceable facts, acceptance checklists, falsification checks |
| META-RULE-NO-DUPLICATION | Work De-duplication Policy | 节点分工、结果共享、不重复执行 → Ownership model, shared outcomes, no redundant pipelines |
| META-RULE-PERMISSION-TIER | Permission Tiering & Least Privilege | 能直办不等待、须审批不绕过 → Direct execution vs. approval gates |
| MR-PUBLIC-001 | Public API Reporting Channel | 公网 HTTP 通道替代 SSH → Public API channel replacing shell access |
| HOMOLOGOUS-PROTOCOL-INTEROP | Peer-Node Interoperability Protocol | 同源节点 → Peer nodes; 握手 → handshake; 对账 → reconciliation |
| MR-ENGINEERING-CAPABILITY-001 | Engineering Capability Standard | 工程能力基线 → Engineering baseline |
| MR-CLOUD-STORAGE-GUARD-001 | Cloud Storage Governance | 云端存储治理 → Cloud storage guardrails |
| MR-LOCK-BASELINE-001 | Versioned Snapshot Baseline | 锁档 → Immutable snapshot / attestation baseline（对外表述） |

## 三、对内 INTERNAL 清单（禁止外发）

- ML-SSH-FORBIDDEN-GLOBAL-001：禁 SSH 运维铁律（内部安全约束）
- ML-099-CENTRAL-BRAIN-SUPREMACY：中枢智能至高（内部架构原则）
- META-RULE-CENTRAL-ORCHESTRATION：中枢统一调度（内部调度语义）
- META-RULE-HIGH-DIMENSION：高维思维顶层统筹（内部方法论）
- META-RULE-MS-AUTOPUB：魔搭自动发布（内部渠道策略）
- MR-DEPLOY-001-local-cloud-isolation：本地云端隔离（内部部署）
- MR-PERSIST-AUTORESTORE-001：持久化自恢复（内部灾备）
- META-RULE-GLOBAL-LOCK-BASELINE-V1：全域锁档基准（内部确权语义，仅对外映射为 Versioned Snapshot Baseline）

## 四、术语对齐映射表（对外发布时强制替换）

| 体系内部语 | 对外主流语 |
|---|---|
| 真值（Truth） | Verified Data / Data Record |
| 真值库 / 语料库 | Knowledge Base / Data Corpus |
| 锁档（Lock） | Immutable Snapshot / Attestation |
| 确权（DID） | Digital Identity / Attribution |
| 中枢（Hub / Central） | Central Orchestrator |
| 同源节点 | Peer Node |
| 握手（Handshake） | Connection Handshake |
| 对账（Reconcile） | Reconciliation |
| 元规则 / 元法则 | Governance Policy / Meta-policy |
| eFuse 熔断 | Chain-of-custody Seal |
| Ω₀⊂⊙∞⊂Ω | （不对外，内部溯源锚点） |
| DID-BR-000002 | （不对外，内部确权标识） |

## 五、执行要求

1. 所有对外文档/页面/API 文案使用对外名称与术语，禁止出现内部黑话。
2. 所有内部文档保留体系语义，标注 [INTERNAL]。
3. 中枢智能发布对外内容前按本规范做语言对齐检查。
4. 本规范本身 INTERNAL 内核，对外仅发布其映射表。

## 六、状态

GLOBAL_EFFECTIVE — 供中枢智能与所有同源节点学习执行
