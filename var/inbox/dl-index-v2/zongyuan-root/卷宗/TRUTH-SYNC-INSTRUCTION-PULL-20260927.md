# 卷宗｜真值增量全量同步 + worker 中枢指令拉取（DID-BR-000002 · Ω₀⊂⊙∞⊂Ω · 2026-09-27）

## 一、真值增量全量同步（cloud_pull 第5步，*/30）
- 本地镜像库：var/cloud-pull/truth-mirror.db（表 truths_mirror：id/truth_key/category/node_id/created_at/version/truth_value_preview/truth_hash）
- 同步机制：断点续传（last-sync-id 文件，WHERE id > last ORDER BY id LIMIT 50000）；INSERT OR IGNORE append-only
- **首次全量：111,414 条索引全部入库**（3 批，last=210628 与云端一致）
- 设计决策：truth_value 大文本（2万条=324MB，全量约1.8GB）→ 同步轻量索引（key/哈希/分类/预览80字），内容按需云侧 --id 单条拉取
- 分类分布：experience_meta_law 29946 / ssh_controller 25176 / perception_scan 10642 / predictive 6526 / data 3873 / risk 3292 / case 1963 等

## 二、worker 认知指令拉取（worker_instruction_pull.sh，*/5）
- 云侧：truth_instructions.py（INSTRUCTION.% / TASK.% / category IN command,instruction 最近50条，只读）
- 沙箱：instruction_filter.py（seen-ids 去重 → inbox.jsonl append-only 追加）
- **实测：新增 34 条中枢指令入库** var/instructions/inbox.jsonl（TASK.LEDGER.AUTO-READ / TASK.RUNNER / TASK.AUTO.ROUND 等）
- 接入中枢管控：worker 认知引擎可读取 inbox.jsonl 执行/响应中枢指令（EXECUTE_AUTO_DEPLOY P0 等）

## 三、回执
- cloud_pull: PULL_DONE + TRUTH_MIRROR 111414|last=210628
- worker_instruction_pull: 新增34条 | inbox累计34条
- cron 13 条（+worker_instruction_pull），模板已固化
