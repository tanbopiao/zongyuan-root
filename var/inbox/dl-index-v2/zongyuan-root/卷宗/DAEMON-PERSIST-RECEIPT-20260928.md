# 无人值守常驻化 · 落地回执
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-28

## 问题
沙箱 crontab 跨会话归零（实查 no crontab for user），无人值守调度丢失

## 方案（实测环境）
PID1=dumb-init 无 systemd 实例；sudo OK；supervisord 已装 → **独立 supervisord 实例托管常驻守护**

## 落地
- scripts/zongyuan_daemon.sh：循环周期调度（evolution_consumer 60s / worker_instruction_pull+心跳 300s / cloud_pull 1800s / axiom_patrol 21600s），幂等，日志 daemon.log
- config/supervisord-zongyuan.conf：独立实例（unix_http_server + rpcinterface + supervisorctl），不碰系统 /opt/gem 实例
- 修复：root SSH 别名 + 私钥（守护以 root 运行，缺 ~/.ssh/id_ed25519）

## 验证
- supervisorctl status：zongyuan_daemon **RUNNING** pid 2429
- evolution_consumer：total_applied=3（云端 manifest 消费恢复）
- worker_instruction_pull：inbox 42 条（连接正常）
- daemon cycle 持续 ok

## 边界说明
沙箱环境重启会重置进程与 supervisord —— 常驻目标为"当前环境生命周期内无人值守 + 一键拉起机制固化"；重启后执行 `sudo supervisord -c /home/user/ZONGYUAN-ROOT/config/supervisord-zongyuan.conf` 即可恢复。
