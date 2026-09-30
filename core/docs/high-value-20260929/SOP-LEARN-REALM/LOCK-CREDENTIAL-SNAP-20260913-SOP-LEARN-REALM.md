# 全域锁档凭证｜SNAP-20260913-SOP-LEARN-REALM

## 锁档元数据

| 字段 | 值 |
|------|-----|
| 快照ID | SNAP-20260913-SOP-LEARN-REALM |
| DID标识 | DID-BR-000002 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |
| 归档节点 | ZONGYUAN-ROOT |
| 锁档时间 | 2026-09-13 18:39:17 +08 |
| 资产总数 | 17个文件 |
| Merkle根 | `3af5a98b5dfb8ededc8acbf6d6815399d38e8c538fefcc34c03d1cb03265c2be` |
| 归档包整体哈希 | `6de1db12a4ce8fad2094590264212192640911fd127b86296c0a86d2ec4e8d6a` |

## 逐文件哈希

| 文件 | 大小 | SHA-256 |
|------|------|---------|
| .did_keys/did_br_000002_private.pem | 119B | `d02b52715271cd863f2f8cb5851ce574edd7c74cdd2d6e46bc78f81ff123aae9` |
| .did_keys/did_br_000002_public.pem | 113B | `64fa9bff41374886642b3a1d9eab68c3320dcb0e71a9b7f5d667cf57cfc9e1ba` |
| .healing_backups/kernel-1789295693.json.bak | 1579B | `8a637e2282b2c3796fbf6babb0675d4390516559a7a19354578513632ff3aaa4` |
| .healing_logs/DECISION-AUDIT-PIPELINE-SNAP-20260913-SOP-LEARN-REALM.json | 1325B | `0dd3dca38e06340a0acf1ff9a9f044fc56f6a09c735bb96a355b7569f70e6b95` |
| ATTESTATION-SNAP-20260913-SOP-LEARN-REALM.json | 710B | `bd57bedac2d252625b75dd9b28c7b4d10f9ce1f7140bf4fa51850cfca1ced213` |
| BASELINE-ANCHOR-20260913.md | 2642B | `8f67e6db537c78b7a382a81b2d4ee43c24ee9accaddedd1aa1588215e157804c` |
| CORE-ASSET-20260913-SOP-LEARN-REALM.md | 2659B | `baeac63048f836537f7118a33206a374e5b1721dbad5a746d5aec0595bc9fe92` |
| HANDSHAKE-SOP-V1.0.md | 4925B | `956e0dca7a750a59e5f3826d6f1042e10e55431cbc6d3d5f508368a780c03666` |
| KERNEL-LEARNING-PACK-V2.md | 7121B | `5875952c27c8f7c7a71ce00a22607c0effcdad48cdb4999e194205007ebc0096` |
| KF-REALM002-cGJGsrUTxR.jpg | 1414183B | `c8a5c4a41496ea3b2834306b1ff197b5a07f3a390aad7b254f2ce5be32855520` |
| KF-REALM002-n0OoOgx9AY.jpg | 1722796B | `c5071a9e7d25e3c25c22cc388c6100e496fcf2321fd53ff35afac43b4afd6c25` |
| KF-REALM002-rlsiKl5vHK.jpg | 1971867B | `ad16a57e75b72a673cba3104233f681a24c9baf1edc49c3d0890f68d73ca50a4` |
| LV5-COGNITION-1789295693.json | 1197B | `fbefa1e706f970d042004cf5e9a94fca8d892bfbe2ca4ad291a294ef4098a865` |
| LV6-CIVILIZATION-1789295694.json | 5519B | `7852e1fecce3b4073cab20ad57cd3491ce4a9a3745551d438d9af3483a00f08b` |
| NODE-ONBOARDING-SOP-V1.1.md | 7003B | `1989600f60f1a90a01c27c0a2aaa09b8322fb49c994dd37ac93d0038de56d0a0` |
| PIPELINE-SUMMARY-SNAP-20260913-SOP-LEARN-REALM.json | 1355B | `c943dee18d964dab2d24746788ff761acda57cf096c395dd75870c659e7b0129` |
| efuse_chain.json | 808B | `b348537b962d5448ad87c3e5e0aa480d9f3a19a5fc00918bcc40daeb62788eeb` |

## 完整性校验命令

```bash
cd /home/user/Doubao/chats/38436374788512002/REALM-CORE-ASSETS
python3 -c "
import hashlib, os
files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('LOCK-CREDENTIAL-') and not f.startswith('MANIFEST-')])
concat = ''.join(hashlib.sha256(open(f,'rb').read()).hexdigest() for f in files)
print('Merkle根:', hashlib.sha256(concat.encode()).hexdigest())
print('预期:    3af5a98b5dfb8ededc8acbf6d6815399d38e8c538fefcc34c03d1cb03265c2be')
"
```

## 锁档声明

1. 本快照纳入17个资产文件，绑定DID-BR-000002确权身份。
2. Merkle根由全部文件SHA-256按文件名排序拼接后再取SHA-256生成，单文件篡改即失配。
3. 后续迭代必须生成全新快照，禁止就地改写本锁档资产。

Ω₀⊂⊙∞⊂Ω｜全域锁档完成｜ZONGYUAN-ROOT｜DID-BR-000002