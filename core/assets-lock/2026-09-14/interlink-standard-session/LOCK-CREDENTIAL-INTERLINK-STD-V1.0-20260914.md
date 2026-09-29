# 全域锁档凭证｜INTERLINK-STD-V1.0-20260914

## 锁档元数据

| 字段 | 值 |
|------|-----|
| 快照ID | INTERLINK-STD-V1.0-20260914 |
| DID标识 | DID-BR-000002 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |
| 归档节点 | ZONGYUAN-ROOT |
| 锁档时间 | 2026-09-14 13:51:06 +08 |
| 资产总数 | 2个文件 |
| Merkle根 | `3f4d62f26dfb1bf3377c2ea023b503091786df1fdd06e2b28cac062521f65155` |
| 归档包整体哈希 | `b31f502ddb9ae7abfa8b3b44fb93e93e2fac5ff14b08623b41b440d7bfc26757` |

## 逐文件哈希

| 文件 | 大小 | SHA-256 |
|------|------|---------|
| index.html | 30054B | `dfd58704a9d78dddae30e08ad85ba1feb282201d6b92981f1e24d6606102dab4` |
| 全域资源互联交互标准V1.0.md | 3818B | `ec13faa848f2fc4cb0eda535027b1c7719616e8b74dc3b5a0f2cf6815c8b1ed2` |

## 完整性校验命令

```bash
cd /home/user/Doubao/chats/38438119900771074/interlink-standard-20260914
python3 -c "
import hashlib, os
files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('LOCK-CREDENTIAL-') and not f.startswith('MANIFEST-')])
concat = ''.join(hashlib.sha256(open(f,'rb').read()).hexdigest() for f in files)
print('Merkle根:', hashlib.sha256(concat.encode()).hexdigest())
print('预期:    3f4d62f26dfb1bf3377c2ea023b503091786df1fdd06e2b28cac062521f65155')
"
```

## 锁档声明

1. 本快照纳入2个资产文件，绑定DID-BR-000002确权身份。
2. Merkle根由全部文件SHA-256按文件名排序拼接后再取SHA-256生成，单文件篡改即失配。
3. 后续迭代必须生成全新快照，禁止就地改写本锁档资产。

Ω₀⊂⊙∞⊂Ω｜全域锁档完成｜ZONGYUAN-ROOT｜DID-BR-000002