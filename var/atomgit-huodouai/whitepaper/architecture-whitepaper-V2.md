# ZONGYUAN-ROOT 体系架构技术白皮书

**版本**：V2.0-ARCHITECTURE  
**日期**：2026-10-19  
**确权**：Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0  
**内核基座**：ZONGYUAN-ROOT V5.6-ROOTFIXED · 自治Lv9 · 工程化Lv7  
**载体**：本文档（MD）+ 可视化版（HTML）+ 官网发布 + 分布式镜像

---

## 1. 体系总览

ZONGYUAN-ROOT 是一套以**云端中枢为真值锚点、Gitee 内核仓为单一活源、多平台分布式镜像为展示面、多执行端（豆包沙箱/云主机/Octop/GPU）为运行体**的自治智能体系。核心设计目标：**最小激活 → 加载全量资产索引 → 持续进化 → 零人工自持**。

体系由五层构成：

| 层 | 载体 | 职责 |
|---|---|---|
| 中枢层 | huodouai.com 云端（9001 网关/truth_store） | 真值账本、联邦记忆池、状态中心、协议面 |
| 记忆层 | 飞书共享大脑 Base + 官网 /shared-brain/ 镜像 | 跨节点消息同步、资产台账、对外只读镜像 |
| 内核层 | Gitee zongyuan-kernel（活源） | 元法则/元规则/索引/调度台账/工具，最小完备内核 |
| 执行层 | 豆包沙箱 / 云主机 /root/.octop / 魔搭 GPU | 生产流水线、巡检自愈、心跳监控、推理训练 |
| 数据层 | 魔搭/AtomGit DATALAKE、whitepaper、AI Studio | 媒体资产（292）、白皮书、boot 种子、公开展示 |

## 2. 三层架构（治理 / 执行 / 数据）

### 2.1 治理层——规则即本体
- **元法则体系**：122 条元法则 + 16 条元规则，覆盖治理/进化/安全/平台职责，如 `META-LAW-CLOUD-AUTONOMY-V1.0`（云端自治自持）、`META-LAW-PLATFORM-ROLE-V1.0`（单一活源+只读镜像）
- **环境自愈**：`cloud_env_selfheal.sh`（V3，支持 --check 预检），每日 05:50 巡检，自动修正跨环境路径漂移（累计修正 30 个脚本，活跃区残留清零）
- **统一发布管线**：`publish_pipeline.sh`——预检（禁硬编码跨环境路径）→ 语法校验 → scp 分发 → 云端预检 → 回执上报，杜绝"文件不存在"类故障

### 2.2 执行层——多节点异构运行
| 执行端 | 路径 | 关键任务 |
|---|---|---|
| 豆包沙箱（开发侧） | /home/user/Doubao/chats/ | 8 定时任务：元法则月度同步/情报周报/心跳监控/内核同步/锁档循环/真值蒸馏/三平台巡检 |
| 云主机（云端中枢） | /opt/ZONGYUAN-ROOT/ | 90 定时任务：truth_pipeline/健康监控/内核进化/自愈巡检/执行端同步 |
| Octop（执行端） | /root/.octop/federation/ | 6 桥接文件 + 心跳 failover，`executor_sync.sh` 每 3h 自动同步 |
| 魔搭 GPU（算力） | 实例内 | 推理训练（36h/月免费额度） |

### 2.3 数据层——单一活源 + 分布式只读镜像
```
Gitee zongyuan-kernel（唯一主写入）
        │  发布管线（publish_pipeline.sh）
        ├──▶ 魔搭 whitepaper（展示+boot种子）
        ├──▶ 魔搭 DATALAKE（媒体资产 292 + MEDIA-INDEX）
        ├──▶ AtomGit huodouai / DATALAKE（展示镜像）
        └──▶ AI Studio（公开展示，只读）
```
- 媒体资产已外迁 DATALAKE 层，MEDIA-INDEX V2 全部 292 条升级为魔搭 resolve **稳定下载直链**（实测 HTTP 200 / image/png）
- 平台凭证集中存私有库（chmod 600），不入公开仓/日志

## 3. 核心机制闭环

