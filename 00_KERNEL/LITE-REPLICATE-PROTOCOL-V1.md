# LITE-REPLICATE-V1 通用技术轻量复刻架构 · 协议

> 确权：DID-BR-000002 ｜ 溯源：Ω₀⊂⊙∞⊂Ω ｜ 版本：V1.0 ｜ 2026-10-22
> 定位：**把「吸收全网前沿技术 → 轻量工程化落地 → 持久性运行」固化为一条可重复的四环节流水线**
> 工程元战略约束：轻量化最高优先级——零第三方依赖、最小文件数、单实现双视图、可核验可证伪

---

## 一、四环节流水线（SCOUT → VERIFY → FORGE → RUN）

### S1 SCOUT 吸收（提炼，不动手）
- 输入：任意前沿技术源（仓库/文章/产品页/论文）
- 动作：提炼一句话定位、核心范式、能力清单、与本体系 L0–L6 既有件的映射
- 产出：种子真值条目（`experience/truth-core/SEED-*.json`）
- 出口条件：claim 逐条标注来源；无源即标记"图内转录/未核验"，不冒充实测

### S2 VERIFY 核验（先核验，后动手）
- 外源多源交叉核验：许可证、版本、官方自述、关键事实 ≥2 独立源
- 三分类裁决：**可直接复用**（安装/配置即可）/ **轻量复刻**（零依赖重实现 ≤ 既有范式）/ **仅借鉴**（设计思想吸收，不抄实现）
- 裁决写入种子真值 `absorb_mapping` + `risk_cost_benefit`
- 红线：许可证不明不复刻；核验失败降级为"仅借鉴"并留痕

### S3 FORGE 轻量锻造（复刻的工程红线）
- **零第三方依赖**：Python 仅 stdlib / JS 仅内置模块；系统命令白名单（curl/git/rsync/scp）
- **最小骨架**：`core（单实现）+ cli + tests + README + LICENSE(MIT) + registry 登记`
- 复刻 ≠ 照搬：必须附加本体系差异层（真值校验/公私隔离/确权锁档 中适用者）
- 出口条件：`test 全绿 + smoke 实测 + 脱敏扫描 0 命中`（对外发布时）
- 脚手架：`00_KERNEL/lite_replicate/template/`（`forge` 一键生成）

### S4 RUN 持久运行（落地不烂尾）
- 登记 `var/lite-registry.json`（台账：源/状态/路径/sha/巡检命令）
- 接入 steady_evolve：`lite_registry_check` 每 12h 跑在册项目测试，失败告警（时间窗去重）
- 对外发布走既有闭环：链块锁档 + 网关真值 + git commit（发布动作仍人工审批）
- 实例重建：`steady_evolve_bootstrap.sh` 口令复原时一并校验 registry 巡检任务

## 二、四条红线（不可配置绕过）

1. **核验先行**：S2 未过不出工程；许可证不明不复刻
2. **零依赖**：任何第三方包引入即违规（轻量化元战略）
3. **复刻≠照搬**：治理层（真值/隔离/确权）原生内建，不外求
4. **高危不自动**：付费、对外发布、删除类动作强制人工审批；执行器只做探测/构建/测试

## 三、件清单

| 件 | 路径 | 职责 |
|---|---|---|
| 协议（本文件） | `00_KERNEL/LITE-REPLICATE-PROTOCOL-V1.md` | 四环节 + 红线 |
| 执行器 | `00_KERNEL/lite_replicate/lite_replicate.py` | `ingest / forge / status / verify` |
| 模板 | `00_KERNEL/lite_replicate/template/` | 最小复刻工程骨架 |
| 台账 | `var/lite-registry.json` | 在册项目唯一事实源 |
| 持久巡检 | steady_evolve 任务 `lite_registry_check` | 每 12h 跑在册测试，失败告警 |

## 四、与既有体系的关系

- 吸收环节复用种子真值范式（与 SEED-DSH-* 同构）
- 运行环节挂 steady_evolve（与心跳/契约探针同守护）
- 对外发布复用 REA/EvidenceGate 已验证的 AtomGit 闭环
- 差异层复用 L0–L6：复刻件只做能力层（L4–L5），不动内核真值（L0–L1）
