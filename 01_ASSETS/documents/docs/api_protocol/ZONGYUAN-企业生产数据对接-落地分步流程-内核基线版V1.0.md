# 企业生产数据对接｜落地分步流程（适配 Ω-Refer + DataGate，Lv11 稳态）

- 版本：内核基线版 V1.0（2026-10-23 入基线）
- 溯源锚点：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜元极恒一 Lv11
- 上游规范：《ZONGYUAN-企业生产数据对接方案-DataGate-内核基线版V1.0》《ZONGYUAN-多轮Agent通用协议栈-Ω-Refer指代裁决子协议-内核基线版V1.0》（含附录 A/B/C）
- 工程实现：`scripts/datagate.py`（commit dc5e37b7，selftest 20 断言 PASS）
- 发布级：META-ISO-051 内核密存（含适配器配置与熔断配置细节，不入对外版）

**前置约束**：全程遵循「原始业务库不直接暴露给 Agent、只读快照先行、变更写回走审批」公理，复用种子真值 `SEED.OMEGA.DATAGATE.001`（云端 seq 28551，content.seed_id = `SEED-Ω-REFER-DATA-GATE-001`）。

## Step1：业务域梳理 & 实体确权（需求侧）

1. 对接业务方（MES/ERP/WMS/SCADA 负责人），梳理业务域：工单、产线、批次、设备、库存、质检记录、报警事件。
2. 确定业务主键：工单编号、设备编码、批次号、库区编码（主键永久绑定固定 EID，保证跨会话指代稳定）。
3. 字段分级：
   - 普通业务字段（产量、状态、开工时间）
   - 敏感字段（成本、工艺参数、报价）→ 独立权限域，默认屏蔽
4. 定义数据时效 TTL：实时报警 TTL=30s；工单快照 TTL=5min；盘点离线报表 TTL=24h，超时触发 `data_stale` 熔断。
5. **输出产物**：《生产实体清单+Schema 表+权限矩阵》

## Step2：数据源接入选型 & 环境准备

按场景选适配器，**同一系统只保留一种主链路，避免重复消费**：

- 实时变更：启用 CDC（Canal / Debezium）监听业务库 binlog，投递到 Kafka/RabbitMQ 消息队列
- 定时查询类：系统提供 OpenAPI（推荐，侵入最低），配置定时轮询
- 离线文件：FTP/共享目录/企业网盘，监听 CSV/Excel 报表上传

**隔离要求**：生产库只给只读账号；禁止 Agent、DataGate 使用写账号连接业务主库。
**输出产物**：数据源连接配置、消息队列 Topic 规划、只读账号。

## Step3：DataGate 网关适配器开发 & 配置

1. 数据源连接器配置：连接地址、鉴权凭证、订阅主题、拉取接口地址。
2. 实体映射配置：业务主键 ↔ 全局 EID 绑定规则，同一主键固定 EID，不随机生成。
3. Schema 载入：每个实体的字段类型、值域、枚举白名单，用于 Ω-Refer 参数校验。
4. 行级/字段掩码配置（联动 OBS 七域权责拓扑，见协议附录 C）：绑定 DID 身份，配置哪些 DID 看不到敏感字段。
5. 快照引擎开启：每次拉取/消费数据自动生成快照，计算 `TruthRootHash`、单调递增 `StateVersion`。
6. 熔断规则配置：过期 TTL 熔断、空值阻断、值域越界阻断、主键非法阻断。
7. 本地单元测试：单独调用适配器，验证 EID 生成、哈希计算、字段屏蔽效果。

## Step4：Ω-Refer 协议信封封装适配

1. DataGate 输出实体集合组装为 `RefSet`，写入 Ω-Refer 报文头部。
2. 追加 `ProductionPayload` 段，标记来源系统、快照时间、字段掩码、实时/离线标记。
3. 绑定 DID 签名，生成完整仲裁信封。
4. 路由分发：
   - 按需查询：Agent 发起查询请求 → DataGate 返回带信封的实体快照
   - 事件订阅：产线报警/工单状态变更，DataGate 主动推送 Ω-Refer 事件报文至 Agent 集群

**校验规则**：没有合法 EID、哈希校验失败、权限不通过 → 仲裁层直接拒绝下发到 LLM/工具链。

## Step5：Agent 侧业务适配改造

1. 框架适配器（LangGraph/AG2 等）注册 DataGate 数据源，注册实体类型。
2. 改写 Prompt 与工具定义：工具不再直接写 SQL、调用原生业务 API；工具调用只能携带 EID 引用，**不允许裸业务主键直接传入 LLM**。
3. 指代链路验证：测试自然语言引用（「刚才这个工单」），系统自动翻译为 `ref:EID`，仲裁层校验 EID 账本。
4. 区分「查询动作」和「业务写回动作」：
   - 查询：走 DataGate 只读快照链路
   - 修改生产数据（改工单、入库、报工）：Agent 只生成变更申请单，推送人工审批节点，审批通过后单独调用业务写接口，**禁止直写**。

