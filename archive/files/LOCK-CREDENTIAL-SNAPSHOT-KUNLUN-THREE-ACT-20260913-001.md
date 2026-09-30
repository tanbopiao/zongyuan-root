# 昆仑洞天·女帝三幕关键帧核心资产全域锁档

## 锁档元数据

| 字段 | 值 |
|------|-----|
| 快照ID | SNAPSHOT-KUNLUN-THREE-ACT-20260913-001 |
| DID标识 | DID-BR-000002 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |
| 归档节点 | ZONGYUAN-ROOT/KUNLUN-THREE-ACT |
| 锁档时间 | 2026-09-13 18:33:56 +08 |
| 资产总数 | 14个文件 |
| Merkle根 | `fe4a01a1d0086fd5f967b96497a6f93ae2c5f8c5a195d5aef95874939f79968c` |
| 归档包整体哈希 | `8271f11271bb024ecd65ef056dd71ea6cc5e1e64edf00bdd954573f6d348548f` |

## 逐文件哈希

| 文件 | 大小 | SHA-256 |
|------|------|---------|
| kunlun-three-act-manifest.json | 4366B | `4a0627ecdac104500866de21f905bcbc1a2e5d9e3277f13a420a0b43004cc71a` |
| kunlun_empress_destiny_keyframe_01.png | 1966328B | `bb712aae0d382432e541697b3774c883c4f0caeeee99e5fb73945eda42827be5` |
| kunlun_empress_destiny_keyframe_02.png | 1934837B | `67649653a2a2c4711dbf51ec1ca9187d8b0ae6f6312b477099a3e2b791a7d3ed` |
| kunlun_empress_destiny_keyframe_03.png | 2251945B | `67ec8466eea589efe15742b2ea10cbc1c7f34403e83d4951d68c1de6e22b36fc` |
| kunlun_empress_destiny_keyframe_04.png | 2270009B | `101e2b33a6f1893bcc09bb4bf3d2b280b5788171f6b64ae0338882722ec4235a` |
| kunlun_empress_gate_optimized_01.png | 1970005B | `1eca2cff446b8c122ba1ee01ffc0d3e9a6764e7817453a86e1b35be091cdf1d6` |
| kunlun_empress_gate_optimized_02.png | 1745933B | `a8bff65a3ad218429161f6d3f85a2679e6ee94cb533192013d9df542aa7a501c` |
| kunlun_empress_gate_optimized_03.png | 2055850B | `89097d2aa11048cf4d508e154a9f74996d3f57896c9304f8eb09a9518dbc4e76` |
| kunlun_empress_gate_optimized_04.png | 1894149B | `44ade055e12bf5dc41250ff4b94d026e8c10f7154acece48b31e8a3a8760c2bf` |
| kunlun_empress_jingutai_clean_keyframe_01.png | 1712845B | `3a435e86d71e726694db35bc40a602092faa486bed63b1de20ee355ca282eb2d` |
| kunlun_empress_jingutai_clean_keyframe_02.png | 1632067B | `8e3989e04d18528b32a071c87899feaec9e02491047f10fa9b289163604f10ad` |
| kunlun_empress_jingutai_clean_keyframe_03.png | 1864543B | `e8f360f4f137093d345db3f4e36468ce447e17acac36d42788f877c5e6ef9948` |
| kunlun_empress_jingutai_clean_keyframe_04.png | 1735559B | `f4e732b786ecc1d3b7d9e8375673666b68eb997ca10181314878597ff0a856a0` |
| kunlun_empress_keyframes_overview_01.png | 2678823B | `986600838d284a6a09c3049f2d3da3051bccfbd6591c44decdfaa42a148f4e2e` |

## 完整性校验命令

```bash
cd /home/user/kunlun-assets/2026-09-13/kunlun-empress-three-act
python3 -c "
import hashlib, os
files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('LOCK-CREDENTIAL-') and not f.startswith('MANIFEST-')])
concat = ''.join(hashlib.sha256(open(f,'rb').read()).hexdigest() for f in files)
print('Merkle根:', hashlib.sha256(concat.encode()).hexdigest())
print('预期:    fe4a01a1d0086fd5f967b96497a6f93ae2c5f8c5a195d5aef95874939f79968c')
"
```

## 锁档声明

1. 本快照纳入14个资产文件，绑定DID-BR-000002确权身份。
2. Merkle根由全部文件SHA-256按文件名排序拼接后再取SHA-256生成，单文件篡改即失配。
3. 后续迭代必须生成全新快照，禁止就地改写本锁档资产。

Ω₀⊂⊙∞⊂Ω｜全域锁档完成｜ZONGYUAN-ROOT/KUNLUN-THREE-ACT｜DID-BR-000002