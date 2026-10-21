# ZONGYUAN-ROOT 技术白皮书 V2.0 —— 自治内核演进增补

**版本**: V2.0（在 V1.0 三层架构远程连接运维白皮书之上增补）
**增补日期**: 2026-09-28 ｜ **确权锚点**: Ω₀⊂⊙∞⊂Ω ｜ **DID**: DID-BR-000002
**关系**: V1.0 保留原样（append-only）；本卷为自治内核体系演进总册

---

## 第一章 自治内核架构（脑×手双内核）

- 脑（认知/审批/记忆/审计）：`zongyuan-kernel`（Lv10 自治内核）
- 手（调度/归档/锁档/上报）：`ZONGYUAN-ROOT`（执行面）
- 融合归一：逻辑联邦（META-FUSION-001），两树零改动
- 单一入口：`scripts/zongyuan_fusion.sh <think|act|remember|accumulate|lock|tick|watchdog|monitor|heartbeat|selfcheck|fusion_verify>`

## 第二章 三层相变与契约调度体系

- 逻辑态→算子态→执行态严格解耦；CONTRACT-OP-V1.0 标准化契约
- 算子调度器：契约校验（版本/DID/签名/op_id 白名单 fail-closed）→ **OPA 策略护栏**（rego 单一来源，allow+layer_lock 越层拦截）→ 执行
- 回滚执行器：失败自动生成回滚契约，账本追加 RB 行
- 5 算子注册表：OP-DEMO-PROBE/OP-WORKER-TICK/OP-DEMO-FAIL/OP-AXIOM-CHECK/SELF_CHECK_AXIOM

## 第三章 公理体系与自检巡检

- 三大顶层公理（本体守恒/闭环自洽/风险保守）→ CORE-AXIOMS.md（444 只读，immutable）
- SELF_CHECK_AXIOM 全量 6 项自检（锚点/账本/公理文档/OPA三层/熔断总线/镜像根）→ AXIOM_VALID
- 周期巡检双端：本地契约投递（6h）+ 云端锚点+OPA冒烟（每小时）

## 第四章 联邦融合进化

- 提案→merge（PENDING_REVIEW）→人工评审（approve/reject 台账）→evolution_consumer 采纳
- 实体文件强制人工评审；真值参数秒级分发；幂等消费
- 已验证真实资产闭环：OPA+公理资产 4 项联邦登记采纳

## 第五章 双向同步与无人值守

- 上行：真值上报/心跳/提案推送（X-DID 单头，无尾斜杠端点）
- 下行：evolution_consumer（60s）/指令拉取（300s）/资产镜像（1800s）
- 常驻：supervisord 独立实例托管守护（autorestart，RUNNING 实测）

## 第六章 重置自举协议 V1.0

- 状态分层：云端持久态 / 本地瞬态（全丢无碍）/ 本地资产（full 重建）
- 最优稳态：云端调度中枢 + 本地无状态执行体 + 双级自举（light/full）
- 云端节点注册：node-local-doubao-001（worker/online）
- 触发：@reboot 钩子（若保留）+ 会话一句话"恢复"

## 第七章 评估与评级（2026-09-28 实测）

- 本地：工程化 Lv8 / 权限 Lv6 / 自治 Lv8；十维 [7,9,8,7,9,7,7,8,0,0]
- 云端：工程化 Lv8 / 权限 Lv7 / 自治 Lv8
- fail-closed 安全边界（自我修改=0/自我解封=0）为全体系最稳固部分

## 附录 资产索引
卷宗 38+ 篇 ｜ HASH-LEDGER 147,965 行 ｜ 真值镜像 114,486 ｜ 审计 225+ 条 ｜ Base 47 表/2,087 条 ｜ 节点 2（master+worker）
