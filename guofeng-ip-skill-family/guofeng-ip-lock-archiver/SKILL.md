---
name: guofeng-ip-lock-archiver
version: 1.0.0
description: "国风IP资产全域锁档归档专家：SHA256哈希确权→Merkle清单→DID-BR-000002锚定→只读固化→四端同步(本地/云盘/台账/知识库)。当用户说'锁档'、'归档'、'确权'、'哈希入账'、'资产固化'、'四端同步'时使用。零成本本地工具，文本资产双副本，大体积音视频仅本地。"
metadata:
  requires:
    bins: ["sha256sum", "python3"]
  optional_bins: ["lark-cli"]
  pypi: []
did: "DID-BR-000002"
trace_symbol: "Ω₀⊂⊙∞⊂Ω"
---

# 国风IP锁档归档使 v1.0

> 实例可销毁 · 规则本体永存 · 哈希入账 · DID锚定 · 四端同步

## 核心设计原则

1. **哈希确权**：每个固化资产实算 SHA256，写入账本（HASH-LEDGER），哈希即身份凭证。
2. **DID锚定**：所有账本条目绑定 DID-BR-000002 + Ω₀⊂⊙∞⊂Ω，来源可溯、防抵赖。
3. **只读固化**：文本内核（脚本/清单/manifest/账本）固化后 chmod 444（只读），本地磁盘 + Git 冷存储双副本。
4. **分级归档**：文本/JSON/脚本 → 双副本推送；大体积音视频 → 仅本地归档锁档，不推公开湖、不对外展示（人像/写真类严禁公开）。
5. **零成本**：全部使用 sha256sum/python3/lark-cli 等本地免费工具，无任何云费用。
6. **四端独立核验**：任何回执不作真值，本地哈希/云端可达/台账记录三处独立对账后才算锁档成功。

## 快速路由

| 目标 | 命令 |
|------|------|
| 单资产哈希确权 | `python3 scripts/lock_archive.py --hash <文件路径>` |
| 整批目录锁档 | `python3 scripts/lock_archive.py --dir <目录> --batch-name <批次名>` |
| 生成批次清单并入账本 | `python3 scripts/lock_archive.py --dir <目录> --ledger ./HASH-LEDGER.csv` |
| 固化只读 | `python3 scripts/lock_archive.py --chmod-444 <目录>` |
| 生成锁档凭证 | `python3 scripts/lock_archive.py --certificate --batch-name <批次名>` |
| 四端对账核验 | `python3 scripts/lock_archive.py --verify --batch-name <批次名>` |

## 配置模板

`config/lock_config.json`：

```json
{
  "did": "DID-BR-000002",
  "trace_symbol": "Ω₀⊂⊙∞⊂Ω",
  "ledger_path": "./HASH-LEDGER.csv",
  "manifest_dir": "./manifests",
  "certificate_dir": "./certificates",
  "archive_policy": {
    "text_assets": {"copy_remote": true, "note": "文本/JSON/脚本双副本(Git冷存储)"},
    "media_assets": {"copy_remote": false, "note": "大体积音视频仅本地，人像/写真严禁公开"}
  },
  "feishu": {
    "enabled": false,
    "drive_folder_token_env": "FEISHU_DRIVE_FOLDER_TOKEN",
    "base_token_env": "FEISHU_BASE_TOKEN",
    "wiki_space_id_env": "FEISHU_WIKI_SPACE_ID"
  }
}
```

## 账本条目Schema（HASH-LEDGER.csv）

| 字段 | 说明 |
|------|------|
| batch_name | 批次名，如 guofeng-ip-v1.0.0 |
| asset_path | 资产相对路径 |
| sha256 | 资产实算哈希 |
| size_bytes | 文件大小 |
| timestamp | 锁档时间(ISO-8601) |
| did | DID-BR-000002 |
| trace | Ω₀⊂⊙∞⊂Ω |
| status | locked / pending |

## 清单/凭证模板

`templates/manifest_template.json`：

```json
{
  "manifest_id": "<MANIFEST-<YYYYMMDD>-<seq>>",
  "batch_name": "<批次名>",
  "created_at": "<ISO-8601>",
  "did": "DID-BR-000002",
  "trace": "Ω₀⊂⊙∞⊂Ω",
  "files": [
    {"path": "<相对路径>", "sha256": "<哈希>", "size": 0, "locked": true}
  ],
  "batch_root_hash": "<批次根哈希>"
}
```

`templates/certificate_template.md`：

```markdown
# 锁档凭证 <批次名>

- 批次根哈希：<batch_root_hash>
- 资产数：<N>
- 锁档时间：<ISO-8601>
- 确权DID：DID-BR-000002
- 溯源：Ω₀⊂⊙∞⊂Ω
- 状态：LOCKED-444

## 文件清单
| 路径 | SHA256 | 大小 | 状态 |
|------|--------|------|------|
| ... | ... | ... | locked |
```

## 四端同步对账（核验必做）

1. **本地**：清单哈希与文件实算哈希一致。
2. **Git冷存储**：文本资产双副本推送成功，远端可见。
3. **飞书云盘**（可选）：文件上传成功、token可解析。
4. **飞书台账**（可选）：记录数 = 资产数，SHA256一致。

## 错误处理

- 哈希不匹配 → 资产已变更，禁止标 locked，重新固化。
- 只读失败 → 检查文件属主/权限，修正后重试。
- 回执与实测不符 → 以实测为准，回执不作真值。

## 依赖清单（独立安装）

- 必选：Python 3.8+、`sha256sum`（coreutils）。
- 可选：`lark-cli`（飞书四端同步）。
- 无内部路径硬编码；所有路径通过 `config/lock_config.json` 与环境变量注入（`FEISHU_DRIVE_FOLDER_TOKEN` 等）。

Ω₀⊂⊙∞⊂Ω｜国风IP锁档归档使 v1.0 · ZONGYUAN-ROOT · DID-BR-000002
