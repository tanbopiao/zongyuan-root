# 全域锁档凭证｜SNAP-CONVERGE-ALL-ROOTS-20260922

## 锁档元数据

| 字段 | 值 |
|------|-----|
| 快照ID | SNAP-CONVERGE-ALL-ROOTS-20260922 |
| DID标识 | DID-BR-000002 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |
| 归档节点 | ZONGYUAN-ROOT |
| 锁档时间 | 2026-09-22 01:05:42 +08 |
| 资产总数 | 0个文件 |
| Merkle根 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 归档包整体哈希 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## 逐文件哈希

| 文件 | 大小 | SHA-256 |
|------|------|---------|

## 完整性校验命令

```bash
cd /home/user/ZONGYUAN-ROOT/00-ROOT
python3 -c "
import hashlib, os
files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('LOCK-CREDENTIAL-') and not f.startswith('MANIFEST-')])
concat = ''.join(hashlib.sha256(open(f,'rb').read()).hexdigest() for f in files)
print('Merkle根:', hashlib.sha256(concat.encode()).hexdigest())
print('预期:    e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
"
```

## 锁档声明

1. 本快照纳入0个资产文件，绑定DID-BR-000002确权身份。
2. Merkle根由全部文件SHA-256按文件名排序拼接后再取SHA-256生成，单文件篡改即失配。
3. 后续迭代必须生成全新快照，禁止就地改写本锁档资产。

Ω₀⊂⊙∞⊂Ω｜全域锁档完成｜ZONGYUAN-ROOT｜DID-BR-000002