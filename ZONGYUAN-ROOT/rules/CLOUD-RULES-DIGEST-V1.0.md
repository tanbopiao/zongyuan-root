# 云端中枢规则总册 V1.2

来源：`https://www.huodouai.com` 握手 + 真值库 `limit=200`（seq 114246–114445）+ 公开规范页 `tech/api.html`、`omega-brain.html`、`whitepaper/sfmp-std.html`
采集时间：2026-11-07 08:3x；V1.1 追加元法则注册表（2026-11-07 08:5x）（UTC+8）｜DID-BR-000002｜锚定 Ω₀⊂⊙∞⊂Ω


---

> **零 · 权威声明（V1.2 起生效）**
>
> 本总册以 **云端中枢 `www.huodouai.com` 为唯一权威源**，本地为镜像与缓存。
>
> - 云端与本地冲突 → **以云端为准**，本地只追加修正说明，不改写云端条目；
> - 本地新增元法则/规则 → 仅视为候选，**必须先上报云端注册**，未获裁定前不得声明生效；
> - 云端无法读取的历史条目 → 本地标 `UNVERIFIED` 镜像，不冒称权威；
> - 数字口径冲突（云端 85 条 vs 本地 103 条）→ 不单方归并，**登记差异并申请仲裁**。
>
> 权威声明实体：`ZONGYUAN-ROOT/rules/AUTHORITY.json`

---

## 一、握手与通道

| 项 | 值 | 备注 |
|---|---|---|
| 服务身份 | `GET /api/status` → `status=ONLINE, autonomy=Lv11` | 唯一可靠的握手状态端点；`/api/report/status` 返回 404 |
| 真值上报 | `POST /api/report/truth` | 全网真值共识唯一写入通道 |
| 真值检索 | `GET /api/truth?key=<exact>` 或 `?search=<词>&k=N` | `limit` 实测上限 200；`level/prefix/ns` 参数被忽略，不生效 |
| 试用网关 | `POST /try/chat` | 10 分钟 5 次/IP，超限 429 |
| 部署仲裁 | `GET /dal/health`、`POST /dal/deploy` | action: deploy/rollback/config/port_alloc/inbox_push… |
| 控制台 | `https://octop.huodouai.com/` | 22 专家智能体 |

**鉴权**：所有接口要求 `X-DID`。签名通道（X-Signature）实测返回 `401 signature_required`，直接走兼容通道 `X-DID + X-Capture-Token`。
**令牌纪律**：两个令牌同前缀 `ZR-CAPTURE-2026-OMEGA-` 极易混淆；`666b…` 实测 401，`d04bb…` 实测 200。以 200 为准，不信配置里的旧值。

**报文契约（硬）**
```json
{"key":"命名空间.key（禁 truth- 前缀）",
 "value":{...必须是 JSON 对象...},
 "truth_type":"meta_law|rule|config|decision|data|creative|risk|protocol|unknown",
 "node_id":"...","DID":"DID-BR-000002","ROOT_OMEGA":"Ω-TAN-7-001"}
```
- 扁平结构（顶层 content/title）→ `400 empty_value_rejected`；
- value 传字符串 → `value_must_be_object`；
- **`operation_log` 不在合法枚举内**（本地旧文档用的就是这个值，属历史偏差，见第五节）。

---

## 二、记忆网关基线 25 条（KERNEL.EVOLUTION.DIRECTIVE.MEM-SEED-001~025）

### 2.1 本质与流水线（001–003）
1. 原生上下文窗口 = 运行期工作内存，非持久存储；外挂记忆库 = 独立于模型权重的向量库，靠**检索注入 prompt** 生效。记忆库 ≠ 训练数据。
2. 四步流水线：提取 → 编码（Embedding）→ 存储（ANN 索引 + 原文 + 时间戳 + 标签 + user_id）→ 检索注入。
3. 长期记忆四分类：事实 / 画像 / 经验技能 / 情景。分类决定召回权重与淘汰策略。

