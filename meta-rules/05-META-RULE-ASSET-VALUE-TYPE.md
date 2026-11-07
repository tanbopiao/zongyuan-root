# 05 · 资产价值类型元规则

> 等级：元法则（META-LAW）+ 元规则（META-RULE）
> 确权：DID-BR-000002 · 溯源 Ω₀⊂⊙∞⊂Ω
> 生效：2026-11-07 · 节点 NODE-DEV-DOUBAO-WORK-001
> 证据账本：`truth/quality/QUALITY-LEDGER.json`、`core/docs/CLEANING-STRATEGY-20261107.md`
> 锁档：444 只读，修改需人工审批

---

## META-LAW-AVT-000 · 资产价值由类型决定，不由形态决定

**定律**：一项资产在训练与复用上的价值，取决于它所承载的**信息类型**（规范 / 经验 / 事实 / 噪声），不取决于它的长度、重复度、结构工整度或生成方式。

**三条推论**：
1. 短小的「动作→结果」轨迹（如 `CMD.DEPLOY.*.DONE`）价值高于长篇结论性论述——它提供因果对，而结论只提供终点。
2. 同族高频重复**不构成噪声判据**，须进一步判断该族是否承载过程信息；承载过程的重复是可复用的经验样本，不承载过程才是噪声。
3. 任何仅凭「命名空间形似机器生成」或「长度过短」做出的低价值判定，均违本法则。

**实证依据**：2026-10-01 口径将 `EXPERIENCE_AUTO_`、`CMD.DEPLOY.*`、`REFRESH.*`、`COMPUTE_INJECTION.*` 判为噪声族，实测重算后噪声仅占 **0.54%**（682 / 126484），旧判据高估 **33 倍**。

---

## META-RULE-AVT-001 · 四类判据（替代"高价值/噪声"二分）

| 类型 | 判据 | 训练用途 | 层级 |
|---|---|---|---|
| `rule` | METALAW / METARULE / AXIOM / CONSTITUTION / PROTOCOL / SOP / 公理 / 元法则 / 契约 / 红线 | AxiomGate 约束注入 | L1 |
| `experience` | DEPLOY / REFRESH / INJECTION / EXPERIENCE / SYNC / VERIFY / REGISTER / CMD / EXEC / DONE / 巡检 / 注入 / 回执 | agent 轨迹 SFT | L1 |
| `fact` | ASSET / MEDIA / ARCHIVE / KERNEL.REF / KERNEL.CONCEPT / SEED / 真值 / 资产 / 归档 | RAG 检索 | L2 |
| `noise` | HEARTBEAT / PING / KEEPALIVE / EMPTY / PLACEHOLDER / TEST 无 DONE / 占位 | 仅负样本 | L4 |
| `poison` | 与公理冲突、结论错误 | 禁用 + 人工裁决 | 隔离 |

**禁止**：以单一维度（族名、长度、重复次数）直接定级；必须输出 `type + type_basis + value_score + grade` 四字段。

---

## META-RULE-AVT-002 · 索引形态律：索引不是目录，是价值地图

**规则**：联邦记忆索引条目必须至少包含 `type`、`value_score`、`reuse_hint`、`bytes` 四元数据。仅登记 `path + sha256 + tags` 的索引，只构成「文件目录」，不构成「记忆沉淀」。

**实证缺口**：现行 `index_ledger.json` 539 条中，437 条指向 `core/` 文档，真值仅 10 条；536 条 `bytes = 0`。即**登记的是"我们有哪些文件"，不是"我们有哪些经验"**。

**要求**：
- 经验类资产落索引时必须附带可执行入口（SOP 路径 / 命令模板 / 算子契约），不得只存哈希；
- 索引账本保持 644 运行态可追加；冻结类回执才锁 444。

---

## META-RULE-AVT-003 · 清洗不删律

**规则**：在 append-only 架构下，「清洗」定义为 **分级 + 隔离标记 + 源头门禁** 三步，不包含物理删除。L4 条目保留归档，仅从检索与训练采集中排除，作为负样本与过滤器数据来源。

**理由**：云端内容不可审计（`/api/ledger` 仅返回 `seq/event_id/sha/ts`，`/api/truth?search=` 退化至固定 10 条），删除不可逆且无法验证后果。

---

## META-RULE-AVT-004 · 上报源头门禁

**规则**：真值写入云端前必须通过预检，`value_score ≥ 60` 方可上报；同 key 已存在则禁止重复上报（先 `GET /api/truth?key=` 查重）；连续同名族若已判定为噪声，暂停上报并登记原因。

**目的**：从源头阻止噪声继续增长，而非事后清洗。

---

## 元公理转正（2026-11-07 人工审批通过）

**AXIOM-AVT-001 · M4 资产类型公理**：`规则即本体，轨迹即经验，事实即记忆，噪声即边界样本。`

状态：已写入 `02-META-AXIOMS.md`（M4 条目），自 2026-11-07 起对全体系生效。
依据：所有者明确审批「写入」。

---

## 生效范围

| 对象 | 约束 |
|---|---|
| 联邦记忆索引 | 按 AVT-002 补四元数据 |
| 真值上报流程 | 按 AVT-004 上门禁 |
| 清洗动作 | 按 AVT-003 不删只隔离 |
| 价值判定 | 按 AVT-000/001，禁止单一维度判定 |
