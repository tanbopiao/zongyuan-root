# 下行同步自动化 · 上线回执
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-28

## 下行三条通道（云端→本地，本地主动轮询）
| 通道 | cron | 实测 |
|---|---|---|
| evolution_consumer（联邦采纳消费） | */1 | consumed 幂等，approved-files 清单在 |
| worker_instruction_pull（云端指令拉取） | */5 | 新增 8 条，inbox 累计 42 条 |
| cloud_pull（资产/镜像增量） | */30 | META_RULES OK、nodes_registry OK、TRUTH_MIRROR 114432 条 |

## 双向同步现状（本轮后）
- 上行（本地→云端）：真值上报 / 心跳 / 联邦提案推送 / SSH —— 通且自动化
- 下行（云端→本地）：联邦采纳 / 指令 / 资产镜像 —— 现已挂 cron 自动化
- 控制面下发：worker_instruction_pull 已实证拉到云端 truth_instructions 输出