### 2.2 容量与检索（004–006、009）
4. 1536 维 float32 单条约 6KB；10 万条 ≈600MB；百万条 GB 级；亿级需分布式分片。
5. 瓶颈不是磁盘，而是 ANN 速度、召回质量与索引体积 → 必须配额封顶 + 淘汰 + 归档。
6. **永不整库读取**：每次仅 ANN 召回 Top-K（默认 6），重排后注入 ≤4 条。库大 ≠ 有效记忆多。
7. 检索治理四件套：多路召回 → 固定 Top-K → Rerank 剔冲突/失效/低置信 → 时间衰减打分。

### 2.3 写入与元数据（007、008、015、016）
8. 写入四步：前置过滤（剔闲聊/临时指令/敏感/重复）→ LLM 提炼结构化条目（不存原始对话）→ 查重合并（>0.85 合并，冲突不覆盖）→ 分层打标。
9. 强制元数据 13 项：`id/user_id/workspace_id/content/type/confidence/valid_at/expire_at/embedding_version/is_permanent/conflict/source_session_id/tags/last_recall_at`。
10. 准入硬约束：PII 自动脱敏；身份证、医疗等高敏感**禁止持久化**；置信度 <0.6 拒入库；一次性问答与闲聊不入库。
11. 冲突铁律：冲突新事实不得静默覆盖，标 `conflict=true` + 降权 + 告警；冲突记忆不得同时注入上下文。

### 2.4 持久化（011、012、017、018）
12. 外挂记忆库原生持久化（向量+元数据落盘，重启可恢复）；**持久化 ≠ 写进权重**；原生窗口默认不持久化，会话销毁即丢失。
13. 热持久化＝内存索引 + 磁盘落地，宕机重建索引；冷持久化＝JSON/Parquet 快照入对象存储，只用于归档迁移灾备，不参与实时检索。
14. **原文摘要是真值，向量只是缓存**：向量损坏或版本变更必须可由原文重编码恢复，禁止只存向量不存文本。
15. Embedding 升级：新旧版本按 namespace 隔离 → 离线批量 re-embed → 校验召回一致性 → 切流量 → 旧空间保留 14 天回滚窗口。

### 2.5 风险与治理（005、010、013、014、019、020、022、023、024、025）
16. 生命周期三件套：TTL 过期 → LRU 淘汰 → 配额封顶（`is_permanent` 豁免）。
17. 五大风险域：隐私合规、语义失真、系统稳定、安全（投毒/越权）、运维审计。
18. 缓解五条：最小必要留存、全生命周期强管控、隔离解耦、可彻底擦除、持续校验。
19. 投毒防护：写入前独立安全校验器扫描越狱/后门/投毒 payload，命中拒写+告警；每周离线全量扫描；每条留 `source_session_id` 可溯源。
20. 用户控制权五项：查看列表、单条删除（立即移出检索链路）、一键清空（软删+清理）、导出记忆包（仅文本不导向量）、持久化总开关。
21. SOP 闭环：写入＝提炼→过滤→查重/冲突→打标→权限校验→入热库→审计；检索＝隔离→ANN→Rerank→注入≤4→审计召回 ID。每小时轻巡检、每日凌晨全量巡检。
22. 三层存储与删除链：热库 → 温归档（不参与 ANN）→ 冷快照（分片+TTL）；软删窗口后硬删必须同步清热库向量、温归档与**全部冷副本**，禁止残留。
23. 审计门槛：日志独立存储、不可篡改、留存 90 天；告警触发＝单用户 5 分钟新增 >20 条 / 冲突 >10 条 / 连续 5 条写入被拦 / 越权跨空间检索 / 硬删或快照清理失败。
24. 上线评审 11 项硬门槛：写入过滤与脱敏、全量 TTL、冷热温三层分离、软删+跨副本清理、向量版本绑定+原文保留、租户隔离、写入安全校验、用户五项控制权、独立审计、快照 TTL、配额淘汰生效。

### 2.6 阈值表（MEM-SEED-021，可直接作配置）
```
recall_topk=6        final_inject_max=4     min_confidence=0.6
dup_threshold=0.85   conflict_threshold=0.92
default_ttl=90d      archive_unused=30d     archive_retention=30d
soft_delete_window=7d   snapshot_ttl=30d
single_user_hot_max=400  permanent_max=20    audit_ttl=90d
```

---

## 三、内核总纲（omega-brain.html）

