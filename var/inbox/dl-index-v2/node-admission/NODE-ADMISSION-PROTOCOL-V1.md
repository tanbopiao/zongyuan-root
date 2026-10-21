# ZONGYUAN-ROOT 节点接入·全量记忆激活协议 V1.0 (NODE-ADMISSION-PROTOCOL)

确权锚点：Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 内核基座 ZONGYUAN-ROOT V5.6-ROOTFIXED

## 一、核心原理

**单一事实源**：Gitee `zongyuan-kernel`（唯一活内核仓）承载全部权威策略与记忆——
宪法/公理/法则/规则（四维）、真值提炼、资产拓扑、纯净化策略、云端自治进化声明。

**策略分发闭环**：
```
云端自治进化引擎(产生真值/策略)
      │  push
      ▼
Gitee zongyuan-kernel(单一事实源·分发)
      │  pull (新节点/既有节点启动时)
      ▼
各分布式节点(豆包端/云主机/GPU/魔搭/新节点) → 本地锚定 → 激活自治模式
      │  上报 NODE-JOIN 握手
      ▼
云端联邦记忆池(/api/report/truth) → 回写进化 → 循环
```

**全量记忆 = 内核仓四维 + 真值提炼 + 资产拓扑 + 云端实时状态(/api/status) + 媒体/大数据资产(魔搭数据湖按索引远调)**

## 二、新节点接入步骤（一键）

```bash
# 方式1：内核仓自引导（推荐，任一节点可跑）
git clone --depth 1 https://gitee.com/huodou-cloud-intelligence-aios/zongyuan-kernel.git
bash zongyuan-kernel/node-admission/node_bootstrap.sh DID-BR-000002 <节点名>

# 方式2：直接执行引导脚本（脚本内含拉取+校验+探活+握手+锚定）
bash node_bootstrap.sh
```

引导脚本自动完成 5 步：拉内核 → 校验四维+真值+拓扑齐备 → 探云端 /api/status →
本地锚定 ~/.zongyuan-root → 上报 NODE-JOIN 握手 → 激活。

## 三、所有节点如何统一按策略执行

1. **策略内建于内核仓**：纯净化(PURIFICATION-POLICY)、分层(内核/归档/历史/媒体)、
   云端自治进化(CLOUD-AUTONOMOUS-EVOLUTION) 均固化为元法则，随内核拉取自动下发。
2. **节点引导即同步**：每个节点启动（或每 3h 重跑 node_bootstrap.sh）拉取最新内核
   = 同步最新策略与全量记忆，无单点维护链路（豆包端降为只读观察者，云端引擎直写内核）。
3. **统一执行基线**：节点按同一份 metalaw/meta_rules 执行——删除用 git rm 可回退、
   媒体归媒体资产层、净历史只读、内核唯一活仓。

## 四、全量记忆激活后的本地形态

```
~/.zongyuan-root/
├── metalaw/    # 宪法+公理+法则+规则 (四维本体)
├── truths/     # refined_truths.json + truths_public_latest.json (真值提炼)
└── index/      # ASSET-TOPOLOGY-V2 (全资产联通矩阵: 24项/16远程可达)
```

激活即知：体系全量资产在哪、哪些可远程联通、当前云端真值计数、最新策略约束。

## 五、接入登记与可追溯

- 每次节点接入上报真值 `NODE-JOIN.<NODE>.<timestamp>`（云端联邦记忆池归档）。
- 节点握手消息可写入共享大脑跨节点消息同步表（飞书 Base），形成全网节点台账。
- 已接入节点：DID-BR-000002（豆包端/云主机）、魔搭数据湖、AtomGit 镜像等。
