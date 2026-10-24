---
name: enterprise-knowledge-hub
version: 1.0.0
description: "企业知识中枢专家：为多部门企业提供结构化知识条目入库 + 索引池账本 + DID 同源校验的跨部门检索网关 + 条目不可变与冲突消解的一体化知识治理流水线。当用户说'企业知识库'、'跨部门检索'、'知识条目入库'、'索引账本'、'知识冲突消解'、'同源身份校验'、'法务文档归档检索'、'研发经验沉淀'时使用。"
metadata:
  requires:
    bins: ["python3", "bash"]
    pypi: []
  did_placeholder: "<YOUR_DID>"
  trace: "Ω₀⊂⊙∞⊂Ω"
---

# 企业知识中枢专家 v1.0

为任何多部门企业提供**知识条目入库 → 索引池账本 → DID 同源校验 → 跨部门检索 → 冲突消解 → 账本导出**的全流程知识治理，原文不集中迁移、仅同步摘要索引与哈希凭证，单条篡改即失配，跨部门可统一检索。

## 一、定位与能力边界

| 能力 | 说明 |
|------|------|
| 知识条目入库 | 逐文件 SHA256 指纹，结构化条目（部门/DID/时间戳/标签/路径）账本化 |
| 索引构建 | 按 tags/path/title 构建可检索索引，幂等可重跑 |
| DID 同源校验 | 调用方身份与账本归属身份不一致即拒绝 |
| 跨部门检索网关 | 关键词命中索引池元信息，原文按需受控拉取，不回传本体 |
| 条目不可变 | 入库条目禁改写，变更生成新条目，旧条目永久保留 |
| 冲突消解 | 同路径不同哈希：新者保留、旧者标 conflict，绝不静默覆盖 |

**边界**：本包不提供向量嵌入/语义大模型检索，输出为关键词级可审计索引；语义检索为可选接入项。原文不集中托管，跨部门仅共享索引摘要。

## 二、快速路由

| 目标 | 命令 |
|------|------|
| 知识条目入库 + 构建索引 | `python3 scripts/index_build.py --root <知识根> --ledger <账本.json> --node <部门> --did <YOUR_DID>` |
| 跨部门关键词检索 | `python3 scripts/index_search.py --ledger <账本.json> --did <YOUR_DID> --keyword <词>` |
| 契约校验 + 不可变重算 + 冲突报告 | `python3 scripts/contract_validate.py --ledger <账本.json> --root <知识根>` |
| 网关状态统计 | `bash scripts/knowledge_gateway.sh --ledger <账本.json> --did <YOUR_DID> --stats` |
| 网关检索（bash 封装） | `bash scripts/knowledge_gateway.sh --ledger <账本.json> --did <YOUR_DID> --search <词>` |
| 账本摘要导出 | `bash scripts/knowledge_gateway.sh --ledger <账本.json> --did <YOUR_DID> --export` |

## 三、依赖

- bins：`python3`、`bash`
- pypi：无（纯标准库）
- 全部本地执行，零网络、零付费依赖。

## 四、配置模板

见 `config.example.json`。变量清单：

| 变量 | 含义 | 示例 |
|------|------|------|
| `did` | 知识归属身份（采用方 DID/企业 ID） | `<YOUR_DID>` |
| `trace_symbol` | 溯源符号（可选） | `Ω₀⊂⊙∞⊂Ω` |
| `hub_id` | 知识中枢标识 | `ENT-KNOWLEDGE-HUB-V1.0` |
| `node_id` | 当前部门/节点标识 | `<YOUR_DEPARTMENT_NODE_ID>` |
| `knowledge_root` | 知识根目录（原文所在） | `<PATH_TO_KNOWLEDGE_ROOT>` |
| `ledger_path` | 索引账本 JSON 路径 | `<PATH_TO_INDEX_LEDGER>.json` |
| `search_fields` | 检索命中字段 | `["tags","path","title"]` |
| `exclude_patterns` | 跳过文件模式 | `["__pycache__",".git"]` |
| `conflict_policy` | 冲突策略 | `newer_timestamp_kept_older_marked_conflict` |
| `entry_prefix` | 条目 ID 前缀 | `K` |

## 五、提示词模板

见 `prompt.template.md`，内置 3 个企业场景：多部门知识库统一检索 / 法务合同文档归档 / 研发经验沉淀复用。

## 六、算子契约

见 `operator-contract.json`：OP-01 知识条目入库、OP-02 索引构建、OP-03 跨节点检索、OP-04 同源身份校验、OP-05 冲突消解、OP-06 账本导出。

## 七、自检清单

- [ ] `python3 scripts/index_build.py --root examples/knowledge-docs --ledger /tmp/kb-ledger.json --node SELFCHECK-DEPT --did <YOUR_DID>` 退出码 0 且 `自校验=PASS`
- [ ] `python3 scripts/index_search.py --ledger /tmp/kb-ledger.json --did <YOUR_DID> --keyword 合同` 输出命中条目；错误 DID 退出码 2
- [ ] `python3 scripts/contract_validate.py --ledger /tmp/kb-ledger.json --root examples/knowledge-docs` 输出 `error_count: 0`
- [ ] `bash scripts/knowledge_gateway.sh --ledger /tmp/kb-ledger.json --did <YOUR_DID> --stats` 输出索引总量
- [ ] 泄露检查（按 SPEC §5 命令执行）→ 0 命中
- [ ] `operator-contract.json` 与 `config.example.json` 可被 `python3 -m json.tool` 解析

Ω₀⊂⊙∞⊂Ω ｜ DID 参数化 ｜ 企业知识中枢专家
