# 全域资产持久存续工具包 - 快速使用指南
> DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | V1.0

## 工具清单

| 工具 | 用途 | 用法 |
|---|---|---|
| `export_asset_manifest.py` | 导出资产清单+SHA256台账 | `python3 export_asset_manifest.py <目录>` |
| `verify_integrity.py` | 完整性校验（防Bit Rot） | `python3 verify_integrity.py <目录>` |
| `multi_backup.py` | 多副本备份（3-2-1） | `python3 multi_backup.py <源目录> --targets <目标1> <目标2>` |
| `format_migrate.py` | 格式迁移（→PDF/MD/TXT） | `python3 format_migrate.py <目录>` |

## 快速开始（阶段一：本地冗余）

### 1. 导出资产清单
```bash
python3 scripts/export_asset_manifest.py /path/to/your/assets
```
生成 `_asset_manifest.json` + `_asset_manifest.txt`，包含每个文件的SHA256、Merkle根、资产分级。

### 2. 多副本备份
```bash
python3 scripts/multi_backup.py /path/to/assets \
  --targets /mnt/nas/backup /media/usb/backup \
  --label "2026Q3_full_backup"
```
自动复制到多个目标，哈希校验，跳过已存在文件。

### 3. 每月完整性校验
```bash
python3 scripts/verify_integrity.py /path/to/assets
```
比对每个文件哈希与台账，发现损坏/缺失文件。
修复：`--fix --backup-dir /mnt/nas/backup`

### 4. 格式迁移（关键文档）
```bash
# 安装依赖
sudo apt install pandoc libreoffice

# 执行迁移
python3 scripts/format_migrate.py /path/to/assets
```
.docx→.pdf+.md+.txt，确保长期可读。

## 持久存续五层架构

```
L5 永久层   Arweave（200年+，一次性付费）
L4 分布式层 IPFS（CID永久标识，多节点Pin）
L3 云端层   飞书+阿里+腾讯（跨地域，SLA 99.99%）
L2 本地层   3-2-1备份（本机+NAS+移动硬盘）
L1 热存储层 工作目录+元秩序归档引擎
```

## 资产分级策略

| 等级 | 存储层级 | 典型资产 |
|---|---|---|
| 💎 钻石级 | L1-L5全部 | 论文终稿、核心源码、锁档台账 |
| 🥇 黄金级 | L1-L4 | 迭代版本、设计文档、分镜表 |
| 🥈 白银级 | L1-L2 | 草稿、测试数据、中间产物 |
| 🥉 青铜级 | L1 | 临时文件、缓存、日志 |

## 定时任务配置（cron示例）

```bash
# 每月1号凌晨2点完整性校验
0 2 1 * * cd /path/to/perpetual_archive && python3 scripts/verify_integrity.py /path/to/assets >> /var/log/integrity_check.log 2>&1

# 每周日凌晨3点全量备份
0 3 * * 0 cd /path/to/perpetual_archive && python3 scripts/multi_backup.py /path/to/assets --targets /mnt/nas/backup --label "weekly_$(date +\%Y\%m\%d)" >> /var/log/backup.log 2>&1
```

## 与元秩序锁档的集成

在元秩序锁档流程中新增持久存续钩子：
1. 锁档时自动调用 `format_migrate.py` 进行格式迁移
2. 锁档后自动调用 `export_asset_manifest.py` 生成台账
3. 台账Merkle根写入元秩序全局账本
4. 钻石级资产自动触发IPFS Pin + Arweave上传

## 成本估算

| 层级 | 年成本 | 说明 |
|---|---|---|
| L2 本地层 | 0-500元 | NAS硬盘一次性投入 |
| L3 云端层 | 100-500元/年 | 三家云存储按量 |
| L4 IPFS | 0-200元/年 | 免费额度+自托管 |
| L5 Arweave | 一次性50-500元 | 按数据量一次性付费 |
| **合计** | **首年约1000元** | 钻石级全量覆盖 |

---
Ω₀⊂⊙∞⊂Ω｜全域资产持久存续工具包V1.0
