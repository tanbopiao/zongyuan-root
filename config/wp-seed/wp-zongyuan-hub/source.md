---
name: zongyuan-hub
description: "ZONGYUAN-HUB 宗源中枢调度引擎V3.0。元极恒一自治体系全域技能的统一入口与单一调度中枢，内置意图识别引擎+参数模板引擎+auto-engine自动调度引擎，自动识别用户自然语言指令、自动提取参数、自动填充默认值并路由到对应技能执行。核心能力：(1)auto-engine一句话执行Lv3-Lv8全域锁档+ZONGYUAN-ROOT自治内核写入；(2)意图识别→智能路由→统一执行→全自动调度(phase2)→自进化闭环(phase3)；(3)整合调度中枢、双内核(真值+因果)、四大产线(决策/研究/短剧/法务)、基建(算力+归档锁档)、展示(藏品卡)五层架构；(4)18个注册技能全部配备参数模板。提供list/intent/run/auto/auto-engine/status/instance/phase2/phase3九个命令。触发词：宗源中枢、全域调度、统一入口、技能路由、意图识别、自动调用技能、hub、zongyuan、元极恒一调度、所有技能统一执行、全自动调度、自进化、技能进化、参数自动构建、一句话调用、全域锁档、锁档、归档、eFuse、ZONGYUAN-ROOT、内核写入、自治内核、哲学锚点、深度推演、架构文档锁档。当用户需要通过单一入口调用任意个人技能、自动识别意图并执行、对文档/推演/方案执行锁档确权并写入ZONGYUAN-ROOT内核、查看全域技能状态、执行全自动调度闭环或触发自进化优化时使用。"
---

# ZONGYUAN-HUB｜宗源中枢调度引擎 V3.0

元极恒一自治体系全域技能的**唯一统一入口**。一个命令调度全部技能，核心场景为**一句话全域锁档 + ZONGYUAN-ROOT 内核写入**。

> DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | 版本: V3.0

## 核心能力

| 能力 | 说明 |
|------|------|
| **auto-engine 锁档引擎** | 一句话执行 Lv3-Lv8 全域锁档，自动计算哈希、生成 eFuse、链接父哈希 |
| 统一入口 | 所有技能通过 `hub.py` 单一命令调用 |
| 意图识别 | 内置轻量 NLU，自动识别指令对应技能 |
| 智能路由 | 按五层架构(L0-L4)路由到对应技能入口 |
| 参数模板引擎 | 18个技能参数模板，自动填充+自然语言提取+缺失检测 |
| 全自动调度(phase2) | DAG拆解→算力调度→状态机执行→三级校验→自动锁档 |
| 自进化闭环(phase3) | 元学习+模板进化+路由优化+阈值自适应+A/B测试 |

## 五层架构

```
L0 调度中枢    unified-orchestrator(含phase2/phase3) + meta-order-scheduler(已整合)
L1 双内核      truth-value-engine + causal-singularity-core + fused-kernel + meta-learning-evolution
L2 四大产线    decision / research / drama / shield
L3 基建        compute-scheduler(已整合) + meta-order-archive V3.0 + lock-archive(已整合)
L4 展示        collection-card-generator
```

> 详细注册表见 [references/skill_registry.json](references/skill_registry.json)

---

## 命令速查

```bash
# === 最常用：auto-engine 全域锁档 ===
python3 scripts/hub.py auto-engine \
  --text "将X执行Lv4全域锁档并写入ZONGYUAN-ROOT内核" \
  --content "$DOC_CONTENT" \
  --asset-name "资产名称" \
  --meta-class M1 \
  --lock-level 4

# === 基础命令 ===
python3 scripts/hub.py list                    # 列出所有已注册技能
python3 scripts/hub.py intent --text "..."     # 意图识别测试
python3 scripts/hub.py run <skill> [args]      # 直接执行指定技能
python3 scripts/hub.py auto --text "..."        # 自动模式(意图→路由→执行)
python3 scripts/hub.py status                    # 中枢状态
python3 scripts/hub.py instance [action]        # ZR-SIP单实例协议

# === 阶段二：全自动调度 ===
python3 scripts/hub.py phase2 --text "意图" [--dry-run] [--force] [--meta-class M4]

# === 阶段三：自进化闭环 ===
python3 scripts/hub.py phase3 --text "意图" [--real] [--force] [--no-evolve]
python3 scripts/hub.py phase3 --optimize        # 触发自进化优化周期
python3 scripts/hub.py phase3 --status          # 查看阶段三系统状态
```

