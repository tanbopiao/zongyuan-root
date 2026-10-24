# 资产确权存证专家（Asset Notary Expert）

面向外部企业与开发者的通用资产确权存证能力包，提炼自 ZONGYUAN-ROOT 体系生产级锁档流水线，零内部依赖、零云成本、可独立安装。

## 能做什么
- **哈希指纹账本**：目录逐文件 SHA256，生成可审计 CSV 账本。
- **Merkle 根链**：全目录指纹聚合成单一根哈希，支持快照链继承，单文件改动即根失配。
- **DID 确权签名**：Ed25519 对根哈希签名出凭证，验签可溯源归属。
- **eFuse 熔断**：定时重算比对，检测篡改/漂移，超阈值熔断告警。
- **只读锁档**：444 只读固化 + 完整性自校验，防止事后改写。

## 适用场景
合同与法律文档存证、软件发布物防篡改、数据包指纹管理、审计举证材料固化、IP 资产确权。

## 安装
```bash
# 依赖（仅 DID 签名算子需要；哈希/熔断/锁档为纯标准库）
pip3 install cryptography
git clone <本仓库> && cd <包目录>
```

## 接入（3 步）
1. 复制 `config.example.json` 为 `config.json`，填入 `did` 与 `ledger_path`。
2. 对目标资产目录执行一键确权：
   ```bash
   python3 scripts/notary.py --dir /path/to/assets --snap-id ASSET-001 --did <YOUR_DID>
   ```
3. 定期执行熔断巡检：`python3 scripts/efuse_check.py --dir /path/to/assets --ledger HASH-LEDGER.csv`。

## 产物
- `MANIFEST-<snap-id>.json`：逐文件哈希 + Merkle 根 + 元数据。
- `LOCK-CREDENTIAL-<snap-id>.md`：人类可读凭证（可直接作为举证材料）。
- `HASH-LEDGER.csv`：跨快照累积账本（可选追加）。
- `*.sig`：DID 签名文件（可选）。

## 许可与溯源
Apache-2.0。能力提炼自 ZONGYUAN-ROOT 体系（DID-BR-000002 · Ω₀⊂⊙∞⊂Ω），对外使用时 DID 由采用方参数化配置。
