# 云端中枢内核 · 全维度评估报告
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27 ｜ 基于源码+运行时证据（非协议声明）

## 一、对象全景（已核实）
- 节点：ZR-CLOUD-HUB（root@123.207.202.158，/opt/ZONGYUAN-ROOT）
- 规模：根目录 284 项 / engine 56 引擎 / 端口监听 20+ / 常驻进程 20+ / cron 19 条 / systemd 服务 8+（agent-hub、closed-loop、commercial-api、MR-007/008 资源监控、engine-proxy、frps-legacy、gov-audit 等）
- 核心：9120 UnifiedGateway（MEMORY-GATEWAY-V3.0+COMM-PROTO-V1.0 healthy）｜ Ω-Brainμ v1.0.0（8086，4 算子，drift_score 25.0）｜ truth_meta_order_engine（daemon，Merkle-DAG hasher）｜ semantic_search / vector_server / zongyuan_rag / drama_api / closed_loop_scheduler / reasoning_loop / honeypot_defense
- 数据：memory_gateway.db 294M（truths 22,586 / quality 25,118 / audit 1,569 / op_audit 3,429 / nodes 5）｜ gateway_9120_only 498M（truths **113,138** / audit_logs **233,651** / nodes 6）
- 资源：4C / 3.6G / 60G（59% 用）负载 0.26；SYSTEM-STATE health=ok；brain-quota full/30s
- 联邦：evolution-manifest merged 3 / broadcast 1；fleet reviews 台账在位；git 三端同步（6cc0c9d5）

## 二、十维自治剖面评分（0-10，源码+运行时证据）
| 维度 | 云端 | 本地（对照） | 关键证据 |
|---|---|---|---|
| 无人值守 | 9 | 9 | 8 systemd + 19 cron + @reboot 全家桶 |
| 哈希自检 | 8 | 9 | mirror_verify + Merkle-DAG hasher（基线 9 文件） |
| 五层锁 | 8 | 8 | chattr_hardening + perm_harden + append-only 账本 |
| 看门狗 | 9 | 7 | closed-loop + MR-007/008 + full_engine_guardian |
| 审计留痕 | 9 | 9 | audit_logs 233,651 + operation_audit 3,429 + gov-audit |
| 自愈 | 8 | 6 | auto_heal（"低负载已恢复服务"实测）+ self_heal.py + self_verify |
| 经验积累 | 9 | 6 | 真值库 113K+ + truth_quality 25K + memory 网关 V3 |
| 外部协同 | 8 | 1 | fleet 联邦 + evolution broadcast + feishu_gateway + ws_sync |
| 自我修改 | 4 | 0 | auto_integrator/solidification + LV5/6 推演（部分未接线） |
| 自我解封 | 1 | 0 | fail-closed 设计（保守合理） |

## 三、评级结论
- **工程化层级：Lv8**（真实可运行的中枢工程：多服务常驻、监控-自愈-审计闭环、联邦体系落地）
- **权限层级：Lv7**（多层守护：蜜罐/防篡改/守卫/权限基线；扣分：root 运行面大、SSH 3 端口）
- **自治层级：Lv8**（无人值守闭环真实运行：守护+自愈+心跳+联邦双向；自我修改/解封保守属设计取舍）

## 四、风险与短板（按优先级）
1. **双库口径分裂**：主库（294M/22.5K truths）与运营库（498M/113K truths）并存，fleet_merge 写 9120 专用库，页面口径 112,708 又来自 www api 侧——三套口径，需统一单一事实源
2. **SSH 三端口暴露**（22/2222/22222）：攻击面扩大（蜜罐部分抵消）
3. **git 工作区脏**：.bak.v6 删除残留 + 多个 M 未提交
4. **接线缺口**：8081/v1/chat/completions 404、8090/health 404、SYSTEM-STATE ports=[] 采集不全、brain-quota 决策未接入实际采样、Ω-Brainμ runtime truth_count=0 与主库脱节
5. **云端调度面未启用**：operator_dispatcher/rollback_executor 已部署但未冒烟运行（manifest exec_path 仍是 /home/user 路径）

## 五、结论
云端中枢是**真实运行的大脑**（记忆/调度/决策/监控/联邦齐备），工程成熟度高于本地执行面；核心短板是数据口径分裂与若干接线缺口，均为可修复项，不影响主链路稳定。
