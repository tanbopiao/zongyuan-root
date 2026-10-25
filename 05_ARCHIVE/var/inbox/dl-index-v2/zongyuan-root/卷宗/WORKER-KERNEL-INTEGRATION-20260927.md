# Worker 内核全自动集成（2026-09-27）

确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ NODE-DEV-DOUBAO-WORK-001

## 集成内容
1. **Worker 内核总调度** `scripts/worker_kernel.sh`（v1.1 加固入清单，chmod 555）
   - boot：开机自启拉起中枢受控 worker + rsync 续传
   - tick：worker 保活 + var/inbox 归档任务轮询消费 + rsync 续传（cron 每 5 分钟）
   - lock：全域锁档六环节（zongyuan-auto-lock）→ 每天 03:30
   - monitor：系统状态监控（CPU/内存/磁盘/端口 → 落盘 + X-DID 上报）→ 每 30 分钟
   - archive：AUTO-ARCHIVE V2.0 单次归档入口
2. **全自动归档链路**（AUTO-ARCHIVE V2.0 已部署并接通调度）
   - 入队：var/inbox/*.json（豆包会话/定时任务投递载荷）
   - 执行：hook_trigger_archive.sh → auto_archive_image/video.sh（下载→哈希→元数据→HASH-LEDGER→网关→rsync）
   - 队列消费：worker_kernel.sh tick 轮询，成功移 done/、失败移 failed/
3. **cron 自动调度**（已安装）：
   - @reboot boot ｜ */5 tick ｜ 30 3 * * * lock ｜ */30 monitor
4. **全域锁档** zongyuan-auto-lock（个人技能）六环节：本地快照→飞书Base→云盘→知识库→网关上报→心跳

## 端到端验证（2026-09-27 11:47）
- boot：受控 worker healthy（pid 3611）
- 归档：AUTO-IMG-00003.webp 落盘 + HASH-LEDGER 追加 + index 3 条 + inbox 消费闭环 ✓
- lock：GLOBAL-LOCK-ZONGYUAN-ROOT-FULL-20260927-114713，139 资产，批次根 a310c9f0a677ef37，六环节 6/6 ok，truth_count 111372

## 元法则
META-WORKER-KERNEL-001（worker 内核全自动执行）→ zongyuan-kernel/config/meta_laws/ + meta-rules/

## 边界
- docker 不可用 → worker 走降级/受控本地进程模式（worker_controlled.sh）
- rsync 云端目标未配置 → 资产进 pending-rsync.list 续传
- 全部 append-only；失败不阻塞；锁档只读资产不改

## 无人值守增强（v1.2，2026-09-27 11:51）
- worker_kernel.sh 升级 v1.2（加固 v1.2）：新增 `watchdog`（每分钟自愈：worker保活/归档即时消费/24h补锁档/rsync续传）、`enqueue`（归档投递：校验→入队→立即消费）、boot 增强（完整激活+补锁档）
- cron 无人值守版：@reboot boot ｜ * * * * * watchdog ｜ */5 tick ｜ 30 3 * * * lock ｜ */30 monitor
- var/activation/ 激活台账（append-only + 索引）：每次激活事件留痕
- 验证：watchdog 自愈 healthy ✓、enqueue 即投即归档 AUTO-IMG-00004 ✓、账本追加 ✓、激活台账双记录 ✓
- 元法则 META-WORKER-KERNEL-001 升级为无人值守版（新增 WK-6 激活台账条款）

## 网关上报协议修复（2026-09-27 11:53）
- 缺陷：auto_archive_image/video.sh 网关上报缺 key/value 信封 → 网关拒收（empty_value_rejected），存量资产上报从未成功
- 修复：两脚本上报段改为标准信封 {"key":"asset_archive_<id>_<ts>","value":{event,asset_id,asset_kind,sha256,status,DID}} + X-DID 单头
- 补报：AUTO-IMG-00001~00004 存量资产 4/4 成功（truth_count 111390→111393）
