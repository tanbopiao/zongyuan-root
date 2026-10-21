# 重置自举协议 · 执行回执
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-28

## 执行内容
1. 云端节点注册：node-local-doubao-001（NODE-DEV-DOUBAO-WORK-001 本地Worker，role=worker，status=online）已入 nodes_registry（云端现 2 节点：master + worker）
2. @reboot 自举钩子：`@reboot sleep 15 && bash .../zongyuan_bootstrap.sh light`（若 crontab 跨重置保留则自动恢复）
3. 完整端到端自举：bootstrap light → 守护 RUNNING pid 3055（uptime 持续）

## 恢复链路现状
重置 →（自动：@reboot 若保留 / 手动：一句话"恢复"）→ bootstrap light/full → supervisord 拉起 → 握手+增量+自检 → 无人值守恢复