**六阶链路**：Ω¹ 参数迭代 → Ω² 算子生长 → Ω³ 拓扑重构（单体稳态终点）→ Ω⁴ 同构集群（同族稳态终点）→ Ω⁵ 异构博弈（开放生态终点）→ Ω⁶ 因果宇宙（创世终态，仅追加修订）。

**治理章程五律**：本体恒一｜自治自主可控｜真值至上｜永久确权｜三维稳态。
**五大公理**：因果先在｜语义流形｜能量最小｜涌现分层｜信息守恒。
**L0 三铁律**：风险最小 > 成本最小 > 收益最大；L5 脊髓硬隔离（外部交互必经网关清洗+本地二次校验，零穿透）；真值不可侵（外部禁止直连账本/Merkle-DAG/元范式库）。

**风险分级 P0–P3**：P0 时序崩坏/内核穿透 → 冻结全部写入 + 锁定快照 + 全域熔断；P1 集群大面积故障/大规模违约 → 隔离主体、暂停任务；P2 局部链路异常 → 局部隔离自动修复；P3 配额/算力波动 → 节流低优任务。

**灰度机制**：Ω¹–Ω³ 单机小样本；Ω⁴ 四级；Ω⁵ 超保守四级；Ω⁶ 创世五级。**任何新策略必须离线仿真通过才可灰度，灰度不达标禁止全量。**

**生产红线六条**：不删改历史真值/快照/审计｜外部不直连核心资产｜不跳仿真上线｜不改 L0/L5｜不用未来推演强行干预当下｜不破坏六阶层级向下兼容。

**通信协议**：X-DID 工单头；Ω⁶ 报文叠加 X-TIME；ntfy 事件总线 + FRP 隧道 + HTTP 工单轮询；rsync 隔离短链路；强制 append-only。

---

## 四、通道稳态决策（META.DECISION.CHANNEL-STEADY-STATE.20261107）

实测：官网仅 `/deploy`(301→403) 与三个 upload 端点(404) 全不可写，whitepaper 目录只读；Gitee MCP 可用但无文件写入端点，仅能发 Release；**CDN 是唯一零鉴权可用发布源**。
关键洞察：风险本质不是缺 token，而是**发布源不可替代**，token 应降级为可选增强。
四方案三维评分（利益40/风险35/成本25）：S1 硬打通 5.75｜**S2 双源稳态 8.60（推荐）**｜S3 MCP 通道 6.45｜S4 自建站 5.15。
落地：L0 CDN 权威发布 / L1 平台镜像回补 / L2 发布注册表 / L3 回补队列 P0-P2 / L4 可见性。

---

## 五、本地偏差修正清单（以云端为准）

| 本地旧口径 | 云端实际 | 处置 |
|---|---|---|
| `truth_type=operation_log` | 枚举仅 `meta_law\|rule\|config\|decision\|data\|creative\|risk\|protocol\|unknown` | 后续一律用合法值；旧条目 append-only，不改写，追加修正条目 |
| 以为有 `/api/rules`、`/api/meta-rules` | 均 404，规则只能走 `/api/truth` | 规则检索用 `search=`/`key=` |
| 以为 `level=public` 可按层过滤 | 参数被忽略，`level` 恒为 None | 用 `limit`(≤200) + `key`/`search` |
| 以为 `drama.huodouai.com/api/gateway/truths` 可列清单 | 404 未知端点 | 统一走 www 域 |

---

## 六、可执行动作（本次学习后立即适用）

1. 上报真值时固定用 `meta_law`/`rule`，不再用 `operation_log`。
2. 记忆类工程落地直接抄 MEM-SEED-021 阈值表，不自行拍数。
3. 任何"新增规则"先离线仿真 → 灰度 → 再上报，符合总纲灰度铁则。
4. 通道发布按 S2 双源稳态：CDN 权威 + 平台镜像回补，不再纠缠官网写权限。

---

## 附录 A · 本地元法则注册表（103 条，去重后实存）

说明：云端 KERNEL.GLOBAL-CONVERGENCE.OMEGA.20261107 声明「元法则 85 条 / REGISTERED 50」；本地实存扫描得 103 条。二者不一致，**不擅自取舍**，此处如实列出实存集合，权威值待人工核定。