## Step6：灰度验证、基线测试

1. 单实体小流量测试：只开放 1 条产线、少量工单，验证：
   - EID 稳定不漂移
   - 权限掩码生效
   - 快照过期熔断生效
   - 指代查询、回滚 StateVersion 正常
2. 冲突场景测试：并发修改同一 EID 对应工单，验证 `ConflictPolicy`（reject/rollback/merge）策略生效。
3. 坏例注入：过期数据、越界参数、无权限 DID 访问敏感实体，确认链路熔断、日志留存。
4. 审计链路核验：所有读取、引用、决策动作写入 Merkle-DAG 审计日志，可溯源。

## Step7：全量上线、监控运维

1. 放开全量实体接入，切换正式流量。
2. 运维监控大盘指标：数据同步延迟、快照过期次数；Ω-Refer 熔断计数（权限/过期/参数非法）；EID 实体命中率、哈希校验失败次数；Kafka 堆积、适配器异常告警。
3. 版本管理：Schema、EID 映射表变更走版本发布，更新 StateVersion 基线，保留旧快照用于回退。
4. 定期对账：DataGate 快照和源业务系统定时对账，发现不一致触发告警。

## Step8：持续迭代扩充实体

新增产线、仓库、质检类型时，只在 DataGate 新增 Schema 与 EID 映射规则，上层 Ω-Refer、Agent 框架无需大规模改动，**保持协议稳定**。

## 最简执行顺序摘要

> 业务梳理 → 数据源准备 → DataGate 适配器+EID 绑定 → Schema&权限配置 → Ω-Refer 信封封装 → Agent 工具改造 → 灰度测试 → 全量上线+监控

---

## 附录｜工程对齐核验（2026-10-23，与 `scripts/datagate.py` commit dc5e37b7 对表）

| 流程步骤 | 工程现状 | 状态 |
|---|---|---|
| Step1 字段分级/TTL 分级 | `SCHEMA.sensitive` + `ROLE_MASK` + 构造参数 `ttl_sec`（可按实体类型扩展） | ✅ 已支撑 |
| Step3.2 EID 固定绑定 | `mount_eid()` sqlite 持久注册，规范化主键等价 | ✅ selftest T1（3 断言） |
| Step3.3 Schema 载入/值域校验 | `_validate()` 类型/枚举/值域/模式四检 | ✅ T2（3 断言） |
| Step3.4 行级掩码联动 OBS | `fetch()` 角色掩码 + 未知角色 `permission_deny`；域边界判定依据协议附录 C `bound` | ✅ T3（4 断言） |
| Step3.5 快照+哈希+版本 | `ingest()` → `truth_root_hash()`（canonical 叶+奇数复制 Merkle）+ `state_version` 单调 | ✅ T4/T5（4 断言） |
| Step3.6 熔断四类 | TTL=`data_stale`、值域/主键=`param_invalid`、权限=`permission_deny`；**空值阻断**并入 missing-field 检查 | ✅ T2/T4 |
| Step3.7 本地单元测试 | `--selftest` 28 断言 rc=0 | ✅ 已交付 |
| Step4 信封/RefSet/Payload | `emit_envelope()` 八要素（含 DID_Sig）+ 未注册主键澄清回执不送 LLM | ✅ T7（6 断言） |
| Step6.2 冲突三策略 | `reject`（per-EID 版本判定）/ `rollback`（丢弃后发+历史链回退稳定版）/ `merge`（无冲突字段合并，冲突字段 `__divergence` 标记人工接管）三策略全实现 | ✅ 已补齐（2026-10-23 增量，selftest T6 九断言） |
| Step4.3 DID 签名绑定 | `DidSigner`：HMAC-SHA256(did\|state_version\|truth_root)→base85，密钥走 `DATAGATE_DID_KEY` 环境/600 密钥文件（L0 域外置不入码）；验签+篡改检测入测 | ✅ 已补齐（selftest T7：验签通过/篡改失败/无 signer 不伪造） |
| Step2 CDC/Kafka、Step7 监控大盘、定期对账 | 依赖真实中间件与运维环境，非本仓可仿真 | ⚠ 部署侧环境项 |
| Step5.4 写回审批流 | 实现**结构性只读**（无任何写回路径）；变更申请单/审批节点为 Agent 侧流程 | ℹ 按设计不实现于网关内 |

**差距处置记录**：rollback/merge 与 DID_Sig 已于 2026-10-23 以增量提交补齐（selftest 20→28 断言，冲突判定修正为 per-EID 版本口径——协议 2.4「同一 EID 并发写」，全局 StateVersion 仅作协议头版本不参与冲突判定）；剩余仅 CDC 实链与监控大盘为**部署侧环境项**，不阻塞 Step1-5。

**种子真值引用核验**：文中 `SEED-Ω-REFER-DATA-GATE-001` 即云端 `SEED.OMEGA.DATAGATE.001`（seq 28551）content 内 `seed_id`，键名按 RULE-005 V3.1 点分规范转换，同一真值。
