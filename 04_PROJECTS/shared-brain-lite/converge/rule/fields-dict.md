# 字段字典与协作元规则（rule/fields-dict.md）

> 只读字段：修改本文件需要人工评审（公理 5/6），改动须在 truth-ledger.csv 留痕。

## 一、truth-ledger.csv 字段定义（10 列，固定顺序）

| # | 字段 | 必填 | 说明 | 示例 |
|---|------|------|------|------|
| 1 | seq | 是 | 账本行号，从 1 递增，**不复用不重排** | `42` |
| 2 | timestamp | 是 | 变更登记时间，ISO8601 本地时区 | `2026-10-22T07:00:00+0800` |
| 3 | node_id | 是 | 变更节点标识（人/AI 节点），全局唯一命名 | `human-zhang` / `AGENT-OPS-01` |
| 4 | file_path | 是 | 变更文件相对路径（仓库根起） | `converge/asset-index.md` |
| 5 | action | 是 | 动作类型，取值见下节枚举 | `merge` |
| 6 | sha256 | 是 | 变更后文件的 SHA256（小写 hex，64 位） | `e3b0c442...` |
| 7 | summary | 是 | 变更摘要，一句话说清"改了什么、为什么" | `新增资产索引第3条` |
| 8 | operator | 是 | 实际操作人/脚本名 | `human` / `sync_shared_brain.py` |
| 9 | status | 是 | 状态：`merged`(已并入) / `pending`(待核验) / `rolledback`(已回滚) | `merged` |
| 10 | commit | 否 | 对应 git commit 短哈希，apply 后由脚本回填 | `49283e42` |

## 二、action 枚举

- `init` 初始化种子
- `sandbox` 沙箱草稿落盘（不进 converge，仅登记）
- `merge` 核验通过并入 converge
- `conflict` 冲突处理记录（须在 summary 写明判定依据：时间戳+哈希）
- `rollback` 回滚操作
- `rule-mod` rule/ 目录修改（必须人工评审）

## 三、sha256 计算口径

- 对**文件原始字节**计算，不加换行、不做编码转换：
  `sha256sum <file> | cut -d' ' -f1`
- 冲突判定：同一 file_path 出现两条不同 sha256 → 以 **timestamp 较新者为准**，但禁止直接覆盖，
  必须先人工比对差异，再以 `conflict` 动作登记解决结果后重新提交。

## 四、目录准入规则

| 目录 | 写权限 | 说明 |
|------|--------|------|
| `sandbox/` | 所有节点自由写 | 试错区，不影响真值 |
| `converge/` | 仅核验通过后合并 | 唯一真值源，默认只读 |
| `converge/rule/` | 人工评审后修改 | 元规则与字段字典 |
| `archive/` | 只读锁档 | 修改必须人工评审 |

## 五、Base（多维表格）字段映射（模式 A/B 通用）

- **真值主表** 列至少包含：`记录ID` `内容` `类型` `负责人` `更新时间` → 导出后由脚本映射为 `record_id, content, type, owner, updated_at`
- **变更审批表**：`变更ID` `目标文件` `核验状态` `处理人` → 对应账本 `status`
- **资产索引表**：`资产名` `链接/路径` `commit` → 对应 `converge/asset-index.md`

> 导出 CSV 需带表头；列名不一致时以本节映射为准，未识别列原样保留。
