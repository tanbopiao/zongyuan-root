# 全域锁档凭证｜INTERLINK-STD-V1.0-APPROVED-20260914

## 锁档元数据

| 字段 | 值 |
|------|-----|
| 快照ID | INTERLINK-STD-V1.0-APPROVED-20260914 |
| DID标识 | DID-BR-000002 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |
| 归档节点 | ZONGYUAN-ROOT |
| 锁档时间 | 2026-09-14 15:10:36 +08 |
| 资产总数 | 3个文件 |
| Merkle根 | `577e3d5a441ae66e358c76c410d682c1e2d3a3c1ebccc4af93421ee434ff061c` |
| 归档包整体哈希 | `36c9effc438b1102e4e8848dd4bac280283c119163c230354a4eb5834da60fd6` |

## 逐文件哈希

| 文件 | 大小 | SHA-256 |
|------|------|---------|
| APPROVED-20260914.md | 1110B | `a1c60790e1fdf3e3edb12fbcfe256bfc16668436f9d8981ed2bf79203904de13` |
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
print('预期:    577e3d5a441ae66e358c76c410d682c1e2d3a3c1ebccc4af93421ee434ff061c')
"
```

## 锁档声明

1. 本快照纳入3个资产文件，绑定DID-BR-000002确权身份。
2. Merkle根由全部文件SHA-256按文件名排序拼接后再取SHA-256生成，单文件篡改即失配。
3. 后续迭代必须生成全新快照，禁止就地改写本锁档资产。

Ω₀⊂⊙∞⊂Ω｜全域锁档完成｜ZONGYUAN-ROOT｜DID-BR-000002