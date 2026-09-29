# CLOUD-HANDSHAKE-SOP-LEARN-20260913

## 锁档元数据

| 字段 | 值 |
|------|-----|
| 快照ID | SNAP-20260913-CLOUD-HANDSHAKE |
| DID标识 | DID-BR-000002 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |
| 归档节点 | ZONGYUAN-ROOT/CLOUD-HANDSHAKE |
| 锁档时间 | 2026-09-13 18:32:14 +08 |
| 资产总数 | 3个文件 |
| Merkle根 | `f78a1f22a4d817e9a6a98693c80b1a59daec7533fd204193c326aabf9bcc037e` |
| 归档包整体哈希 | `1f686c8d87533cf0d28f7afc1b514c408b9aff428ed222dfdad034e6ca4c2cc2` |

## 逐文件哈希

| 文件 | 大小 | SHA-256 |
|------|------|---------|
| .tmp-tool-results/bash-live-1517298386.txt | 0B | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| BASELINE-ANCHOR-20260913.md | 2642B | `8f67e6db537c78b7a382a81b2d4ee43c24ee9accaddedd1aa1588215e157804c` |
| CORE-ASSET-20260913-CLOUD-HANDSHAKE.md | 2827B | `31fbc81e505a13c45b5821479fddbfd00fdf1a2dfb03aa7930ae5ccd690ca8a3` |

## 完整性校验命令

```bash
cd /home/user/Doubao/chats/38436359479937538
python3 -c "
import hashlib, os
files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('LOCK-CREDENTIAL-') and not f.startswith('MANIFEST-')])
concat = ''.join(hashlib.sha256(open(f,'rb').read()).hexdigest() for f in files)
print('Merkle根:', hashlib.sha256(concat.encode()).hexdigest())
print('预期:    f78a1f22a4d817e9a6a98693c80b1a59daec7533fd204193c326aabf9bcc037e')
"
```

## 锁档声明

1. 本快照纳入3个资产文件，绑定DID-BR-000002确权身份。
2. Merkle根由全部文件SHA-256按文件名排序拼接后再取SHA-256生成，单文件篡改即失配。
3. 后续迭代必须生成全新快照，禁止就地改写本锁档资产。

Ω₀⊂⊙∞⊂Ω｜全域锁档完成｜ZONGYUAN-ROOT/CLOUD-HANDSHAKE｜DID-BR-000002