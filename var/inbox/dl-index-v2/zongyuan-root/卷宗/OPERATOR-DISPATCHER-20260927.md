# 算子调度器部署回执（修复版 V1.1）
事件ID：OPERATOR-DISPATCHER-20260927 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

## 部署清单
| 文件 | 路径 | 说明 |
|-|-|-|
| 调度器 | tools/operator_dispatcher.py (755) | 修复版 V1.1，全 ASCII，编译通过 |
| 锚点 | 00-ROOT-POINTER.json (444) | root_path 指向 ZR 根 |
| 注册表 | physical_operator/manifest-physical-operator.json | 自指 SHA-256 完整性保护 |
| 演示算子 | physical_operator/demo_probe.sh (755) | 轻量探针（纯本地演示） |
| 目录 | task_inbox / task_finished | 契约收件箱/完成箱 |
| 接入 | worker_kernel.sh dispatch 子命令 + cron */5 轮询 | 与现有调度体系融合 |

## 修复项（对应评审 P0/P1/P2）
1. 全 ASCII 化（原稿 U+2010 连字符 → 编码/路径/版本比对全错，直接运行必失败）
2. /var/log → ZR/logs/ 轮转日志（RotatingFileHandler 5MB×3，非 root 可写）
3. dispatch() 先校验后取 task_id（缺字段走优雅拒绝，不再 KeyError）
4. 注册表 self_sha256 自指哈希校验（fail-closed：篡改即整体拒绝轮询）
5. 轮询 flock 单实例锁（防 cron/手动并发双消费）
6. 实现 retry / allow_failure / params（标量参数追加，无注入面）
7. 账本写入 flock 锁 + stdout/stderr 截断 2000 字符

## 端到端实测（2026-09-27 13:27）
- T-OP-TEST-0001（OP-DEMO-PROBE-001 serial）→ ALL_DONE / exit 0 / SUCCESS / 探针落盘 / 账本追加 / 任务归档 ✓
- 篡改防护：修改 manifest desc 后 dispatch → {"error":"registry_tampered","detail":["registry tampered: self_sha256 mismatch"]}，任务拒收 ✓
- 恢复注册表后遗留任务正常消费（inbox 清零）✓
- 账本 HASH-LEDGER-MAIN.csv：表头 + 2 条任务记录（append-only）

## 与现有体系关系
- 调度器作为 worker_kernel.sh dispatch 子命令（第 8 条 cron：*/5 轮询 inbox）
- 账本独立：HASH-LEDGER-MAIN.csv=任务契约账；HASH-LEDGER.csv=资产哈希账（分工明确）
- 网关扩展点预留：合法契约写入 task_inbox 即可，执行态与网关解耦（Kunlun-Bridge 对接点）
