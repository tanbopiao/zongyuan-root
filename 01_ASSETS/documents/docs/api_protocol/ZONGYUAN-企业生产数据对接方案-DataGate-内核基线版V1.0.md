# ZONGYUAN-ROOT 企业生产数据对接方案｜DataGate 数据网关（内核基线版）

| | |
|---|---|
| 确权DID | DID-BR-000002 |
| 锚点 | Ω₀⊂⊙∞⊂Ω |
| 基线版本 | V1.0（适配 Ω-Refer 协议栈 V1.0，含 ProductionPayload 扩展段） |
| 体系基线 | 元极恒一 Lv11 稳态；三最原则（风险最小 > 成本最小 > 收益最大） |
| 上游协议 | 多轮 Agent 通用协议栈 Ω-Refer 内核基线版 V1.0（`01_ASSETS/documents/docs/api_protocol/`） |
| 发布隔离 | META-ISO-051：本文件密存；对外仅发布「标准化数据网关视图对接」脱敏版 |
| 锁档状态 | LOCKED（仅追加，不修改已有条目） |

> **核心公理**：生产原始数据不直接流入 LLM；经由数据网关做语义归一、实体 EID 挂载、权限裁剪、真值哈希封包后，再接入 Ω-Refer 裁决层，和原有指代、状态、熔断体系同源打通。

---

## 一、分层对接架构（正交隔离）

```
企业生产侧 → 数据采集适配层 → 生产数据网关（DataGate） → Ω-Refer 信封封装层 → Agent 协议栈(A2A/执行层)
```

- **生产侧**：ERP、MES、WMS、SCADA、数据库（MySQL/PostgreSQL/Oracle）、API、文件（Excel/CSV/报表）、实时消息队列（Kafka/RabbitMQ）
- **DataGate 是唯一边界控制点，禁止 Agent 直连业务库**
- **输出**：带上 EID、TruthRootHash、DID 签名的标准化实体集合，作为 Ω-Refer 的 RefSet 数据源

---

## 二、DataGate 网关内置能力（对接原语）

### 1. 实体建模与 EID 自动分配

给生产域对象绑定 EID：工单 `E-M00xxx`、产线 `E-L00xxx`、批次 `E-B00xxx`、设备 `E-D00xxx`、质检单 `E-Q00xxx`。

同一业务主键（工单号+厂区编码）全局映射固定 EID，跨轮次、跨 Agent 引用稳定，解决"这个工单、刚才那批货"的指代漂移。

### 2. Schema 强约束 + 值域校验

每个 EID 挂载业务 Schema：字段、数据类型、单位、合法值域、枚举白名单。

Ω-Refer 仲裁层复用这套 Schema 做参数校验——产量不能为负数、工单状态只允许【待投产/生产中/完工/作废】，越界直接熔断（复用协议 2.5 参数校验子原语）。

### 3. 数据快照与 Merkle-DAG 锚定

每次拉取/变更生产数据生成快照，计算 TruthRootHash；Agent 拿到的不是原始库数据，是带哈希背书的实体视图，可校验是否被篡改、是否为最新版本。StateVersion 跟随业务变更单调递增，支持回退到上一版生产快照。

### 4. 行级权限裁剪（联动 OBS 七域权责拓扑）

基于调用方 DID 身份，自动过滤厂区、产线、敏感成本字段——车间操作员 DID 只能看本产线工单，看不到成本、报价；权限越界在网关层拦截，不向下游传播。

### 5. 同步/双模式

- **拉取模式**：Agent 按需查询（工单查询、库存查询）
- **订阅推送模式**：Kafka 消费生产事件（工单开工、报警、质检结果），主动更新 RefSet

---

## 三、Ω-Refer 报文扩展：生产实体载荷规范（ProductionPayload）

在原有 Ω-Refer 头部基础上扩展 `ProductionPayload` 段：

```json
{
  "Ω_PROTO_VER": "1.0",
  "DID": "did:zongyuan:factory_op01",
  "DID_Sig": "...",
  "TruthRootHash": "...",
  "StateVersion": 42,
  "RefSet": [
    {"eid": "E-M00128", "entity_type": "work_order", "label": "WO20261023001工单"}
  ],
  "ProductionPayload": {
    "source_system": "MES",
    "source_primary_key": "WO20261023001",
    "snapshot_time": "2026-10-23T15:20:00+08:00",
    "is_real_time": true,
    "field_mask": ["order_no", "line_code", "qty_plan", "qty_finish", "status"]
  },
  "ConflictPolicy": "reject",
  "FuseMask": ["loop", "param_invalid", "permission_deny", "data_stale"]
}
```