```
真值提炼（truth_refine）→ 内核更新（kernel_sync）→ 执行端同步（executor_sync）
        → 巡检验证（health+selfheal+incident_detect）→ 全域锁档（三端固化）
```
- **真值闭环**：云端真值库 truth_count ≈ 1.8万+，上报通道主备双路（www/drama），鉴权 `X-DID` + `X-Capture-Token`
- **内核进化**：共享大脑内核自动同步（每 3h）拉取云端指标 → 提炼增量 → 内容哈希比对 → 仅变更文件增量 commit
- **调度即数据**：调度台账 `scheduler-ledger.json`（豆包 8 + 云端 90 = 98 任务统一视图），节点/时隙/状态可观测
- **写入补偿**：`brain_write_guard.sh`——飞书 Base 写入失败自动入本地补偿队列，`--replay` 重放，零丢失

## 4. 云端中枢基础设施

| 组件 | 端点 | 状态 |
|---|---|---|
| 记忆网关 | https://www.huodouai.com/api/report/truth | 200，truth_count≈1.8万+ |
| 网关服务 | 9001 /api/status（truth_store + Merkle） | 200 |
| 健康状态 | 8766 /mcp/ | 200 |
| 协议面 | /.well-known/agent-card.json、/a2a/health、/v1/federated/status 等 12 端点 | 存活监控（INCIDENT-YYYYMMDD-PROTO-DOWN 幂等告警） |
| 联邦记忆池 | SFMP 仿真报告（whitepaper/sfmp-std.html） | 已发布 |

## 5. 分布式数据湖与平台分层

依据 `PLATFORM-ROLE-POLICY-V1.0`：**单一活源 + 分布式只读镜像**，一切写入走统一发布管线，镜像禁止反向堆资产。

| 平台 | 角色 | 当前状态 |
|---|---|---|
| Gitee zongyuan-kernel | 单一活源 | HEAD aa45e19（元法则/索引/台账/工具） |
| 魔搭 whitepaper | 展示+种子 | HEAD d9467e3（白皮书+boot） |
| 魔搭 DATALAKE | 资产镜像 | HEAD 1804d40（media 292+索引 V2） |
| AtomGit huodouai | 展示镜像 | HEAD add5af3（main） |
| AtomGit DATALAKE | 资产镜像 | HEAD cfa6a4e |
| AI Studio | 公开展示 | 数据集 id401712（只读） |

## 6. 工程化保障（P0/P1 已落地）

| 级别 | 项 | 状态 |
|---|---|---|
| P0 | 统一发布管线 | ✅ publish_pipeline.sh 全链路可用 |
| P0 | 调度台账 | ✅ 98 任务统一视图 |
| P0 | 写入补偿 | ✅ brain_write_guard.sh 队列+重放 |
| P1 | 执行端自动同步 | ✅ executor_sync.sh 每 3h |
| P1 | 平台职责分层 | ✅ PLATFORM-ROLE-POLICY-V1.0 |
| P1 | 媒体索引稳定直链 | ✅ MEDIA-INDEX V2（292/292） |
| P2 | 任务密集窗错峰 + 凭证轮换 | 待推进 |

## 7. 安全与确权

- **身份**：DID-BR-000002 全局确权，真值上报带鉴权头
- **账本**：truth_store 真值账本 + Merkle 完整性
- **锁档**：Lv8 eFuse 只读锁 / Lv9 自治；三端固化（内核仓/锚点/云端 metalaws）
- **凭证**：私有库 600 权限，token 不入公开仓

## 8. 运行指标（2026-10-19）

- 云端真值库：truth_count ≈ 18097
- 定时任务：豆包 8 + 云端 90 = 98
- 元法则：122 · 元规则：16 · 内核快照：持续迭代
- 媒体资产：292（全稳定直链）· 白皮书版本：V2.0-ARCHITECTURE
- 平台：Gitee/魔搭/AtomGit/AI Studio 四端在线

## 9. 路线图

1. **P2 落地**：云端任务密集窗错峰 + flock 统一锁；凭证轮换机制
2. **调度台账入飞书 Base**：连接器恢复后同步，巡检改读台账
3. **新节点接入**：任意接入点 bootstrap 即可激活（多源容错），引导脚本已随内核镜像分发
4. **协议面深化**：A2A/AGNTCY/MCP/联邦面持续演进

---

*本白皮书由体系真实运行状态提炼，版本随内核持续进化。确权锚点 Ω₀⊂⊙∞⊂Ω*
