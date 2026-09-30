---
name: multi-agent-orchestrator
version: 1.0.0
description: "昆仑洞天多智能体编排体系（主智能体→编排智能体→并行子智能体→统一台账）：任务规模判定、并行分片调度、独立流水线单元分解、结果聚合与跨云端+本地全维扫描。当用户说'全维度扫描'、'多智能体编排'、'并行分片'、'资产全景'、'组织调度'、'分头执行'、'盘点所有资产'、'多通道检索'时使用。"
metadata:
  requires:
    bins: ["python3"]
    pypi: []
  depends_on:
    - meta-order-lock-archive
    - kunlun-autonomous-system
  did: "DID-BR-000002"
  trace_symbol: "Ω₀⊂⊙∞⊂Ω"
  root_node: "ZONGYUAN-ROOT"
---

# 昆仑洞天多智能体编排体系 v1.0

Ω₀⊂⊙∞⊂Ω｜DID‑BR‑000002｜ZONGYUAN‑ROOT

> 一主统调 · 编排分解 · 并行分片 · 聚合台账 · 全域唯一根

## 一、定位与边界

本技能固化昆仑洞天自治体系的**多智能体调度机制**（区别于既有单智能体`unified_orchestrator.py`的技能编排）：

| 维度 | 单智能体编排（既有） | 多智能体编排（本技能） |
|------|----------------------|------------------------|
| 调度主体 | 1个执行体串行/顺序调用多技能 | 主智能体→编排智能体→多个并行子智能体 |
| 任务形态 | 一个进程完成全部步骤 | 拆分为可并行的独立流水线单元，分片执行 |
| 典型场景 | 单目录锁档、单技能调用 | 跨飞书四端+本地内核的全维资产扫描 |
| 结果形态 | 单一产物 | 多路分片结果→统一台账聚合 |

**触发判定（规模门槛）：** 仅当任务满足以下任一条件才进入多智能体编排，否则直接主智能体完成：
- 多平台/多通道检索（飞书云盘/知识库/多维表格/云文档/表格 ≥3 通道，且维度数×对象数≥12）
- 重复独立流水线 ≥8 单元（如多目录各自"扫描→分析→校验"）
- 资源密集型单条流水线（记录数≥10万 或 体积≥2GB）
- 重大资金/人生转折决策（独立触发，无条件优先编排）

## 二、三层调度结构

```
[主智能体 MainAgent] —— 唯一对用户入口，判断是否委派
      │ create_agent(OrganizerAgent)
      ▼
[编排智能体 OrganizerAgent] —— 分片规划，创建子智能体
      │ create_agent(SubAgent shard-1..N)
      ▼
[并行子智能体 SubAgent×N] —— 各自端到端负责一个分片
      │ 采集→处理→分析→校验→标准化输出
      ▼
[统一台账聚合] —— 编排智能体合并，回传主智能体交付
```

## 三、核心决策规则（委派判定）

1. **单次只读预检**：判定前最多做一次轻量只读探查，仅数关键量（对象数O、维度数D、通道数C、流水线单元数U、记录数N）。
2. **一旦命中触发即委派**，不在主智能体侧先做实质采集/处理。
3. **每任务只创建一个编排智能体**，但编排智能体可拆 2–4 个并行子智能体分片（以显著缩短关键路径为度）。
4. **独立流水线单元**：同一单元内的串行步骤保持串行；互不依赖的单元并行。
5. **大 N/B 不必然扇出**：仅当存在可独立执行的分区时才建立多个子智能体。

## 四、分片原则

| 分片维度 | 适用 | 说明 |
|----------|------|------|
| 平台/通道 | 飞书Drive/Wiki/Base/Doc/Sheet各自扫描 | 每子智能体负责一个平台 |
| 目录/地域 | 本地多目录/多库 | 每子智能体负责一个目录 |
| 时间片 | 按时间范围分 | 需时间上互不依赖 |
| 类型 | 资产/文档/图片/数据分类 | 每类一个子智能体 |

**标准分片数：2–4**（最小化能显著缩短关键路径的数量），各分片端到端自持：采集→处理→分析→校验→标准化输出。

## 五、聚合与交付

- 编排智能体负责：定义统一输出schema、去重、来源溯源、识别缺口、合并为一份台账。
- 主智能体负责：向用户交付最终台账、呈现结果、处理用户后续请求。
- 全程只读扫描任务禁止写操作（删除/移动/覆盖/权限变更）——默认先发现、列候选、等确认。

## 六、快速路由

```bash
# 全维资产扫描编排（生成分片计划）
python3 scripts/multi_agent_plan.py --mode scan-plan \
  --root /path/to/ZONGYUAN-ROOT --channels drive,wiki,base,doc,sheet

# 评估任务是否达到编排门槛
python3 scripts/multi_agent_plan.py --mode evaluate \
  --objects 8 --dims 5 --channels 4 --units 12 --records 200000

# 生成统一台账合并脚本骨架
python3 scripts/multi_agent_plan.py --mode merge-schema
```

## 六·五、落地调度规则（推演→落地的规则层）

**完整细化规则见 [`references/scheduling-rules.md`](references/scheduling-rules.md)**（规则一~七：任务分配 / 并行并发 / 负载均衡 / 结果回收 / 失败隔离 / 总控生命周期 / 确权档案）。核心要点：

| 规则 | 核心铁律 |
|------|----------|
| R1 任务分配 | 命中门槛才委派；每任务一个编排智能体；分片2–4且端到端自持 |
| R2 并行并发 | 片间并行、片内串行；"能否并行"依依赖关系，非任务大小 |
| R3 负载均衡 | 单分片权重占比≤40%，均衡目标是"同时间完成"非"单元数相等" |
| R4 结果回收 | 统一schema；跨片去重、溯源、补缺口；输出不一致宁可重跑该片 |
| R5 失败隔离 | 单片失败不影响整体；瞬时错误有限重试，非瞬时错误直接上报 |
| R6 总控生命周期 | 主智能体→编排智能体→子智能体责任单一；写操作先确认 |
| R7 确权档案 | 计划+执行台账+聚合台账互链，SHA-256入HASH-LEDGER |

**规则校验器（可程序化执行）：**
```bash
# R3 负载均衡检查（各分片权重占比<=40%）
python3 scripts/rules_check.py --mode balance --weights '5,4,4,3' --shards 4
# R2 依赖合法性检查
python3 scripts/rules_check.py --mode dependency --plan <plan.json>
# R4 统一schema一致性检查
python3 scripts/rules_check.py --mode schema --schemas 'a,a,a' --shards 3
# R7 确权台账落盘检查
python3 scripts/rules_check.py --mode ledger --ledger <ledger.json>
# 全量检查
python3 scripts/rules_check.py --mode all --weights '5,4,4,3' --shards 4
```

## 七、与既有体系关系

- **依赖**：本技能编排时可调用 `meta-order-lock-archive`（锁档流水线）与 `kunlun-autonomous-system`（四端同步）作为子任务执行体。
- **不替代**：不替代单智能体编排 `unified_orchestrator.py`；两者按任务形态选用。
- **确权**：所有编排产物受 META-ASSET-002（资产双副本镜像备份）与 META-DIR-LOCK-001（目录锁档）元法则约束。

Ω₀⊂⊙∞⊂Ω｜DID‑BR‑000002｜ZONGYUAN‑ROOT