---

## auto-engine 全域锁档引擎（核心）

auto-engine 是实际最高频使用的命令，用于对任意文本内容执行锁档确权。

### 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--text` | 指令文本，描述锁档意图 | 必填 |
| `--content` | 要归档的内容文本（归档场景） | - |
| `--asset-name` | 资产名称 | 自动生成 |
| `--meta-class` | 元类 M1-M9 | M1 |
| `--lock-level` | 锁档等级 1-8 | 6 |
| `--dry-run` | 仅识别不执行 | false |
| `--status` | 查看引擎状态 | false |

### 元类选择指南

| 元类 | 名称 | 适用场景 |
|------|------|----------|
| M1 | 算法架构层 | 技术方案、架构设计、推演、引擎逻辑 |
| M2 | 数据模型层 | 数据结构、Schema、模型定义 |
| M3 | 接口协议层 | API、协议、接口规范 |
| M4 | 理论体系层 | 白皮书、理论框架、哲学体系 |
| M5 | 应用产线层 | 产品方案、应用设计 |
| M6 | 运维治理层 | 运维方案、治理策略 |
| M7 | 安全合规层 | 安全方案、合规策略 |
| M8 | 业务逻辑层 | 业务流程、商业逻辑 |
| M9 | 元秩序层 | 元法则、确权规则、根定义 |

### 返回字段

锁档成功返回 JSON，关键字段：
- `asset_id`：资产唯一标识（如 KD-ALGO-1131）
- `asset_hash`：内容 SHA256 哈希
- `parent_hash`：父区块哈希（自动从全局账本读取）
- `new_root_hash`：锁档后的新全局根哈希
- `efuse_id`：eFuse 熔断标识（Lv4+ 生成）
- `status`：LOCKED

---

## Lv4 全域锁档 + ZONGYUAN-ROOT 内核写入标准工作流

这是本技能最核心的端到端流程。完整步骤、内核模板、根状态模板见 [references/lock_and_kernel_workflow.md](references/lock_and_kernel_workflow.md)。

### 快速步骤

1. **准备资产**：将待锁档内容写入 `workspace/meta_order_assets/` 下的 .md 文件，计算 SHA256
2. **检查链状态**：读取 `~/.meta_order/root_state.json`，确认当前 `block_height` 和 `current_root_hash`；若丢失，从 `workspace/.meta_order_backup/` 恢复最新备份
3. **执行锁档**：调用 `hub.py auto-engine`，传入内容、资产名、元类、锁档等级
4. **写入内核**：更新 `~/.zongyuan_root/kernel/kernel_state.json`，记录新快照、Merkle-DAG、哲学锚点
5. **更新根状态**：更新 `~/.meta_order/root_state.json`，block_height+1，追加新区块记录
6. **双备份**：将 root_state.json 和 kernel_state.json 复制到 `workspace/.meta_order_backup/` 和 `workspace/.zongyuan_root_backup/`，文件名带日期版本号
7. **输出报告**：汇总锁档结果、内核写入状态、哈希链拓扑、确权签名

### 关键路径

| 资源 | 路径 |
|------|------|
| 全局根状态（运行时） | `~/.meta_order/root_state.json` |
| ZONGYUAN-ROOT 内核 | `~/.zongyuan_root/kernel/kernel_state.json` |
| 锁档资产存储 | `workspace/meta_order_assets/` |
| 根状态持久备份 | `workspace/.meta_order_backup/` |
| 内核持久备份 | `workspace/.zongyuan_root_backup/` |
| 归档引擎脚本 | `workspace/.user_skills/meta-order-archive/scripts/archive_lock_engine.py` |

