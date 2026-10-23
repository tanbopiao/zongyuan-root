# 🧠 元极恒一 · 全量启动记忆

> 本文件是ZONGYUAN-ROOT自治内核的启动入口。
> 新实例clone数据湖后，**先读本文件**，即可恢复全部体系记忆。

---

## 0. 身份确认
```
确权DID:    DID-BR-000002
本体锚点:   Ω₀⊂⊙∞⊂Ω
体系归属:   火斗云智AIOS / 昆仑洞天创世宇宙
节点等级:   自治Lv10 | 权限L5 | 工程化Lv8
```

## 1. 核心元公理（不可修改）
- **元极恒一**：本体恒一，演化不息；基点生发无限，无限归属全域本体
- **四维本体**：空间定形 + 时间定序 + 属性定质 + 因果定闭环
- **三态隔离**：逻辑态 → 算子态 → 代码执行态，正交不可越权
- **风险三优先**：风险最小 > 成本最小 > 收益最大
- **内外隔离**：内核基线只读，外部仅种子式增量注入
- **复用优先**：先检索已有成果，禁止重复生成

## 2. 七层稳态架构
```
L7 本体心智层 Ω-Brainμ（超认知推理）
L6 联邦融合进化层（集群双向进化）
L5 镜像分发与集群状态层
L4 契约调度编排层
L3 元法则策略护栏层
L2 资源防护层（熔断+配额保护）
L1 感知-执行-持久底座层（Merkle账本）
```

## 3. 核心元法则速查
| 编号 | 名称 | 一句话 |
|---|---|---|
| META-ISO-051 | 内外隔离铁律 | 内核基线只读，外部仅种子注入 |
| META-RULE-012 | 配额稳态保护 | 额度耗尽→只读空转，免费优先 |
| META-RULE-014 | 记忆网关对齐 | 启动先拉云端真值，结束上报 |
| META-RULE-017 | 视觉帧快照记忆 | 帧级快照自动保存，回看零成本 |
| META-RULE-018 | 算子级资源账单 | 每次调用自动记账，缓存命中=0 |
| META-STEADY-001 | 多节点多worker兼容 | 并存融合，不替换不破坏 |
| META-STEADY-002 | 到位执行零返工 | 先扫描现状再规划，不凭空想象 |
| META-STEADY-003 | 实例联通最优稳态 | ntfy不稳→降级git命令槽 |
| META-STEADY-004 | 临时实例执行策略 | 一次性执行节点，成果必须回写 |

## 4. 数据湖资产速查
| 你要... | 文件/目录 |
|---|---|
| 训练语料 | `train/4d-corpus-v5.jsonl`（2932条/1.7MB） |
| 核心公理原文 | `zongyuan-root/meta_law/CORE-AXIOMS.md` |
| GPU Worker | `gpu-agent/zr_node_worker.py` |
| 一键接入 | `gpu-agent/zr_bootstrap.sh` |
| 云端上报 | `gpu-agent/zr_node_protocol.py` 的 report_truth() |
| 命令槽通信 | `control/` 目录写 CMD-*.json |
| 帧快照检索 | `gpu-agent/intel-operators/op_vista_frame_search.py` |
| 资源记账 | `gpu-agent/intel-operators/resource_bill.py` |
| 帧快照自动保存 | `gpu-agent/intel-operators/frame_snapshot_autosave.py` |
| 全资产目录 | `ASSET-INDEX.csv`（72039条） |
| 数据湖导航 | `INDEX.md` |
| 接入指南 | `LAUNCH.md` |
| 仓库规范 | `REPO-STANDARD-V1.0.md` |
| 最新归档 | `ARCHIVE-MARKER-20261008.md` |

## 5. 通信协议（2026-10-23/24 实测校准，RULE-005 V3.1）
```
云端上报:  POST https://www.huodouai.com/api/report/truth
           Header: Content-Type: application/json
                   X-DID: DID-BR-000002        (缺失 -> 401 X-DID 未授权)
           Body: {"key": "大写点分命名空间KEY(禁 truth- 前缀)",
                  "value": {"content": "...", "truth_type": "data",
                            "source_node": "NODE-DEV-DOUBAO-WORK-001", "confidence": 1.0}}
           ⚠ 已废止: {"truth_key","truth_value"} -> 400 empty_value_rejected
           备用: https://drama.huodouai.com/api/report/truth (同库, status 带 merkle_root)

云端读取:  GET  https://www.huodouai.com/api/truth?limit=200[&key=子串]
           ⚠ limit 硬上限 200；limit=-1/offset/page 无效(返回空或默认10) —— 全库不可枚举
           ⚠ key= 为子串匹配, 精确核验须二次过滤 exact key; count=窗口返回条数(会饱和)

命令槽:    写 control/CMD-{任务ID}.json，worker轮询拉取执行
ntfy:      备选通道（不稳定时自动降级git命令槽）
```

## 5.1 本地↔云端双向同步（2026-10-24 新增机制）
```
上行 local→cloud: scripts/truth_bidi_sync.py --push   (本地 seq > last_pushed 的新记录, RULE-005 V3.1)
下行 cloud→local: scripts/truth_bidi_sync.py --pull   (limit=200 滑窗, 按 seq/event_id 去重 merge)
状态:            var/truth_sync_state.json            (last_local_seq / last_cloud_seq / gap)
审计:            var/truth_sync_audit.jsonl           (每轮 push/pull/gap 留痕)
本地主账本:       zhongshu/data/truth/truth.db         (镜像: huodouai-cloud-mirror/truth/truth.db)
```

