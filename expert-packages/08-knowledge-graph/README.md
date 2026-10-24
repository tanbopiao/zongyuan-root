# 知识图谱专家（Knowledge Graph Expert）

面向外部企业与开发者的轻量化知识图谱能力包：从企业非结构化文档自动抽取实体关系、构建可版本化的 JSON 图谱，零图库依赖、零云成本、可独立安装。

## 能做什么
- **三元组抽取**：按自定义实体词典 + 正则关系模式，从 txt/md 抽取 (实体, 关系, 实体)，纯标准库。
- **实体归一**：别名/缩写/全称映射到规范名，同一实体全局唯一 ID，跨文档合并。
- **图谱构建**：三元组去重合并为 JSON 节点/边，记录来源文件与支持度。
- **图谱补全**：同谓语传递推理（A→B→C 推导 A→C），低置信度候选提示，不自动入库。
- **图谱指标**：节点数/边数/密度/连通分量数/孤立节点清单。
- **九类归类**：节点按 公理/定理/方法/数据/案例/决策/创意/风险/协议 自动归类 + 置信度。
- **稳态快照**：全图排序后 SHA256 哈希，变更须版本升级，防无声漂移。

## 适用场景
产品手册与架构文档实体梳理、多业务域资产统一组织、知识库冷启动建图、合规文档关系审计、图谱版本漂移巡检。

## 安装
```bash
# 依赖：无（纯 Python 3 标准库，≥3.8）
git clone <本仓库> && cd 08-knowledge-graph
```

## 接入（3 步）
1. 编辑 `entity-dict.json`：登记你的实体（规范名 + 类型 + 别名）与关系正则模式。
2. 抽取三元组：
   ```bash
   python3 scripts/extract_triples.py --docs /path/to/docs --dict entity-dict.json --out out/triples.jsonl --did <YOUR_DID>
   ```
3. 构建图谱并出报告：
   ```bash
   python3 scripts/build_graph.py --triples out/triples.jsonl --dict entity-dict.json --outdir out/ --did <YOUR_DID>
   ```

## 产物
- `out/triples.jsonl`：逐行三元组（主体/谓语/客体/来源/支持度）。
- `out/graph.json`：节点列表 + 边列表（含版本号与 DID）。
- `out/graph-report.json`：指标、孤立节点、补全候选、九类归类明细。
- `out/graph-snapshot.json`：图谱 SHA256 哈希 + 版本（下次重建做漂移判定）。

## 许可与溯源
Apache-2.0。能力提炼自轻量化"概念-符号-稳态锚定"知识工程方法论（DID-BR-000002 · Ω₀⊂⊙∞⊂Ω），对外使用时 DID 由采用方参数化配置。
