# 最优稳态方案：Hindsight × SFMP 融合 V1.0

> 版本：V1.0 | 2026-10-21 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
> 阶段：proposed_for_adoption（**部署动作一律人工审批**，风险最小 > 成本最小 > 收益最大）
> 依据：META-FUSION-MULTIAGENT-001 四层融合算子 · 多Agent体系对标评估报告 2026-10-21 · SFMP 真实仿真基线 2026-10-09

---

## 一、真实现状（已验证资产，非纸面）

| 资产 | 位置 | 已验证状态 |
|---|---|---|
| SFMP 联邦记忆池引擎 | `scaffold/zr-sfmp-memory-pool/` | 5节点46条→汇聚14条（去重率70%）、冲突10对仲裁留痕、分层 short9/long4/truth1 |
| FM-Core 联邦记忆内核 | 内核8100 + 边缘Agent8000 | 三轮测试 15/15 + 12/12 + 15/15 PASS，fm_core.db + FAISS 索引哈希锁定 |
| 融合算子 | `00_KERNEL/metalaws/META-FUSION-MULTIAGENT-001_*.json` | 已注册（17→18条），phase=proposed_for_adoption，未部署 |
| 种子真值 | `experience/truth-core/SEED-MULTIAGENT-BENCH-WRITE-20261021.json` | 11条云端回执 seq 23064–23074 |
| 对外技术观察报告 | `04_PROJECTS/技术报告/技术观察报告-多Agent体系对标-Hindsight-TeamAI-V1.0.md` | KD-ALGO-9912（M1/Lv8）锁档 |

**核心缺口**：SFMP 解决了「联邦汇聚」（去重/仲裁/分层/检索），但节点端仍是简单写入，缺少 Hindsight 式
**结构化记忆抽取与反思**（retain/recall/reflect + 证据信念）；Hindsight 解决单节点记忆，但**不做分布式冲突裁决**。
二者恰好互补——融合即补齐「单节点记忆质量 × 联邦汇聚治理」的完整闭环。

---

## 二、融合映射（两套四层的对齐关系）

| Hindsight（节点层 L-A） | SFMP（联邦层） | 对齐动作 |
|---|---|---|
| World facts 世界事实 | truth 真值沉淀 | retain 抽取的事实经幻觉校验后入 truth 层 |
| Experiences 经验 | long 长期 | 经验条目带来源节点与置信度入 long |
| Observations 带证据信念（增量精炼不覆盖） | short/long + 冲突留痕 | 证据计数对接 SFMP 置信度仲裁；精炼≠覆盖，冲突走留痕 |
| Mental models 顶层固化零检索直读 | truth（只读缓存位） | **R1 风险**：加过期/失效标记，禁止直读用于高频动态业务 |
| recall 四路并行检索 | 统一检索（关键词/标签/节点/层级+热度） | SFMP 检索作为 recall 的召回通道之一 |
| reflect 深度自省 | 联邦汇聚 merge/仲裁 | reflect 产出上汇 FederatedMemoryPool；跨节点冲突仍由联邦层（CRDT/置信度+时间）裁决，**节点不自裁** |

幻觉校验（L-D）三植入点同时压在两侧接口上：**retain 写入前**（入池前拦）、**recall 检索过滤**（出池前滤）、**输出后自审**（交付前审）。

---

## 三、三阶段最优稳态路径

### P1 单节点试装（不动联邦裁决）
1. 在 SFMP `MemoryPool` 节点端试装 Hindsight 三算子语义（标签化 retain、检索 recall、反思 reflect），保持纯标准库零成本口径
2. 记忆条目升级为「带证据 Observations」结构（证据计数字段）
3. 产出与 46→14 基线对照，验证去重率不回退
4. **先锁档（链块+总账）再推进**

### P2 分层映射 + 幻觉校验植入
1. 落实上表四层映射，truth/long 层写入路径嵌入「retain 写前校验」
2. SFMP 检索出口嵌入「recall 结果过滤」，报告与交付链路嵌入「输出后自审」
3. Mental models 位增加过期/失效标记（**R1 缓解**）
4. 与 `META-ISO-051` 内外隔离/证据溯源/结果自审对齐核验

### P3 联邦闭环 + 调度/资产分层接入
1. 节点产出按既有通道上汇 `FederatedMemoryPool`，冲突清单留痕可审计
2. Organizer 固化 Skill/Subagent 路由（轻能力→Skill；长流程→Subagent 摘要回传，**R3 缓解**）
3. Agent skill/MCP/元规则/Prompt 托管 AtomGit + TeamAI 拉取、变更走 PR（**R2 缓解**：动态记忆仍归联邦网关，TeamAI 只管静态资产）
4. 每阶段部署动作**人工审批**后执行

---

## 四、稳态判据（达成即锁定该阶段）

- P1：节点端记忆带证据结构化，去重率 ≥ 基线 70%，零第三方依赖
- P2：幻觉校验三植入点 3/3 就位，Mental Model 过期标记生效
- P3：跨节点冲突 100% 走联邦仲裁留痕（节点零自裁），Organizer 路由与 PR 资产流全通
- 全程：六条禁止类刚性规则零违反（见 META-FUSION-MULTIAGENT-001）

## 五、立即执行项

- [ ] P1 试装方案走人工审批（未审批不动内核）
- [ ] P1 审批通过后：SFMP 节点端三算子试装 + 证据字段扩展
- [ ] P1 产出对照 46→14 基线并锁档
- [ ] P2/P3 按阶段门推进，每阶段先锁档再推进

---

主节点hub-central-agent / DID-BR-000002 / 锚定Ω₀⊂⊙∞⊂Ω / 部署人工审批
