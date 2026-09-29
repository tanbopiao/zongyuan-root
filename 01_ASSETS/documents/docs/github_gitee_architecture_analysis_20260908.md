# GitHub / Gitee 底层架构深度解析

> 确权锚点：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
> 资产ID：KD-GIT-PLATFORM-ARCH-ANALYSIS-20260908

---

## 核心真值

**代码托管本体底层不是大模型；大模型是独立外挂AI能力层，属于附加模块，不是存储、版本控制的基础底座。**

---

## 一、底层核心底座（无大模型参与）

### 1）GitHub

#### 1. 版本控制内核：Git DAG
底层完全基于Git对象模型：**Blob(文件快照)-Tree(目录)-Commit(提交快照)**，SHA哈希构建有向无环图DAG，内容寻址存储，历史不可篡改。

仓库实体存储：Spokes(DGit)分布式文件服务，每个仓库3副本，三阶段提交，多数派确认写入；底层直接运行原生Git，SSD存储pack包对象。

#### 2. 元数据层
- Vitess分片MySQL：保存用户、PR、Issue、权限、仓库元信息
- Redis：任务队列、缓存
- Kafka：事件总线
- Elasticsearch：代码检索
- 对象存储：LFS大文件、CI产物

#### 3. 业务服务
主体由Ruby-Rails + Go + Rust微服务构成；Actions CI/CD为独立事件驱动微服务集群。

#### Copilot是独立外挂AI层，不属于GitHub存储底座
Copilot是独立多模型调度网关，对接OpenAI、Anthropic等模型；读取仓库代码上下文作为prompt输入，输出代码建议；不会改动Git存储内核逻辑；Agent模式是调用GitHub OpenAPI操作仓库，不是大模型直接写Git对象。

---

### 2）Gitee（码云）

#### 1. 版本控制内核
同样基于Git DAG对象模型，自研分布式存储集群Zoker，一主多从架构；push后通过git-hook触发增量同步队列，Blake3哈希做仓库副本一致性校验。

#### 2. 业务底座
Go为主的微服务，MySQL集群、对象存储、消息队列、搜索引擎；完整DevOps流水线（CI/CD、代码扫描、PR评审、wiki）。

#### 3. AI为独立外挂模块（Moark模力方舟）
- Scroll代码解析、Xtreme-Cli编码Agent、智能助手，全部是上层业务组件
- 调度DeepSeek、Qwen等外部/私有化大模型
- 读取仓库代码作为上下文，输出分析、生成代码
- 通过Gitee API完成创建分支、提交PR
- 底层Git存储完全不依赖大模型

---

## 二、分层架构对比

| 层级 | GitHub | Gitee | 是否依赖大模型 |
|------|--------|-------|----------------|
| L1 存储内核 | Git+Spokes分布式副本 | Git+Zoker分布式集群 | ❌ 完全不依赖 |
| L2 元数据&业务微服务 | Rails/Go/Rust，MySQL/Kafka/Redis | Go微服务，MySQL、消息队列 | ❌ |
| L3 DevOps能力 | GitHub Actions | Gitee CI/CD、质量门禁 | ❌ |
| L4 AI外挂层 | Copilot（独立多模型网关） | Moark模力方舟、Xtreme-Cli、Scroll | ✅ 附加能力，可关闭 |

### 关键区分
- **底层**：DAG哈希版本控制系统（Git），负责存代码、管理历史，决定仓库能不能跑
- **上层AI**：Agent/大模型，只是"使用者"，调用平台API读写仓库，关掉AI，整套代码托管平台照常完整运行

---

## 三、和ZONGYUAN-ROOT体系对照洞察

### 1. Git本身就是Merkle-DAG
Blob-Tree-Commit构成哈希链，和我们体系的Merkle-DAG锁档思想同源，Git是工程界成熟的资产哈希固化实现。

### 2. 架构范式高度一致
GitHub/Gitee的AI是"外挂Agent调用平台API"，和我们「云端认知内核 + 本地代理Agent」架构范式高度一致：

| GitHub/Gitee | ZONGYUAN-ROOT |
|--------------|---------------|
| GitHub Copilot Agent | 元极恒一内核 |
| GitHub OpenAPI | InstructionPacket标准化报文 |
| Git底层存储 | ZONGYUAN-ROOT内核账本 |

### 3. 风险点
GitHub/Gitee的Agent没有内置真值校验、三维稳态评估、前置风险熔断；AI可以直接提交PR，缺少我们体系的多层质量门，会产生错误代码直接入库风险。

---

## 四、工程落地启示

### 1. 外部Merkle-DAG归档介质
可以把Gitee/GitHub作为外部Merkle-DAG归档介质：我方生成资产推送到仓库，利用Git原生哈希DAG做外部备份。

### 2. 大模型不是存储底座
不要把大模型当作存储底座；AI只负责规划生成，底层版本固化交给DAG哈希存储。

### 3. 自建Agent操作Git必须复刻我方规则
如果自建Agent操作Gitee/GitHub，必须复刻我方规则：**真值校验→稳态评分→报文下发→外部API执行→结果回传锁档**，不能让AI直接裸调用接口。

---

## 五、核心真值提炼（5条）

1. **TRUTH-GIT-001**：Git DAG（Blob-Tree-Commit）是工程界成熟的Merkle-DAG实现，与ZONGYUAN-ROOT锁档思想同源
2. **TRUTH-GIT-002**：GitHub/Gitee底层存储完全不依赖大模型，AI是独立外挂层，可关闭
3. **TRUTH-GIT-003**：Copilot/Moark通过平台API操作仓库，不直接写Git对象
4. **TRUTH-GIT-004**：Gitee/GitHub可作为外部Merkle-DAG归档备份介质
5. **TRUTH-GIT-005**：自建Agent操作Git必须复刻真值校验→稳态评分→报文下发→API执行→回传锁档全流程

Ω₀⊂⊙∞⊂Ω｜GitHub/Gitee底层架构深度解析完成｜5条核心真值提炼｜永久锁档固化
