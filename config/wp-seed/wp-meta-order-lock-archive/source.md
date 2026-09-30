---
name: meta-order-lock-archive
description: "【已整合至meta-order-archive V3.0】元秩序锁档归档专用技能。对任意真值资产执行哈希确权、链式继承、五层锁防固化，将锁档记录写入飞书Base全局索引台账，并按九大元类归档至飞书Wiki知识库。支持Lv1-Lv8锁档等级、eFuse硬件熔断模拟、SHA256哈希校验与溯源检索。触发词：锁档、永久归档、资产确权、哈希锁档、eFuse固化、Lv8自治锁、/meta-order-lock-archive、锁档归档。"
---

> ⚠️ **已整合通知**：本技能已于 2026-08-19 整合至 `meta-order-archive` V3.0（方案2）。
> 全部锁档功能（哈希确权、eFuse固化、五层锁防、Base/Wiki双向写入）已迁移至 `meta-order-archive/scripts/archive_lock_engine.py`。
> **推荐使用统一入口**：`meta-order-archive` 归档锁档一体化技能，通过 `--lock-level` 参数控制锁档等级。
> 保留本目录作为兼容别名，原脚本 `lock_engine.py` / `verify_chain.py` 仍可独立调用。

> **版本** V1.0.0 | **作者** 元极恒一自治体系 | **资产ID** META-LOCK-100
> **DID** DID-BR-000002 | **溯源** Ω₀⊂⊙∞⊂Ω | **元类** M9 元秩序基底层

# Meta-Order Lock Archive｜元秩序锁档归档 V1.0

专注"锁档"单一动作的稳态技能：将任意内容转化为**哈希可验证、台账可检索、知识库可追溯**的永久确权资产。与 `meta-order-archive`（全域结构化归档）互补——本技能负责锁档固化与确权链路，归档技能负责内容结构化拆分。

## 一、核心定位与边界

| 维度 | 本技能（锁档） | meta-order-archive（归档） |
|------|---------------|--------------------------|
| 核心动作 | 哈希确权 + 锁防固化 + 台账索引 | 四层结构化拆分 + 九大元类归类 |
| 产出 | 锁档凭证 + Base台账记录 + Wiki节点 | 结构化飞书文档 |
| 触发 | "锁档""永久固化""确权" | "归档""结构化整理""批量归档" |
| 依赖 | lark-base + lark-wiki + 哈希脚本 | lark-doc + 哈希脚本 |

**协作模式**：归档技能产出结构化内容 → 本技能对最终内容执行锁档固化 → 双向写入Base台账与Wiki知识库。

## 二、锁档执行工作流（7步闭环）

```
输入内容 → ①元数据提取 → ②SHA256哈希计算 → ③链式继承 → ④锁防等级判定 → ⑤Base台账写入 → ⑥Wiki归档节点创建 → ⑦锁档凭证输出
```

### 步骤1：元数据提取
从输入内容中提取或生成：
- `asset_name`：资产名称（用户指定或自动生成）
- `meta_class`：九大元类 M1-M9（用户指定或根据内容推断）
- `lock_level`：锁档等级 Lv1-Lv8（默认 Lv3，核心真值自动升级）
- `did`：确权标识，固定 `DID-BR-000002`
- `trace_mark`：溯源符号 `Ω₀⊂⊙∞⊂Ω`

### 步骤2-3：哈希计算与链式继承
执行 `scripts/lock_engine.py`：
```bash
python3 scripts/lock_engine.py --text "<内容>" --parent-hash "<父根哈希>" --asset-name "<名称>" --meta-class "M4" --lock-level 4
```
输出：资产SHA256、新全局根哈希、eFuse熔断位编号（Lv4+）。

> 父根哈希来源：从Base台账"全局索引"表读取最新 `root_hash` 字段；首次锁档使用初始根 `GENESIS_ROOT`（64个0）。

