# 沧澜镜海REALM-005核心资产+SOP学习全域锁档

## 锁档元数据

| 字段 | 值 |
|------|-----|
| 快照ID | SNAP-20260913-REALM005-CANGYANJINGHAI |
| DID标识 | DID-BR-000002 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |
| 归档节点 | ZONGYUAN-ROOT/REALM-005/CANGYAN-JINGHAI |
| 锁档时间 | 2026-09-13 18:34:02 +08 |
| 资产总数 | 7个文件 |
| Merkle根 | `11dc7247e4aca1be871e27b0015e7ddca0062fe9051b7c04ad427efc60d3a471` |
| 归档包整体哈希 | `7491ccc53649ce452b978f3104c1589cf747c1721e6927925620f6e0fefdabce` |

## 逐文件哈希

| 文件 | 大小 | SHA-256 |
|------|------|---------|
| REALM-005/REALM005-剧情帧-金涟漪.png | 1802677B | `f34d16f2266a0604acbcd85fbbc4234f2253fb90353f0da2697cd028ea1e5f19` |
| REALM-005/REALM005-升格帧-神格合一.png | 1853552B | `29cb38b2a3b47109cbe07f95b0558c4a4ae01c5d59c571399ef6eaa4d60466e6` |
| REALM-005/REALM005-封面帧-月神立镜海.png | 1226851B | `eb04224d457c77013c700e2fab02b4ab13254f2a767bf115dff0f85c5cf92f99` |
| REALM-005/REALM005-爆点帧-月神玄鸟双显.png | 1062038B | `2790d0242decd7e1b0d12a481dfc3de1f7c474cd96257033f05fb9176097b81c` |
| SOP-DOCS/BASELINE-ANCHOR-20260913.md | 297B | `b438469b31d703c0ae3f61a1b753e2e9c42713bc850dc041550867a2d5e76102` |
| SOP-DOCS/HANDSHAKE-SOP-V1.0.md | 397B | `be1f1f71c38526aec6aff2bc7c87db5d48c35444b3f666aee871796d2ca5810c` |
| SOP-DOCS/NODE-ONBOARDING-SOP-v1.1.md | 337B | `e4d3a5849f52da87d7c086f07a0aa411165a0b0f8e96fe9e2c3c7dffd48ca7e3` |

## 完整性校验命令

```bash
cd /home/user/Doubao/chats/38436374678573314/CORE-ASSETS
python3 -c "
import hashlib, os
files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('LOCK-CREDENTIAL-') and not f.startswith('MANIFEST-')])
concat = ''.join(hashlib.sha256(open(f,'rb').read()).hexdigest() for f in files)
print('Merkle根:', hashlib.sha256(concat.encode()).hexdigest())
print('预期:    11dc7247e4aca1be871e27b0015e7ddca0062fe9051b7c04ad427efc60d3a471')
"
```

## 锁档声明

1. 本快照纳入7个资产文件，绑定DID-BR-000002确权身份。
2. Merkle根由全部文件SHA-256按文件名排序拼接后再取SHA-256生成，单文件篡改即失配。
3. 后续迭代必须生成全新快照，禁止就地改写本锁档资产。

Ω₀⊂⊙∞⊂Ω｜全域锁档完成｜ZONGYUAN-ROOT/REALM-005/CANGYAN-JINGHAI｜DID-BR-000002