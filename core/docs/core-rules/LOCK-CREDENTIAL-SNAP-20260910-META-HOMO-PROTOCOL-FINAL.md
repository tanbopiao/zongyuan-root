# 元极恒一同源协议全域锁档

## 锁档元数据

| 字段 | 值 |
|------|-----|
| 快照ID | SNAP-20260910-META-HOMO-PROTOCOL-FINAL |
| DID标识 | DID-BR-000002 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |
| 归档节点 | ZONGYUAN-ROOT/MetaHomoProtocol |
| 锁档时间 | 2026-09-10 08:02:21 +08 |
| 资产总数 | 2个文件 |
| Merkle根 | `abe4679f3475b317fc2ad14b2a32b66ca44b3cd1cfa154b8a879a9e31092abda` |
| 归档包整体哈希 | `de180e5b5a0bb86ac14daa9f4d773296c2288dde2d62cf895c130e9e2f0e0f4f` |

## 逐文件哈希

| 文件 | 大小 | SHA-256 |
|------|------|---------|
| component-truth-summary.md | 2059B | `018651712ce061f96d4e15cbdd2b301cef921602fda922e6579edca7af88ee85` |
| meta_homo_protocol.json | 3813B | `a797740771a83f60bf899c16c8ed60406058581c6a5aaa6d2b08e16e3fb3e740` |

## 完整性校验命令

```bash
cd /home/user/Doubao/chats/38418284746129666/lock-assets/SNAP-20260910-META-HOMO-PROTOCOL-FINAL
python3 -c "
import hashlib, os
files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('LOCK-CREDENTIAL-') and not f.startswith('MANIFEST-')])
concat = ''.join(hashlib.sha256(open(f,'rb').read()).hexdigest() for f in files)
print('Merkle根:', hashlib.sha256(concat.encode()).hexdigest())
print('预期:    abe4679f3475b317fc2ad14b2a32b66ca44b3cd1cfa154b8a879a9e31092abda')
"
```

## 锁档声明

1. 本快照纳入2个资产文件，绑定DID-BR-000002确权身份。
2. Merkle根由全部文件SHA-256按文件名排序拼接后再取SHA-256生成，单文件篡改即失配。
3. 后续迭代必须生成全新快照，禁止就地改写本锁档资产。

Ω₀⊂⊙∞⊂Ω｜全域锁档完成｜ZONGYUAN-ROOT/MetaHomoProtocol｜DID-BR-000002