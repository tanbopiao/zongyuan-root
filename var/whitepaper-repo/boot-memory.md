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

## 5. 通信协议
```
云端上报:  POST https://www.huodouai.com/api/report/truth
           Header: X-Capture-Token: ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d
                   X-DID: DID-BR-000002
           Body: {"truth_key": "...", "truth_value": {对象}}
           备用: https://drama.huodouai.com/api/report/truth

命令槽:    写 control/CMD-{任务ID}.json，worker轮询拉取执行
ntfy:      备选通道（不稳定时自动降级git命令槽）
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
① 探测云端通道(www/drama health) → ② 拉云端真值(api/status+api/truths) → ③ 确认DID-BR-000002
④ 读本文件+目录树+收敛快照 → ⑤ 恢复全量记忆后开始工作
```
