# ntfy 通信层部署卷宗
确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27

## 一、架构（SOP 长任务稳态 · 通信层落地）
- 云端自建 server：`/opt/ZONGYUAN-ROOT/ntfy/ntfy`（v2.11.0），systemd `zongyuan-ntfy.service`（Restart=always，持久），监听 `127.0.0.1:8514`（公网 8514 被 nginx 拦截，本机可用，留作 nginx 反代加固候选）
- 公共通道：`https://ntfy.sh/zongyuan-did-br-000002-7f3a9c2e-{heartbeat,tasks,results}`（主题带熵前缀，消息带 X-DID 头 + DID 字段双校验）
- 沙箱客户端：`~/bin/ntfy` + `scripts/worker_ntfy.sh`（cron */5）

## 二、worker_ntfy.sh 能力
1. 心跳发布（与 cloud_link SSH 通道并存，双通道容错）
2. 任务拉取（断点续传：since=last-ntfy-id）
3. 白名单指令：TASK.PING→pong / TASK.STATUS→状态 / TASK.HEARTBEAT→回执；未知指令拒绝执行仅记录
4. 结果回传 results 主题 + 本地审计 task-exec.log

## 三、端到端实测（2026-09-27 17:54）
| 链路 | 结果 |
|---|---|
| 云端下发 TASK.PING → 沙箱回传 pong | ✅ |
| 云端下发 TASK.STATUS → 回执 kernel/worker/cron OK | ✅ |
| 未知指令 TASK.NTFY.LINK.TEST | ✅ 拒绝（UNKNOWN_INSTRUCTION_NOT_EXECUTED） |
| 沙箱心跳发布 heartbeat 主题 | ✅ |

## 四、边界
- 沙箱 35min 重置：ntfy 消息缓存在云端/公共服务，重置后 worker_ntfy.sh 由 cron 恢复执行，断点 last-ntfy-id 从上次位置续拉（消息不丢）
- 安全：白名单指令防注入；X-DID 头同源校验；主题名熵前缀防碰撞
- 待加固：云端自建 server 经 nginx 反代公网（替换公共 ntfy.sh）
