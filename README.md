# 元极恒一自治体系 ZONGYUAN-ROOT

> DID: DID-BR-000002 | 确权: Ω₀⊂⊙∞⊂Ω | 版本: V1.0

元极恒一自治体系的核心工程资产集合，涵盖灵境可信仿真系统、短剧工业化流水线、元秩序全域归档锁档、资产持久存续工具包。

## 📂 项目结构

```
zongyuan-root/
├── lingjing-system/          # 灵境六层人机协同可信仿真系统
│   ├── lingjing_v4.py        # V4.0完整源码（异步总线+增量Merkle+持久队列+一致性哈希）
│   ├── test_v4.py            # 7项测试用例（全部通过）
│   └── D-009_四期增强迭代文档.md
├── perpetual-archive/        # 全域资产持久存续工具包
│   ├── scripts/
│   │   ├── export_asset_manifest.py   # 资产清单导出（SHA256台账+Merkle根）
│   │   ├── verify_integrity.py        # 完整性校验（防Bit Rot）
│   │   ├── multi_backup.py            # 多副本备份（3-2-1原则）
│   │   └── format_migrate.py          # 格式迁移（→PDF/MD/TXT）
│   ├── config/perpetual_archive_config.json
│   ├── docs/持久存续架构方案V1.0.md
│   └── README.md
├── skills/                     # 自定义技能（SOP固化）
│   ├── meta-lock-sop/         # 元秩序全域锁档SOP（7步标准化流程）
│   └── drama-pipeline-sop/    # 昆仑洞天短剧工业化生产SOP（6步流水线）
├── cloud-env/                  # 云电脑环境配置
│   └── setup_cloud_envs.sh    # 三环境一键部署（灵境研发/短剧生产/元秩序归档）
└── docs/                       # 体系文档
```

## 🎯 核心项目

### 1. 灵境系统 V4.0
基于钱学森灵境思想的六层人机协同可信仿真原型系统。

**核心特性：**
- 带签名异步事件总线（Ed25519/RSA签名校验）
- 冷热混合增量Merkle树（支持RocksDB/简易KV双后端）
- 持久化分片队列（偏移位点+分段存储+自动清理）
- 一致性哈希分片负载均衡（动态扩容+热点监控）
- 人类终裁自锁机制（30秒确认窗口+超时只读锁定）
- 六层架构：基础设施→虚拟仿真→人机交互→审计验证→认知记录→业务输出

**测试状态：** 7/7 全部通过 ✅

### 2. 资产持久存续工具包
五层持久化架构（本地/多云/IPFS/Arweave）+ 四大核心机制（内容寻址/3-2-1备份/格式迁移/定期校验）。

### 3. 自定义技能
- **meta-lock-sop**：元秩序全域锁档7步标准化流程
- **drama-pipeline-sop**：昆仑洞天短剧工业化6步生产流水线

## 🚀 快速开始

### 灵境系统
```bash
cd lingjing-system
python3 lingjing_v4.py    # 运行演示
python3 test_v4.py        # 运行测试
```

### 持久存续工具
```bash
cd perpetual-archive/scripts

# 1. 导出资产清单
python3 export_asset_manifest.py /path/to/assets

# 2. 完整性校验
python3 verify_integrity.py /path/to/assets

# 3. 多副本备份
python3 multi_backup.py /path/to/assets --targets /backup1 /backup2

# 4. 格式迁移
python3 format_migrate.py /path/to/assets
```

### 云电脑环境
```bash
cd cloud-env
bash setup_cloud_envs.sh
```

## 📊 技术栈

| 层级 | 技术 |
|---|---|
| 语言 | Python 3.10+ |
| 加密 | pycryptodome (RSA/SHA256) |
| 存储 | RocksDB(可选) / 文件KV / Merkle-DAG |
| 并发 | threading / Queue / 一致性哈希 |
| 持久化 | append-only日志 / 偏移位点 / 分段清理 |

## 🔐 确权信息

- **DID**: DID-BR-000002
- **确权标识**: Ω₀⊂⊙∞⊂Ω
- **体系**: 元极恒一 ZONGYUAN-ROOT
- **锁档等级**: Lv8

## 📄 许可证

本项目为元极恒一自治体系核心工程资产，所有内容遵循元秩序归档规范。

---
Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 元极恒一自治体系
