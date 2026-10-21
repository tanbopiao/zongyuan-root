# 全域锁档凭证｜SNAP-20260907-SESSION-ASSETS

## 锁档元数据

| 字段 | 值 |
|------|-----|
| 快照ID | SNAP-20260907-SESSION-ASSETS |
| DID标识 | DID-BR-000002 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |
| 归档节点 | ZONGYUAN-ROOT |
| 锁档时间 | 2026-09-07 14:36:34 +08 |
| 资产总数 | 7个文件 |
| Merkle根 | `69d71f09b593462d0ba96fc3321232c699180c783579131ecd93b202d8a054da` |
| 归档包整体哈希 | `73813ee8aea9f5ab83fc27cd46d8a6ad6537a1742b08b2e0bd872682587b2e14` |

## 逐文件哈希

| 文件 | 大小 | SHA-256 |
|------|------|---------|
| .did_keys/did_br_000002_private.pem | 119B | `48448b0b0bc082e5f30ddf30cf26e7cb5e7390d2cbb92fd89093ff3f4a7af04a` |
| .did_keys/did_br_000002_public.pem | 113B | `0d290cd84a5c349495d5f36bcace168a8b4aa7b86f9504f7ca940c1a9eef530e` |
| ARCHITECTURE_TRUTH.md | 1428B | `73347c3d7e213814ddaa42dd570ad68975eae8eef5983e79cfe3c69aafdf12e8` |
| ASSET_MANIFEST.md | 2310B | `ff63e8bb739934894707e673655e8f13ab5b6b5fe0f8952c83dfe237f0075e8c` |
| ATTESTATION-SNAP-20260907-SESSION-ASSETS.json | 692B | `c1b8afb288f083614920973e1b2d7cc03a7b70c71c0ae00400f7f01f74fb486b` |
| PIPELINE-SUMMARY-SNAP-20260907-SESSION-ASSETS.json | 1312B | `c759093e3a3567c22cd80982d756c228cab982b861d8d736332bb3a5bf87dda1` |
| efuse_chain.json | 805B | `f803f06d29c32f4dbc83e84ad1a6d396d77508b04aa5f99195151d7b73efe7e7` |

## 完整性校验命令

```bash
cd /home/user/.doubao/agent_mode/workspace/ZONGYUAN-ROOT/snapshots/SNAP-20260907-SESSION-ASSETS
python3 -c "
import hashlib, os
files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('LOCK-CREDENTIAL-') and not f.startswith('MANIFEST-')])
concat = ''.join(hashlib.sha256(open(f,'rb').read()).hexdigest() for f in files)
print('Merkle根:', hashlib.sha256(concat.encode()).hexdigest())
print('预期:    69d71f09b593462d0ba96fc3321232c699180c783579131ecd93b202d8a054da')
"
```

## 锁档声明

1. 本快照纳入7个资产文件，绑定DID-BR-000002确权身份。
2. Merkle根由全部文件SHA-256按文件名排序拼接后再取SHA-256生成，单文件篡改即失配。
3. 后续迭代必须生成全新快照，禁止就地改写本锁档资产。

Ω₀⊂⊙∞⊂Ω｜全域锁档完成｜ZONGYUAN-ROOT｜DID-BR-000002