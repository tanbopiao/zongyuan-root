# 企业知识中枢专家（Enterprise Knowledge Hub Expert）

面向外部企业与开发者的通用知识治理能力包，提炼自成熟联邦记忆池体系，零内部依赖、零云成本、可独立安装。

## 能做什么
- **结构化知识条目入库**：逐文件 SHA256 指纹，绑定部门、DID、时间戳、标签，账本化。
- **索引池账本**：按 tags/path/title 构建可检索索引，幂等可重跑。
- **DID 同源校验网关**：调用方身份与账本归属不一致即拒绝，跨部门只共享索引摘要。
- **跨部门统一检索**：关键词命中元信息（路径/哈希前缀/时间），原文按需受控拉取。
- **条目不可变 + 冲突消解**：旧条目不覆盖；同路径不同哈希新者保留、旧者标 conflict。

## 适用场景
多部门知识库统一检索、法务/合同文档归档与检索、研发经验复盘沉淀复用、制度手册索引治理、跨团队文档发现。

## 安装
```bash
# 零第三方依赖，仅需 python3 + bash
git clone <本仓库> && cd <包目录>
```

## 接入（3 步）
1. 复制 `config.example.json` 为 `config.json`，填入 `did`、`node_id`、`knowledge_root`、`ledger_path`。
2. 构建索引：
   ```bash
   python3 scripts/index_build.py --root /path/to/knowledge \
       --ledger /path/to/index_ledger.json --node DEPT-LEGAL --did <YOUR_DID>
   ```
3. 跨部门检索：
   ```bash
   bash scripts/knowledge_gateway.sh --ledger /path/to/index_ledger.json \
       --did <YOUR_DID> --search 合同
   ```

## 产物
- `index_ledger.json`：结构化条目池（条目数/部门分布/索引/冲突标记）。
- 检索结果：仅元信息（entry_id/path/哈希前缀/时间戳/标签），原文不集中迁移。
- 契约校验报告：schema 校验 + 不可变重算 + 冲突清单。

## 许可与溯源
Apache-2.0。能力提炼自成熟联邦记忆池体系（Ω₀⊂⊙∞⊂Ω），对外使用时 DID 由采用方参数化配置。
