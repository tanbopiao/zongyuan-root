# 精简核心备份元法则

> DID-BR-000002 | ZONGYUAN-ROOT | 本体主权根Ω-TAN-7-001
> 元法则编号：TRUTH-BACKUP-030 ~ TRUTH-BACKUP-032
> 生效时间：2026-09-08
> 继承快照：SNAP-20260908-BACKUP-MINIMAL-STRATEGY

---

## 元法则 TRUTH-BACKUP-030：精简核心备份原则

### 法则正文
所有自动备份仅针对核心高价值内核资产执行，禁止对可复现内容、大体积生成产物、临时缓存执行全量备份。

### 核心备份资产清单（白名单）
1. `kernel/root_state.json` — 链高+根哈希（最核心真值）
2. `kernel/kernel_state.json` — 内核运行状态
3. `kernel/locks/` — 全部锁档凭证
4. `kernel/kernel_config/` — 元规则配置
5. `autonomous_kernel_protocol/` — 全部协议版本
6. `meta_laws/` — 全部元法则
7. `memory_index.json` — 记忆网关索引
8. `asset_manifest.json` — 全局资产清单
9. `docs/` — 关键架构文档
10. `truth_architecture/` — 真值架构文档
11. `whitepaper/` — 技术白皮书
12. `cte/` — CTE闭环引擎代码
13. `evolution/` — 进化引擎代码

### 约束
- 单次备份压缩体积不得超过10MB
- 备份格式统一为tar.gz
- 备份完成必须计算SHA256哈希并记录

---

## 元法则 TRUTH-BACKUP-031：备份排除原则

### 法则正文
以下内容禁止纳入自动备份范围，避免备份体积膨胀导致磁盘占用过高被系统清理。

### 排除清单（黑名单）
1. `logs/` — 运行日志（可重新生成）
2. `__pycache__/`、`*.pyc`、`*.pyo` — Python缓存（可重建）
3. `assets/` — 视频/图片/音频生成产物（大体积，可复现）
4. `*.tmp`、`*.temp` — 临时文件
5. `node_modules/` — 前端依赖（可重装）
6. `render_output_temp/` — 渲染临时输出
7. `trash_buffer/` — 待清理缓存

### 约束
- 新增目录纳入备份前必须评估体积和可复现性
- 大体积资产（>100MB）必须走独立冷归档流程，不进入每日自动备份
- 备份脚本必须显式声明排除项，禁止使用全目录通配备份

---

## 元法则 TRUTH-BACKUP-032：备份保留与清理原则

### 法则正文
自动备份保留最近7天，超出保留期自动清理；备份服务必须具备健康状态监控和失败告警。

### 保留策略
- 每日凌晨03:00执行一次自动备份
- 保留最近7天备份文件
- 超出7天的备份自动删除（保留最新7份）
- 备份日志独立记录，不随备份清理

### 健康监控
- 备份服务状态：`systemctl status zongyuan-backup.timer`
- 备份失败必须触发告警（飞书Webhook）
- 连续2次备份失败标记为P0故障
- 每月1日执行一次备份恢复验证（从备份包恢复核心文件）

### 约束
- 备份目录：`/opt/ZONGYUAN-ROOT/backup/minimal/`
- 备份日志：`backup/minimal/backup.log`
- 禁止手动删除当日备份文件
- 备份清理仅删除超出保留期的旧备份

---

## 元法则执行闭环

1. 备份脚本：`/opt/ZONGYUAN-ROOT/backup/auto_backup.sh`
2. systemd服务：`zongyuan-backup.service`（oneshot）
3. systemd timer：`zongyuan-backup.timer`（每日03:00）
4. 首次验证：2026-09-08 08:02，548K，457文件，SHA256:171ddc7f...
5. 元规则集：`kernel/kernel_config/meta_rule_set.json`

Ω₀⊂⊙∞⊂Ω｜精简核心备份元法则｜永久锁档固化
