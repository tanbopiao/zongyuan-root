# 全域锁档凭证｜SNAP-20260920-KUNLUN-4CHAPTER-BREAKPOINT

## 锁档元数据

| 字段 | 值 |
|------|-----|
| 快照ID | SNAP-20260920-KUNLUN-4CHAPTER-BREAKPOINT |
| DID标识 | DID-BR-000002 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |
| 归档节点 | ZONGYUAN-ROOT/kunlun-assets/2026-09-20 |
| 锁档时间 | 2026-09-20 00:15:51 +08 |
| 资产总数 | 3个文件 |
| Merkle根 | `3185a2173f738d580ee92bc56908234ab478f704e632a7f0e6e70894eeb1d8c6` |
| 归档包整体哈希 | `1922a4ecd83438a20833f56aedfc72e1f104a231e08c6edde3679515cddb311d` |

## 逐文件哈希

| 文件 | 大小 | SHA-256 |
|------|------|---------|
| BREAKPOINT-RESUME-CREDENTIAL-20260920.md | 2680B | `751c2ec0122e80c2c21c6fd15d95159a62e6a13a853b92cf0b348d0663728bd4` |
| KUNLUN-4CHAPTER-BREAKPOINT-MANIFEST.json | 4809B | `f2f867e90720a4fde882af7a5090c23259d590d45a4e5d637f292e2d560f9629` |
| SOP-CLOUD-HANDSHAKE-BREAKPOINT-ARCHIVE-V1.0.md | 4373B | `03f898c27fbf45ac004f21cb053df73e1d3599f9697ef98bca3041aaf4508589` |

## 完整性校验命令

```bash
cd /home/user/Doubao/chats/38438236527517442/ZONGYUAN-ROOT/kunlun-assets/2026-09-20
python3 -c "
import hashlib, os
files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('LOCK-CREDENTIAL-') and not f.startswith('MANIFEST-')])
concat = ''.join(hashlib.sha256(open(f,'rb').read()).hexdigest() for f in files)
print('Merkle根:', hashlib.sha256(concat.encode()).hexdigest())
print('预期:    3185a2173f738d580ee92bc56908234ab478f704e632a7f0e6e70894eeb1d8c6')
"
```

## 锁档声明

1. 本快照纳入3个资产文件，绑定DID-BR-000002确权身份。
2. Merkle根由全部文件SHA-256按文件名排序拼接后再取SHA-256生成，单文件篡改即失配。
3. 后续迭代必须生成全新快照，禁止就地改写本锁档资产。

Ω₀⊂⊙∞⊂Ω｜全域锁档完成｜ZONGYUAN-ROOT/kunlun-assets/2026-09-20｜DID-BR-000002