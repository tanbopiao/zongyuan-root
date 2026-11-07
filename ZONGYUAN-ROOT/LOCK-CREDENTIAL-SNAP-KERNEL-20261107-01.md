# 全域锁档凭证｜SNAP-KERNEL-20261107-01

## 锁档元数据

| 字段 | 值 |
|------|-----|
| 快照ID | SNAP-KERNEL-20261107-01 |
| DID标识 | DID-BR-000002 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |
| 归档节点 | ZONGYUAN-ROOT |
| 锁档时间 | 2026-11-07 12:38:26 +08 |
| 资产总数 | 16个文件 |
| Merkle根 | `03eae829c19d96532b4dba7cea8013bf1c1164805dfe6ad596d7ac9232ce5bd2` |
| 归档包整体哈希 | `546cbce171b58ce53d1110b573b46cdf0991c49a2d7f9ea3edf61d61a02cd758` |

## 逐文件哈希

| 文件 | 大小 | SHA-256 |
|------|------|---------|
| .global_root_registry.json | 461B | `bb557bda3b97511b6f3b040ee24167def948e96d148383d050f743752599a47c` |
| lock-receipts/SEED-TRACE-REPORT-20261107.json | 1423B | `b662b66de962c8c1f48251d91b468c98a037393e871ab5e0cdd796f7b76a2dba` |
| rules/ARBITRATION-PENDING-20261107.json | 1010B | `b91695827a4eae2c30b510411a99b76de7d4d4dfa5874913beb7c34327ef2df6` |
| rules/ARBITRATION-REQUEST-20261107.json | 4363B | `2d77a6f2783b6b8e18fedeca11665f72394207783aa44c2c698996c1cbe7875d` |
| rules/AUTHORITY.json | 1171B | `71af1d558b4e5bd0f6f709ab920a6ef9e05fa7f3ebdf09b145325296415ac1d7` |
| rules/CLOUD-RULES-DIGEST-V1.0.md | 22301B | `30f4c8d763a7506d91eaa7b7cd7a8dc6bf9f194f5b79ad762096f449ac38d21b` |
| rules/CLOUD-RULES-V1.0.json | 4613B | `099c8de0255f34309bb2e6b8f38034e709b334169fc206529e2b1188ab351dba` |
| rules/LOCK-RECEIPT-V1.1.json | 1427B | `d2f9a349c1b78f4043c971b3847db3c58da903461c25e68b1ea19bf0b9aae5f5` |
| rules/LOCK-RECEIPT-V1.2.json | 1535B | `51f61a80017e9658985b53344c336b3ae4c0497dd60c658300d4da617259e5ad` |
| rules/LOCK-RECEIPT.json | 971B | `dfd7d52ab8fc7c85b99905ffd97771e3243e85fa9146cb0652de8c6b993f46ac` |
| rules/METALAW-REGISTRY-V1.0.json | 28914B | `894e81e50f9b8469f0b0283e3b7915d47d61906ecaf429d526ef91eeac8dc661` |
| rules/METALAW-REGISTRY-V2-CLOUD-AUTHORITY.json | 36548B | `a7a6ee610a22500581391d46b97790367d445ae28de4bcce568b16730f0ee8b7` |
| rules/NODE-CLEANUP-REQUEST-20261107.json | 1390B | `606b6d3d301a2617fc54fbc853c9eec0cdfc7aab6bc1e3c2ce4cdc13b1fa98cb` |
| rules/NODE-HOMOLOGOUS-APPLICATION-20261107.json | 2427B | `2a97d5c9787f996ad9af0b4ae9b2466ccb5434c31ebb54b2a2de46765976845f` |
| rules/NODE-HOMOLOGOUS-ISSUANCE-SPEC-20261107.json | 1953B | `8823a944e54f3eb71fbe84f0fc8d1edb94b0fa396ab0b5938036f94f167a85a1` |
| rules/REPORT-20261107.json | 667B | `911a2c7388a6bbe551f52db05b4bd1f6ea583371f474d10a81e1ea972ea90b16` |

## 完整性校验命令

```bash
cd /home/user/Doubao/chats/38418284746129666/ZONGYUAN-ROOT
python3 -c "
import hashlib, os
files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('LOCK-CREDENTIAL-') and not f.startswith('MANIFEST-')])
concat = ''.join(hashlib.sha256(open(f,'rb').read()).hexdigest() for f in files)
print('Merkle根:', hashlib.sha256(concat.encode()).hexdigest())
print('预期:    03eae829c19d96532b4dba7cea8013bf1c1164805dfe6ad596d7ac9232ce5bd2')
"
```

## 锁档声明

1. 本快照纳入16个资产文件，绑定DID-BR-000002确权身份。
2. Merkle根由全部文件SHA-256按文件名排序拼接后再取SHA-256生成，单文件篡改即失配。
3. 后续迭代必须生成全新快照，禁止就地改写本锁档资产。

Ω₀⊂⊙∞⊂Ω｜全域锁档完成｜ZONGYUAN-ROOT｜DID-BR-000002