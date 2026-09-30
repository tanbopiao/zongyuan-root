---
name: data-forge
description: "DATA-FORGE 数据锻造引擎V1.0。元极恒一自治体系数据处理核心，支持多格式数据导入(CSV/Excel/JSON/TSV)、智能数据清洗(去重/空行/空格)、统计分析(数值列统计/分类列Top5/分布)、格式转换(CSV↔JSON)、数据摘要报告生成。触发词：数据处理、数据分析、数据清洗、CSV处理、Excel处理、统计分析、数据转换、数据锻造、data-forge。当用户需要处理表格数据、清洗数据集、做统计分析、或转换数据格式时使用。"
---

# DATA-FORGE｜数据锻造引擎

元极恒一自治体系数据处理核心。多格式导入→智能清洗→统计分析→格式转换，全链路数据锻造。

> DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | 版本: V1.0

## 核心能力

| 能力 | 说明 |
|------|------|
| 多格式导入 | CSV/TSV/JSON/Excel(xlsx) 自动识别 |
| 智能清洗 | 去重、空行移除、首尾空格去除 |
| 统计分析 | 数值列(min/max/mean/sum)、分类列(唯一值/Top5) |
| 格式转换 | CSV↔JSON 互转 |
| 摘要报告 | 结构化数据锻造报告输出 |

## 命令速查

```bash
# 1. 查看数据基本信息
python3 scripts/data_processor.py info --input data.csv

# 2. 数据清洗（去重+空行+空格）
python3 scripts/data_processor.py clean --input data.csv --output cleaned.json
python3 scripts/data_processor.py clean -i data.csv -o out.json --no-dedup   # 不去重

# 3. 统计分析
python3 scripts/data_processor.py analyze --input data.csv
python3 scripts/data_processor.py analyze -i data.csv --clean --output stats.json  # 先清洗再分析

# 4. 格式转换
python3 scripts/data_processor.py convert --input data.csv --output data.json
python3 scripts/data_processor.py convert -i data.json -o data.csv
```

## 清洗选项

| 选项 | 默认 | 说明 |
|------|------|------|
| `--no-dedup` | 关闭去重 | 基于行内容MD5去重 |
| `--keep-empty` | 保留空行 | 全空行默认移除 |
| `--no-strip` | 保留空格 | 字符串首尾空格默认去除 |

## 输出格式

- **clean**: 输出清洗后JSON数组
- **analyze**: 输出统计JSON（含数值列/分类列详情）
- **info**: 终端输出基本信息
- **convert**: 输出目标格式文件

## 约束

- Excel支持需要openpyxl库，未安装时自动降级提示
- 大文件建议分批处理，单文件推荐<100MB
- 所有输出默认UTF-8编码，CSV使用utf-8-sig兼容Excel
- 数值列判定标准：超过50%的值可转为浮点数
