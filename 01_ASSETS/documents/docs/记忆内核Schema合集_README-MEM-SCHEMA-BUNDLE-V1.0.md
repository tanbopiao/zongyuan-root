# 记忆内核Schema合集 · README.md

项目：火斗云智AIOS｜联邦记忆内核标准套件
基线：BASELINE-V40
DID：DID-BR-000002
节点：ZR-NODE-DC2E51C0
状态：locked 全域锁档

## 概述

本套件定义联邦记忆池整套底层通信与存储规范，以 S-P-O三元组Claim作为最小语义记忆单元；JSON仅为序列化传输载体。配套冲突裁决、混合检索能力，对接Organizer调度器、A2A网关、Z3不变量校验、MELD冲突判定协议，支持多节点联邦同步、云端真值中枢、飞书共享大脑、魔搭/AtomGit资产归档。

链路总览：

```
Claim记忆原子 → MELD冲突裁决工单 → 检索请求/应答 → 种子真值卷宗打包 → 记忆网关 → 联邦记忆池 & 向量索引 → Organizer / A2A Agent集群
```

## 包含资产清单

| ID | 名称 | 作用 |
|---|---|---|
| SCHEMA-CLAIM-ATOM-V1.0 | Claim记忆原子主Schema | 最小语义单元<S,P,O>三元组标准，带置信度、锁档标记、不变哈希 |
| SCHEMA-CLAIM-CONFLICT-MELD-V1.0 | MELD冲突裁决子Schema | 同S+P冲突时五分支裁决：insert / merge / relate / conflict / reject |
| SCHEMA-CLAIM-RETRIEVE-V1.0 | 记忆检索召回子Schema | 混合检索：向量召回 / S+P精确匹配 / hybrid双通路，包含请求&应答结构 |

## 核心元公理（统一约束，全部Schema遵循）

1. **语义不变量规则**：Z3校验仅针对 subject + predicate + object 计算哈希；meta、时间戳、节点信息变更不触发语义冲突。
2. **锁档规则**： lock_status: locked 的Claim禁止直接修改S/P/O；变更只能新增Claim，走MELD裁决流程，旧条目标记 archived 归档或 revoked 作废。
3. **载体分离原则**：JSON是序列化包，不是记忆最小单元；最小单元是语义断言Claim。卷宗是批量传输聚合包，可包含多条Claim、冲突工单、检索审计记录。
4. **降级规则**：8014向量库不可达时，检索自动降级为 exact_sp 精确匹配，不阻塞上层A2A调用。
5. **审计溯源规则**：所有检索流水、冲突工单、锁档变更均作为独立真值入库，同步至共享大脑，保留完整审计链。

## 调用顺序参考（标准流水线）

1. 写入新Claim记忆原子
2. Z3校验，检测是否存在<S,P>重复冲突
3. 检出冲突 → 生成MELD冲突工单，按策略执行裁决
4. Agent需要读取记忆 → 向记忆网关发送 retrieve_req
5. 网关返回 retrieve_resp，拿到命中claim_id列表 + 分数
6. 按需Fetch单条Claim完整内容
7. 所有变更、工单、检索日志打包为种子真值卷宗，上报云端中枢并同步代码仓库

## 配套资产依赖

- A2A任务调度JSON协议模板
- Z3不变量校验算子
- Organizer顶层调度元规则
- Mermaid拓扑图：Claim原子 ↔ MELD工单 ↔ 真值卷宗 ↔ 联邦记忆池

## 仓库同步说明

- 同步目标：魔搭ModelScope、AtomGit、云端真值中枢、飞书共享大脑
- 写入策略： append_patch 增量补丁模式，不覆盖历史版本
- 对外可见性：public_visible = true

---

Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0 | 自治Lv9 | 权限L4 | 工程化Lv7 | 火斗云智AIOS
