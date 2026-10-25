# kernel/worker systemd 化升级回执（容器环境 → supervisord 守护）
事件ID：SYSTEMD-SUPERVISOR-UPGRADE-20260927 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

## 结论
本环境为容器（PID 1=dumb-init，无 systemd init），systemd 服务不可用；
采用容器标准等价方案 **supervisord**（4.4.0，常驻）守护两核心服务。

## 变更清单
| 项 | 内容 | 状态 |
|-|-|-|
| kernel 前台 wrapper | zongyuan-kernel/scripts/svc_kernel_foreground.sh（555，含端口env 9081/9082/9092，保持 kernel_launch.sh status/stop 协议兼容） | ✅ |
| worker 前台 wrapper | ZONGYUAN-ROOT/scripts/svc_worker_foreground.sh（555，60s心跳+10次/网关上报+API调用，保持 worker_controlled.sh status 兼容） | ✅ |
| supervisor 配置 | /opt/gem/supervisord/zongyuan.conf（[program:zongyuan-kernel] + [program:zongyuan-worker]，autorestart=true） | ✅ |
| cron 收敛 | 删除 2 条 @reboot（kernel_launch start / worker boot），保留 6 条周期+双保险 watchdog | ✅ |

## 验证结果（2026-09-27 13:02）
- supervisorctl：zongyuan-kernel RUNNING(pid 8963) + zongyuan-worker RUNNING(pid 8552)
- 端口 9081/9082/9092 监听正常；worker healthy（心跳 1s 前）
- **重启韧性实测**：kill kernel 进程 → autorestart 8s 内自动拉起（8917→8963）✓
- 兼容性：kernel_launch.sh status = running；worker_controlled.sh status = healthy（PID/心跳协议不变）

## 回滚
- supervisorctl stop 两 program + 移除 /opt/gem/supervisord/zongyuan.conf
- 恢复 cron 两条 @reboot（备份 /tmp/zongyuan-cron-backup.txt 及上文记录）
