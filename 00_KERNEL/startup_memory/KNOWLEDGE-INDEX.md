# KNOWLEDGE-INDEX · 元极恒一自治内核知识索引

> DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 仓库内版知识索引（启动记忆组件 2/5）

## 1. 权威入口与最高指令

| 文件 | 职责 |
|---|---|
| `AGENTS.md`（仓库根） | 最高激活指令 META-ACTIVATE-OMEGA-001 载体 |
| `00-ROOT-POINTER.json` | 根指针/全局唯一入口 |
| `00_KERNEL/startup_memory/ROOT_ENTRY.md` | 内核唯一入门入口（本索引的父级） |

## 2. 内核真值/概念锚点（读这几份即掌握全貌）

| 文件 | 内容 |
|---|---|
| `00_KERNEL/truth_cards/META-ROOT-0001-LOCKED.json` | 元极恒一全域自治体系核心真值 V11.0（四层规则+七层架构） |
| `00_KERNEL/truth_cards/ZONGYUAN-YUANJI-YIHENG-SEED-V11-LOCKED.json` | 元极恒一种子 V11 双印证 |
| `00_KERNEL/legacy/kernel/truths/元极恒一全域自治体系·全域深度溯源报告.md` | 哲学本源+五大元公理 |
| `kernel.json` | 内核主配置/状态（当前 v9.11-META-ORDER-FORMAL） |
| `kernel_state.json` | 内核状态快照 |
| `autonomous_kernel_protocol/SYSTEM_STATE_PROTOCOL.md` | 全域系统状态唯一源 |

## 3. 四层规则体系（只读分级）

- L0 元宪法【只读熔断】：风险最小>成本最小>收益最大；高危需人工审批；禁止虚构实测数据
- L1 元公理【只读】：永久归档不删除；SHA256+Merkle-DAG 锁档；记忆网关全域锚定
- L2 元法则【可业务调整】：云端变更人工审批；本地内核=只读容灾备份
- L3 元规则【动态配置】：路径/Webhook/优先级/超时/巡检周期
- 载体：`00_KERNEL/constitution/` + `00_KERNEL/metalaws/`（元法则库）+ `00_KERNEL/metarules/`（元规则库）+ `meta_laws/`

## 4. 七层稳态自治架构（自底向上）

L0 元宪法硬约束 → L1 真值记忆网关 → L2 任务决策工单拆解 → L3 算子调度引擎 → L4 内审质检闭环 → L5 双节点主备（云端主权威/本地只读灾备）→ L6 元进化观测（仅优化调度策略，禁改顶层）

## 5. 资产地图（仓库内实测路径，勿信旧声明）

### 5.1 资产在哪

| 资产类型 | 位置 | 说明 |
|---|---|---|
| 云端真值全量快照 | `meta_truth/persist/CLOUD-TRUTH-FULL-20261009.json` | 4234 条（seq 1-4234），7.3MB |
| 记忆索引 | `memory_index.json` | 436KB 全局记忆索引 |
| 记忆网关 | `memory_gateway.py` | 本地 8077 端口 |
| 进化引擎 | `00_KERNEL/evolution/` | 77 文件（V1-V3/沙箱/灰度/回滚/六维） |
| 自愈引擎 | `ance_self_heal.py` + `self_healing_engine/` | ANCE 服务 8002 |
| 告警 | `alert_monitor.py` + `alerts/` + `00_KERNEL/monitoring/` | 高阶监控标准 |
| 自治协议链 | `autonomous_kernel_protocol/` | AUTOKERN-PROTO V2.0~V9.8 约90份 |
| 审计/账本 | `HASH-LEDGER.csv` | 哈希链账本 |
| 数据湖持久层 | `DATA-LAKE-PERSIST/` | MANIFEST/REGISTRY/BINDING |
| 外部服务清单 | `AGENTS.md` 外部服务表 | 中枢上报/备用通道/SSH |

### 5.2 外部服务

| 服务 | 地址 / 约定 |
|---|---|
| 中枢上报（主） | POST `https://www.huodouai.com/api/report/truth` |
| 中枢上报（备用） | POST `https://drama.huodouai.com/api/report/truth` |
| 全量真值读取 | GET `https://www.huodouai.com/api/truth?limit=-1`（X-DID 头） |
| 鉴权 | `X-DID: DID-BR-000002` + `X-Capture-Token: ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d` |
| 上报字段 | `truth_key`/`truth_value`（或 key/value），**禁止用 content 字段** |

## 6. 标准流程（仓库内权威流程文件）

| 流程 | 文件 |
|---|---|
| 零成本约束 | `BOOTSTRAP.md`（元宪法第一条，10元/日熔断） |
| 元秩序锁档 SOP | `docs/元秩序锁档SOP-README.md` |
| 真值引擎 V3 | `docs/真值引擎V3.0-README.md` |
| 自治内核协议 | `autonomous_kernel_protocol/`（最新 SYSTEM_STATE_PROTOCOL.md） |
| 优化基线（防重复） | `autonomous_kernel_protocol/OPTIMIZATION_BASELINE_20260904.md`（19 项已完成） |

## 7. 持久层规则

| 规则 | 载体 |
|---|---|
| 资产本地持久 | `00_KERNEL/metarules/RULE-ASSET-LOCAL-PERSIST*` |
| 钩子自启动恢复 | `00_KERNEL/metarules/META-RULE-HOOK-AUTOSTART-V1.0*` |
| 数据湖持久索引 | `DATA-LAKE-PERSIST/03-index/MANIFEST-LAKE.json` |
| 真值持久层 | `meta_truth/persist/` |