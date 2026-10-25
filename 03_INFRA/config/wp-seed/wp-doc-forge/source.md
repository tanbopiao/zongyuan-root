---
name: doc-forge
description: "DOC-FORGE 文档锻造引擎V1.0。元极恒一自治体系文档生成核心，内置6种专业模板(技术白皮书/分析报告/一页纸简历/协议文档/决策备忘录/真值卡)，支持模板引擎内容注入、多格式导出(Markdown/HTML/JSON)、自动确权签名(DID+溯源+哈希)。触发词：文档生成、白皮书、报告生成、简历生成、协议起草、决策备忘录、真值卡、文档锻造、doc-forge。当用户需要基于模板生成结构化文档、白皮书、报告、简历、或协议时使用。"
---

# DOC-FORGE｜文档锻造引擎

元极恒一自治体系文档生成核心。模板引擎→内容注入→多格式导出，全链路文档锻造。

> DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | 版本: V1.0

## 核心能力

| 能力 | 说明 |
|------|------|
| 6种专业模板 | 白皮书/报告/简历/协议/决策备忘录/真值卡 |
| 模板引擎 | JSON内容注入，按结构自动渲染 |
| 多格式导出 | Markdown / HTML / JSON |
| 自动确权 | DID+溯源标识+内容哈希+时间戳 |
| 自定义模板 | 支持references/目录下自定义JSON模板 |

## 内置模板

| 模板名 | 名称 | 适用场景 |
|--------|------|---------|
| `whitepaper` | 技术白皮书 | 架构/技术/理论白皮书 |
| `report` | 分析报告 | 行业/竞品/研究报告 |
| `resume` | 一页纸简历 | 求职简历精简版 |
| `contract` | 协议文档 | 商业/劳动/保密协议 |
| `decision_memo` | 决策备忘录 | 三维稳态决策记录 |
| `truth_card` | 真值卡 | 高密度真值提炼卡 |

## 命令速查

```bash
# 1. 列出可用模板
python3 scripts/doc_generator.py templates

# 2. 生成文档（基于内容JSON）
python3 scripts/doc_generator.py generate --template whitepaper --content content.json --output whitepaper.md
python3 scripts/doc_generator.py generate -t resume -c resume.json -f html -o resume.html

# 3. 快速生成（仅标题，空模板）
python3 scripts/doc_generator.py generate --template truth_card --title "QR分解真值卡" --output card.md

# 4. 格式选择
python3 scripts/doc_generator.py generate -t report -c data.json -f markdown   # 默认
python3 scripts/doc_generator.py generate -t report -c data.json -f html         # HTML
python3 scripts/doc_generator.py generate -t report -c data.json -f json         # 结构化JSON
```

## 内容JSON格式

```json
{
  "title": "文档标题",
  "metadata": {"作者": "元极恒一", "版本": "1.0"},
  "abstract": "摘要内容...",
  "background": "背景...",
  "architecture": "架构...",
  "conclusion": "结论...",
  "references": ["来源1", "来源2"]
}
```

> 字段名需与模板structure对应，缺失字段自动跳过。

## 自定义模板

在 `references/` 目录下创建 `{template_name}.json`：

```json
{
  "name": "自定义模板名",
  "structure": ["section1", "section2", "section3"],
  "description": "模板说明"
}
```

## 输出特性

- **Markdown**: 标准GFM格式，含元数据引用块、确权页脚
- **HTML**: 独立完整HTML，内嵌黑金风格CSS，可直接浏览器打开
- **JSON**: 结构化输出，含content_hash(SHA256)、生成时间戳、DID确权

## 约束

- 所有输出自动附加DID-BR-000002确权标识
- 内容哈希基于SHA256，用于后续归档校验
- 模板structure中的字段名使用snake_case
- 大文档建议分章节生成后合并
