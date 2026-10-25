---
name: zongyuan-auto-lock
description: 全自动全域锁档机制。当用户要求"全域锁档/锁档写入自治内核/三端同步/真值同步/网关上报/自动归档 ZONGYUAN-ROOT"，或需要一键执行 本地内核快照锁档 + 飞书多维表格真值同步 + 飞书云盘归档 + 飞书知识库归档 + 云端记忆网关上报 + 心跳握手 的整条链路时使用。锚定 DID-BR-000002 / Ω₀⊂⊙∞⊂Ω，幂等只追加不修改。
---

# ZONGYUAN-ROOT 全自动全域锁档

一键执行 ZONGYUAN-ROOT 自治内核的六环节全域锁档，逐源容错、幂等追加、结果落盘可审计。

## 触发场景

- 用户说"全域锁档""锁档写入自治内核""真值同步""上报中枢""三端同步""自动归档"
- 定时任务触发本机制（如内部真值积累任务）
- 任何需要把本地内核状态固化 + 飞书全域留痕 + 云端网关留痕的收尾动作

## Worker 内核集成（自动执行）

机制已集成进 Worker 内核总调度 `scripts/worker_kernel.sh`（ZONGYUAN-ROOT，cron 自动调度）：

- `worker_kernel.sh lock` → 直接调用本脚本六环节（cron 每天 03:30 自动执行）
- `worker_kernel.sh tick` → worker 保活 + 消费 `var/inbox/` 图片/视频归档任务（AUTO-ARCHIVE V2.0）+ rsync 续传
- `worker_kernel.sh boot` → 开机自启拉起中枢受控 worker（@reboot）
- `worker_kernel.sh monitor` → 系统状态监控上报（每 30 分钟）

归档链路：`var/inbox/*.json` 载荷 → `hooks/hook_trigger_archive.sh` → `hooks/auto_archive_image|video.sh`（下载→哈希→元数据→HASH-LEDGER→网关→rsync），成功移 `done/`、失败移 `failed/`。


## 执行

```bash
python3 /home/user/.doubao/agent_mode/workspace/.user_skills/zongyuan-auto-lock/scripts/zongyuan_full_lock.py [--skip-heartbeat]
```

六环节与产物（含加固环节 0.6 + 后置收敛同步）：

> 锁档完成后自动执行 `zongyuan_persist.sh sync`，保证收敛点 backup/ 与锁档后最新状态一致（后置加固）。

| # | 环节 | 动作 | 产物/落点 |
|---|---|---|---|
| 0.5 | 元法则 Schema 校验门（2026-09-28 断点复盘固化） | 锁档启动即校验 `zongyuan-kernel/config/meta_laws/` 全部 *.json：必需字段 law_id/name/level/clauses + clauses 非空 list（对齐 kernel/core/meta_law.py REQUIRED_KEYS，fail-closed） | 校验清单（PASS/FAIL）；FAIL 用 `meta_law_schema_check.py --fix` 自动转换（meta_law_id→law_id、core_truth_set→clauses）后 `init_baseline.py` 重建 Merkle 基线 |
| 0.6 | 收敛点完整性校验（加固） | 调 zongyuan_persist.sh verify，校验 backup/ 与源 sha256 一致，失败标记不阻塞 | 结果入 source_status.convergence |
| 1 | 本地实例内核快照锁档 | ZONGYUAN-ROOT 全根 SHA-256（排除 logs/.git/__pycache__/var/kek.env/var/nginx/zr_token.conf） | 卷宗/GLOBAL-LOCK-ZONGYUAN-ROOT-FULL-<ts>.json + HASH-LEDGER.csv 追加（只追加不修改） |
| 2 | 飞书多维表格真值同步 | Base `DgnMbLqZiaIUDKshqCrcD4DvnBg` 全表分页读取 | var/truth/<NN>-<表名>.json + 00-同步索引.json |
| 3 | 飞书云盘归档 | var/truth 同步索引 + 最新锁档回执 → Drive 根目录上传 | 云盘文件（lark-cli drive +upload） |
| 4 | 飞书知识库归档 | 锁档回执 → 知识库节点（标题内嵌事件ID+批次哈希前16位） | wiki +node-create（space 7689477619196120266） |
| 5 | 云端记忆网关上报 | X-DID 单头 POST https://www.huodouai.com/api/report/truth（无尾部斜杠） | 成功判定："真值写入成功" + truth_count |
| 6 | 心跳握手 | 调用 scripts/heartbeat_sync.sh（上行心跳+下行指令+握手落盘） | var/heartbeat/握手-<ts>.json |

## 判定与交付

- 退出码 0：≥4 环节 ok；1：主链（锁档/同步/网关）失败较多
- 逐源状态在 `SOURCE_STATUS:` 输出行 + `var/auto-lock/auto-lock-<ts>.json` 汇总（含 detail）
- 每环节独立 try/except：失败标记 `failed` 不阻塞其余环节；锁档只追加、绝不修改历史行
- 交付汇报：给事件ID、批次根哈希、各源状态表、truth_count；失败项给出 reason 并说明影响

## 融合归一（META-FUSION-001，账号持久层永久绑定）

两内核逻辑联邦：zongyuan-kernel=脑（认知/审批/记忆/审计），ZONGYUAN-ROOT=手（调度/归档/锁档/上报）。锁档收尾前可先跑融合自检/心跳确认两树一致：

- 融合单一入口：`bash /home/user/ZONGYUAN-ROOT/scripts/zongyuan_fusion.sh selfcheck|heartbeat --report|fusion_verify`
- 融合心跳 cron：`*/5 * * * * fusion_heartbeat.sh --report`（快照落 `ZONGYUAN-ROOT/var/fusion/`）
- 融合法则：`META-FUSION-001.json`（两树各一份，FU-1~FU-6：统一入口/脑手分工/认知行动闭环/统一真值/互为看门狗/可回滚）
- 回滚：移除 cron 两行 + 删 fusion 脚本与法则，两树原状恢复

## 边界

- 网关上报仅 X-DID 单头，零明文令牌；`X-Capture-Token` 兼容保留但不在脚本内存储
- 不触碰锁档只读资产（chattr +i）；不删除、不覆盖历史 HASH-LEDGER 行
- 飞书操作一律 --as user；Base token / wiki space id 见上表