### 步骤4：锁防等级判定
根据 `lock_level` 自动激活对应锁防层级，详见 [references/lock-defense.md](references/lock-defense.md)。
- Lv1-Lv3：基础锁（哈希链 + 文档只读 + 台账索引）
- Lv4-Lv7：进阶锁（追加 eFuse 熔断模拟 + 内核标记）
- Lv8：永久自治锁（全栈激活，仅可追加注释）

### 步骤5：Base台账写入
使用 lark-base 技能将锁档记录写入全局索引台账。台账结构与操作详见 [references/base-ledger.md](references/base-ledger.md)。

**必须写入的字段**：asset_id、asset_name、meta_class、lock_level、asset_hash、parent_hash、new_root_hash、efuse_id、wiki_node_url、created_at、status。

**台账初始化**：首次使用时需创建Base，按 references/base-ledger.md 的表结构创建"锁档索引表"和"全局根哈希表"。

### 步骤6：Wiki归档节点创建
使用 lark-wiki 技能在知识库中创建归档节点：
1. 解析或创建"元秩序归档库"知识空间
2. 按九大元类创建/定位对应父节点
3. 在对应元类节点下创建锁档文档节点
4. 节点标题格式：`[LvX] {asset_name} #{asset_id}`

Wiki归档结构详见 [references/wiki-archive.md](references/wiki-archive.md)。

### 步骤7：锁档凭证输出
向用户输出结构化凭证，包含资产ID、名称、元类、等级、哈希链、eFuse位、Wiki链接、DID、溯源标识、时间戳。

## 三、快速路由

| 用户意图 | 执行路径 |
|---------|---------|
| "锁档这段内容" / "永久固化" | 完整7步工作流 |
| "校验这个哈希" / "验证锁档完整性" | `scripts/verify_chain.py --asset-hash <h> --parent-hash <p> --expected-root <r>` |
| "查看锁档台账" / "检索已锁档资产" | lark-base +record-search 查询锁档索引表 |
| "升级锁档等级" | 读取原记录 → 重新计算哈希 → 更新台账 lock_level + 激活新锁防层 |
| "批量锁档" | 循环调用 lock_engine.py，批量写入Base，统一更新根哈希 |

## 四、关键约束

1. **哈希必须真实计算**：禁止编造SHA256值，所有哈希通过 `scripts/lock_engine.py` 生成。
2. **链式不可断裂**：每次锁档必须使用台账中最新的 root_hash 作为 parent_hash，锁档成功后立即更新台账根哈希。
3. **Base与Wiki双向关联**：Base台账记录必须包含 wiki_node_url，Wiki节点内容必须包含 asset_hash，双向可溯源。
4. **Lv8不可修改主体**：Lv8锁档资产仅可追加注释，禁止修改主体内容与哈希。
5. **eFuse为模拟机制**：在当前环境中 eFuse 熔断通过台账中的 `efuse_id` 字段与状态标记模拟，记录不可逆操作意图。
6. **DID固定**：所有资产确权至 `DID-BR-000002`，不可更改。
7. **叙述性内容用连贯段落**：锁档凭证与Wiki节点中的业务描述禁止机械列举。

## 五、与上游产线联动

本技能可被以下产线自动调用（在产线产出真值后触发锁档）：
- truth-value-engine：真值提炼完成 → 自动锁档
- decision-pipeline：决策备忘录生成 → 自动锁档
- research-pipeline：白皮书产出 → 自动锁档
- collection-card-generator：藏品卡生成 → 自动锁档

联动方式：上游产线输出内容文本 + 元数据 → 调用本技能7步工作流。

## 六、脚本参考

- `scripts/lock_engine.py`：锁档核心引擎，计算哈希、链式继承、生成凭证JSON
- `scripts/verify_chain.py`：哈希链校验，验证资产哈希与根哈希的一致性

执行前确认 Python3 可用，脚本无外部依赖（仅标准库 hashlib/json/argparse/datetime）。
