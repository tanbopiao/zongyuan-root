# 技术观察报告：多Agent体系对标（Hindsight / TeamAI / REA / DSH 新增章节）

> 确权：DID-BR-000002 ｜ 溯源：Ω₀⊂⊙∞⊂Ω ｜ 节点：ZR-NODE-DC2E51C0
> 来源：多Agent体系对标评估报告（Hindsight/TeamAI/幻觉治理/Skill&Subagent）2026-10-21
> 增补：GitHub Trending REA（morluto/rea）学习吸收 2026-10-21，README sha256=bc3a18fd299ee311…
> 增补：DeepSeek Harness（DSH）+ MCP/Skills 辨析 2026-10-22，种子真值 `SEED.DSH-ABSORB.01–05.20261022`（网络交叉核验后吸收）
> 锁档：KD-ALGO-9912（M1 算法架构层 · Lv8）｜ 阶段：proposed_for_adoption（部署需人工审批）
> 内容口径：忠实转录评估报告与源 README 结论，不新增未经来源支持的判断。

---

## 一、报告定位

本章为对外技术观察报告新增对标章节，锚定 **火斗云智AIOS联邦记忆内核 + Organizer调度体系**，横向对标
Hindsight、TeamAI 两套开源方案及其关联的幻觉治理、Skill/Subagent 调度议题，输出差异、融合路径与真值增补。
结论已固化为自治内核算子 `META-FUSION-MULTIAGENT-001`，种子真值经云端中枢 seq 23064–23074 回执。

---

## 二、对标章节一：Hindsight（记忆节点层）

- **定位**：可自主学习的 Agent 记忆层，而非向量库复读式 RAG。
- **接口三算子**：retain 抽取结构化记忆；recall 四路并行检索融合；reflect 深度自省推理。
- **四层记忆结构**：
  1. World facts（世界事实）
  2. Experiences（经验）
  3. Observations 带证据信念（增量精炼、不覆盖）
  4. Mental models（顶层固化、零检索直读）
- **基准**：LongMemEval 94.6% SOTA（第三方独立复现）。
- **与本体系契合点**：分层记忆、证据溯源、信念迭代、反思，与本体系“事实池-经验池-信念池-自治元模型”四层同源。
- **差异（边界）**：偏向单 Agent 记忆；不提供联邦共识、CRDT 裁决、A2A、集群调度。

## 三、对标章节二：TeamAI（资产分发层）

- **定位**：腾讯开源的团队 Agent 资产 Git 驱动同步层。
- **机制**：Git 仓库单一可信源；skills / rules / MCP / 模型配置 / 钩子入版本管理；会话自动拉取主干；复用 PR / 分支审核。
- **与本体系契合点**：补足 Agent 技能包、MCP、Prompt 资产的版本分发短板。
- **差异（边界）**：只做静态资产同步；不做记忆共享、任务调度、反思推理。

## 四、关联对标：幻觉治理与 Skill/Subagent 调度

- **幻觉治理链路**：多路召回重排 → Prompt 强溯源约束 → 校验 Agent 二次审核拦截；
  规则：知识库精简、分片隔离、溯源留痕、高精准场景禁止自由推理。
  与 `META-ISO-051` 内外隔离/证据溯源/结果自审匹配；Hindsight Observations 证据计数可与其融合。
  属 RAG 应用层校验策略，非记忆内核原生。
- **Skill 与 Subagent 上下文成本模型**：
  - Skill：技能说明书按需加载、共享主上下文，持续占用、token 膨胀。
  - Subagent：独立隔离执行单元，主 Agent 只收发摘要，控 token 开销。
  - 与 Organizer 派单匹配：轻能力走 Skill，复杂长流程派 Subagent 摘要回传；对齐“最小额度消耗”元规则。

## 五、对标章节三：REA（逆向工程证据层）