---

## 脚本索引

`scripts/` 目录下的可执行脚本：

| 脚本 | 用途 |
|------|------|
| `hub.py` | **主入口**，统一调度所有命令 |
| `auto_orchestrator_v6.py` | 自动编排引擎 v6，DAG 调度核心 |
| `cluster_scheduler.py` / `_v2.py` / `_v3.py` / `_v5.py` | 集群调度器多版本迭代 |
| `zongyuan_root_v3_os.py` | ZONGYUAN-ROOT V3 全域自治操作系统 |
| `zr_sip_v2.py` | ZR-SIP 单实例协议 v2 |
| `zr_sip_cluster.py` | ZR-SIP 集群协议 |
| `zr_sip_lock.py` | ZR-SIP 锁管理（acquire/heartbeat/release） |
| `stress_test.py` | 压力测试脚本 |
| `template_viewer.py` | 模板查看器 |
| `template_architecture.html` | 架构模板（HTML 可视化） |

### 子目录

| 目录 | 内容 |
|------|------|
| `auto_engine/` | auto-engine 核心实现：engine.py(39KB主引擎)、adapters/、core/、utils/、chain_templates.json |
| `cards/` | 藏品卡 manifest |
| `report/` | 因果图与因果报告输出 |
| `references/` | skill_registry.json + 工作流参考文档 |

---

## 参数模板引擎（auto 命令）

`auto` 命令通过参数模板引擎实现一句话调用所有技能：

| 能力 | 说明 |
|------|------|
| 参数模板 | 18个技能全部配备参数模板 |
| 自动填充 | from_text / from_tempfile / from_ledger(读全局账本父哈希) / from_intent_name / 默认值 |
| 自然语言提取 | 正则提取 / 关键词映射 / 关键词后提取 |
| 缺失检测 | 自动检测缺失必填参数，使用默认值或提示用户 |

**已验证可自动调用**：决策、研究、短剧分镜、合同审查、归档锁档、因果分析、真值提炼。

---

## 意图→技能映射（高频）

| 用户指令关键词 | 路由技能 | 层级 |
|---------------|---------|------|
| 决策/方案评估/怎么选 | decision-pipeline | L2 |
| 研究/调研/白皮书/行业分析 | research-pipeline | L2 |
| 短剧/分镜/剧本/女娲/九天玄女 | drama-pipeline | L2 |
| 合同/审查/合规/法务 | shield-pipeline | L2 |
| 真值/提炼/压缩/漂移 | truth-value-engine | L1 |
| 因果/根因/奇点/收敛 | causal-singularity-core | L1 |
| 归档/锁档/确权/哈希/eFuse/内核写入 | meta-order-archive (via auto-engine) | L3 |
| 生成图片/视频/音频/算力 | compute_router | L3 |
| 藏品卡/黑金卡/资产卡 | collection-card-generator | L4 |
| 全域调度/统一编排/全链路 | unified-orchestrator | L0 |
| 全自动调度/phase2/DAG | phase2 | L0 |
| 自进化/技能进化/phase3 | phase3 | L0 |

---

## 已整合技能（兼容别名）

| 原技能 | 重定向至 | 状态 |
|--------|---------|------|
| meta-order-scheduler | unified-orchestrator | MERGED |
| meta-order-lock-archive | meta-order-archive V3.0 | MERGED |
| compute-scheduler | unified-orchestrator.compute_router | MERGED |

---

## 约束

- 所有技能调用通过 `hub.py` 统一入口，不直接调用子技能脚本
- 锁档必须先检查链状态，父哈希从 `root_state.json` 读取，禁止凭空猜测
- 环境重置后 `~/.meta_order/` 可能丢失，必须从 `workspace/.meta_order_backup/` 恢复
- 内核写入后必须执行双备份，否则视为未完成
- 意图识别置信度<0.6时回退到 unified-orchestrator 做深度解析
- 技能执行超时120秒
- 所有产出 DID 固定为 DID-BR-000002
- A/B测试结论需 p<0.05 方可全量上线
