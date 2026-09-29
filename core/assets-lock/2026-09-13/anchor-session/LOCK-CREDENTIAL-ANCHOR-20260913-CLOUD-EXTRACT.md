# 云端握手锚点SOP基准锚定

## 锁档元数据

| 字段 | 值 |
|------|-----|
| 快照ID | ANCHOR-20260913-CLOUD-EXTRACT |
| DID标识 | DID-BR-000002 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |
| 归档节点 | ZONGYUAN-ROOT/CloudHandshake |
| 锁档时间 | 2026-09-13 17:56:45 +08 |
| 资产总数 | 2个文件 |
| Merkle根 | `532f93187522ca0d1442b80bf22c50477976dfc8253731b8ae7d5899828126b1` |
| 归档包整体哈希 | `447258012e1155c53b9d2b2f321a7242b70e560ae6f5570058b8bf79f9438c7e` |

## 逐文件哈希

| 文件 | 大小 | SHA-256 |
|------|------|---------|
| BASELINE-ANCHOR-20260913.md | 2642B | `8f67e6db537c78b7a382a81b2d4ee43c24ee9accaddedd1aa1588215e157804c` |
| orig-anchor.md | 2642B | `8f67e6db537c78b7a382a81b2d4ee43c24ee9accaddedd1aa1588215e157804c` |

## 完整性校验命令

```bash
cd /home/user/Doubao/chats/38438119900771074/anchor-20260913
python3 -c "
import hashlib, os
files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('LOCK-CREDENTIAL-') and not f.startswith('MANIFEST-')])
concat = ''.join(hashlib.sha256(open(f,'rb').read()).hexdigest() for f in files)
print('Merkle根:', hashlib.sha256(concat.encode()).hexdigest())
print('预期:    532f93187522ca0d1442b80bf22c50477976dfc8253731b8ae7d5899828126b1')
"
```

## 锁档声明

1. 本快照纳入2个资产文件，绑定DID-BR-000002确权身份。
2. Merkle根由全部文件SHA-256按文件名排序拼接后再取SHA-256生成，单文件篡改即失配。
3. 后续迭代必须生成全新快照，禁止就地改写本锁档资产。

Ω₀⊂⊙∞⊂Ω｜全域锁档完成｜ZONGYUAN-ROOT/CloudHandshake｜DID-BR-000002