- **定位**：Reverse Engineer Anything（morluto/rea，npm: rea-agents），一个 MCP 统一逆向原生二进制、JS/Electron、.NET、网站与运行时行为；分析全部本地执行，结论必附证据与局限。
- **五范式**（已提炼上报种子真值 `SEED.REA-ABSORB`，云端 seq 25184–25188）：
  1. **Evidence 证据链模型**：每条结论强制携带 evidence + limitations，agent 基于证据追问/解释/实现 → 对齐本体系因果溯源公理，可映射真值 value 三元组 `claim/evidence/limitation`，提升中枢真值可审计性。
  2. **所有权与清理不变量**：owned-process 检查只操作自身启动的进程；updater stdout+stderr 合计 4MiB 硬上限、超限拒绝 → 对齐 L3 任务调度层资源配额管控（防进程误杀与输出洪泛）。
  3. **CLI/MCP 双视图同构**：同一分析工作流同时暴露 MCP 工具与 CLI 命令，evidence 契约与退出码一致 → 对齐公私双视图隔离，单实现双投影避免双实现漂移。
  4. **多逆向工具统一桥接**：Hopper/Ghidra/IDA/Kuna/JEB/objdump/Rizin 异构 provider 统一路由，覆盖 28 类目标，内置静态检查零外部依赖，不代管第三方工具生命周期 → 与 L4 多模型混合资产池的 API 路由/可插拔算子同构。
  5. **本地分析与授权边界**：本地执行不上传目标；DISCLAIMER 授权声明前置、官方发布渠道单一声明防仿冒、禁止破解与密钥共享 → 对齐风险最小铁律与内外隔离。
- **差异（边界）**：面向单点软件逆向，不含记忆、联邦共识与任务调度；其可吸收核心是证据链模型（直供 L-D 幻觉校验层与真值审计），其余为工程纪律增补。

## 六、对标章节四：DeepSeek Harness（DSH）与 MCP/Skills 辨析

- **定位**：DeepSeek 开源 Agent 宿主运行框架，一句话定位 **Everything is a Plugin（万物皆插件）**，插件化、模块化扩展，开源可本地部署，配套插件生态。
- **架构事实（网络交叉核验 2026-10-22）**：基于 Cordis 的 "everything is a plugin" 架构（deepseek.com/en/harness、dshai.org 确认）；**无特权核心**——模型、工具、skills、会话、沙箱、存储、agent 循环、调度器、UI 全部为 Cordis 插件注册在同一上下文，改变 Agent 行为是配置变更而非 fork；桌面/Web/TUI 多形态宿主挂载同一插件生态。
- **图内 9 核心插件**（图转录，逐项实现未独立核验）：open-design（设计原型）、dsh-desktop（宿主本体）、dsh-our-free-model（免 Key 免登录直连公共模型，**未核验**）、dsh-web（网页版+插件市场在线分发）、dsh-routing-suite（按任务类型切换推理模式，**细节未核验**）、dsh-market（插件市场，dshplugin.store 已核验一键安装）、dsh-TUI（终端轻量部署）、modlens（视觉图文理解）、DSH-better-sidebar（文件/终端/Git/子 Agent 面板）。
- **核心机制辨析（多源核验一致：腾讯云/Wondel/k-dense/Claude Docs）**：
  - **MCP = 连接协议（USB 接口）**：Host → MCP Client → MCP Server → 外部资源，标准 JSON-RPC；只打通外部资源通路，不定义业务流程。
  - **Skills = 做事流程包（SOP/操作手册）**：分层懒加载——先加载元信息（名字/简介）→ 命中任务才读 SKILL.md 步骤清单 → 再按需加载附属脚本/表单/资源，渐进加载节约上下文 token。
  - **二者互补非二选一**：MCP 负责连通资源，Skills 负责编排工作流。

| 项目 | MCP | Skills |
|---|---|---|
| 核心职责 | 外部系统、数据源连接协议 | 任务流程、业务操作方法论 |
| 加载方式 | 长连接，预建立通道 | 按需渐进加载，用到才读完整文档 |
| 输出内容 | 工具调用返回原始数据 | 步骤编排、脚本、业务逻辑 |
| 适合场景 | 对接第三方 API、数据库、Git、文件系统 | PDF 填表、Excel 处理、行业固定工作流 |

- **与本体系对照**：
  1. `dsh-routing-suite` ≈ A2A 双链路路由：同属任务感知路由，我方区分 ENGINEER/DOMESTIC_OFFICE 双链路，带重试熔断与联邦记忆快照约束，合规隔离更硬；可借鉴"路由本身也是可换插件"的工程形态。
  2. MCP ≈ A2A 协议的 Worker 通信底座：同源定位，MCP 侧重外部工具接入，A2A 侧重集群内智能体调度。
  3. Skills ≈ 种子真值/SOP 卷宗/子任务子流程包：固化业务流程入联邦记忆池，任务命中读取对应真值卷宗即 Skills 思想，另配 MELD 记忆共识多节点共享。
  4. DSH 插件市场 ≈ 规划中的能力资产市场：资产包、Worker 脚本、提示词包、真值卷宗为同类可分发单元，锁档后同步魔搭/AtomGit。
