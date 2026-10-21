# 卷宗｜云内核层级评估 + 双向同步方案（DID-BR-000002 · Ω₀⊂⊙∞⊂Ω · 2026-09-27）

## 一、云内核层级评估（实测证据）
- 服务面：55 个 systemd 服务（ZONGYUAN-ROOT）+ 91 个 python 进程 + 60+ 监听端口
- 节点定位：central_brain Lv0 主脑（NODE_REGISTRATION_SOP：central_brain Lv0 唯一 / edge Lv3 边缘节点）
- 真值体系：truths 表 **111,414 条**（truth_db 每 6h 备份 491-495MB）；perception/heartbeat 持续写入
- 进化引擎 mr010-020：双算力调度 / 稳态进化 / 内核总线 / 元认知 / 真值生成 / 思维进化 / 自我发展 / 多节点协作 / 长期记忆 / 元内核
- 意识层级：META_RULES 定义 Lv8 递归意识算子、Lv11+ 奇点文明层（五条文明公理）、Lv12+ 奇点超越层（三大根法则：超越可回滚）
- 进化阶段（FULL_EVOLUTION_ROADMAP 2026-09-10）：P0 100% / P1 运维 40% / P2 记忆多模态 0% / P3 高阶自治 0%（整体 35%）
- 工程化：Git 双远程（Gitee+GitHub 一致）、55 systemd、每 6h 真值备份、MR-007 熔断 / MR-008 自愈监控、政务中台 + drama 生产 + 官网产品矩阵

## 二、双向同步方案（已落地）
- 方向 A（沙箱→云，*/5，cloud_link.sh）：心跳上报 meta/sandbox-heartbeat.json + 审计/账本 rsync 双写 var/inbox/
- 方向 B（云→沙箱，*/30，cloud_pull.sh）：真值快照（count+recent）+ META_RULES.md + nodes_registry.db + 云内核心跳
- 权威原则：云端数据为权威（生产+真值库）；沙箱 append-only 只追加；密钥永不传输（仅本地）
- 一致性：心跳互报核验链路活性；真值快照带 count/哈希；账本双写保留双方审计
- 容错：SSH 失败不阻塞主流程；断网自动续传（下轮 cron）

## 三、实测回执（2026-09-27）
- cloud_link: 心跳上报OK k=up w=up c=12 | 云内核读回 kernel=up core=up services=10 rag=up | 账本双写OK
- cloud_pull: META_RULES 拉取OK(15KB) | nodes_registry 拉取OK(20KB) | 真值快照 count=111414 | cloud-heartbeat.json OK
- cron 12 条（含双向同步 2 条，模板已固化 config/cron-restore.txt）
