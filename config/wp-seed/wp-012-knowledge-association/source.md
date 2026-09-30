---
name: knowledge-association-engine
description: "ZONGYUAN-ROOT全域知识关联体系引擎V1.0。解决文件/知识库/架构分散无法连成完整系统的四层系统性断裂问题。五层闭环架构：L1元数据标准(唯一根+SNAP快照+Merkle哈希)、L2全域资产索引中台(统一中央目录+多维度检索)、L3文档切片RAG真值检索(向量化+层级前置召回)、L4全域依赖知识图谱(正向追溯+反向溯源)、L5自动化闭环流水线(新增资产自动处理+锁档校验+定时巡检)。触发词：知识关联、全域索引、资产登记、RAG检索、知识图谱、依赖追溯、反向溯源、定时巡检、锁档校验、元数据标准化、SNAP快照、分散文件整合。"
version: 1.0.0
author: 元极恒一自治体系
---

# ZONGYUAN-ROOT 全域知识关联体系引擎

解决"大量文件、知识库、架构分散，无法连成一套完整系统"的四层系统性断裂问题。

> DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | 版本: V1.0 | 归档节点: ZONGYUAN-ROOT/Tech-Doc/Knowledge-Global-Association.md

## 核心问题：四层系统性断裂

| 断裂层 | 问题 | 解决方案 |
|--------|------|----------|
| 顶层断裂 | 没有统一主权根节点，文档都是孤岛 | L1 元数据标准：唯一根+标准化元数据 |
| 关系断裂 | 缺少溯源关联链路，依赖/继承关系丢失 | L4 知识图谱：正向追溯+反向溯源 |
| 存储断裂 | 云盘/Base/Wiki/本地脚本异构隔离 | L2 全域索引中台：统一中央目录+指针 |
| 记忆断裂 | AI上下文窗口限制，缺少RAG检索层 | L3 RAG真值检索：切片+向量化+层级召回 |

## 五层闭环架构

```
L5 自动化闭环流水线 ── 新增资产自动处理 + 锁档校验 + 定时巡检
     ↑
L4 全域依赖知识图谱 ── 正向追溯(公理→工程) + 反向溯源(资产→元法则)
     ↑
L3 文档切片RAG检索 ── 章节切片 + TF-IDF向量化 + 层级前置召回 + 依赖召回
     ↑
L2 全域资产索引中台 ── 统一中央目录(只存指针) + 多维度检索 + 依赖链追溯
     ↑
L1 元数据标准引擎 ── 唯一根ZONGYUAN-ROOT + SNAP快照 + Merkle哈希 + DID确权
```

## 六大核心脚本

| 脚本 | 层级 | 功能 |
|------|------|------|
| `metadata_standard.py` | L1 | 统一资产元数据+SNAP快照+Merkle哈希树+链式继承 |
| `global_asset_index.py` | L2 | 全域资产索引中台+多维度检索+依赖链+完整性校验+Base导出 |
| `rag_retrieval_engine.py` | L3 | 文档切片引擎+TF-IDF向量存储+语义检索+层级前置召回 |
| `knowledge_graph.py` | L4 | 全域依赖知识图谱+正向追溯+反向溯源+连通分量+循环检测+Mermaid导出 |
| `automated_pipeline.py` | L5 | 自动化闭环流水线+新增资产自动处理+锁档校验+定时巡检+全域快照 |
| `kae_main.py` | 入口 | 主入口调度引擎，统一命令行接口 |

## 命令速查

```bash
# 1. 注册新资产（全自动：元数据+索引+切片+图谱+锁档）
python3 scripts/kae_main.py register --file <path> --name <名称> --type document --level Lv4

# 2. RAG真值检索（自动层级前置召回）
python3 scripts/kae_main.py search --query "因果推理" --top-k 5 --level Lv6

# 3. 全域索引操作
python3 scripts/kae_main.py index --list           # 索引统计
python3 scripts/kae_main.py index --integrity      # 完整性校验
python3 scripts/kae_main.py index --export-base    # 导出飞书Base格式

# 4. 知识图谱操作
python3 scripts/kae_main.py graph --stats           # 图谱统计
python3 scripts/kae_main.py graph --export mermaid  # 导出Mermaid
python3 scripts/kae_main.py graph --forward <资产ID>  # 正向追溯
python3 scripts/kae_main.py graph --backward <资产ID> # 反向溯源

# 5. 定时巡检（扫描新增文件，自动归档关联）
python3 scripts/kae_main.py inspect --dirs <目录1,目录2>

# 6. 全域锁档校验（依赖完整性+引用断裂+资产失联）
python3 scripts/kae_main.py verify

# 7. 创建全域快照（Merkle哈希树固化）
python3 scripts/kae_main.py snapshot --name <快照名>

# 8. 查看体系运行状态
python3 scripts/kae_main.py status
```

## 核心能力详解

### L1 元数据标准
- 每份资产强制附加：确权DID、SNAP编号、Merkle哈希、层级、子域、依赖列表、衍生列表、版本号、锁档状态、L0合规校验
- 链式哈希继承：新根哈希 = SHA256(父哈希:资产哈希)
- SNAP快照：对全域资产状态进行Merkle树固化

### L2 全域资产索引中台
- 索引条目不存完整文件，只存指针（云盘路径/Wiki链接/Base表ID/哈希凭证）
- 多维度检索：按层级/子域/类型/存储/标签/关键词
- 依赖链追溯：递归向上追溯所有上游依赖
- 完整性校验：断裂引用检测+孤儿资产识别

### L3 RAG真值检索
- 文档按章节切片，每段打上层级/子域/关键词/依赖标签
- TF-IDF向量化存储，余弦相似度检索
- **层级前置召回**：讨论Lv6自动召回Lv0-Lv5全套前置架构定义
- 依赖召回：基于资产依赖关系召回相关上下文
- 组合上下文：直接生成可喂给大模型的上下文文本

### L4 全域依赖知识图谱
- 从索引表的依赖/继承字段自动构建图谱
- **正向追溯**：顶层公理如何落地成工程产出
- **反向溯源**：某张角色图/某个资产，源头遵循哪条创世元法则
- 连通分量检测：识别孤立子图
- 循环依赖检测
- Mermaid可视化导出

### L5 自动化闭环流水线
- 新增资产全自动处理：元数据补全→索引登记→切片入库→图谱节点→自动锁档
- 全域锁档校验：全链路依赖完整性+文档引用断裂+资产失联检测
- 定时巡检：每日自动扫描新增文件，自动归档关联
- 全域快照：Merkle哈希树固化整个体系状态

## 与现有系统的契合点

之前落地的：数据隔离引擎、FastAPI服务、飞书三端同步、全域哈希锁档，全部是这套关联体系的底层底座。

本引擎补齐的核心中间层：**全域资产索引中台 + RAG真值检索链路**，补齐之后，分散在云盘、知识库、多维表格里所有架构、资产，就会真正连通为ZONGYUAN-ROOT唯一完整自治系统。

## 两个常见误区

1. ❌ 把所有文件合并成一个超大文档 → 文档臃肿、检索困难、无法分权限
   ✅ 文件保持拆分，依靠索引+图谱建立关联

2. ❌ 依赖大模型自带记忆功能 → 容量有限、不可确权、无法哈希锁档
   ✅ 外部存储承担永久记忆，AI负责检索、解析、编排、校验

## 约束

- 所有资产挂载归属 ZONGYUAN-ROOT 唯一根节点
- 确权DID固定为 DID-BR-000002
- 索引条目不存完整内容，只存指针
- 新增资产自动触发全流水线处理
- 所有产出遵循元秩序归档规范