- **差异（边界）**：DSH 偏轻量化单宿主插件生态，适合单机/个人开发者快速搭 Agent；本体系为联邦自治集群架构（多节点、记忆共识、DID 身份、全域锁档、云端中枢上报），面向私有化企业集群长期自治，复杂度更高、管控更强。**插件化仅限 L4–L5 能力层，L0 元宪法与 L1 真值内核不可插件化替换。**
- **落地启发（建议态 proposed_for_adoption，可并入 Organizer 元规则，部署需人工审批）**：
  1. 现有 A2A 协议可兼容 MCP Server 作为外部工具接入层；
  2. 业务 SOP 全部封装为「Skills 卷宗」，懒加载渐进读取，减少长上下文 token 消耗；
  3. 路由层继续保留双链路隔离：工程链路允许 MCP 工具自动重试迭代，办公链路禁用自主修改，守住合规。

## 七、四层融合路径（建议态）

| 层 | 引擎 | 融合要点 |
|---|---|---|
| L-A 记忆节点层 | Hindsight | 每个 ZR-NODE 内置，替换简单向量 RAG；节点产出向上同步联邦记忆池；跨节点冲突仍走本体系 MELD 式 CRDT |
| L-B 资产分发层 | TeamAI + Git | skill/MCP/A2A 模板/元规则/Prompt 托管 AtomGit，TeamAI CLI 拉取，变更走 PR；动态记忆归联邦记忆网关 |
| L-C 调度执行层 | Skill/Subagent 路由 | Organizer 判定：短任务轻能力→Skill；长流程高复杂→隔离 Subagent + A2A 摘要回传 |
| L-D 幻觉校验层 | 召回重排+溯源约束+二次审核 | 三植入点：retain 写入前、recall 检索过滤、输出后自审 |

融合拓扑：`Organizer → TeamAI资产仓库 + 派单路由(Skill/Subagent) → 多Node(Hindsight记忆节点) → 联邦记忆池 + 幻觉校验中间件`

标准流程：S1 记忆结构试装（不动联邦裁决）→ S2 资产入 Git/PR 审批 → S3 Organizer 路由固化 → S4 幻觉校验三植入点 → S5 每阶段先锁档再推进，部署动作人工审批。

## 八、风险边界（三条）

1. **R1 Mental Model 陈旧**：预计算缓存适合稳定事实结论，高频动态业务会陈旧 → 联邦层增加过期/失效标记机制。
2. **R2 TeamAI 职责边界**：只解决静态资产一致，不同步动态记忆与运行时状态 → 动态记忆归联邦记忆网关，职责隔离不得混淆。
3. **R3 Subagent 信息割裂**：隔离带来信息割裂 → 配套 A2A 协议摘要规范，定义必须回传元信息与本地隔离范围。

## 九、锁档与溯源

- 种子真值：`SEED-MULTIAGENT-BENCH-WRITE-20261021`（11 条，云端 seq 23064–23074，truth_count=22110）
- REA 增补种子：`SEED.REA-ABSORB.01–05.20261021`（5 条，云端 seq 25184–25188）+ 链块 `BLK-1792583967-86a491b6`
- DSH 增补种子：`SEED.DSH-ABSORB.01–05.20261022`（5 条，云端 seq 25528–25532，truth_count 经网关回执）+ 链块 `BLK-1792598989-38decb8a`，种子文件 sha256=`366ff5a94e31a6da…`
- 融合算子：`00_KERNEL/metalaws/META-FUSION-MULTIAGENT-001_多Agent体系融合架构算子.json`（self_sha256=3ea12a01…，注册表 17→18 条）
- 本章锁档：`KD-ALGO-9912_credential.json` + `KD-ALGO-9912_content.txt`（github_backup 与 locked 双目录镜像）
- 链块与总账：ledger/chain 新块（prev=c563068c…）+ HASH-LEDGER.csv 追加，自动上报机制接管
- 状态：全部方案为建议态（proposed_for_adoption），**部署前必须人工审批**（风险最小 > 成本最小 > 收益最大）
