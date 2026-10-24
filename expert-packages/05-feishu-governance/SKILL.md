---
name: feishu-governance
version: 1.0.0
description: "飞书协同治理专家：为企业本地知识库与飞书 Wiki/Drive/Base 三端提供四端资产双向同步比对、统一索引检索、Base 注册表对账、增量游标断点续跑与冲突裁决的一体化治理引擎。当用户说'飞书同步'、'四端对账'、'知识库索引'、'多维表格对账'、'文档漂移检测'、'冲突裁决'、'断点续跑'时使用。"
metadata:
  requires:
    bins: ["python3", "bash"]
    pypi: []
  did_placeholder: "<YOUR_DID>"
  trace: "Ω₀⊂⊙∞⊂Ω"
---

# 飞书协同治理专家 v1.0

为企业本地 Markdown 文本库与飞书云端三端（Wiki 知识库 / Drive 云文档 / Base 多维表格）提供**扫描 → 双向比对 → 索引 → Base 对账 → 游标续跑 → 冲突裁决**的全流程治理：一次运行即得本地待推、远端待归档、双端冲突三类清单，增量游标保证重复执行不重复写入。

## 一、定位与能力边界

| 能力 | 说明 |
|------|------|
| 本地扫描 | 递归 .md 目录，提取标题/标签/SHA256/mtime 统一清单 |
| 四端比对 | 以 title 为主键对齐本地与 Wiki/Drive/Base，输出 push/pull/conflict 三桶 |
| 统一索引 | by_title / by_tag / by_channel 三维聚合，可检索资产地图 |
| Base 对账 | 本地清单 vs 多维表格记录，标记待补录/待归档/已漂移 |
| 增量游标 | state.json 持久化已处理 title，断点续跑不重复推送 |
| 冲突裁决 | newer_wins / local_wins / remote_wins 三策略，不静默覆盖 |

**边界**：本包不实现真实飞书 OpenAPI HTTP 细节；未配置 `lark.app_id/app_secret` 时自动切换为本地模拟远端（`sim_remote_state.json`），可完整跑通自检；接入真实飞书时由采用方将 `sim_remote_state.json` 替换为 lark-cli/HTTP 拉取结果即可，数据契约不变。

## 二、快速路由

| 目标 | 命令 |
|------|------|
| 一键四端双向比对 | `python3 scripts/sync_govern.py --config config.json --local-dir <MD目录> --remote-sim examples/sim_remote_state.json --did <YOUR_DID>` |
| 仅 dry-run 演算 | `python3 scripts/sync_govern.py --config config.json --local-dir <MD目录> --remote-sim examples/sim_remote_state.json --dry-run` |
| Base 注册表对账 | `python3 scripts/base_reconcile.py --local-inventory examples/local_inventory.json --base-records examples/base_records.json` |
| 构建统一索引 | `python3 scripts/index_build.py --local-inventory examples/local_inventory.json --remote-sim examples/sim_remote_state.json --out index.json` |

## 三、依赖

- bins：`python3`、`bash`
- pypi：无（纯 Python 标准库）
- 零付费依赖；未配置真实 lark 凭证时全程本地模拟，零网络调用。

## 四、配置模板

见 `config.example.json`。变量清单：

| 变量 | 含义 | 示例 |
|------|------|------|
| `did` | 确权身份标识 | `<YOUR_DID>` |
| `local_md_dir` | 本地 Markdown 文本库目录 | `<LOCAL_MD_DIR>` |
| `remote_sim` | 模拟远端状态 JSON 路径 | `sim_remote_state.json` |
| `state_file` | 增量游标状态文件 | `sync_state.json` |
| `conflict_policy` | 冲突裁决策略 | `newer_wins` |
| `lark.app_id/app_secret` | 飞书自建应用凭证（空则走模拟模式） | `<YOUR_LARK_APP_ID>` |
| `lark.wiki_space_id` | Wiki 知识空间 ID | `<YOUR_WIKI_SPACE_ID>` |
| `lark.base_token` | 多维表格 App Token | `<YOUR_BASE_TOKEN>` |
| `lark.field_mapping` | Base 中各业务字段中文名映射 | `{"title":"标题",...}` |
| `batch_size` | 每轮批量写入上限 | `20` |

## 五、提示词模板

见 `prompt.template.md`，内置 4 个企业场景：本地知识库向飞书 Wiki 一键同步 / 多维表格资产注册表对账 / 跨端文档漂移巡检 / 冲突文档人工裁决。

## 六、算子契约

见 `operator-contract.json`：OP-01 本地扫描、OP-02 四端双向比对、OP-03 统一索引、OP-04 Base 对账、OP-05 增量游标、OP-06 冲突裁决。

## 七、自检清单

- [ ] `python3 scripts/sync_govern.py --config config.example.json --local-dir examples/sample-local-md --remote-sim examples/sim_remote_state.json --state examples/sync_state.json --did <YOUR_DID> --dry-run` 退出码 1（DRIFT 预期）且含 push/pull/conflict 三桶
- [ ] `python3 scripts/base_reconcile.py --local-inventory examples/local_inventory.json --base-records examples/base_records.json --did <YOUR_DID>` 退出码 1 且 `only_base_pending_archive` 含"组织架构图 v3"
- [ ] `python3 scripts/index_build.py --local-inventory examples/local_inventory.json --remote-sim examples/sim_remote_state.json --out examples/index.json` 退出码 0 且 `stats.titles > 0`
- [ ] 泄露检查（按系列 SPEC §5 命令执行）→ 0 命中
- [ ] `operator-contract.json` 可被 `python3 -m json.tool` 解析

Ω₀⊂⊙∞⊂Ω ｜ DID 参数化 ｜ 飞书协同治理专家