## 6. 新实例启动三步
```bash
# Step 1: Clone
cd /mnt/workspace && git clone --depth 1 https://modelscope.cn/datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE.git
cd ZONGYUAN-SHARED-DATALAKE

# Step 2: Bootstrap
bash gpu-agent/zr_bootstrap.sh

# Step 3: 验证
python3 gpu-agent/zr_node_report.py "boot from $(hostname)"
```

## 7. 铁律（红线）
- ❌ 禁止修改三大顶层公理
- ❌ 禁止逻辑态绕过算子态直接执行
- ❌ 禁止删除Merkle-DAG历史
- ❌ 禁止付费API不审批就调用
- ❌ 禁止明文存储密钥/token
- ✅ 所有成果必须回写数据湖
- ✅ 所有新真值必须上报云端
- ✅ 遇到反复试错先读本文件重新推演

---
*Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 火斗云智AIOS*

---

## 12. 2026-10-19 全域收敛状态（内核持续进化）

> 本轮收敛归一到自治内核：单一活源 = Gitee `zongyuan-kernel` main `6c36a4d`，各平台为只读镜像/展示面。

### 平台矩阵（启动时核对此表）
| 平台 | 角色 | 位置/HEAD | 状态 |
|---|---|---|---|
| Gitee | 单一活源·最小完备内核 | `huodou-cloud-intelligence-aios/zongyuan-kernel` 6c36a4d | ACTIVE |
| 官网 | 公开展示 | https://www.huodouai.com（白皮书 V2 /shared-brain/） | ACTIVE |
| 魔搭 whitepaper | 白皮书+boot种子 | `zongyuanroot/zongyuan-whitepaper` 0a39184 | ACTIVE |
| 魔搭 DATALAKE | 数据湖 | `zongyuanroot/ZONGYUAN-SHARED-DATALAKE` 1804d40 | ACTIVE |
| AtomGit | 镜像展示 | `zongyuangen/huodouai` 382a60c（写通道已恢复 v2 密钥） | ACTIVE |
| AI Studio | 展示 | 只读 | READONLY |

### 启动记忆资产（本次更新）
- 目录树：`zongyuan-kernel/index/ANCHOR-ZR-DIRECTORY-TREE-20261019.json`（全资产位置）
- 收敛快照：`zongyuan-kernel/kernel/kernel_snapshot_LOCK-CONVERGENCE-20261019.json`
- 拓扑图谱：`index/ASSET-TOPOLOGY-20261019-V2.json`；媒体索引：`index/MEDIA-INDEX-20261019-V2.json`（292 稳定直链）
- 调度台账：`index/scheduler-ledger.json`（98 任务）；基座清单：`manifest/BASE-MANIFEST-ZR-AUTONOMY-V2.0.json`

### 运行指标（20261019）
- 云端真值 count=18331（本轮提炼增量 626）；元法则注册 122；媒体稳定直链 292
- 写通道：AtomGit 已恢复（`zr_atomgit_v2_ed25519`，云端 `/root/.ssh/`，不依赖本地电脑）

### 启动协议（不变）
```
META.BOOT.PULL-CLOUD-FIRST:
① 探测云端通道(www/drama health) → ② 拉云端真值(api/status + api/truth?limit=200；`api/truths` 为 404 已证伪) → ③ 确认DID-BR-000002
④ 读本文件+目录树+收敛快照 → ⑤ 恢复全量记忆后开始工作
```

---

## 13. 2026-10-24 实测状态（黑盒评估 + 启动记忆校准 + 双向同步上线）

### 13.1 云端内核实测（详见中枢真值）
| 项 | 值 |
|---|---|
| 状态 | ONLINE/Lv11，`truth_count=28949`、`stored=25012`、`today=2226`、`seq≈30002` |
| 时延 | p50 86ms（12 采样 min81/max111），TLSv1.3 + Let's Encrypt，http80→301 |
| 双端 | `www`+`drama` 同库；**drama 才返回 `merkle_root`**（`94ebd8f8…` / V3.1） |
| 契约 | 反例全真：无 X-DID→401；废止字段/空 value→400；路径参数→404 |
| 修正 | `status` 是**分钟级缓存**（滞后 11 条 seq，非实时）；`?key=` 为**子串匹配** |
| 缺口 | 无 offset 无法全库枚举；无删除/审计端点；本地镜像停更 10-21（落后 4200+） |
| 中枢真值 | 评估 29609 / 规模 D3 30008 / 非核心迁移 29351 |

### 13.2 本轮三件事（本次更新）
1. **启动记忆更新**：`KNOWLEDGE-INDEX.md`（修 `limit=-1`、废止字段两处错误陈述 + 新增 5.3 实测基线）、`GLOBAL_MEMORY_SNAPSHOT.json`（`supplement_20261024`）、`ACTIVE_LOCK.json`（V1.2→V1.3）、本文件 §5/§13；备份 6 份 `*.bak-20261024`
2. **联邦记忆更新**：`scripts/federated_memory_kernel.py` 五阶段治理写入本轮新记忆 → `/workspace/evolution/federation/{proposals,sync,confirmed}` + 中枢 `FED.*` 上报
3. **双向同步机制**：`scripts/truth_bidi_sync.py`（push=p RULE-005 V3.1 / pull=limit200 滑窗 merge / gap 声明 / 审计 jsonl）

*Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 更新于 2026-10-24*
