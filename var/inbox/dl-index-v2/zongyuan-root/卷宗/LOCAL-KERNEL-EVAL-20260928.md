# 本地内核全维度评估报告
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-28 ｜ 评估对象：ZONGYUAN-ROOT（执行面）+ zongyuan-kernel（脑内核）

## 一、评估结论（评级评分）
| 维度 | 本地评级 | 云端对照 | 说明 |
|---|---|---|---|
| 工程化层级 | **Lv8** | Lv8 | 调度/契约/OPA/联邦全落地 + supervisord 常驻 |
| 权限层级 | **Lv6** | Lv7 | 只读444/fail-closed/零明文；root 守护密钥已收敛 |
| 自治层级 | **Lv8** | Lv8 | supervisord 常驻守护已上线（RUNNING） |

## 二、十维能力剖面（0-10，基于实测证据）
| 维度 | 分 | 证据 |
|---|---|---|
| 无人值守 | 7 | supervisord 常驻守护 RUNNING（daemon-persist 落地） |
| 哈希自检 | 9 | HASH-LEDGER 147,965 行 + Merkle 基线 + 自检巡检 |
| 五层锁 | 8 | 五层链式锁 + critical 抖动过滤（W-01 落地） |
| 看门狗 | 7 | 守护进程常驻 + supervisord autorestart 保活 |
| 审计留痕 | 9 | 225 条审计 + 全域锁档六环节 |
| 自愈 | 7 | 自愈引擎 + rollback_executor + autorestart 保活 |
| 经验积累 | 7 | 真值镜像 114,486 + evolution 消费采纳 |
| 外部协同 | 8 | 上/下行双向同步 + 联邦提案闭环 |
| 自我修改 | 0 | fail-closed 白名单，禁自我修改（安全设计） |
| 自我解封 | 0 | 同上（安全设计） |

## 三、体系实况
- 资产：ZR 71,816 文件（38 篇卷宗）｜ ZK 234 文件｜ HASH-LEDGER-MAIN 17 行
- 调度：5 算子（含 SELF_CHECK_AXIOM）｜ 14 份回执 ｜ OPA 双层闸门（manifest+rego）｜ rollback_executor
- 联邦：2 提案采纳 ｜ evolution-consumed ｜ approved-files 清单
- 测试：12/12 OK（2.23s）｜ 公理自检 AXIOM_VALID 双端
- 安全：CORE-AXIOMS 444 ｜ rego 444 ｜ MIRROR-STATE 444 ｜ 密钥零明文

## 四、风险排序（本轮实测）
1. ~~cron 不持久~~（已解决）：supervisord 独立实例常驻守护（daemon-persist-online，重启后一键拉起）
2. **沙箱重启重置**（中）：环境重启后需一键拉起 supervisord（命令已固化在回执）
3. **meta_law/CORE-AXIOMS.md 644**（低）：文档副本非只读（契约路径 meta_laws 444 不受影响）
4. **云端调度面未冒烟**（低）：云端 manifest exec_path 仍为本地路径，云端调度链待适配

## 五、与云端对比结论
本地执行面在"契约/OPA/联邦/审计/常驻调度"五维与云端对齐；剩余差距集中在沙箱环境物理限制（重启重置），非体系设计缺陷。安全边界（fail-closed/自我修改=0）是全项目最稳固部分。