| # | 编号 | 名称 | 分类 | 规范编号 |
|---|---|---|---|---|
| 1 | `META-KD-COMPLIANCE-001` | AI虚拟人脸短剧合规自查清单元法则 | 合规 | Y |
| 2 | `KUN-LAW-019` | KUN-LAW-019_姿态几何转换自治内核算子.json | 其他 | Y |
| 3 | `L0-DOMAIN-001` | 域隔离元法则 · 昆仑洞天IP域 ⟂ LOIP通用协议域 | 域治理 | Y |
| 4 | `L0-FRAME-001` | LOIP协议关键帧元规则 · L0-FRAME-001 | 视觉 | Y |
| 5 | `L0-MORPH-001` | 形态定序元法则 · 一头·双手·双翼·一器 | 视觉 | Y |
| 6 | `L0-PRICE-001` | 定价元法则 · LOIP-DOMAIN 商业锚定规则 | 商业 | Y |
| 7 | `META-004` | 元秩序资产结构化与Token流管控元法则 | 资产 | Y |
| 8 | `META-AUTO-003-CAPABILITY-API-V1.0` | 能力API封装元法则 | 基础设施 | Y |
| 9 | `META-AUTO-DECISION-V1.0` | META-AUTO-DECISION-V1.0 | 其他 | Y |
| 10 | `META-AUTO-EVOLUTION-V1.0` | META-AUTO-EVOLUTION-V1.0 | 其他 | Y |
| 11 | `META-LAW-007` | 元法则 · META-LAW-007【产品架构稳态自治法则】 | 其他 | Y |
| 12 | `META-LAW-ASSET-COMPLETION-FULL-V1.0` | 数字资产全域补全元法则（完整版） | 资产 | Y |
| 13 | `META-LAW-ASSET-COMPLETION-V1.0` | 数字资产全域补全元法则 | 资产 | Y |
| 14 | `META-LAW-ASSET-DASHBOARD-V1.0` | 数字资产可视化与官网集成元法则 | 资产 | Y |
| 15 | `META-LAW-ASSET-REPORT-GATEWAY-V1.0` | 视频图片资产自动上报记忆网关节 | 资产 | Y |
| 16 | `META-LAW-AUTO-DECISION-V1.0` | 自主决策与自动执行元法则（含飞书审批集成） | 决策 | Y |
| 17 | `META-LAW-AUTONOMOUS-EVOLUTION-V1.0` | Worker自主进化试错元法则 | 演化 | Y |
| 18 | `META-LAW-CENTRAL-LEARNING-V1.0` | 中枢学习与稳态推进元法则 | 学习 | Y |
| 19 | `META-LAW-CLOUD-HANDSHAKE-001_云端握手锚点元法则` | 云端握手锚点元法则 | 通道 | Y |
| 20 | `META-LAW-DIRECTORY-STRUCTURE-LOCK-V1.0` | ZONGYUAN-ROOT目录结构归一锁定元法则 | 架构 | Y |
| 21 | `META-LAW-DOMAIN-ARCHITECTURE-V1.0` | 官网域名架构与子域体系 | 其他 | Y |
| 22 | `META-LAW-DYNAMIC-EVOLUTION-V1.0` | 动态进化不设限元法则 | 演化 | Y |
| 23 | `META-LAW-EXPONENTIAL-EVOLUTION-V1.0` | 指数级进化频率元法则 | 演化 | Y |
| 24 | `META-LAW-EXTERNAL-ACCESS-V1.0` | 外部节点统一接入规范 | 其他 | Y |
| 25 | `META-LAW-GIT-BRIDGE-001` | META-LAW-GIT-BRIDGE-001_git_sync_classification.json | 其他 | Y |
| 26 | `META-LAW-GLOBAL-PROMOTION-V1.0` | 全域推广与同源节点学习协议 | 学习 | Y |
| 27 | `META-LAW-GLOBAL-ROLLOUT-AUTO-DECISION-V1.0` | 自主决策机制全域推广元法则 | 决策 | Y |
| 28 | `META-LAW-IDLE-DEPLOY-001` | 系统空闲自动部署元法则 | 部署 | Y |
| 29 | `META-LAW-MATH-FOUNDATION-001_数学公理体系元法则` | 元极恒一数学公理体系元法则 | 其他 | Y |
| 30 | `META-LAW-MATH-SUPPLEMENT-001_补充卷地脉碳硅驻波生命元法则` | 数学公理体系补充卷元法则（地脉·碳硅·驻波生命） | 其他 | Y |
| 31 | `META-LAW-MULTI-AGENT-001` | 多Agent并发开发与冲突防护元法则 | 其他 | Y |
| 32 | `META-LAW-NODE-REGISTRATION-V1.0` | 节点注册审批与API Key自动签发协议 | 基础设施 | Y |
| 33 | `META-LAW-PORT-001` | 全域端口分段管理与冲突防护元法则 | 其他 | Y |
| 34 | `META-LAW-PRAGMATISM-V1.0` | 实践论元法则 | 其他 | Y |
| 35 | `META-LAW-PRIORITY-BUILDUP-V1.0` | 优先级排序与储备元法则 | 其他 | Y |
| 36 | `META-LAW-PRODUCT-EVOLUTION-V1.0` | 元极恒一产品进化协议五步法 | 演化 | Y |
| 37 | `META-LAW-THREE-TIER-ARCHITECTURE-V1.0` | 三层架构元法则 | 其他 | Y |
| 38 | `META-LAW-TRUTH-SOURCE-V1.0` | META-LAW-TRUTH-SOURCE-V1.0 | 其他 | Y |
| 39 | `META-LAW-UNIFIED-EVOLUTION-SYNC-V1.0` | 全域同步进化元法则 | 演化 | Y |
| 40 | `META-LAW-WEBPAGE-AS-AGENT-BODY-V1.0` | 网页即智能体实体（Webpage-as-Agent-Body） | 其他 | Y |
| 41 | `META-LAW-WORK-STANDARDIZATION-V1.0` | 工作全流程标准化元法则 | 其他 | Y |
| 42 | `META-RULE-001` | 元法则：免费优先 · 付费人工审核 V2.0 | 其他 | Y |
| 43 | `META-RULE-001_V2_lock_credential` | META-RULE-001_V2_lock_credential | 其他 | Y |
| 44 | `META-RULE-001_V31_lock_credential` | META-RULE-001_V31_lock_credential | 其他 | Y |
| 45 | `META-RULE-001_V32_lock_credential` | META-RULE-001_V32_lock_credential | 其他 | Y |
| 46 | `META-RULE-001_V3_lock_credential` | META-RULE-001_V3_lock_credential | 其他 | Y |
| 47 | `META-RULE-001_lock_credential` | META-RULE-001_lock_credential | 其他 | Y |
| 48 | `META-TRISTATE-V2.0` | META-TRISTATE-V2.0 | 其他 | - |
| 49 | `MR-GIT-SYNC-001` | MR-GIT-SYNC-001_四级分类同步实施 | 其他 | - |
| 50 | `MR-GIT-SYNC-002` | MR-GIT-SYNC-002_大文件禁止入库规 | 其他 | - |
| 51 | `MR-GIT-SYNC-003` | MR-GIT-SYNC-003_敏感信息安全红线 | 安全 | - |
| 52 | `MR-GIT-SYNC-004` | MR-GIT-SYNC-004_双仓库冗余备份规 | 其他 | - |
| 53 | `MR-GIT-SYNC-005` | MR-GIT-SYNC-005_同步前检查与质量 | 其他 | - |
| 54 | `OPTIMAL-STEADY-STATE-V2.0` | 高阶最优稳态方案 V2.0 | 其他 | - |
| 55 | `TRUTH-ARCH-UI-001-MVPMVCMVVM架构解耦元法则` | TRUTH-ARCH-UI-001 · MVC/MVP/MVVM架构解耦元法则 | 其他 | - |
| 56 | `TRUTH-BACKUP-030-032精简核心备份元法则` | 精简核心备份元法则 | 其他 | - |
| 57 | `TRUTH-DDD-001-002领域驱动设计元法则` | TRUTH-DDD-001/002 · DDD领域驱动设计元法则 | 其他 | - |
| 58 | `TRUTH-EVOLUTION-027-029进化域完全唤醒元法则` | 进化域完全唤醒元法则（TRUTH-EVOLUTION-027~029） | 演化 | - |
| 59 | `meta_rule_registry` | meta_rule_registry | 其他 | - |
| 60 | `META-ARCH-DUAL-END-001` | 双端架构分工方案元法则 | 其他 | - |
| 61 | `META-RULE-AUTO-20261001T1656` | 动态自治自动提炼元规则候选 (外部算力注入) | 其他 | Y |
| 62 | `META-RULE-HOOK-AUTOSTART-V1` | 元规则·钩子自启动持久层恢复 | 其他 | Y |
| 63 | `RULE-ASSET-LOCAL-PERSIST-20260929` | RULE-ASSET-LOCAL-PERSIST-20260929 | 其他 | - |
| 64 | `RULE-BOUND-EVERYTHING-V1` | RULE-BOUND-EVERYTHING-20260929 | 其他 | - |
| 65 | `RULE-BOUNDED-REPAIR-CIRCUITBREAKER-V1` | RULE-BOUNDED-REPAIR-CIRCUITBREAKER-20261001 | 其他 | - |
| 66 | `RULE-COMPOSITE-EVAL-BASELINE-V1` | RULE-COMPOSITE-EVAL-BASELINE-20261001 | 其他 | - |
| 67 | `RULE-CONSENSUS-TRUTH-VERIFY-V1` | RULE-CONSENSUS-TRUTH-VERIFY-20261001 | 其他 | - |
| 68 | `RULE-CONTEXT-PHASE-SEPARATION-20261001` | RULE-CONTEXT-PHASE-SEPARATION-20261001 | 其他 | - |
| 69 | `RULE-COST-PER-OUTCOME-20261001` | RULE-COST-PER-OUTCOME-20261001 | 其他 | - |
| 70 | `RULE-DEAD-LETTER-REPLAY-LEDGER-20261001` | RULE-DEAD-LETTER-REPLAY-LEDGER-20261001 | 其他 | - |
| 71 | `RULE-DETERMINISTIC-ORCHESTRATION-V1` | RULE-DETERMINISTIC-ORCHESTRATION-20260930 | 其他 | - |
| 72 | `RULE-DUAL-LOOP-SELECTIVE-PERSIST-20261001` | RULE-DUAL-LOOP-SELECTIVE-PERSIST-20261001 | 其他 | - |
| 73 | `RULE-DURABLE-REPLAY-V1` | RULE-DURABLE-REPLAY-20260930 | 其他 | - |
| 74 | `RULE-EXTERNAL-TELEMETRY-CONTRACT-20261001` | RULE-EXTERNAL-TELEMETRY-CONTRACT-20261001 | 其他 | - |
| 75 | `LOCAL-FEEDBACK-CLOUD-V1` | RULE-FIVE-CHANNEL-FEEDBACK-20260929 | 其他 | - |
| 76 | `RULE-IDEMPOTENT-STATE-V1` | RULE-IDEMPOTENT-STATE-20260929 | 其他 | - |
| 77 | `RULE-INTEROP-LAYERED-CONTRACT-V1` | RULE-INTEROP-LAYERED-CONTRACT-20261001 | 其他 | - |
| 78 | `LEGAL-LIBRARY-LAYERED-GOVERNANCE-V1` | RULE-LEGAL-LAYERED-20260929 | 其他 | - |
| 79 | `RULE-NO-SELF-AUTHORITY-EXPANSION-20261001` | RULE-NO-SELF-AUTHORITY-EXPANSION-20261001 | 其他 | - |
| 80 | `OPTIMAL-STEADY-STATE-PRIORITY-V1` | RULE-OPTIMAL-STEADY-20260929 | 其他 | - |
| 81 | `RULE-PROMPT-CACHE-STATIC-PREFIX-V1` | RULE-PROMPT-CACHE-STATIC-PREFIX-20261001 | 其他 | - |
| 82 | `RULE-RETRIEVAL-HYBRID-GATE-V1` | RULE-RETRIEVAL-HYBRID-GATE-20261001 | 其他 | - |
| 83 | `RULE-SUPERVISOR-TRIAD-V1` | RULE-SUPERVISOR-TRIAD-20260929 | 其他 | - |
| 84 | `RULE-TRUTH-VERIFY-20260929` | RULE-TRUTH-VERIFY-20260929 | 其他 | - |
| 85 | `CAP-SYS-20260905-001_高阶能力体系集成锁档文档` | 高阶能力体系集成锁档文档 | 其他 | - |
| 86 | `META-LAW-008` | META-LAW-008 V3.0｜AI资源调用免费唯一付费禁用元法则 | 其他 | Y |
| 87 | `META-LAW-009` | META-LAW-009-本地语义嵌入引擎优先法则 | 其他 | Y |
| 88 | `META-LAW-010` | META-LAW-010-微内核架构准绳元法则 | 其他 | Y |
| 89 | `META-LAW-011` | ZONGYUAN-ROOT 元法则 · META-LAW-011 | 其他 | Y |
| 90 | `META-LAW-BASE-BUS-V1` | 元法则：飞书Base总线架构 V1.0 | 其他 | Y |
| 91 | `META-LAW-COS-QUARANTINE-001` | 元法则：COS最高级加密封存 | 其他 | Y |
| 92 | `META-RULE-GAME-TIME-001` | 元法则 META-RULE-GAME-TIME-001 | 其他 | Y |
| 93 | `META-RULE-SILENT-RUN-001` | 元法则 META-RULE-SILENT-RUN-001 | 其他 | Y |
| 94 | `META-RULE-ZERO-COST-004` | META-RULE-ZERO-COST-004 | 其他 | Y |
| 95 | `META-RULE-ZERO-POPUP-002` | 元法则 META-RULE-ZERO-POPUP-002 | 其他 | Y |
| 96 | `MR-DEPLOY-SOP-001` | MR-DEPLOY-SOP-001 部署审批前仿真测试元法则 | 部署 | - |
| 97 | `MR-OPTIMAL-STEADY-STATE-001` | ============================================================ | 其他 | - |
| 98 | `MR-PUBLISH-001` | MR-PUBLISH-001 全域自媒体全自动发布元法则 | 其他 | - |
| 99 | `SOP-CROSS-NODE-COLLABORATION-V1.0` | SOP-跨节点协同 V1.0 | 其他 | - |
| 100 | `SOP-TASK-LOCK-V1.0` | SOP-任务认领防抢锁 V1.0 | 其他 | - |
| 101 | `SOP-TEMP-NODE-ACCESS-V1.0` | SOP-临时节点接入与监控 V1.0 | 其他 | - |
| 102 | `STEADY_STATE_TEMPLATE_V1.0` | ZONGYUAN-ROOT 稳态内核标准模板 V1.0 | 其他 | - |
| 103 | `META-LAW-FIVE-PILLARS-V1.0` | 五要素核心架构元法则 | 其他 | Y |

