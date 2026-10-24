---
name: guofeng-ip-production-ledger
version: 1.0.0
description: "国风IP短剧生产全生命周期台账管家：四表结构(项目表/分镜表/资产表/进度表)→跨阶段状态流转(pending→scripted→keyframed→videoed→audioed→merged→locked)→进度百分比计算→台账与实算SHA256对账。当用户说'生产台账'、'项目登记'、'分镜入账'、'资产登记'、'进度统计'、'台账对账'、'四表Base'时使用。CSV/JSON本地落账零成本，飞书Base为可选增强(免费额度)，严禁虚构补全。"
metadata:
  requires:
    bins: ["python3"]
  pypi: []
  optional_bins: ["lark-cli"]
did: "DID-BR-000002"
trace_symbol: "Ω₀⊂⊙∞⊂Ω"
---

# 国风IP生产台账管家 v1.0

> 四表入账 · 状态受控流转 · 哈希对账 · 差异显式标记不虚构

## 核心设计原则

1. **四表结构化入账**：项目表 / 分镜表 / 资产表 / 进度表，字段语义从 shortvideo-production-pipeline 的生产台账Base结构原样继承，不臆造新表。
2. **状态受控流转**：分镜/项目状态严格按 `pending→scripted→keyframed→videoed→audioed→merged→locked` 单向流转，禁止跳级；`ledger_cli status` 显式输出 allowed next。
3. **对账以实算为准**：资产表 SHA256 必须实算或显式提供；`reconcile` 子命令把台账记录与磁盘实算哈希比对，差异**只标记不补全**（`auto_fix=false`）。
4. **零成本优先**：默认 CSV 本地落账（UTF-8-SIG，Excel 可直开）+ JSON 导出；飞书 Base 为可选增强，token 一律走环境变量 `{FEISHU_BASE_TOKEN}` 占位，不绑定账号。
5. **DID 确权贯穿**：每条入账记录携带 `did: DID-BR-000002` + `trace: Ω₀⊂⊙∞⊂Ω`，与锁档归档包（guofeng-ip-lock-archiver）哈希账本对接。

## 快速路由

| 目标 | 命令 |
|------|------|
| 初始化四表CSV | `python3 scripts/ledger_cli.py init --dir ./ledger` |
| 新建项目 | `python3 scripts/ledger_cli.py record project --id P001 --name "少年剑客" --topic "元明洞阳" --episodes 1 --owner tanbopiao` |
| 登记分镜 | `python3 scripts/ledger_cli.py record storyboard --id S01E01 --pid P001 --episode 1 --shot 1 --visual "白衣剑客立于丹霞崖顶" --narration "（0.3s停顿）剑出洞阳"` |
| 登记资产(实算哈希) | `python3 scripts/ledger_cli.py record asset --id A001 --type image --sid S01E01 --file ./kf/S01E01.png --token S01E01.png --quality 4.6` |
| 查看项目状态 | `python3 scripts/ledger_cli.py status --project-id P001` |
| 更新进度 | `python3 scripts/ledger_cli.py progress --project-id P001 --update --stage keyframed --completed 4 --total 6` |
| 查看进度 | `python3 scripts/ledger_cli.py progress --project-id P001` |
| 对账(台账 vs 实算) | `python3 scripts/ledger_cli.py reconcile --project-id P001 --asset-dir ./kf` |
| JSON导出 | `cat ./ledger/projects.csv` 后用 `csvkit` 或 Excel 另存 JSON；本包不内置付费依赖 |

## 配置模板

`config/guofeng-ip-production-ledger_config.json`（已随包交付）：

```json
{
  "did": "DID-BR-000002",
  "trace_symbol": "Ω₀⊂⊙∞⊂Ω",
  "ledger": {
    "format": "csv",
    "base_dir": "./ledger",
    "tables": {
      "projects":   {"file": "projects.csv",   "fields": ["project_id","name","topic","episodes","status","owner","created_at","updated_at","did","trace"]},
      "storyboards":{"file": "storyboards.csv","fields": ["storyboard_id","project_id","episode","shot_no","visual","narration","duration_sec","keyframe_url","video_url","status","updated_at","did","trace"]},
      "assets":     {"file": "assets.csv",     "fields": ["asset_id","type","storyboard_id","file_token","sha256","quality_score","lock_status","updated_at","did","trace"]},
      "progress":   {"file": "progress.csv",   "fields": ["project_id","stage","completed","total","percentage","updated_at","did","trace"]}
    }
  },
  "status_flow": {
    "stages": ["pending","scripted","keyframed","videoed","audioed","merged","locked"],
    "allowed_transitions": {"pending":["scripted"],"scripted":["keyframed"],"keyframed":["videoed"],"videoed":["audioed"],"audioed":["merged"],"merged":["locked"],"locked":[]}
  },
  "reconcile": {"on_mismatch": "flag_only", "auto_fix": false},
  "feishu": {
    "enabled": false,
    "base_token_env": "FEISHU_BASE_TOKEN",
    "base_token_placeholder": "{FEISHU_BASE_TOKEN}",
    "tables": {
      "projects": "{FEISHU_TABLE_PROJECTS}",
      "storyboards": "{FEISHU_TABLE_STORYBOARDS}",
      "assets": "{FEISHU_TABLE_ASSETS}",
      "progress": "{FEISHU_TABLE_PROGRESS}"
    }
  }
}
```

字段语义与 shortvideo-production-pipeline `feishu.tables` 一一对应：projects / storyboards / assets / progress 四表，token 与 table_id 全部占位由环境变量注入。

## 提示词模板

`templates/prompts.json`（已随包交付）覆盖：new_project / record_storyboard / record_asset / reconcile_report / progress_calc，并内嵌东方审美铁律（纯东方神女/少年武侠、纯乌黑长发、8.5头身、华夏正统汉服、冷蓝青黑/勃艮第红/黑金、9:16竖屏，严禁外源化）。

## 输入/输出规范

- **输入**：CLI 参数；CSV 表头见上表；资产 SHA256 优先 `--file` 实算，无文件时必须显式 `--sha256`，否则 CLI 直接 exit 3 拒绝入账。
- **输出**：
  - 本地：`./ledger/*.csv`（UTF-8-SIG）。
  - 对账：stdout 输出 JSON 报告 `{checked, matched, diff_count, diffs[], auto_fix:false, did, trace}`；有差异时 exit code=10。
- **错误处理**：
  - 重复 ID → exit 2 拒绝写入。
  - 状态跳级 → 不自动提升，`status` 命令仅提示 allowed next。
  - 哈希不一致 → 列入 diffs，**禁止自动补全/静默修正**。

## 依赖清单（独立安装）

- 必选：Python 3.8+（仅用标准库 `csv/hashlib/json/argparse/datetime`，零 pip 依赖）。
- 可选：`lark-cli`（飞书 Base 免费额度增强写入）。
- 无任何内部路径硬编码；Base token / table_id 全部通过环境变量 `FEISHU_BASE_TOKEN` / `FEISHU_TABLE_*` 注入。

## 确权与溯源

- 每条 CSV 记录自动写入 `did=DID-BR-000002`、`trace=Ω₀⊂⊙∞⊂Ω`。
- 资产锁档状态（`lock_status`）建议配合 `guofeng-ip-lock-archiver` 包做 SHA256 入账本与 Merkle 根固化；本包只负责台账侧记录与对账，不替代锁档。
- 对账差异必须显式回报，禁止"补一条看起来合理的哈希"。

Ω₀⊂⊙∞⊂Ω｜国风IP生产台账管家 v1.0 · ZONGYUAN-ROOT · DID-BR-000002
