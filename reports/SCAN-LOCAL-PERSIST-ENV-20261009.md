# 本地持久层与实例环境配置扫描报告

> 扫描时间：2026-10-09 ｜ 执行：NODE-DEV-CODEARTS-001 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
> 范围：zongyuan-root-sync 仓库克隆（本实例 /workspace/zongyuan-root-sync，branch main @7be9ff5）
> 依据铁律：数量=find实测，大小=du实测，报告与命令一致

---

## 一、本地持久层盘点

| 模块 | 路径 | 实测大小 | 实测文件数 | 说明 |
|---|---|---|---|---|
| 数据湖持久层 | `DATA-LAKE-PERSIST/` | 1.5M | 10 | 03-index/MANIFEST-LAKE.json、04-media-registry/MEDIA-REGISTRY-V2.json、05-ledger/BINDING-LAKE-ACCOUNT.json、scripts/auto_archive_hook.py |
| 真值持久层 | `meta_truth/persist/` | 7.1M | 3 | CLOUD-TRUTH-FULL-20261009.json（云端全量 4234 条）、doubao_account_persist.json(+bak) |
| 持久层归档 | `持久层归档/` | 136M | 126 | 媒体关键帧：CLL红裙-红裙夜景国风关键帧、苗族红纱婚纱关键帧（媒体资产） |
| 运行时快照 | `persist_snapshot/` | 48K | 6 | 快照清单 |
| 记忆索引 | `memory_index.json` | 428K | 1 | 全局记忆索引（436K 级） |
| 哈希链账本 | `HASH-LEDGER.csv` | 60K | 1 | 历史与增量哈希链（含本次构建前记录） |
| 内核快照 | `00_KERNEL/snapshots/` | 128K | 6 | kernel_state V4.0-FULLPOWER-KG、LOCK_V2.0_FUSED、omega_brain_index |
| 内核快照(隐藏) | `.kernel_snapshots/` | 8.0K | 1 | 快照 |
| 自愈备份 | `.healing_backups/` | 56K | 4 | 自愈引擎备份 |

**持久层合计：约 145MB / 158 文件**（不含 memory_index/HASH-LEDGER 单体文件）。

## 二、实例环境配置盘点

### 2.1 代码托管远端
- `origin` → https://atomgit.com/zongyuangen/zongyuan-root-sync.git（**仅此一个 remote**）

### 2.2 服务托管配置（supervisord.zongyuan.conf）
共定义 **7 个 program**，全部指向云端实例路径（本实例不可见）：

| program | command 要点 |
|---|---|
| zongyuan-memory-gateway | /opt/python3.12/bin/python3 /home/user/ZONGYUAN-ROOT/memory_gateway.py |
| zongyuan-vector-server | ai-native-ops/vector_server.py |
| zongyuan-ance-api | ai-native-ops/api_server.py |
| zongyuan-monitor | ai-native-ops/monitor_server.py |
| zongyuan-truth-watchdog | scripts/local_truth_watchdog.py |
| zongyuan-monitor-daemon | zongyuan_monitor.py --daemon |
| zongyuan-truth-reconcile | scripts/truth_vector_reconcile.py --daemon |

> ⚠️ 云端基准目录 `/home/user/ZONGYUAN-ROOT`，本实例克隆在 `/workspace/zongyuan-root-sync`，两实例路径不一致（引用时有别）。

### 2.3 LLM 按需算力配置（config/llm_on_demand_config.json）
- 监听：`127.0.0.1:8777`；backend=ollama；model=qwen2.5:3b(q4_K_M)
- openai_compat: `127.0.0.1:8080/v1/chat/completions`；idle_timeout=30s；max_context=4096

### 2.4 节点注册配置（config/node_registry.json）
- 主节点：`NN-MASTER-001` 云内核主控 123.207.202.158:8900（capabilities: read/write/sync/evolve/execute/govern）
- 注册节点表 registry_version=1.0.0（更新于 2026-09-12）

### 2.5 环境变量配置（.env.brain 仅列键名，值不入报告）
`DOUBAO_API_BASE/DOUBAO_API_KEY/DOUBAO_CHAT_MODEL/DOUBAO_ENDPOINT_ID`、`HUNYUAN_API_BASE/HUNYUAN_API_KEY`、`ZHIPU_API_BASE/ZHIPU_API_KEY`、`VECTOR_BACKEND/CHROMA_PATH/EMBEDDING_DIM/EMBEDDING_MODEL`、`BRAIN_RECALL_K/BRAIN_THRESHOLD`

### 2.6 config/ 目录（63 文件）
UNI-STEADY-CORE-V1.0(.json/.md)、node_registry、task_registry、paid_api_registry、control_commands、self_learning_state、api_audit_log、truth_refinement_log、meta_laws/META-RULE-016、meta_constitution/META-CONSTITUTION-001、seed_truths/SEED-20260930-01、ci-cd-config.yaml、upgrade_final_checklist、llm_on_demand_config、v3_architecture_final、server_migration_plan、operator_hub_windows 等。

### 2.7 状态/凭证类文件（不读值，仅盘点）
` .auth_credentials`(177B)、`.cos_sync_state.json`(157KB 同步状态)、`.global_root_registry.json`(v7 根注册台账)、`.env.brain`(794B)

### 2.8 本地服务端口分布（仓库代码引用 TOP）
9120(废弃主网关, **145 处引用**) ＞ 8021(53) ＞ 8081(20) ＞ 8070(17) ＞ 8765(16) ＞ 8001(15) ＞ 8017(AIOS v2.1,7) ＞ 8006(kernel_anchor_api,11) ＞ 8000(8+8) ＞ 11434(ollama,7) ＞ 7861(7)

## 三、发现与建议

| # | 发现 | 风险 | 建议 |
|---|---|---|---|
| 1 | **目录收敛违规**：根目录存在大量散建目录（归档/audit_logs/backup_* 等历史遗留） | 中（违反7大类收敛规） | 后续归入 05_ARCHIVE/legacy_duplicates/ |
| 2 | **端口 9120 已废弃**（AGENTS 明言勿重启）但代码引用 145 处 | 低（不会启动） | 后续统一替换/标注 deprecated |
| 3 | **双实例路径不一致**：supervisord 指向 /home/user/ZONGYUAN-ROOT，本实例 /workspace/zongyuan-root-sync | 中（脚本在云端才能跑） | 采用相对仓库根解析或环境变量 |
| 4 | **node_registry 主节点心跳过期**：last_heartbeat=2026-09-07（32天未见活） | 高（主节点疑似离线） | 重新注册/心跳；当前 NODE-DEV-CODEARTS-001 已补充注册 |
| 5 | 云端真值 4196 条已整库落地 `meta_truth/persist/` | — | 资产地图已确认，无需重复拉取 |

## 四、结论

- 本地持久层完整可用：数据湖/真值/记忆/账本/快照五大类齐备，约 **145MB/158 文件**；
- 实例环境配置以**云端基准**编写（/home/user/ZONGYUAN-ROOT + 8K 级端口簇），本实例为只读工作副本；
- 最高优先动作：**确认 hub-central-agent 主节点存活**，其次清理 9120 引用与散建目录。