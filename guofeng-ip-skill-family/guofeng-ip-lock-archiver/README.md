# 国风IP锁档归档使 guofeng-ip-lock-archiver v1.0

> 国风IP资产全域锁档归档专家：SHA256哈希确权 → Merkle清单 → DID锚定 → 只读固化 → 四端同步

## 安装

```bash
# 必选：python3 + sha256sum(coreutils)，系统自带
# 可选：lark-cli（飞书四端同步）
```

## 快速开始

```bash
# 单资产哈希确权
python3 scripts/lock_archive.py --hash ./storyboard.json

# 整批目录锁档 + 入账本
python3 scripts/lock_archive.py --dir ./release-v1.0 --batch-name guofeng-ip-v1.0.0 --ledger ./HASH-LEDGER.csv

# 固化只读
python3 scripts/lock_archive.py --chmod-444 ./release-v1.0
```

## 配置

编辑 `config/lock_config.json`：
- `ledger_path` / `manifest_dir` / `certificate_dir`：账本与产物路径
- `archive_policy`：文本资产双副本 / 媒体资产仅本地（人像写真严禁公开）
- `feishu`：四端同步开关与token环境变量名

## 分级归档铁律

1. 文本/JSON/脚本：本地 + Git冷存储双副本。
2. 大体积音视频：仅本地归档锁档，不推公开湖。
3. 人像/写真类：仅本地，不对外展示。

## 确权

所有条目携带 `did: DID-BR-000002` + `trace: Ω₀⊂⊙∞⊂Ω`；回执不作真值，四端独立核验。

Ω₀⊂⊙∞⊂Ω｜国风IP锁档归档使 v1.0 · ZONGYUAN-ROOT · DID-BR-000002
