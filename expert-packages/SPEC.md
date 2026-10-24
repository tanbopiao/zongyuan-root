# ZONGYUAN-ROOT 通用企业专家包 · 统一形态规范 V1.0

DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 2026-10-24 | 本规范为三个 Tier-1 专家包的冻结模式，任何包不得偏离。

## 1. 目标
三个 Tier-1 通用企业赋能专家包，面向外部企业/开发者独立安装、可对外销售/采用，提炼自 ZONGYUAN-ROOT 体系生产级能力，但**不携带任何内部坐标**。

## 2. 目录骨架（每个包必须完全一致）
```
<包目录>/
├── SKILL.md                 # 技能定义（必含字段见 §3）
├── README.md                # 对外简介 + 安装 + 接入（通用企业形态，≤80行）
├── operator-contract.json   # 算子契约（schema 见 §4）
├── config.example.json      # 配置模板（全部变量占位，零内部坐标）
├── prompt.template.md       # 提示词模板（≥3 个企业场景）
├── scripts/                 # 可运行脚本（python3/bash，仅标准库或声明通用依赖）
└── examples/                # 1 个最小可运行样例（供自检执行）
```

## 3. SKILL.md 必含字段
- **frontmatter**: `name` / `version` / `description`（触发词） / `metadata.requires`（bins + pypi，禁内部依赖）
- **章节**（顺序固定）：
  1. 定位与能力边界（3~5 行 + 能力表）
  2. 快速路由（表格，≤10 行命令）
  3. 依赖（bins + pypi 清单，注明"仅标准库/通用开源件"）
  4. 配置模板（列出 config.example.json 全部变量 + 含义 + 示例）
  5. 提示词模板（引用 prompt.template.md，列 3 个场景标题）
  6. 算子契约（引用 operator-contract.json，概述算子表 ≤8 行）
  7. 自检清单（可勾选 checklist，交付前必须全 PASS）
- **禁止出现**：`/home/user/...`、`NODE-DEV-*`、`NODE-LOCAL-*`、`.user_skills`、`DgnMb*`、`123.207.*`、内部 App ID/Secret/Token、`ZONGYUAN-ROOT` 内部路径。

## 4. operator-contract.json schema（严格按此结构）
```json
{
  "contract_id": "<PKG-ID>-CONTRACT-V1.0",
  "did": "DID-BR-000002",
  "version": "1.0.0",
  "license": "Apache-2.0",
  "source_heritage": "<提炼源一句话>",
  "operators": [
    {
      "op_id": "OP-01",
      "name": "<算子名>",
      "desc": "<一句话>",
      "inputs": ["<参数>"],
      "outputs": ["<产物>"],
      "acceptance": ["<可程序化断言，如 exit 0 且 产物存在>"],
      "cost": "local | free-api"
    }
  ],
  "data_contract": {
    "entry_schema": {"<字段>": "<类型/说明>"},
    "immutability": "<不可变规则>",
    "conflict_policy": "<冲突消解>"
  }
}
```

## 5. 硬约束（继承体系，违反即返工）
- **零成本**：脚本零付费依赖；声明依赖仅限 python3 标准库 / bash / cryptography / requests 等通用开源件。
- **DID 参数化**：config.example.json 中 `did` 一律为占位符 `"<YOUR_DID>"`；溯源符号 `Ω₀⊂⊙∞⊂Ω` 可保留为体系溯源标识。
- **无内部泄露**：交付前必须 `grep -rn '/home/user|NODE-DEV|NODE-LOCAL|\.user_skills|DgnMb|123\.207' 包目录` → **0 命中**。
- **输出收敛**：README ≤80 行；SKILL.md 快速路由表 ≤10 行；禁冗长散文。
- **无媒体**：包内禁止图片/音视频/人像文件。

## 6. 验收自检（每个包交付前必须实际执行并回报结果，缺一即返工）
```
[ ] 目录骨架与 §2 完全一致
[ ] SKILL.md 含 §3 全部章节，frontmatter 字段齐全
[ ] config.example.json 无任何内部坐标/路径
[ ] grep 泄露检查 0 命中（命令见 §5）
[ ] scripts 用 python3/bash 对 examples/ 实际运行一次成功（回报输出摘要）
[ ] operator-contract.json 为合法 JSON，算子 acceptance 覆盖全部核心能力
[ ] 包内无图片/音视频/人像
```