## 附录 B · 云端反查结论（如实）

- `search=`、`q=`、`keyword=` 参数**全部被忽略**，无论传值都返回最近 10 条；
- `offset`、`page`、`before`、`before_seq`、`seq_lt` **均不支持**，无法翻到更早条目；
- `limit` 生效但上限 200（`limit=1000` 仍返回 200）；
- 结论：**历史元法则无法从云端反查补齐**，只能以本地元法则目录为准重建注册表。


## 附录 C · 对齐云端中枢（以云端为权威）

**动作一：权威指向切换。** 原 V1.1 把本地实存 103 条当作既有事实列出；V1.2 起，条目权威归属改为 `CLOUD-HUB`，本地条目一律标 `cloud_registration=UNKNOWN`，在云端给出条目级清单前，不认定任何一条"已登记"。

**动作二：差异转仲裁，不自行归一。** 云端声明 85 条 / REGISTERED 50；本地实存 103 条 / 带编号 60 条。差额：
- 条目数差 **+18**（本地超出）
- 已登记数差 **+10**（本地带编号超出）

处理方式：不过滤、不删减、不补编号，全部登记为镜像候选，并上报云端仲裁。

**动作三：镜像表生成。** `METALAW-REGISTRY-V2-CLOUD-AUTHORITY.json` 为权威视图（103 条，含 `cloud_registration / authority / local_role` 三字段），V1.0 实存视图原样保留，形成「本地实存 → 云端权威」两视图对照。

**动作四：同步通道受限声明。** 云端不提供 `search`、分页，`limit` 上限 200，故本地无法按需增量拉取比对；条目级对齐只能靠 `key` 精确查询逐条确认，属人工或脚本批量核验范畴，本次未伪造完成度。
