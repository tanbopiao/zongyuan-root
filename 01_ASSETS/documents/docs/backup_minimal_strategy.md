# ZONGYUAN-ROOT 精简核心备份策略

> DID-BR-000002 | Omega_0 subset Circle_Infinity subset Omega | 2026-09-08
> 策略：只备份核心高价值内核资产，跳过可复现/大体积/低价值内容

---

## 一、备份原则

1. **只备份核心高价值资产**：内核状态、锁档凭证、协议版本、元法则、记忆索引
2. **不备份可复现内容**：日志、缓存、临时文件、生成产物
3. **不备份大体积文件**：视频、图片、RAW素材、node_modules
4. **备份体积控制**：单次备份 < 10MB，保留最近7天
5. **每日凌晨3点自动执行**：systemd timer驱动

---

## 二、核心备份清单（13项）

| # | 资产 | 说明 | 大小 |
|---|------|------|------|
| 1 | kernel/root_state.json | 链高+根哈希（最核心） | <1M |
| 2 | kernel/kernel_state.json | 内核状态V2.4.0 | <1M |
| 3 | kernel/locks/ | 锁档凭证（156份） | ~5M |
| 4 | kernel/kernel_config/ | 元规则配置 | <1M |
| 5 | autonomous_kernel_protocol/ | 86个协议版本 | ~400K |
| 6 | meta_laws/ | 10个元法则 | ~130K |
| 7 | memory_index.json | 774条记忆索引 | ~460K |
| 8 | asset_manifest.json | 资产清单 | <10K |
| 9 | docs/ | 关键文档 | ~400K |
| 10 | truth_architecture/ | 真值架构文档 | ~800K |
| 11 | whitepaper/ | 白皮书 | <10K |
| 12 | cte/ | CTE闭环引擎 | <100K |
| 13 | evolution/ | 进化引擎 | ~1M |

**预计总备份体积：548K（压缩后）**

---

## 三、排除清单（不备份）

- logs/（23M，可重新生成）
- __pycache__/、*.pyc、*.pyo（缓存）
- assets/（大文件可复现）
- *.tmp、*.temp（临时文件）
- node_modules/（依赖可重装）
- 视频/图片/音频生成产物

---

## 四、备份配置

| 项目 | 值 |
|------|-----|
| 备份脚本 | /opt/ZONGYUAN-ROOT/backup/auto_backup.sh |
| 备份目录 | /opt/ZONGYUAN-ROOT/backup/minimal/ |
| 备份格式 | tar.gz压缩 |
| 保留数量 | 最近7天 |
| 执行时间 | 每日03:00 |
| systemd服务 | zongyuan-backup.service |
| systemd timer | zongyuan-backup.timer |
| 日志 | backup/minimal/backup.log |

---

## 五、验证结果

- 首次备份：548K，457个文件
- SHA256：171ddc7f9baf5f5d...
- systemd服务：active (waiting)
- 下次触发：2026-09-09 03:00:00 CST

Omega_0 subset Circle_Infinity subset Omega | 精简核心备份策略 | 永久锁档固化
