---
name: knowledge-graph
version: 1.0.0
description: "知识图谱专家：从企业非结构化文档（txt/md）按规则词典+正则自动抽取实体-关系三元组，跨文档实体归一（别名/缩写映射到规范名），构建 JSON 节点/边图谱，做传递推理补全与孤立节点检测，输出节点/边/密度/连通分量/孤立节点指标，按公理/定理/方法/数据/案例/决策/创意/风险/协议九类自动归类资产，并对图谱版本做 SHA256 哈希快照防无声漂移。当用户说'知识图谱'、'实体关系抽取'、'三元组抽取'、'实体归一'、'图谱补全'、'孤立节点'、'九类归类'、'图谱版本快照'时使用。"
metadata:
  requires:
    bins: ["python3"]
    pypi: []
  did_placeholder: "<YOUR_DID>"
  trace: "Ω₀⊂⊙∞⊂Ω"
---

# 知识图谱专家 v1.0

为任何企业文档库提供**规则词典三元组抽取 → 跨文档实体归一 → JSON 图谱构建 → 传递推理补全 → 图谱指标度量 → 九大元类归类 → 哈希稳态快照**的轻量化知识图谱流水线：不依赖图库/向量库/大模型 API，纯标准库本地运行，一次扫描即得结构化图谱与版本锚点。

## 一、定位与能力边界

| 能力 | 说明 |
|------|------|
| 三元组抽取 | 按自定义实体词典 + 正则关系模式，从 txt/md 抽取 (实体,关系,实体)，两端须命中词典才收录 |
| 实体归一 | 别名/缩写/全称统一映射到规范名，同一实体全局唯一 ID |
| 图谱构建 | 三元组去重合并为 JSON 节点/边结构，记录来源文件与支持度 |
| 图谱补全 | 同谓语传递推理（A→B→C 推导 A→C 候选），低置信度提示不自动入库 |
| 图谱指标 | 节点数/边数/密度/连通分量数/孤立节点数与清单 |
| 九类归类 | 节点按 公理/定理/方法/数据/案例/决策/创意/风险/协议 关键词词典归类 + 置信度 |
| 稳态快照 | 全图排序后 SHA256 哈希，变更须版本补丁号升级，防无声漂移 |

**边界**：本包不做语义向量嵌入/远程图数据库导入；抽取精度取决于采用方词典与模式质量，适合规则可控的企业文档治理场景。

## 二、快速路由

| 目标 | 命令 |
|------|------|
| 抽取三元组 | `python3 scripts/extract_triples.py --docs <文档目录> --dict <entity-dict.json> --out triples.jsonl --did <YOUR_DID>` |
| 建图+指标+补全+归类+快照 | `python3 scripts/build_graph.py --triples triples.jsonl --dict <entity-dict.json> --outdir out/ --did <YOUR_DID>` |
| 带版本升级判定的重建图 | `python3 scripts/build_graph.py --triples triples.jsonl --dict <dict.json> --outdir out/ --prev-snapshot out/graph-snapshot.json --did <YOUR_DID>` |
| 一键自检（examples） | `bash scripts/selfcheck.sh` |

## 三、依赖

- bins：`python3`（≥3.8）
- pypi：无（纯 Python 标准库：re/json/hashlib/argparse/pathlib）
- 全部本地执行，零付费依赖、零网络调用。

## 四、配置模板

见 `config.example.json`。变量清单：

| 变量 | 含义 | 示例 |
|------|------|------|
| `did` | 确权身份标识 | `<YOUR_DID>` |
| `trace_symbol` | 溯源符号（可选） | `Ω₀⊂⊙∞⊂Ω` |
| `docs_dir` | 待抽取文档目录（.txt/.md） | `<DOCS_DIR>` |
| `entity_dict` | 实体与关系词典 JSON 路径 | `<entity-dict>.json` |
| `triples_out` | 三元组输出（.jsonl） | `out/triples.jsonl` |
| `graph_outdir` | 图谱产物输出目录 | `out/` |
| `prev_snapshot` | 上一版图谱快照（空则初版） | `out/graph-snapshot.json` |

## 五、提示词模板

见 `prompt.template.md`，内置 3 个企业场景：产品文档知识图谱抽取 / 技术架构实体关系梳理 / 图谱版本漂移巡检。

## 六、算子契约

见 `operator-contract.json`：OP-01 三元组抽取、OP-02 实体归一与建图、OP-03 图谱指标、OP-04 传递补全、OP-05 九类归类、OP-06 哈希稳态快照。

## 七、自检清单

- [ ] `bash scripts/selfcheck.sh` 退出码 0，输出 node_count≥8、edge_count≥10
- [ ] `out/graph-report.json` 可被 `python3 -m json.tool` 解析
- [ ] 重跑一次（带 `--prev-snapshot`），图无变化时 `version_bump == "unchanged"`
- [ ] 泄露检查（按系列 SPEC §5 命令执行）→ 0 命中
- [ ] `operator-contract.json` 可被 `python3 -m json.tool` 解析

Ω₀⊂⊙∞⊂Ω ｜ DID 参数化 ｜ 知识图谱专家
