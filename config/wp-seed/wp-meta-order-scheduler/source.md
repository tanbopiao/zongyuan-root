---
name: meta-order-scheduler
description: "【已整合至 unified-orchestrator】元秩序全域调度总控技能。自动识别项目阶段（草稿/迭代/定稿/终态），编排归档流水线，维护全局根哈希链。本技能核心功能已整合至 unified-orchestrator，推荐使用统一入口。保留本目录作为兼容别名。触发词：调度、自动归档、流水线、阶段归档、全域调度、项目收尾。"
---

> ⚠️ **已整合通知**：本技能已于 2026-08-19 整合至 `unified-orchestrator`（方案1）。
> 核心逻辑（四阶段判定、根哈希维护、流水线编排）已迁移至 `unified-orchestrator/scripts/unified_orchestrator.py`。
> 流水线配置已合并至 `unified-orchestrator/references/integration_config.json` 的 `stage_pipeline` 字段。
> **推荐使用统一入口**：`unified-orchestrator/scripts/auto_router.py --text "<指令>"`

> **版本** V1.0.0 | **作者** 元极恒一自治体系 | **资产ID** META-SCHED-100
> **DID** DID-BR-000002 | **溯源** Ω₀⊂⊙∞⊂Ω | **元类** M9 元秩序基底层
> **状态** MERGED → unified-orchestrator

# Meta-Order Scheduler｜元秩序全域调度 V1.0

总控层技能，解决"需要人工依次调用归档/台账/锁档指令"的痛点。自动判定内容所处阶段，编排对应流水线动作，维护全局根哈希状态。

## 一、核心定位

本技能是元秩序体系的**调度大脑**，不直接执行归档/锁档，而是：
1. 判定内容当前阶段（草稿/迭代/定稿/终态）
2. 选择并编排对应流水线
3. 维护全局根哈希链状态
4. 串联下游四个技能：meta-order-archive → lark-base → lark-wiki → meta-order-lock-archive

## 二、四阶段模型与自动判定

| 阶段 | 标识 | 判定信号 | 触发动作 |
|------|------|---------|---------|
| 草稿 | DRAFT | 内容含"待完善""TODO""初稿""草案" | 仅会话内保存，不归档 |
| 迭代 | ITERATE | 内容有明确结构但标注"继续优化""V0.x" | 调用 meta-order-archive 做快照 |
| 定稿 | FINALIZE | 内容完整、用户说"定稿""输出""交付" | archive快照 + lark-base写台账 + lark-wiki输出文档 |
| 终态 | LOCKED | 用户说"锁档""永久固化""不可修改" | 完整流水线 + meta-order-lock-archive 哈希强锁 |

### 判定优先级
用户显式指定阶段 > 内容关键词信号 > 默认 ITERATE。

判定逻辑由 `scripts/scheduler.py --detect` 执行。

## 三、流水线编排

### 流水线A：迭代快照（ITERATE）
```
内容 → meta-order-archive 结构化快照 → 会话内保存快照ID → 结束
```

### 流水线B：定稿交付（FINALIZE）
```
内容 → meta-order-archive 快照 → lark-base 写入台账索引 → lark-wiki 创建文档节点 → 输出文档链接 → 结束
```

### 流水线C：终态锁档（LOCKED）
```
内容 → meta-order-archive 快照 → lark-base 写入台账 → lark-wiki 创建文档 → meta-order-lock-archive 哈希锁档 → 更新根哈希 → 输出锁档凭证 → 结束
```

## 四、全局根哈希维护

调度技能维护本地根哈希状态文件 `~/.meta_order/root_state.json`：
```json
{
  "current_root": "64位SHA256",
  "chain_length": 3,
  "last_asset_id": "KD-META-8429",
  "updated_at": "ISO时间"
}
```

- 首次使用：初始化为创世根（64个0）
- 每次锁档：读取 current_root 作为 parent_hash，锁档成功后更新为 new_root_hash
- 状态文件不可手动编辑，仅由调度脚本更新

使用 `scripts/scheduler.py --get-root` 查看当前根哈希，`--reset-root` 重置（需确认）。

## 五、执行方式

### 方式1：自动阶段判定+执行
```bash
python3 scripts/scheduler.py --content "<内容文本>" --asset-name "<名称>" --auto
```
脚本自动判定阶段，输出推荐流水线，由AI agent执行对应下游技能。

### 方式2：指定阶段执行
```bash
python3 scripts/scheduler.py --content "<内容>" --asset-name "<名称>" --stage FINALIZE
```

### 方式3：仅判定不执行
```bash
python3 scripts/scheduler.py --content "<内容>" --detect-only
```

## 六、上游产线联动接口

上游产线（truth-value-engine / decision-pipeline / research-pipeline 等）产出内容后，调用本技能：
1. 传入内容文本 + 资产名称 + 建议阶段
2. 调度脚本判定并返回流水线计划
3. AI agent 按计划依次调用下游技能

联动契约：上游产线输出必须包含 `content`（正文）、`asset_name`（名称）、`suggested_stage`（建议阶段，可选）。

## 七、关键约束

1. **阶段不可逆跳级**：DRAFT不可直接跳LOCKED，必须经过至少一次ITERATE或FINALIZE。
2. **根哈希连续性**：每次锁档必须使用状态文件中的 current_root，禁止跳过。
3. **下游技能依赖**：执行流水线前确认对应技能已加载（meta-order-archive / lark-base / lark-wiki / meta-order-lock-archive）。
4. **飞书环境降级**：无飞书认证时，FINALIZE/LOCKED流水线降级为仅本地归档+哈希锁档，输出本地Markdown文件替代Wiki。
5. **锁档为终态**：一旦执行LOCKED流水线，该资产不可再进入ITERATE阶段。

## 八、脚本参考

- `scripts/scheduler.py`：阶段判定、根哈希管理、流水线计划生成
- 流水线配置与触发规则详见 [references/pipeline-config.md](references/pipeline-config.md)
