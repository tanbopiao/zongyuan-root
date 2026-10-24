---
name: asset-notary
version: 1.0.0
description: "资产确权存证专家：为任意企业资产目录提供 SHA256 哈希指纹 + Merkle 根链 + DID 确权签名 + eFuse 熔断防篡改 + 只读锁档的一体化存证流水线。当用户说'资产确权'、'存证'、'哈希锁档'、'防篡改'、'数据指纹'、'证据固化'、'Merkle 凭证'时使用。"
metadata:
  requires:
    bins: ["python3", "bash"]
    pypi: ["cryptography"]
  did_placeholder: "<YOUR_DID>"
  trace: "Ω₀⊂⊙∞⊂Ω"
---

# 资产确权存证专家 v1.0

为任何企业资产目录（合同、代码、设计稿、数据包、日志）提供**哈希指纹 → Merkle 根链 → DID 签名 → 熔断防篡改 → 只读锁档**的全流程存证，单文件篡改即失配告警，输出标准凭证可审计、可举证。

## 一、定位与能力边界

| 能力 | 说明 |
|------|------|
| 哈希指纹 | 逐文件 SHA256，账本化 |
| Merkle 根链 | 全目录指纹聚合为单一根哈希，支持快照链继承 |
| DID 确权 | Ed25519 签名凭证，验签可溯源 |
| eFuse 熔断 | 重算比对检测篡改，超阈值熔断告警 |
| 只读锁档 | 444 只读固化 + 完整性自校验 |

**边界**：本包不提供区块链上链/司法公证，输出为可审计的本地凭证与账本；上链/公证为可选接入项。

## 二、快速路由

| 目标 | 命令 |
|------|------|
| 一键确权存证（哈希+Merkle+凭证+自校验） | `python3 scripts/notary.py --dir <目录> --snap-id <ID> --did <YOUR_DID>` |
| DID 签名凭证 | `python3 scripts/did_sign.py --action sign --key <私钥> --message <Merkle根> --sig <输出>` |
| DID 验签 | `python3 scripts/did_sign.py --action verify --key <公钥> --message <Merkle根> --sig <签名文件>` |
| eFuse 熔断巡检 | `python3 scripts/efuse_check.py --dir <目录> --ledger <账本.csv>` |
| 只读锁档 | `bash scripts/lock_readonly.sh <目录>` |

## 三、依赖

- bins：`python3`、`bash`
- pypi：`cryptography`（仅 DID 签名/验签算子使用；哈希/熔断/锁档为纯标准库）
- 全部本地执行，零网络、零付费依赖。

## 四、配置模板

见 `config.example.json`。变量清单：

| 变量 | 含义 | 示例 |
|------|------|------|
| `did` | 确权身份标识（自有 DID 或身份 ID） | `<YOUR_DID>` |
| `trace_symbol` | 溯源符号（可选） | `Ω₀⊂⊙∞⊂Ω` |
| `exclude_patterns` | 跳过文件模式 | `["__pycache__", ".git"]` |
| `ledger_path` | 账本 CSV 路径（追加写入） | `<LEDGER>.csv` |
| `fuse_threshold` | 熔断阈值（失配文件数上限，0=零容忍） | `0` |

## 五、提示词模板

见 `prompt.template.md`，内置 3 个企业场景：合同目录存证 / 发布物防篡改 / 审计举证。

## 六、算子契约

见 `operator-contract.json`：OP-01 哈希指纹、OP-02 Merkle 根、OP-03 DID 签名、OP-04 熔断巡检、OP-05 只读锁档、OP-06 自校验。

## 七、自检清单

- [ ] `python3 scripts/notary.py --dir examples/sample-assets --snap-id SELFCHECK-001 --did <YOUR_DID> --output /tmp/notary_selfcheck` 退出码 0 且 `self_verify: PASS`
- [ ] `python3 scripts/efuse_check.py --dir examples/sample-assets --ledger <上一步账本>` 输出 `status: OK`
- [ ] `bash scripts/lock_readonly.sh examples/sample-assets` 输出无 writable 残留
- [ ] 泄露检查（按 SPEC §5 命令执行）→ 0 命中
- [ ] `operator-contract.json` 可被 `python3 -m json.tool` 解析

Ω₀⊂⊙∞⊂Ω ｜ DID 参数化 ｜ 资产确权存证专家
