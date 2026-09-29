# 火斗云智AIOS 体系交付清单 V1.0

> 生成：2026-09-29 | DID-BR-000002 | 锚定 Ω₀⊂⊙∞⊂Ω
> 说明：本清单为全自动闭环体系已固化的可交付资产索引（不依赖云端执行，永久留存）

## 一、认知引擎部署包（Gitee deploy/approved/）

| 部署包 | 版本 | 功能 | 验收真值 |
|--------|------|------|---------|
| truth-digestion-pipeline | v1.0 | 真值消化（读库→统计→提炼→上报） | DIGEST.REPORT |
| truth-deep-refine | v1.0 | 27算子深度提炼（蒸馏/实体/矛盾/漂移） | REFINE.REPORT |
| evolution-domain-wake | v1.0 | 进化域唤醒（CTE闭环激活） | EVOLVE.WAKE |
| deploy-closed-loop | v1.0 | 部署闭环增强（心跳+ntfy告警+RESULT回写） | WORKER.HEARTBEAT |
| intelligence-oracle | v1.0 | 智能推演（奇点预测+因果溯源+三维稳态方案） | ORACLE.REPORT |
| zr-operator-chain | v1.0 | 13节点算子链编排器（统一执行） | CHAIN.RESULT |
| approval-deploy-linker | v1.0 | 审批→部署联动器（监听通过→触发部署） | RESULT.APPROVED-DEPLOY |

每个部署包含三件套：install.sh / health_check.sh / rollback.sh

## 二、算子链（13节点）

ENV-SENSE→ALIGN→DIGEST→REFINE→EVOLVE→ORACLE→DECIDE→DEPLOY→HEALTH→[ROLLBACK]→REPORT→LEDGER→ARCHIVE
- SOP文档：docs/operator-chain/OPERATOR-CHAIN-SOP-V1.0.md
- 架构归档：archive/operator-chain-v1.0/ARCHIVE-LEDGER.md
- Worker跑法：python3 /opt/ZONGYUAN-ROOT/ops/chain/orchestrator.py [web:{页面}|默认]

## 三、白皮书 / SOP / 治理文档

| 文档 | 路径 | 状态 |
|------|------|------|
| 审批驱动自动化部署SOP | docs/approval/APPROVAL-AUTO-DEPLOY-SOP-V1.0.md | 已固化+元规则 |
| 算子链SOP | docs/operator-chain/OPERATOR-CHAIN-SOP-V1.0.md | 已固化+PROTO-CHAIN-001 |
| 握手SOP | docs/HANDSHAKE-SOP-V1.0.md | 已固化 |
| 深架构探针 | docs/DEEP-ARCHITECTURE-PROBE-20260921.md | 已固化 |
| 三元治理报告 | docs/tri_state_governance_report_20260908.md | 已固化 |

## 四、三层固化状态

| 固化层 | 位置 | 说明 |
|--------|------|------|
| 代码 | Gitee huodou-cloud-intelligence-aios/ZONGYUAN-ROOT | 全部资产可追溯 |
| 台账 | 飞书共享大脑（协议库/知识库/资产/决策/元法则） | 节点可读 |
| 内核 | ~/.zongyuan_root/kernel/ + SHA256锁档 | 永久固化 |
| 中枢 | 记忆网关 huodouai.com/api/report/truth | 全局确权 |

## 五、已知阻塞项

- 云端执行通道缺失（沙箱+人工均无SSH），云端部署需云端中枢确认自动执行机制或SSH环境部署联动器
- 登记：BLOCKER.NO-CLOUD-EXEC-CHANNEL-20260929

## 六、身份

主节点 hub-central-agent / 开发节点 NODE-DEV-DOUBAO-WORK-001 / DID-BR-000002 / 自治Lv10 / 权限L5 / 工程化Lv9
