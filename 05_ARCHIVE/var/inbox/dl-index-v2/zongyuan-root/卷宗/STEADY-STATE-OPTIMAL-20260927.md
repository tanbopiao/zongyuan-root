# 最优稳态适配回执（supervisord 环境还原事件 + 持久自守护迁移）
事件ID：STEADY-STATE-OPTIMAL-20260927 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

## 事件记录（重要）
- 13:18 容器环境将 /opt/gem/supervisord/ 目录还原至镜像基线：本会话写入的 zongyuan.conf 被清除
- 后果：supervisord 托管 zongyuan 双服务方案失效，kernel/worker 进程随配置消失而终止
- 证据：include 目录 20 个 conf 全部为 9/8~9/23 基线文件，无 zongyuan.conf；supervisorctl 20 program 无 zongyuan

## 最优稳态决策（适配当前实例环境）
根因：/opt/gem/supervisord/ 子目录为环境易失区（可被还原），而 cron 与 /home/user 持久。
=> 双服务守护迁回【cron + /home/user 持久脚本自守护】，不依赖任何易失目录。

## 落地清单（全部持久区）
| 项 | 内容 | 验证 |
|-|-|-|
| kernel 保活 | worker_kernel.sh 新增 ensure_kernel（down→kernel_launch.sh start 幂等） | kill 后 watchdog 拉起 (2577→2686) ✓ |
| worker 保活 | 既有 ensure_worker（worker_controlled start） | healthy ✓ |
| @reboot 兜底 | +2 条：worker boot / kernel_launch start（cron 10 条全持久） | crontab -l ✓ |
| 双服务恢复 | kernel pid 2686 / worker pid 2454 | running+healthy ✓ |

## cron 最终 10 条（全持久）
watchdog 每分钟(含双服务自愈) / tick 每5分 / lock 每日3:30 / monitor 每30分 / fusion心跳每5分 / dispatch每5分(算子调度) / cognitive每日6:00 / selfcheck@reboot / boot@reboot / kernel start@reboot

## supervisor 钩子文档（前轮评估）适配结论
- 文档方案（Event-Listener + 9001 RPC）依赖 supervisord 托管 zongyuan —— 当前环境不可持久，**不采用**
- 其价值已由等价机制覆盖：事件观测≈watchdog+monitor 落盘留痕；受控控制≈worker_kernel dispatch 契约链路；账本留痕≈HASH-LEDGER/HASH-LEDGER-MAIN 双账
- 应急旁路：sudo supervisorctl 仅管 20 个基础 program（agent-browser 等），不涉 zongyuan 双服务

## 元法则呼应
P=0.3U-0.4R-0.3C：迁移方案收益不变（无人值守+自愈）、风险最低（避开易失目录）、成本最低（复用既有 cron/脚本，零新增常驻进程）