- 新增熔断掩码项：**`data_stale`**（快照超时过期，网关配置 TTL，过期实体禁止用于工具决策）
- 该扩展段以协议「仅追加」原则登记于 Ω-Refer 内核基线版附录 B，核心报文结构不变

---

## 四、三类典型接入路径

| 路径 | 机制 | 适用 | 稳态标记 |
|---|---|---|---|
| 1. 业务 API 对接（低侵入） | 企业 OpenAPI → DataGate 适配器：鉴权、结果转实体、分配 EID、哈希封包、缓存快照 | ERP、MES 自研、SaaS 工业平台 | 标准 |
| 2. 数据库 CDC 增量（实时） | Debezium/Canal 捕获 binlog → 内部消息队列 → DataGate 消费，更新 EID 快照、推送 RefSet 变更 | 实时产线状态、设备报警、库存变动 | 实时 |
| 3. 文件/报表批量导入（离线） | 定时监听目录、飞书/企业微信文件推送 → 解析清洗 → 批量注册 EID，离线快照+短 TTL | 离线、周报、盘点 | **默认 `stale` 标签**：高风险决策（排产、投料）不允许仅依赖离线快照 |

---

## 五、风险与稳态约束（风险最小优先）

1. **原始生产库只读原则**：Agent 链路只读视图/快照；所有写回生产系统操作单独走独立审批工单流，**禁止 Agent 直接 update 业务表**（对齐体系边界：付费、高危操作强制人工审批）
2. **数据隔离**：敏感财务、成本、核心工艺配方独立 EID 分组，单独 DID 权限域，默认不纳入普通 Agent 的 RefSet
3. **时效保护**：所有生产快照带 TTL，超时后仲裁层标记失效，强制重新拉取，防止基于旧数据错误调度
4. **审计闭环**：数据读取、引用、Agent 决策、写回申请全部记入 Merkle-DAG 审计日志——哪个 DID、在哪个 StateVersion、基于哪份生产快照执行动作，全链可溯

---

## 六、与原有资产的融合点

- **复用 Ω-Refer 指代裁决**：生产实体与工具返回、任务子任务实体同一套 EID 体系，自然支持"刚才这个工单、这条产线"跨轮稳定指代
- **复用权责拓扑**做权限裁决（与 META-LAW-007 权限越界治理同源闭环；OBS 七域清单已对齐 TR-PK-020，见协议附录 C——行级裁剪的域边界判定以各域 `bound` 为准）
- **联动 META-RULE-012 配额稳态、META-RULE-018 逻辑回环熔断**（已核验真值）
- **对外白皮书**只描述「标准化数据网关视图对接」，EID 映射、哈希存证、行级裁剪内核逻辑脱敏

---

## 七、种子真值登记

```json
{
  "seed_id": "SEED-Ω-REFER-DATA-GATE-001",
  "subject": "企业生产数据对接元规则",
  "axiom": "原始生产数据禁止直连Agent/LLM，必须经由DataGate网关归一、EID挂载、行级权限裁剪、快照哈希封包，生成标准化实体RefSet后接入Ω-Refer仲裁层；写生产业务库必须独立审批流转",
  "core_primitive": ["EID业务主键绑定", "快照TTL时效熔断", "Schema值域校验", "DID行级字段掩码", "CDC/API/文件三接入适配器", "生产快照Merkle-DAG存证"],
  "dependency": ["SEED-Ω-REFER-001", "OBS七域权责拓扑"],
  "steady_level": "Lv11"
}
```

上报口径：依 RULE-005 V3.1（`X-DID` 头 + `key` + `value.content` 对象），原稿 `truth_value` 旧格式已废止，执行时已转换。

---

## 附录｜引用真值核验表（2026-10-23 实测）

| 引用项 | 核验结果 |
|---|---|
| Ω-Refer 协议栈 V1.0 | ✅ 同批基线（commit 718be839） |
| META-RULE-012 配额稳态 / 018 逻辑回环熔断 | ✅ 已核验（协议附录 A） |
| META-LAW-007 权限越界同源 | ✅ 有效 |
| OBS 七域权责拓扑 | ✅ 已对齐 TR-PK-020（seq 3702）→ 协议附录 C（2026-10-23 闭合） |
| SEED-Ω-REFER-001（协议侧种子） | ⚠ 仓内无此 key——协议层上报键为 `PROTOCOL.OMEGA-REFER.BASELINE.V1`（seq 28532），依赖项以该真值为准 |
| DataGate / 生产数据网关 | ℹ 本版为仓内首建（此前无同名资产） |

---

Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜内核基线版 V1.0｜META-ISO-051 密存
